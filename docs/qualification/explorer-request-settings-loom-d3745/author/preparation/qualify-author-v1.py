import hashlib, json, os, pathlib, signal, stat, subprocess, sys, time
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'candidate'
OUT = ROOT / 'author-v1'
OUT.mkdir(exist_ok=False)

def identity(path):
    data = path.read_bytes()
    return {'path': str(path.relative_to(SOURCE)), 'bytes': len(data),
            'sha256': hashlib.sha256(data).hexdigest(), 'mode': stat.S_IMODE(path.stat().st_mode),
            'git_blob': hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()}

before = [identity(p) for p in sorted(SOURCE.rglob('*')) if p.is_file()]
freeze = {'schema': 'hamon.loom.towerops-settings-author-freeze.v1',
          'utc': datetime.now(timezone.utc).isoformat(), 'state': 'unpublished isolated candidate',
          'base': '202782f29f3a0ed1411e67a7744f9e63f26926f1', 'files': before}
(OUT / 'source-freeze.json').write_text(json.dumps(freeze, indent=2) + '\n')
commands = [
    ('syntax', ['node', '--check', 'web/app.js'], None),
    ('settings', ['node', 'tests/test_explorer_request_settings.cjs'], 10),
    ('selection', ['node', 'tests/test_explorer_replay_selection.cjs'], 10),
    ('explanation', ['node', 'tests/test_explorer_explanation.cjs'], 5),
]
receipt = {'schema': 'hamon.loom.towerops-settings-author.v1',
           'utc': datetime.now(timezone.utc).isoformat(), 'runtime': subprocess.check_output(['node', '--version'], text=True).strip(),
           'scope': 'Cloud Node production-script controls; no browser, native HTTP or full repository suite claim.',
           'source_before': before, 'commands': [], 'accepted': False}
for label, argv, expected in commands:
    outpath, errpath = OUT / (label + '.stdout'), OUT / (label + '.stderr')
    with outpath.open('xb') as out, errpath.open('xb') as err:
        proc = subprocess.Popen(argv, cwd=SOURCE, stdout=out, stderr=err, start_new_session=True)
        timeout = False
        try:
            code = proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            timeout = True
            os.killpg(proc.pid, signal.SIGKILL)
            code = proc.wait(timeout=5)
    text = outpath.read_text()
    counted = expected is None or (f'# tests {expected}\n' in text and f'# pass {expected}\n' in text and '# fail 0\n' in text and '# cancelled 0\n' in text)
    row = {'label': label, 'argv': argv, 'pid': proc.pid, 'exit_code': code, 'timed_out': timeout,
           'expected_tests': expected, 'test_count_match': counted, 'passed': code == 0 and not timeout and counted,
           'stdout': {'path': outpath.name, 'bytes': outpath.stat().st_size, 'sha256': hashlib.sha256(outpath.read_bytes()).hexdigest()},
           'stderr': {'path': errpath.name, 'bytes': errpath.stat().st_size, 'sha256': hashlib.sha256(errpath.read_bytes()).hexdigest()}}
    receipt['commands'].append(row)
    (OUT / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
after = [identity(p) for p in sorted(SOURCE.rglob('*')) if p.is_file()]
receipt['source_after'] = after
receipt['source_unchanged'] = before == after
receipt['accepted'] = before == after and all(row['passed'] for row in receipt['commands'])
(OUT / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'accepted': receipt['accepted'], 'source_unchanged': before == after,
                  'commands': [{k: row[k] for k in ['label', 'exit_code', 'test_count_match', 'passed']} for row in receipt['commands']],
                  'receipt': str(OUT / 'receipt.json')}))
sys.exit(0 if receipt['accepted'] else 1)
