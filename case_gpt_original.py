"""GPT subscription delivered snippet, unchanged asserted hash values. Not trusted until run."""
from towerops import Ack, Approval, AdvisoryPlanner, Aircraft, AuditLog, ControlRoom, GateRejected, SafetyPolicy, WorldState
policy = SafetyPolicy()
state = WorldState(1, 1000.0, (Aircraft('TWR218', -5.0, 0.0, 10000.0, 1.0, 0.0), Aircraft('TWR419', 5.0, 0.0, 10000.0, -1.0, 0.0)))
advisory = AdvisoryPlanner(policy).plan(state, 1002.0)[0]
approval = Approval(advisory.advisory_hash, 'approve', 1002.2, 'synthetic-controller')
ack = Ack(advisory.advisory_hash, 'accepted', 1002.4)
assert state.world_hash == 'd01e0ef289cfb1310e8090bd2f068862f8d90f92b7939b8227223c2b85d0da6a'
assert advisory.advisory_hash == 'd7af68a35f2bd3b5f5c6f88b892acb8b5b11533992df0b6dc255b485b03cc27f'
approved_room = ControlRoom(policy)
after = approved_room.apply(state, advisory, approval, ack, 1002.5)
assert after.world_hash == '3741eb3b2fe72f06313a8872f34f1a54c8bc857d3cb87fbb40a96128f4709e35'
room = ControlRoom(policy)
try:
    room.apply(state, advisory, approval, None, 1002.5)
except GateRejected as exc:
    assert exc.reason == 'ack_missing'
else:
    raise AssertionError('MISSING ACK unexpectedly accepted')
assert [e['kind'] for e in room.audit.events] == ['screen_pass', 'approval', 'reject']
assert room.audit.head == 'a857d8403223d03f85462815a859a767650ba5fcb43d20668fab610a059c8cf3'
assert AuditLog.verify(room.audit.events)
print('GPT exact hash assertions passed')
