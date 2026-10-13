"""Author controls for one frozen Explorer browser candidate; no independent claim."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import socket
import stat
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
PACKET = ROOT / 'candidate-packet-v1.json'
EXPECTED_PACKET = 'bc4450944a7aa7170e963af8f98e912283f17ae0df22b72f86f399ab9ef1b171'
raw = PACKET.read_bytes()
if hashlib.sha256(raw).hexdigest() != EXPECTED_PACKET:
    raise RuntimeError('Frozen packet bytes differ')
packet = json.loads(raw)
candidate = ROOT / 'candidate-v1'
candidate.mkdir(exist_ok=False)
for item in packet['files']:
    relative = Path(item['path'])
    if relative.is_absolute() or '..' in relative.parts:
        raise RuntimeError('Invalid projected path')
    body = item['content'].encode('utf-8')
    blob = hashlib.sha1(b'blob ' + str(len(body)).encode() + b'\0' + body).hexdigest()
    if len(body) != item['bytes'] or hashlib.sha256(body).hexdigest() != item['sha256'] or blob != item['git_blob']:
        raise RuntimeError('Packet identity mismatch')
    path = candidate / relative
    path.parent.mkdir(exist_ok=True, parents=True)
    path.write_bytes(body)
    path.chmod(int(item['mode'], 8))

def identity(path):
    body = path.read_bytes()
    return {'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest(),
            'mode': oct(stat.S_IMODE(path.stat().st_mode))}

def source_snapshot():
    return {item['path']: identity(candidate / item['path']) for item in packet['files']}

before = source_snapshot()
commands = [
    ['python3', '-B', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_explorer_explanation_http.py', '-v'],
    ['python3', '-O', '-B', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_explorer_explanation_http.py', '-v'],
    ['node', 'tests/test_explorer_explanation.cjs'],
    ['node', 'tests/test_explorer_replay_selection.cjs'],
    ['python3', '-B', '-m', 'unittest', 'test_explorer', '-v'],
]
streams = ROOT / 'streams-v1'
streams.mkdir(exist_ok=False)
results = []
for index, argv in enumerate(commands):
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    result = subprocess.run(argv, cwd=candidate, capture_output=True, timeout=45,
                            env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
    row = {'argv': argv, 'started_utc': started, 'exit_code': result.returncode}
    for kind in ('stdout', 'stderr'):
        body = getattr(result, kind)
        path = streams / f'{index}.{kind}'
        path.write_bytes(body)
        row[kind] = {'path': str(path.relative_to(ROOT)), 'bytes': len(body),
                     'sha256': hashlib.sha256(body).hexdigest(), 'utf8': body.decode('utf-8')}
    results.append(row)
    print(json.dumps({'command': index, 'exit_code': result.returncode}), flush=True)
after = source_snapshot()
accepted = before == after and all(row['exit_code'] == 0 for row in results)
receipt = {'schema': 'towerops-browser-explanation-author-controls-root-d3745-v1',
           'scope': 'Author tests on actual native Python/Node; not independent browser receiving',
           'base_commit': packet['base'], 'device_id': 'cadafaf3-4d0b-4c4f-a0d3-34a95d2cec90',
           'hostname': socket.gethostname(), 'user': os.environ.get('USER'), 'python': sys.version,
           'platform': platform.platform(), 'supervisor': identity(Path(__file__)),
           'packet': identity(PACKET), 'source_before': before, 'commands': results,
           'source_after': after, 'source_preserved': before == after, 'accepted': accepted,
           'closed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
body = (json.dumps(receipt, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
path = ROOT / 'author-receipt-v1.json'
with path.open('xb') as target:
    target.write(body)
print(json.dumps({'accepted': accepted, 'receipt': str(path), 'bytes': len(body),
                  'sha256': hashlib.sha256(body).hexdigest()}), flush=True)
raise SystemExit(0 if accepted else 1)
