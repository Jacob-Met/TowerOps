#!/usr/bin/env python3
"""One independent temporary-prefix public CLI course; never start Explorer."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shlex
import signal
import stat
import subprocess
import sys
import traceback

HERE=Path(__file__).resolve().parent
PYTHON='/usr/bin/python3'
PATHS=sorted(['EXPLORER.md','explorer.py','replay_explain.py','scenarios.py',
              'towerops.py','web/app.js','web/index.html','web/style.css'])

def enc(x):
    return (json.dumps(x,ensure_ascii=True,sort_keys=True,indent=2)+'\n').encode('ascii')

def bytes_id(raw):
    return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),
            'git_blob':hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()}

def ident(p):
    s=p.lstat()
    out={'device':s.st_dev,'inode':s.st_ino,'mode':stat.S_IMODE(s.st_mode),
         'uid':s.st_uid,'gid':s.st_gid,'links':s.st_nlink,'mtime_ns':s.st_mtime_ns,'ctime_ns':s.st_ctime_ns}
    if stat.S_ISLNK(s.st_mode):out.update(type='symlink',target=os.readlink(p),size=s.st_size)
    elif stat.S_ISDIR(s.st_mode):out.update(type='directory',size=s.st_size)
    elif stat.S_ISREG(s.st_mode):out.update(type='file',**bytes_id(p.read_bytes()))
    else:raise RuntimeError('unexpected file kind: '+str(p))
    return out

def namespace(p):
    result={'.':ident(p)}
    def walk(d):
        for q in sorted(d.iterdir(),key=lambda x:x.name):
            row=ident(q);result[q.relative_to(p).as_posix()]=row
            if row['type']=='directory':walk(q)
    walk(p)
    return result

def helper_identity(p):
    return {k:v for k,v in ident(p).items() if k!='type'}

def pin(p):
    row=ident(p)
    return {k:row[k] for k in ('bytes','sha256','git_blob','mode')}

def same(a,b):return enc(a)==enc(b)

def main():
    spec_path=Path(sys.argv[1]).resolve()
    spec=json.loads(spec_path.read_text())
    freeze=json.loads((HERE/'freeze-v1.json').read_text())
    for row in freeze['controls']:
        assert same(pin(Path(row['path'])),{k:row[k] for k in ('bytes','sha256','git_blob','mode')}),row['path']
    assert sys.executable==PYTHON and sys.version==freeze['environment']['python_version']
    assert os.getuid()==freeze['environment']['uid'] and sys.platform=='linux'
    tools=Path(spec['tools_dir']).resolve();tool=tools/'stage_explorer.py'
    assert set(spec['files'])=={'stage_explorer.py','install_explorer.py'}
    assert sorted(x.name for x in tools.iterdir())==sorted(spec['files'])
    for name,row in spec['files'].items():assert same(pin(tools/name),row),name
    assert spec['files']['install_explorer.py']['git_blob']=='a732823616549e398dbd2ff5ad75d17b08442091'
    output=HERE/'received-v1';output.mkdir()
    receipt={'schema':'forge.towerops-release-receiving.v1','accepted':False,
             'started':datetime.datetime.now(datetime.timezone.utc).isoformat(),
             'scope':'cloud temporary-prefix public CLI; no source/runtime/native installation execution',
             'spec':spec,'spec_identity':pin(spec_path),'checks':[],'commands':[],
             'controller_pid':os.getpid(),'environment':freeze['environment']}
    controls=[Path(r['path']) for r in freeze['controls']]+[HERE/'freeze-v1.json',spec_path]
    before_controls={str(p):ident(p) for p in controls}
    fixtures=json.loads((HERE/'fixture-receipt-v1.json').read_text())
    sources={t:Path(p) for t,p in fixtures['sources'].items()}
    prefixes={t:Path(p) for t,p in fixtures['prefixes'].items()}
    oracles={t:json.loads((HERE/('expected-inspect-'+t+'.json')).read_text()) for t in ('a','b')}
    input_before={t:namespace(p) for t,p in sources.items()}
    tools_before=namespace(tools)
    before_prefix={t:namespace(p) for t,p in prefixes.items()}
    cwd=HERE/'foreign-cwd';foreign_before=namespace(cwd)
    receipt.update(controls_before=before_controls,inputs_before=input_before,tools_before=tools_before,
                   prefixes_before=before_prefix,foreign_before=foreign_before)

    def check(label,actual,expected):
        ok=same(actual,expected)
        receipt['checks'].append({'label':label,'actual':actual,'expected':expected,'pass':ok})
        if not ok:raise AssertionError(label)

    def invoke(label,args,expected_exit):
        stdout=output/(label+'.stdout');stderr=output/(label+'.stderr')
        cmd=[PYTHON,'-B',str(tool),*map(str,args)]
        row={'label':label,'argv':cmd,'stdout_path':str(stdout),'stderr_path':str(stderr),'expected_exit':expected_exit}
        receipt['commands'].append(row)
        with stdout.open('xb') as out,stderr.open('xb') as err:
            child=subprocess.Popen(cmd,cwd=cwd,env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','LC_ALL':'C.UTF-8'},
                                   stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True)
            row['pid']=child.pid
            try:row['exit_code']=child.wait(timeout=30)
            except subprocess.TimeoutExpired:
                row['timed_out']=True
                os.killpg(child.pid,signal.SIGTERM)
                try:child.wait(timeout=3)
                except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=3)
                row['exit_code']=child.returncode
        row.update(stdout=pin(stdout),stderr=pin(stderr),stdout_text=stdout.read_text(),stderr_text=stderr.read_text())
        try:os.killpg(child.pid,0);row['group_absent']=False
        except ProcessLookupError:row['group_absent']=True
        check(label+' closed',{'exit':row['exit_code'],'group_absent':row['group_absent'],'timeout':row.get('timed_out',False)},
              {'exit':expected_exit,'group_absent':True,'timeout':False})
        if expected_exit==0:
            check(label+' empty stderr bytes',len(stderr.read_bytes()),0)
            raw=stdout.read_bytes();check(label+' ASCII LF',raw.isascii() and raw.endswith(b'\n'),True)
            return json.loads(raw)
        check(label+' no success stdout bytes',len(stdout.read_bytes()),0)
        err=json.loads(stderr.read_bytes())
        check(label+' controlled refusal',err.get('ok') is False and isinstance(err.get('error'),str) and bool(err['error']),True)
        return err

    def install_args(tag,kind,digest,r):
        return ['install','--source-dir',sources[tag],'--prefix',prefixes[kind],
                '--expect-digest',digest,'--receipt-new',r]

    def refusal(label,tag,kind,digest):
        r=output/(label+'-installation.json');p=prefixes[kind];prior=namespace(p)
        invoke(label,install_args(tag,kind,digest,r),2)
        check(label+' namespace unchanged',namespace(p),prior)
        check(label+' receipt absent',os.path.lexists(r),False)

    def success(label,tag):
        oracle=oracles[tag];digest=oracle['digest'];p=prefixes['main'];prior=namespace(p)
        release=p/'share/towerops/explorer/releases'/digest
        alias=p/'bin'/('towerops-explorer-'+digest[:12]);r=output/(label+'-installation.json')
        expected={'ok':True,'digest':digest,'release':str(release),'selector':str(alias),'receipt':str(r)}
        actual=invoke(label,install_args(tag,'main',digest,r),0)
        check(label+' success report',actual,expected)
        after=namespace(p)
        for rel,old in prior.items():
            new=after.get(rel)
            if old['type']=='directory':
                check(label+' existing directory '+rel,{k:new[k] for k in ('type','device','inode','mode','uid','gid')},
                      {k:old[k] for k in ('type','device','inode','mode','uid','gid')})
            else:check(label+' prior terminal '+rel,new,old)
        release_ns=namespace(release)
        check(label+' exact release entries',sorted(release_ns),sorted(['.','web',*PATHS,'towerops-explorer','installation.json']))
        for row in oracle['manifest']['files']:
            dest=release/row['path'];src=sources[tag]/row['path']
            check(label+' source bytes '+row['path'],bytes_id(dest.read_bytes()),bytes_id(src.read_bytes()))
            check(label+' canonical mode '+row['path'],stat.S_IMODE(dest.lstat().st_mode),row['mode'])
        wrapper=('#!/bin/sh\nexec /usr/bin/python3 -B '+shlex.quote(str(release/'explorer.py'))+' serve "$@"\n').encode()
        check(label+' exact wrapper',bytes_id((release/'towerops-explorer').read_bytes()),bytes_id(wrapper))
        check(label+' wrapper mode',stat.S_IMODE((release/'towerops-explorer').lstat().st_mode),0o755)
        check(label+' absolute selector',{'is_symlink':alias.is_symlink(),'target':os.readlink(alias)},
              {'is_symlink':True,'target':str(release/'towerops-explorer')})
        metadata=json.loads((release/'installation.json').read_bytes())
        stamp=metadata.pop('installed_at')
        check(label+' timestamp UTC',datetime.datetime.fromisoformat(stamp).utcoffset()==datetime.timedelta(0),True)
        check(label+' metadata',metadata,{'schema':'towerops.explorer-staged-version.v1','digest':digest,
              'manifest':oracle['manifest'],'wrapper':bytes_id(wrapper),'python':'/usr/bin/python3',
              'purpose':'Additional foreground loopback Synthetic Explorer; content identity only.'})
        check(label+' metadata mode',stat.S_IMODE((release/'installation.json').lstat().st_mode),0o644)
        installed=json.loads(r.read_bytes())
        check(label+' receipt mode',stat.S_IMODE(r.lstat().st_mode),0o600)
        expected_fields={'schema':'towerops.explorer-stage.v1','ok':True,'phase':'complete','digest':digest,
                         'release':str(release),'selector':str(alias),'receipt':str(r),
                         'server_started':False,'existing_commands_changed':False,
                         'selector_target':str(release/'towerops-explorer')}
        check(label+' receipt semantic fields',{k:installed[k] for k in expected_fields},expected_fields)
        check(label+' exact captured inputs',installed['inputs'],{n:helper_identity(sources[tag]/n) for n in PATHS})
        check(label+' exact installed identities',installed['installed'],
              {n:helper_identity(release/n) for n in PATHS+['towerops-explorer','installation.json']})
        start=datetime.datetime.fromisoformat(installed['started']);finish=datetime.datetime.fromisoformat(installed['finished'])
        check(label+' receipt time order',start.utcoffset()==datetime.timedelta(0) and finish.utcoffset()==datetime.timedelta(0) and start<=finish,True)
        expected_added={release.relative_to(p).as_posix(),(release/'web').relative_to(p).as_posix(),alias.relative_to(p).as_posix()}
        expected_added.update((release/n).relative_to(p).as_posix() for n in PATHS+['towerops-explorer','installation.json'])
        collection='share/towerops/explorer/releases'
        if collection not in prior:expected_added.add(collection)
        check(label+' only expected additions',sorted(set(after)-set(prior)),sorted(expected_added))
        created=installed['created']
        check(label+' created entries exact',sorted(created),sorted([str(r)]+[str(p/n) for n in expected_added]))
        check(label+' receipt first selector last',[created[0],created[-1]],[str(r),str(alias)])
        receipt.setdefault('installation_receipts',{})[tag]={'path':str(r),'identity':pin(r),'value':installed}
        return r

    error=None
    try:
        check('empty foreign cwd',sorted(foreign_before),['.'])
        for tag in ('a','b'):
            actual=invoke('01-inspect-a' if tag=='a' else '02-inspect-b',['inspect','--source-dir',sources[tag]],0)
            check('inspect '+tag+' exact type-strict oracle',actual,oracles[tag])
            check('inspect '+tag+' prefix preservation',{t:namespace(p) for t,p in prefixes.items()},before_prefix)
        check('distinct independently expected digests',oracles['a']['digest']!=oracles['b']['digest'],True)
        digest=oracles['a']['digest'];wrong=('0' if digest[0]!='0' else '1')+digest[1:]
        refusal('03-wrong-digest','a','main',wrong)
        receipt_a=success('04-corrected-a','a');receipt_a_before=ident(receipt_a)
        refusal('05-repeat-a','a','main',oracles['a']['digest'])
        success('06-side-by-side-b','b')
        check('A original receipt unchanged',ident(receipt_a),receipt_a_before)
        refusal('07-occupied-alias','a','occupied',oracles['a']['digest'])
        refusal('08-dangling-alias','a','dangling',oracles['a']['digest'])
        check('exact eight commands',len(receipt['commands']),8)
    except Exception as exc:
        error={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
    finally:
        try:
            receipt.update(controls_after={str(p):ident(p) for p in controls},inputs_after={t:namespace(p) for t,p in sources.items()},
                           tools_after=namespace(tools),prefixes_after={t:namespace(p) for t,p in prefixes.items()},foreign_after=namespace(cwd))
            check('all frozen controls unchanged',receipt['controls_after'],before_controls)
            check('all source namespaces unchanged',receipt['inputs_after'],input_before)
            check('offered tools namespace unchanged',receipt['tools_after'],tools_before)
            check('foreign cwd unchanged',receipt['foreign_after'],foreign_before)
        except Exception as exc:
            receipt['closure_error']={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
        receipt['error']=error
        receipt['accepted']=error is None and 'closure_error' not in receipt and all(c['pass'] for c in receipt['checks'])
        receipt['finished']=datetime.datetime.now(datetime.timezone.utc).isoformat()
        (output/'receipt.json').write_bytes(enc(receipt))
    print(json.dumps({'accepted':receipt['accepted'],'checks':len(receipt['checks']),
                      'commands':len(receipt['commands']),'receipt':str(output/'receipt.json')}))
    return 0 if receipt['accepted'] else 1

if __name__=='__main__':raise SystemExit(main())
