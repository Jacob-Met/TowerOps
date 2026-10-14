"""Admit five settings paths and exact independent browser evidence."""
import base64, hashlib, json, stat, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
TOOLS = Path('/dev/shm/loom-d3745-fanout-comparison-html/publication/tools')
PREFIX = 'docs/qualification/explorer-request-settings-loom-d3745/'
BASE = '202782f29f3a0ed1411e67a7744f9e63f26926f1'
TREE = '90c81370fb3215943a8b64a4264f8e362a05d479'
PRODUCT = {'web/app.js', 'web/index.html', 'EXPLORER.md',
           'tests/test_explorer_request_settings.cjs', 'tests/test_explorer_replay_selection.cjs'}

def sha(body):
    return hashlib.sha256(body).hexdigest()

def blob(body):
    return hashlib.sha1(b'blob ' + str(len(body)).encode() + b'\0' + body).hexdigest()

def encode(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + '\n').encode('ascii')

def identity(path):
    path = Path(path)
    s = path.lstat()
    assert stat.S_ISREG(s.st_mode), str(path)
    body = path.read_bytes()
    return {'source_path': str(path), 'native_mode': stat.S_IMODE(s.st_mode),
            'bytes': len(body), 'sha256': sha(body), 'git_blob': blob(body), 'mode': '100644'}

def main():
    assert len(sys.argv) == 3, 'original independent descriptor path and SHA256 required'
    independent_path = Path(sys.argv[1]).resolve()
    independent_body = independent_path.read_bytes()
    assert sha(independent_body) == sys.argv[2]
    independent = json.loads(independent_body)
    assert independent['prefix'] == PREFIX + 'independent-anvil/'
    author_path = ROOT / 'author-publication-inputs-v1.json'
    author_body = author_path.read_bytes()
    assert sha(author_body) == '050bb0aa02e1d3a41c32817365805cc7060de2e82b45a27c4d2928d1de67b731'
    author = json.loads(author_body)
    assert author['prefix'] == PREFIX + 'author/' and len(author['files']) == 43
    freeze = json.loads((ROOT / 'author-v1/candidate-freeze-v1.json').read_text())
    manifest_body = (ROOT / 'author-v1/candidate-manifest-v1.json').read_bytes()
    assert sha(manifest_body) == freeze['manifest']['sha256']
    manifest = json.loads(manifest_body)
    assert len(manifest['files']) == 15
    assert manifest['base_commit'] == BASE and set(manifest['changed_paths']) == PRODUCT
    for row in manifest['files']:
        p = Path(manifest['root']) / row['path']
        actual = identity(p)
        assert all(actual[k] == row[k] for k in ('bytes', 'sha256', 'git_blob'))
        assert actual['native_mode'] == row['mode']
    parent = json.loads((HERE / 'parent-tree-v1.json').read_text())
    assert parent['sha'] == TREE and parent['truncated'] is False
    leaves = {r['path']: r for r in parent['tree'] if r['type'] != 'tree'}
    assert len(leaves) == 1600
    assert PRODUCT - set(leaves) == {'tests/test_explorer_request_settings.cjs'}
    selected, inventory, sources, support, original_bodies = {}, [], [], [], {}

    def add(destination, mode, body, origin):
        assert destination not in selected
        assert destination.startswith(PREFIX) or destination in PRODUCT
        assert mode in ('100644', '100755')
        git = blob(body)
        selected[destination] = {'path': destination, 'mode': mode, 'sha': git,
                                'encoding': 'base64', 'content': base64.b64encode(body).decode('ascii')}
        row = {'path': destination, 'mode': mode, 'bytes': len(body), 'sha256': sha(body)}
        inventory.append({**row, 'git_blob': git, 'origin': origin})
        return row

    def add_row(row, destination):
        p = Path(row.get('mirror_path', row['source_path']))
        actual = identity(p)
        assert (actual['bytes'], actual['sha256']) == (row['bytes'], row['sha256']), str(p)
        if row.get('git_blob'):
            assert actual['git_blob'] == row['git_blob'], str(p)
        native_mode = row.get('native_mode')
        if isinstance(native_mode, str):
            native_mode = int(native_mode, 8)
        if native_mode is not None and not row.get('mirror_path'):
            assert actual['native_mode'] == native_mode, str(p)
        body = p.read_bytes()
        original_bodies[str(p)] = body
        return add(destination, row['mode'], body, {'read_path': str(p),
                   'read_mode': actual['native_mode'], 'original_source_path': row['source_path']})

    for row in manifest['files']:
        if row['path'] in PRODUCT:
            r = {**row, 'source_path': str(Path(manifest['root']) / row['path']),
                 'native_mode': row['mode'], 'mode': '100644'}
            sources.append(add_row(r, row['path']))
    assert len(sources) == 5
    for row in author['files']:
        support.append(add_row(row, author['prefix'] + row['path']))
    explicit = [
        (HERE / 'README.md', 'README.md'),
        (HERE / 'fresh-owner-check-v1.json', 'fresh-owner-check-v1.json'),
        (HERE / 'received-display-review-v1.json', 'received-display-review-v1.json'),
        (author_path, 'author-publication-inputs-v1.json'),
        (independent_path, 'independent-publication-inputs-v1.json'),
        (Path(__file__), 'assemble-publication-v1.py'),
        (ROOT.parent / 'root-towerops-releases/settings-source-review-v1.json', 'peer-reviews/root-source-review-v1.json'),
        (ROOT.parent / 'root-towerops-releases/settings-browser-review-v1.json', 'peer-reviews/root-browser-review-v1.json'),
    ]
    for p, destination in explicit:
        support.append(add_row(identity(p), PREFIX + destination))
    tools_authority = json.loads((TOOLS.parent / 'publication-tools.json').read_text())
    for row in tools_authority['files']:
        body = (TOOLS / row['path']).read_bytes()
        assert (len(body), sha(body), blob(body)) == (row['bytes'], row['sha256'], row['git_blob'])
    tools_record = {'schema': 'hamon.loom.towerops-settings-publication-tools.v1',
                    'repository': tools_authority['repository'], 'commit': tools_authority['commit'],
                    'files': tools_authority['files'],
                    'scope': 'Published maintained selection/layout/full-tree tools, used without product or tool test replay.'}
    support.append(add(PREFIX + 'publication-tools.json', '100644', encode(tools_record),
                       {'generated_from': 'Exact authenticated published maintained tool identities'}))
    source_rows = [r for r in manifest['files'] if r['path'] in PRODUCT]
    binding = {'schema': 'hamon.loom.towerops-settings-source-binding.v1',
               'repository': 'Jacob-Met/TowerOps', 'source_parent': BASE, 'parent_tree': TREE,
               'parent_leaf_count': len(leaves), 'source_files': source_rows,
               'runtime_projection': manifest, 'workflows': [leaves['.github/workflows/ci.yml'], leaves['.github/workflows/airspace-demo.yml']],
               'candidate_freeze': identity(ROOT / 'author-v1/candidate-freeze-v1.json'),
               'author_descriptor': identity(author_path), 'independent_descriptor': identity(independent_path),
               'source_scope': 'Exactly five source/test/guide leaves: four existing files plus one new focused test. All 1596 unselected parent leaves remain unchanged. Existing installed runtime/default selector and disjoint root issue139 staging work remain separate.',
               'qualification_scope': 'Focused cloud Node production-script author controls and separately frozen native browser/production-HTTP receiving. No installation, real-world authority or full-repository-suite claim.',
               'history': 'The raw author outer receipt is false for a reporter-prefix predicate; all four commands exited zero, all twenty-five named methods passed, and a separate retained-output classification preserves the original failure. Original observer v1 failed only its GET-body diagnostic; v2 corrected it using exact prior CLI outputs. No author product rerun.',
               'consumer': 'Independent original descriptor preserves native original/candidate browser receiving and exact source-at-execution state. Installed-use adoption is separately owned and qualified.'}
    support.append(add(PREFIX + 'source-binding-v1.json', '100644', encode(binding),
                       {'generated_from': 'Original parent, candidate manifest/freeze and unmodified original descriptors'}))
    for row in independent['files']:
        add_row(row, independent['prefix'] + row['path'])
    for p, body in original_bodies.items():
        assert Path(p).read_bytes() == body
    packet = {'schema': 'hamon.source-packet/1',
              'source': {'repository': 'Jacob-Met/TowerOps', 'commit': BASE, 'tree': TREE},
              'files': [selected[p] for p in sorted(selected)]}
    policy = {'schema': 'hamon.publication-layout/1', 'source_files': sources, 'support_files': support,
              'evidence_prefix': PREFIX, 'descriptor_schema': independent['schema'],
              'descriptor_prefix': independent['prefix']}
    out = HERE / 'admission-v1'
    out.mkdir()
    for name, body in [('source-packet.json', encode(packet)), ('layout-policy.json', encode(policy)),
                       ('selection-inventory.json', encode(inventory)), ('source-binding-v1.json', encode(binding)),
                       ('publication-tools.json', encode(tools_record)), ('original-independent-descriptor.json', independent_body)]:
        (out / name).open('xb').write(body)
    commands = []
    def run(label, argv):
        result = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
        for stream in ('stdout', 'stderr'):
            (out / (label + '.' + stream)).open('xb').write(getattr(result, stream))
        commands.append({'label': label, 'argv': argv, 'exit_code': result.returncode,
                         'stdout': {'bytes': len(result.stdout), 'sha256': sha(result.stdout)},
                         'stderr': {'bytes': len(result.stderr), 'sha256': sha(result.stderr)}})
        assert result.returncode == 0, label + ': ' + result.stderr.decode(errors='replace')
    packet_path = out / 'source-packet.json'
    plan_path = out / 'git-object-plan.json'
    policy_path = out / 'layout-policy.json'
    run('prepare', [sys.executable, '-B', str(TOOLS / 'prepare_git_objects.py'), str(packet_path),
                    '--sha256', sha(packet_path.read_bytes()), '--out', str(plan_path)])
    run('layout', [sys.executable, '-B', str(TOOLS / 'validate_publication_layout.py'), str(plan_path),
                   '--sha256', sha(plan_path.read_bytes()), '--policy', str(policy_path),
                   '--policy-sha256', sha(policy_path.read_bytes()), '--descriptor', str(independent_path),
                   '--descriptor-sha256', sha(independent_body)])
    for p, body in original_bodies.items():
        assert Path(p).read_bytes() == body
    receipt = {'schema': 'hamon.loom.towerops-settings-publication-admission.v1', 'accepted': True,
               'source_files': len(sources), 'support_files': len(support), 'author_files': len(author['files']),
               'independent_files': len(independent['files']), 'selected_files': len(selected),
               'payload_bytes': sum(r['bytes'] for r in inventory), 'commands': commands,
               'plan': identity(plan_path),
               'scope': 'Selected source/evidence admission only; no product execution or Git commit/ref mutation.'}
    (out / 'receipt.json').open('xb').write(encode(receipt))
    print(json.dumps(receipt, sort_keys=True))

if __name__ == '__main__':
    main()

