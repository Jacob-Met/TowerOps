from __future__ import annotations

import hashlib
import json
import math
from fractions import Fraction
from dataclasses import asdict, dataclass, replace
from typing import Any, Iterable

ZERO_HASH = "0" * 64


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_obj(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _finite_time(value: Any) -> bool:
    return type(value) is int or (type(value) is float and math.isfinite(value))


class GateRejected(RuntimeError):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class Aircraft:
    aircraft_id: str
    x_nm: float
    y_nm: float
    altitude_ft: float
    vx_nm_min: float
    vy_nm_min: float
    climb_ft_min: float = 0.0

    def projected(self, minutes: float) -> "Aircraft":
        return replace(
            self,
            x_nm=self.x_nm + self.vx_nm_min * minutes,
            y_nm=self.y_nm + self.vy_nm_min * minutes,
            altitude_ft=self.altitude_ft + self.climb_ft_min * minutes,
        )


@dataclass(frozen=True)
class WorldState:
    version: int
    observed_at: float
    aircraft: tuple[Aircraft, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "observed_at": self.observed_at,
            "aircraft": [asdict(a) for a in sorted(self.aircraft, key=lambda x: x.aircraft_id)],
        }

    @property
    def world_hash(self) -> str:
        return sha256_obj(self.to_dict())

    def get(self, aircraft_id: str) -> Aircraft:
        for aircraft in self.aircraft:
            if aircraft.aircraft_id == aircraft_id:
                return aircraft
        raise KeyError(aircraft_id)

    def replace_aircraft(self, updated: Aircraft, observed_at: float) -> "WorldState":
        values = tuple(updated if a.aircraft_id == updated.aircraft_id else a for a in self.aircraft)
        return WorldState(version=self.version + 1, observed_at=observed_at, aircraft=values)


@dataclass(frozen=True)
class Advisory:
    aircraft_id: str
    world_hash: str
    set_vx_nm_min: float
    set_vy_nm_min: float
    set_climb_ft_min: float
    issued_at: float
    expires_at: float
    rationale: str

    @property
    def advisory_hash(self) -> str:
        return sha256_obj(asdict(self))


@dataclass(frozen=True)
class Approval:
    advisory_hash: str
    decision: str
    approved_at: float
    approver: str


@dataclass(frozen=True)
class Ack:
    advisory_hash: str
    status: str
    acknowledged_at: float


class AuditLog:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def append(self, kind: str, payload: dict[str, Any]) -> str:
        prev = self.events[-1]["event_hash"] if self.events else ZERO_HASH
        event = {"seq": len(self.events), "kind": kind, "payload": payload, "prev_hash": prev}
        event_hash = hashlib.sha256(prev.encode("ascii") + b"\n" + canonical_bytes(event)).hexdigest()
        event["event_hash"] = event_hash
        self.events.append(event)
        return event_hash

    @property
    def head(self) -> str:
        return self.events[-1]["event_hash"] if self.events else ZERO_HASH

    @staticmethod
    def verify(events: Iterable[dict[str, Any]]) -> bool:
        prev = ZERO_HASH
        for expected_seq, raw in enumerate(events):
            event = dict(raw)
            claimed = event.pop("event_hash", None)
            if event.get("seq") != expected_seq or event.get("prev_hash") != prev:
                return False
            actual = hashlib.sha256(prev.encode("ascii") + b"\n" + canonical_bytes(event)).hexdigest()
            if claimed != actual:
                return False
            prev = actual
        return True


@dataclass(frozen=True)
class SafetyPolicy:
    min_horizontal_nm: float = 5.0
    min_vertical_ft: float = 1000.0
    horizon_min: float = 5.0
    sample_step_min: float = 0.5
    max_state_age_sec: float = 10.0
    max_speed_nm_min: float = 6.0
    max_climb_ft_min: float = 3000.0

    @staticmethod
    def _linear_abs_unsafe_interval(offset: float, rate: float, limit: float, horizon: float) -> tuple[float, float] | None:
        """Open time interval in [0,horizon] where abs(offset + rate*t) < limit."""
        if limit <= 0.0 or horizon < 0.0:
            return None
        if rate == 0.0:
            return (0.0, horizon) if abs(offset) < limit else None
        t1, t2 = (-limit - offset) / rate, (limit - offset) / rate
        lo, hi = sorted((t1, t2))
        lo, hi = max(0.0, lo), min(horizon, hi)
        return (lo, hi) if lo < hi else None

    @staticmethod
    def _horizontal_unsafe_interval(dx: float, dy: float, dvx: float, dvy: float, limit: float, horizon: float) -> tuple[float, float] | None:
        """Open time interval in [0,horizon] where horizontal separation is below limit."""
        if limit <= 0.0 or horizon < 0.0:
            return None
        a = dvx * dvx + dvy * dvy
        b = 2.0 * (dx * dvx + dy * dvy)
        c = dx * dx + dy * dy - limit * limit
        if a == 0.0:
            return (0.0, horizon) if c < 0.0 else None
        disc = b * b - 4.0 * a * c
        if disc <= 0.0:
            return None
        root = math.sqrt(disc)
        lo, hi = sorted(((-b - root) / (2.0 * a), (-b + root) / (2.0 * a)))
        lo, hi = max(0.0, lo), min(horizon, hi)
        return (lo, hi) if lo < hi else None

    def _pair_conflict(self, a: Aircraft, b: Aircraft) -> bool:
        h = self._horizontal_unsafe_interval(
            a.x_nm - b.x_nm, a.y_nm - b.y_nm,
            a.vx_nm_min - b.vx_nm_min, a.vy_nm_min - b.vy_nm_min,
            self.min_horizontal_nm, self.horizon_min,
        )
        if h is None:
            return False
        v = self._linear_abs_unsafe_interval(
            a.altitude_ft - b.altitude_ft, a.climb_ft_min - b.climb_ft_min,
            self.min_vertical_ft, self.horizon_min,
        )
        if v is None:
            return False
        return max(h[0], v[0]) < min(h[1], v[1])

    def state_has_conflict(self, state: WorldState) -> bool:
        values = list(state.aircraft)
        return any(self._pair_conflict(values[i], values[j]) for i in range(len(values)) for j in range(i + 1, len(values)))

    def advisory_safe(self, state: WorldState, advisory: Advisory) -> bool:
        if advisory.world_hash != state.world_hash:
            return False
        if math.hypot(advisory.set_vx_nm_min, advisory.set_vy_nm_min) > self.max_speed_nm_min:
            return False
        if abs(advisory.set_climb_ft_min) > self.max_climb_ft_min:
            return False
        try:
            target = state.get(advisory.aircraft_id)
        except KeyError:
            return False
        candidate = replace(target, vx_nm_min=advisory.set_vx_nm_min, vy_nm_min=advisory.set_vy_nm_min, climb_ft_min=advisory.set_climb_ft_min)
        return all(not self._pair_conflict(candidate, other) for other in state.aircraft if other.aircraft_id != candidate.aircraft_id)


class AdvisoryPlanner:
    """Deterministic synthetic planner; model adapters may propose alternatives, never bypass the frozen gate."""

    def __init__(self, policy: SafetyPolicy) -> None:
        self.policy = policy

    def plan(self, state: WorldState, now: float) -> list[Advisory]:
        if not self.policy.state_has_conflict(state):
            return []
        values = sorted(state.aircraft, key=lambda x: x.aircraft_id)
        target = values[-1]
        for vy in [2.0, -2.0, 3.0, -3.0, 0.0]:
            advisory = Advisory(
                aircraft_id=target.aircraft_id,
                world_hash=state.world_hash,
                set_vx_nm_min=target.vx_nm_min,
                set_vy_nm_min=vy,
                set_climb_ft_min=target.climb_ft_min,
                issued_at=now,
                expires_at=now + 8.0,
                rationale="synthetic projected-separation recovery",
            )
            if self.policy.advisory_safe(state, advisory):
                return [advisory]
        return []


class ControlRoom:
    def __init__(self, policy: SafetyPolicy | None = None) -> None:
        self.policy = policy or SafetyPolicy()
        self.audit = AuditLog()

    def _fresh(self, state: WorldState, now: float) -> None:
        if not _finite_time(state.observed_at) or not _finite_time(now):
            self.audit.append("reject", {"reason": "invalid_state_time"})
            raise GateRejected("invalid_state_time")
        if state.observed_at > now:
            self.audit.append("reject", {"reason": "future_state", "world_hash": state.world_hash})
            raise GateRejected("future_state")
        if type(now) is int or type(state.observed_at) is int:
            age = Fraction(now) - Fraction(state.observed_at)
        else:
            age = now - state.observed_at
        if age > self.policy.max_state_age_sec:
            self.audit.append("reject", {"reason": "stale_state", "world_hash": state.world_hash})
            raise GateRejected("stale_state")

    def screen_batch(self, state: WorldState, advisories: list[Advisory], now: float) -> list[str]:
        self._fresh(state, now)
        by_aircraft: dict[str, set[str]] = {}
        for advisory in advisories:
            by_aircraft.setdefault(advisory.aircraft_id, set()).add(advisory.advisory_hash)
        if any(len(hashes) > 1 for hashes in by_aircraft.values()):
            self.audit.append("reject", {"reason": "conflicting_recommendations", "world_hash": state.world_hash})
            raise GateRejected("conflicting_recommendations")
        hashes: list[str] = []
        for advisory in advisories:
            if not _finite_time(advisory.issued_at) or not _finite_time(advisory.expires_at):
                self.audit.append("reject", {"reason": "invalid_advisory_time", "aircraft_id": advisory.aircraft_id})
                raise GateRejected("invalid_advisory_time")
            if advisory.issued_at < state.observed_at or advisory.issued_at > now or advisory.expires_at < advisory.issued_at:
                self.audit.append("reject", {"reason": "invalid_advisory_time", "advisory_hash": advisory.advisory_hash})
                raise GateRejected("invalid_advisory_time")
            if advisory.world_hash != state.world_hash:
                self.audit.append("reject", {"reason": "world_hash_mismatch", "advisory_hash": advisory.advisory_hash})
                raise GateRejected("world_hash_mismatch")
            if now > advisory.expires_at:
                self.audit.append("reject", {"reason": "expired_advisory", "advisory_hash": advisory.advisory_hash})
                raise GateRejected("expired_advisory")
            if not self.policy.advisory_safe(state, advisory):
                self.audit.append("reject", {"reason": "unsafe_advisory", "advisory_hash": advisory.advisory_hash})
                raise GateRejected("unsafe_advisory")
            hashes.append(advisory.advisory_hash)
        self.audit.append("screen_pass", {"world_hash": state.world_hash, "advisory_hashes": hashes})
        return hashes

    def apply(self, state: WorldState, advisory: Advisory, approval: Approval | None, ack: Ack | None, now: float) -> WorldState:
        self.screen_batch(state, [advisory], now)
        if approval is None or approval.advisory_hash != advisory.advisory_hash or approval.decision != "approve":
            self.audit.append("reject", {"reason": "human_approval_required", "advisory_hash": advisory.advisory_hash})
            raise GateRejected("human_approval_required")
        if not _finite_time(approval.approved_at):
            self.audit.append("reject", {"reason": "invalid_approval_time", "advisory_hash": advisory.advisory_hash})
            raise GateRejected("invalid_approval_time")
        if approval.approved_at < advisory.issued_at or approval.approved_at > advisory.expires_at or approval.approved_at > now:
            self.audit.append("reject", {"reason": "invalid_approval_time", "advisory_hash": advisory.advisory_hash})
            raise GateRejected("invalid_approval_time")
        self.audit.append("approval", asdict(approval))
        if ack is None:
            self.audit.append("reject", {"reason": "ack_missing", "advisory_hash": advisory.advisory_hash})
            raise GateRejected("ack_missing")
        if ack.advisory_hash != advisory.advisory_hash or ack.status != "accepted":
            self.audit.append("reject", {"reason": "ack_invalid", "advisory_hash": advisory.advisory_hash})
            raise GateRejected("ack_invalid")
        if not _finite_time(ack.acknowledged_at):
            self.audit.append("reject", {"reason": "invalid_ack_time", "advisory_hash": advisory.advisory_hash})
            raise GateRejected("invalid_ack_time")
        if ack.acknowledged_at < approval.approved_at or ack.acknowledged_at < advisory.issued_at:
            self.audit.append("reject", {"reason": "invalid_ack_time", "advisory_hash": advisory.advisory_hash})
            raise GateRejected("invalid_ack_time")
        if ack.acknowledged_at > advisory.expires_at or ack.acknowledged_at > now:
            self.audit.append("reject", {"reason": "ack_late", "advisory_hash": advisory.advisory_hash})
            raise GateRejected("ack_late")
        self.audit.append("ack", asdict(ack))
        target = state.get(advisory.aircraft_id)
        updated = replace(target, vx_nm_min=advisory.set_vx_nm_min, vy_nm_min=advisory.set_vy_nm_min, climb_ft_min=advisory.set_climb_ft_min)
        new_state = state.replace_aircraft(updated, observed_at=now)
        self.audit.append("simulated_actuation", {
            "advisory_hash": advisory.advisory_hash,
            "before_world_hash": state.world_hash,
            "after_world_hash": new_state.world_hash,
        })
        return new_state


def baseline_apply_unchecked(state: WorldState, advisory: Advisory, now: float) -> WorldState:
    target = state.get(advisory.aircraft_id)
    updated = replace(target, vx_nm_min=advisory.set_vx_nm_min, vy_nm_min=advisory.set_vy_nm_min, climb_ft_min=advisory.set_climb_ft_min)
    return state.replace_aircraft(updated, observed_at=now)
