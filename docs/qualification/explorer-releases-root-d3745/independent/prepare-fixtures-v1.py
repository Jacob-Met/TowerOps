#!/usr/bin/env python3
"""Prepare original saved-byte oracles; never import or execute product source."""
import hashlib
import json
import os
from pathlib import Path
import shlex
import stat
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PATHS = sorted(['EXPLORER.md', 'explorer.py', 'replay_explain.py', 'scenarios.py',
                'towerops.py', 'web/app.js', 'web/index.html', 'web/style.css'])
LEGACY = 'c77e98e68d627c3ad75edc2d775ee8da018dbdcf'

def encoded(x):
    return (json.dumps(x, ensure_ascii=True, sort_keys=True, indent=2)+'\n').encode('ascii')

def identity(p):
    b = p.read_bytes()
    return {'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest(),
            'git_blob': hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest(),
            'mode': stat.S_IMODE(p.lstat().st_mode)}

def put(p, b, mode=0o644):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('xb') as f: f.write(b)
    p.chmod(mode)

def main():
    fixtures = HERE/'fixtures'
    fixtures.mkdir()
    tree = json.loads((HERE/'original-tree-bindings.json').read_text())
    refs = {r['path']: r for r in tree['rows']}
    original = ROOT/'loom-towerops-request-settings/original'
    authority = ROOT/'loom-towerops-request-settings/preparation/original-source-identities-v1.json'
    pins = {r['path']: r for r in json.loads(authority.read_text())['files']}
    originals = {}
    for name in PATHS:
        p = original/name
        i = identity(p)
        assert {k: i[k] for k in ('bytes','sha256','git_blob','mode')} == {k:pins[name][k] for k in ('bytes','sha256','git_blob','mode')}
        assert i['git_blob'] == refs[name]['sha'] and i['bytes'] == refs[name]['size']
        assert oct(i['mode'])[2:] == refs[name]['mode'][3:]
        originals[name] = {'source_path': str(p), **i}
        for tag in ('a', 'b'):
            raw = p.read_bytes()
            if tag == 'b' and name == 'EXPLORER.md':
                raw += '\n\nSaved receiving variation: caf\u00e9 / \u6771\u4eac. This byte appendix changes content identity only.\n'.encode('utf-8')
            mode = i['mode']
            if tag == 'b' and name == 'explorer.py': mode = 0o644
            if tag == 'b' and name == 'web/style.css': mode = 0o600
            put(fixtures/('source-'+tag)/name, raw, mode)
    helper = ROOT/'root-towerops-releases/source/tools/install_explorer.py'
    assert identity(helper)['git_blob'] == refs['tools/install_explorer.py']['sha']
    put(HERE/'unchanged-helper/install_explorer.py', helper.read_bytes(), 0o755)
    put(fixtures/'source-a/ignored-extra.txt', b'Ignored source neighbor; never copied.\n')
    put(fixtures/'source-b/ignored-extra.txt', b'Ignored source neighbor; never copied.\n')
    oracles = {}
    for tag in ('a','b'):
        files=[]
        for name in PATHS:
            i=identity(fixtures/('source-'+tag)/name)
            files.append({'path':name,'bytes':i['bytes'],'sha256':i['sha256'],
                          'mode':0o755 if name=='explorer.py' else 0o644})
        manifest={'schema':'towerops.explorer-content.v1','files':files}
        digest=hashlib.sha256(encoded(manifest)).hexdigest()
        obj={'ok':True,'digest':digest,'manifest':manifest}
        put(HERE/('expected-inspect-'+tag+'.json'),encoded(obj))
        oracles[tag]=obj
    prefixes = {}
    for kind, leaf in [('main',"prefix with apostrophe's space"),('occupied','occupied-prefix'),('dangling','dangling-prefix')]:
        p=fixtures/leaf
        (p/'bin').mkdir(parents=True);(p/'share').mkdir()
        prefixes[kind]=str(p)
    p=Path(prefixes['main']);old=p/'share/towerops/explorer'/LEGACY
    for name in PATHS:
        src=fixtures/'source-a'/name
        put(old/name,src.read_bytes(),0o755 if name=='explorer.py' else 0o644)
    wrapper=('#!/bin/sh\nexec /usr/bin/python3 -B '+shlex.quote(str(old/'explorer.py'))+' serve "$@"\n').encode()
    put(old/'towerops-explorer',wrapper,0o755)
    put(old/'legacy-custody.json',encoded({'fixture_only':True,'original_runtime':LEGACY}))
    (p/'bin/towerops-explorer').symlink_to(old/'towerops-explorer')
    put(p/'bin/unrelated-command',b'#!/bin/sh\nexit 0\n',0o755)
    alias='towerops-explorer-'+oracles['a']['digest'][:12]
    put(Path(prefixes['occupied'])/'bin'/alias,b'Existing unrelated alias; preserve.\n',0o700)
    (Path(prefixes['dangling'])/'bin'/alias).symlink_to('/nonexistent/forge-owned-dangling-target')
    (HERE/'foreign-cwd').mkdir()
    setup={'schema':'forge.towerops-release-fixtures.v1','interpreter':sys.executable,
           'python_version':sys.version,'uid':os.getuid(),'originals':originals,
           'helper_original':{'source_path':str(helper),**identity(helper)},
           'prefixes':prefixes,'sources':{t:str(fixtures/('source-'+t)) for t in ('a','b')},
           'digests':{t:oracles[t]['digest'] for t in ('a','b')},'original_before_after':
           all(identity(Path(r['source_path']))=={k:r[k] for k in ('bytes','sha256','git_blob','mode')} for r in originals.values())}
    put(HERE/'fixture-receipt-v1.json',encoded(setup))
    print(json.dumps({'prepared':True,'digests':setup['digests'],'originals_preserved':setup['original_before_after']}))

if __name__=='__main__': main()
