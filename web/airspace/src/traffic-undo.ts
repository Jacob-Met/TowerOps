import { SafetyPolicy, WorldState, canonicalJson } from './core';

export interface TrafficUndoContext {
  state: WorldState;
  policy: SafetyPolicy;
  now: number;
  // A new scenario may contain identical values. Its lifetime still ends Undo.
  scenario: object;
}

export interface TrafficEditSnapshot {
  readonly state: WorldState;
  readonly selected: string;
  readonly key: string;
  readonly policy_clock_key: string;
  readonly scenario: object;
}

interface UndoEntry {
  label: string;
  before: TrafficEditSnapshot;
  after_key: string;
}

const copyWorld = (state: WorldState): WorldState => ({
  ...state, aircraft: state.aircraft.map(aircraft => ({ ...aircraft })),
});

function contextKey(context: TrafficUndoContext): string | null {
  if (!Number.isSafeInteger(context.state.version) || context.state.version < 0 ||
      !Number.isFinite(context.now)) return null;
  try {
    return canonicalJson({ state: context.state, policy: context.policy, now: context.now });
  } catch {
    return null;
  }
}

/** One authored edit, available only in the exact context it produced. */
export class TrafficEditUndo {
  private entry: UndoEntry | null = null;

  clear(): void {
    this.entry = null;
  }

  private current(context: TrafficUndoContext): UndoEntry | null {
    if (this.entry && (
      this.entry.before.scenario !== context.scenario ||
      this.entry.after_key !== contextKey(context) ||
      context.state.version >= Number.MAX_SAFE_INTEGER
    )) this.clear();
    return this.entry;
  }

  label(context: TrafficUndoContext): string | null {
    return this.current(context)?.label ?? null;
  }

  capture(context: TrafficUndoContext, selected: string): TrafficEditSnapshot | null {
    this.current(context);
    const key = contextKey(context);
    if (!key || !context.state.aircraft.some(aircraft => aircraft.aircraft_id === selected)) return null;
    const state = copyWorld(context.state);
    for (const aircraft of state.aircraft) Object.freeze(aircraft);
    Object.freeze(state.aircraft);
    Object.freeze(state);
    return Object.freeze({
      state, selected, key, scenario: context.scenario,
      policy_clock_key: canonicalJson({ policy: context.policy, now: context.now }),
    });
  }

  record(label: string, before: TrafficEditSnapshot | null, after: TrafficUndoContext): boolean {
    this.current(after);
    const afterKey = contextKey(after);
    if (!before || !afterKey) {
      this.clear();
      return false;
    }
    // A refused or unchanged action keeps an earlier applicable edit.
    if (before.scenario === after.scenario && before.key === afterKey) return false;
    // A context replacement or revision-only change is not an authored traffic edit.
    if (before.scenario !== after.scenario ||
        before.policy_clock_key !== canonicalJson({ policy: after.policy, now: after.now }) ||
        after.state.version !== before.state.version + 1 ||
        after.state.version >= Number.MAX_SAFE_INTEGER ||
        canonicalJson(before.state.aircraft) === canonicalJson(after.state.aircraft)) {
      this.clear();
      return false;
    }
    this.entry = { label, before, after_key: afterKey };
    return true;
  }

  take(context: TrafficUndoContext): { state: WorldState; selected: string; label: string } {
    const entry = this.current(context);
    if (!entry) throw new Error('No traffic edit is available to undo in this world.');
    this.clear();
    return {
      state: {
        ...context.state,
        version: context.state.version + 1,
        observed_at: context.now,
        aircraft: copyWorld(entry.before.state).aircraft,
      },
      selected: entry.before.selected,
      label: entry.label,
    };
  }
}
