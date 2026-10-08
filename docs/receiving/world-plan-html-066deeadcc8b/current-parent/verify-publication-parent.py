"""Source-only publication-parent verification; no product execution."""
from pathlib import Path
import hashlib
import json
import sys
import tarfile

def require(v, m):
    if not v:
        raise ValueError(m)

def git(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\x00' + raw).hexdigest()
raw = Path(sys.argv[1]).read_bytes()
with tarfile.open(sys.argv[2], 'r:xz') as archive:
    data = {m.name: archive.extractfile(m).read() for m in archive.getmembers() if m.isfile()}
current = json.loads(raw)
prior = json.loads(data['evidence/primary-git-provenance.json'])
reconstruction = json.loads(data['evidence/current-parent-reconstruction.json'])
old = {r['path']: r for r in prior['current_tree']['tree'] if r['type'] == 'blob'}
new = {r['path']: r for r in current['leaves']}
require(not current['truncated'], 'Full current tree required')
require(current['parents'][0] == reconstruction['parent'], 'Expected immediate prior parent')
removed = sorted(set(old) - set(new))
added = sorted(set(new) - set(old))
changed = [p for p in sorted(set(old) & set(new)) if (old[p]['sha'], old[p]['mode']) != (new[p]['sha'], new[p]['mode'])]
require(removed == [] and changed == ['web/airspace/src/core.ts'], 'Only browser source modified')
require(len(added) == 6 and all((p.startswith('docs/qualification/callsign-order-c77045b4/') or p in ['web/airspace/tests/identifier-parity.json', 'web/airspace/tests/identifier-parity.test.ts'] for p in added)), 'Exact six scoped upstream additions')
base = json.loads(data['evidence/baseline-complete-manifest.json'])
rows = []
for row in base['files']:
    p = row['path']
    expected = git(data['baseline/' + p]) if p != 'README.md' else git(prior['current_readme']['content'].encode())
    require(new[p]['sha'] == expected, 'Current canonical closure content ' + p)
    require((old[p]['sha'], old[p]['mode']) == (new[p]['sha'], new[p]['mode']), 'Parent-to-parent content/mode ' + p)
    rows.append({'path': p, 'git_blob': new[p]['sha'], 'canonical_mode': new[p]['mode']})
proposed = data['publication/README.md']
block = reconstruction['readme_block'].encode()
require(proposed.count(block) == 1 and git(proposed.replace(block, b'', 1)) == new['README.md']['sha'], 'Exact current README reconstruction')
require(new['explorer.py']['mode'] == '100755', 'Preserve unowned executable mode')
output = {'schema': 'towerops.plan-html-publication-parent-verification/1', 'parent': current['parent'], 'tree': current['tree'], 'prior_source_only_parent': reconstruction['parent'], 'prior_leaf_count': len(old), 'current_leaf_count': len(new), 'upstream_added': added, 'upstream_changed': changed, 'upstream_removed': removed, 'closure_files': rows, 'readme_overlay': {'bytes': len(proposed), 'sha256': hashlib.sha256(proposed).hexdigest(), 'git_blob': git(proposed)}, 'source_payload_sha256': hashlib.sha256(raw).hexdigest(), 'native_execution_at_new_parent': False, 'final_checkout_gate': 'Normal hosted checks at the exact proposed head; all unowned current leaves and modes preserved by overlay'}
print(json.dumps(output, indent=2) + '\n', end='')
