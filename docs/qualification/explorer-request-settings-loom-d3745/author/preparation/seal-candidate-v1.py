import difflib, hashlib, json, pathlib, re, stat
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / 'author-v1'
SOURCE = ROOT / 'candidate'
ORIGINAL = ROOT / 'original'

def identity(path):
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
            'mode': stat.S_IMODE(path.stat().st_mode),
            'git_blob': hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()}

def save(name, body):
    path = OUT / name
    with path.open('x') as f:
        f.write(json.dumps(body, indent=2) + '\n')
    return {'path': str(path), **identity(path)}

receipt = json.loads((OUT / 'receipt.json').read_text())
checks = []
for command in receipt['commands']:
    stdout, stderr = OUT / command['stdout']['path'], OUT / command['stderr']['path']
    for stream, p in [('stdout', stdout), ('stderr', stderr)]:
        actual = identity(p)
        assert all(actual[k] == command[stream][k] for k in ['bytes', 'sha256'])
    assert command['exit_code'] == 0 and not command['timed_out']
    assert stderr.read_bytes() == b''
    expected = command['expected_tests']
    if expected is not None:
        text = stdout.read_text()
        fields = {key: int(value) for key, value in re.findall(r'^ℹ (tests|pass|fail|cancelled|skipped|todo) (\d+)$', text, re.M)}
        assert fields == {'tests': expected, 'pass': expected, 'fail': 0, 'cancelled': 0, 'skipped': 0, 'todo': 0}
        named = re.findall(r'^✔ (.+) \([^\n]+ms\)$', text, re.M)
        assert len(named) == expected
        checks.append({'label': command['label'], 'summary': fields, 'named_passes': named})
    else:
        assert stdout.read_bytes() == b''
assert receipt['accepted'] is False and receipt['source_unchanged'] is True
audit = save('reporter-classification-audit-v1.json', {
    'schema': 'hamon.loom.towerops-settings-reporter-audit.v1', 'utc': datetime.now(timezone.utc).isoformat(),
    'raw_receipt': identity(OUT / 'receipt.json'), 'raw_accepted_preserved': False,
    'finding': 'Collector required TAP summary lines; actual Node 24.19.0 spec reporter emitted ℹ summary lines. All four commands exited 0; complete retained streams establish ten new and fifteen inherited passing methods, no failures/cancellations/skips/todos.',
    'checks': checks, 'product_rerun': False, 'accepted_within_scope': True,
    'scope': 'Read-only classification of exact retained raw output; no rewritten original receipt or browser/native HTTP claim.'})
fence = ['web/app.js', 'web/index.html', 'EXPLORER.md', 'tests/test_explorer_request_settings.cjs', 'tests/test_explorer_replay_selection.cjs']
files, changed = [], []
for path in sorted(SOURCE.rglob('*')):
    if not path.is_file():
        continue
    rel = path.relative_to(SOURCE).as_posix()
    row = {'path': rel, 'source_path': str(path), **identity(path)}
    files.append(row)
    original = ORIGINAL / rel
    if not original.exists() or identity(original) != identity(path):
        changed.append(rel)
        old = original.read_text().splitlines(keepends=True) if original.exists() else []
        new = path.read_text().splitlines(keepends=True)
        (OUT / (rel.replace('/', '--') + '.patch')).write_text(''.join(difflib.unified_diff(old, new, fromfile='a/' + rel, tofile='b/' + rel)))
assert sorted(changed) == sorted(fence)
assert len(files) == 15
manifest = save('candidate-manifest-v1.json', {'schema': 'hamon.loom.towerops-settings-candidate.v1',
    'root': str(SOURCE), 'state': 'unpublished isolated candidate',
    'base_commit': '202782f29f3a0ed1411e67a7744f9e63f26926f1',
    'base_tree': '90c81370fb3215943a8b64a4264f8e362a05d479', 'files': files,
    'changed_paths': fence, 'unchanged_inherited_leaves': 10})
runtime = ['web/app.js', 'web/index.html', 'web/style.css', 'explorer.py', 'scenarios.py', 'towerops.py', 'replay_explain.py', 'EXPLORER.md']
projection = save('runtime-projection-v1.json', {'schema': 'hamon.loom.towerops-settings-runtime.v1',
    'root': str(SOURCE), 'state': 'unpublished isolated candidate', 'base_commit': '202782f29f3a0ed1411e67a7744f9e63f26926f1',
    'files': [row for row in files if row['path'] in runtime]})
freeze = save('candidate-freeze-v1.json', {'schema': 'hamon.loom.towerops-settings-freeze.v1',
    'utc': datetime.now(timezone.utc).isoformat(), 'manifest': manifest, 'runtime_projection': projection,
    'author_receipt': {'path': str(OUT / 'receipt.json'), **identity(OUT / 'receipt.json')},
    'classification_audit': audit,
    'public_contract': identity(ROOT / 'preparation/public-contract-v1.md'),
    'original_corrected_observation': identity(ROOT / 'original-observation-v2/receipt.json'),
    'limits': 'Original v1 observation and author outer false receipts remain exact. Product commands are controlled cloud Node methods, not actual browser receiving. Independent browser candidate remains unexposed pending source gate.'})
print(json.dumps({'manifest': manifest, 'projection': projection, 'freeze': freeze, 'audit': audit, 'source_paths': changed}))
