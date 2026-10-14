"""Bounded installed-command receiving after explicit publication and root release."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import shlex
import shutil
import signal
import socket
import stat
import subprocess
import sys
import time
import traceback
import urllib.request

ROOT = Path(__file__).resolve().parent
DIGEST = '82d3ab784c221b9fa320edbfc0a6f725a5beb8c293d0681646fedcfb880e0216'
NAME = 'towerops-explorer-82d3ab784c22'
PREFIX = Path('/home/jacob/.local')
NAMESPACE = PREFIX/'share/towerops'
OLD = NAMESPACE/'explorer/c77e98e68d627c3ad75edc2d775ee8da018dbdcf'
RELEASE = NAMESPACE/'explorer/releases'/DIGEST
SELECTOR = PREFIX/'bin'/NAME
NEIGHBORS = ['towerops-explorer','tsuka','tsuka-report','tsuka-lookup','seatrush-progress-preview']

def require(value, message):
    if not value:
        raise ValueError(message)

def dig(raw):
    return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),
            'git_blob':hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()}

def ident(path):
    p=Path(path)
    try: s=p.lstat()
    except FileNotFoundError: return {'present':False}
    row={'present':True,'device':s.st_dev,'inode':s.st_ino,'mode':stat.S_IMODE(s.st_mode),
         'uid':s.st_uid,'gid':s.st_gid,'links':s.st_nlink,'mtime_ns':s.st_mtime_ns,'ctime_ns':s.st_ctime_ns}
    if stat.S_ISLNK(s.st_mode):row.update(kind='link',target=os.readlink(p))
    elif stat.S_ISDIR(s.st_mode):row['kind']='directory'
    else:
        require(stat.S_ISREG(s.st_mode),'regular selected file '+str(p))
        row.update(kind='file',**dig(p.read_bytes()))
    return row

def inventory(paths):
    return {str(p):ident(p) for p in sorted(set(map(Path,paths)))}

def tree(root):
    root=Path(root);result={'.':ident(root)};pending=[root]
    while pending:
        current=pending.pop()
        for p in sorted(current.iterdir()):
            row=ident(p);result[str(p.relative_to(root))]=row
            require(len(result)<=200,'bounded owned tree')
            if row['kind']=='directory':pending.append(p)
    return result

def group_present(pid):
    try:os.killpg(pid,0);return True
    except ProcessLookupError:return False

def cleanup(proc, first=signal.SIGTERM):
    actions=[]
    if proc.poll() is None:
        os.killpg(proc.pid,first);actions.append(signal.Signals(first).name)
    try:code=proc.wait(timeout=7)
    except subprocess.TimeoutExpired:
        if group_present(proc.pid):os.killpg(proc.pid,signal.SIGKILL);actions.append('SIGKILL')
        code=proc.wait(timeout=3)
    if group_present(proc.pid):os.killpg(proc.pid,signal.SIGKILL);actions.append('residual-SIGKILL')
    return {'exit':code,'actions':actions,'group_absent':not group_present(proc.pid)}

parser=argparse.ArgumentParser()
parser.add_argument('--spec',required=True,type=Path)
parser.add_argument('--output',required=True,type=Path)
args=parser.parse_args()
require(args.spec.is_absolute() and args.output.is_absolute(),'absolute spec and new output')
freeze=json.loads((ROOT/'freeze-v1.json').read_bytes())
for rel,row in freeze['files'].items():
    got=ident(ROOT/rel)
    require(all(got[k]==row[k] for k in ('bytes','sha256','mode')),'frozen control '+rel)
spec=json.loads(args.spec.read_bytes())
require(spec['schema']=='anvil.towerops-release.native-spec.v1','spec schema')
for key in ['tool_commit','feature_commit']:
    require(re.fullmatch('[0-9a-f]{40}',spec[key]) is not None,'published '+key)
require(spec['native_authorized'] is True,'separate root native release')
authorization=Path(spec['root_release']['path'])
require(ident(authorization)['sha256']==spec['root_release']['sha256'],'exact root release record')
require(spec['content_digest']==DIGEST,'reviewed content digest')
content_bytes=(ROOT/'expected-content-v1.json').read_bytes()
require(hashlib.sha256(content_bytes).hexdigest()==DIGEST,'canonical expected manifest bytes')
content=json.loads(content_bytes)
authority=json.loads((ROOT/'received-source-authority-v1.json').read_bytes())
tool_authority=json.loads((ROOT/'reviewed-tool-authority-v1.json').read_bytes())
source=Path(spec['source_root']);tool=Path(spec['tool_root'])
require(source.is_absolute() and tool.is_absolute(),'absolute owned inputs')
toolpaths=[]
for row in tool_authority['files']:
    if row['path'] not in ['tools/stage_explorer.py','tools/install_explorer.py']:continue
    p=tool/row['path'];got=ident(p)
    require(all(got[k]==row[k] for k in ('bytes','sha256','git_blob','mode')),'published tool '+row['path'])
    toolpaths.append(p)
require(len(toolpaths)==2,'both tool and maintained helper')
sourcepaths=[]
for row in authority['files']:
    p=source/row['path'];got=ident(p)
    require(all(got[k]==row[k] for k in ('bytes','sha256','git_blob','mode')),'published source '+row['path'])
    sourcepaths.append(p)
require(len(sourcepaths)==8,'eight runtime/guide files')
require(sys.platform=='linux' and os.getuid()==1000,'native Linux uid1000')
account=pwd.getpwuid(os.getuid())
require(account.pw_name=='jacob' and account.pw_dir=='/home/jacob' and socket.gethostname()=='hamon-thinkpad','native account and host')
for p in [PREFIX,PREFIX/'bin',PREFIX/'share',NAMESPACE,NAMESPACE/'explorer',OLD]:
    got=ident(p);require(got['kind']=='directory' and got['uid']==1000,'existing owned real prefix '+str(p))
require(not os.path.lexists(RELEASE) and not os.path.lexists(SELECTOR) and shutil.which(NAME) is None,'new release/selector/PATH absent')
original=json.loads((ROOT/'accepted-original-source-v1.json').read_bytes())
for row in original['rows']:
    got=ident(OLD/row['path'])
    require(got['kind']=='file' and got['bytes']==row['size'] and got['git_blob']==row['sha'] and got['mode']==int(row['mode'],8)&0o777,'original c77 source '+row['path'])
default=PREFIX/'bin/towerops-explorer'
require(default.is_symlink() and os.readlink(default)==str(OLD/'towerops-explorer'),'original default selector exact')
neighbor_paths=[]
for name in NEIGHBORS:
    p=PREFIX/'bin'/name;require(os.path.lexists(p),'existing neighbor '+name)
    neighbor_paths.extend([p,p.resolve(strict=True)])
before_neighbors=inventory(neighbor_paths);before_namespace=tree(NAMESPACE)
controlpaths=[ROOT/x for x in freeze['files']]+[ROOT/'freeze-v1.json',args.spec,authorization]+toolpaths+sourcepaths
before=inventory(controlpaths)
args.output.mkdir(exist_ok=False);out=args.output;cwd=out/'foreign-cwd';cwd.mkdir()
receipt_path=out/'installation-receipt.json'
receipt={'schema':'anvil.towerops-release.native-receiving.v1','accepted':False,'started_ns':time.time_ns(),'pid':os.getpid(),
         'spec':spec,'identity':{'uid':os.getuid(),'user':account.pw_name,'passwd_home':account.pw_dir,'host':socket.gethostname(),'transport_HOME':os.environ.get('HOME'),'PATH':os.environ.get('PATH'),'python':sys.version},
         'before':before,'neighbors_before':before_neighbors,'namespace_before':before_namespace,'commands':[],'checks':[],'http':[],
         'scope':'One additional installed command, PATH help, foreground loopback static GET and owned stop. No browser, POST, run/replay/explain, repeat install, feature78 or legacy119 replay.'}
active=None
env=os.environ.copy()

def check(value,name):
    receipt['checks'].append({'name':name,'passed':bool(value)});require(value,name)

def command(name,argv,timeout=15):
    global active
    so=out/(name+'.stdout');se=out/(name+'.stderr')
    row={'name':name,'argv':argv,'cwd':str(cwd),'stdout_path':str(so),'stderr_path':str(se),'started_ns':time.time_ns()}
    receipt['commands'].append(row)
    with so.open('xb') as stdout,se.open('xb') as stderr:
        try:
            active=subprocess.Popen(argv,cwd=cwd,env=env,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,start_new_session=True)
            row['pid']=active.pid
            row['exit']=active.wait(timeout=timeout)
            row['group_absent']=not group_present(active.pid)
            check(row['group_absent'],name+' child group closed')
        except BaseException:
            if active is not None:row['exception_cleanup']=cleanup(active)
            raise
        finally:
            active=None;row.update(stdout=ident(so),stderr=ident(se),finished_ns=time.time_ns())
    return row['exit'],so.read_bytes(),se.read_bytes()

try:
    code,stdout,stderr=command('install',['/usr/bin/python3','-B',str(tool/'tools/stage_explorer.py'),'install','--source-dir',str(source),'--prefix',str(PREFIX),'--expect-digest',DIGEST,'--receipt-new',str(receipt_path)])
    check(code==0 and stderr==b'','one install success without stderr')
    summary=json.loads(stdout)
    check(summary=={'ok':True,'digest':DIGEST,'release':str(RELEASE),'selector':str(SELECTOR),'receipt':str(receipt_path)},'complete public success JSON')
    installed_receipt=json.loads(receipt_path.read_bytes());receipt['installation_receipt']=installed_receipt
    check(ident(receipt_path)['mode']==0o600 and installed_receipt['ok'] is True and installed_receipt['phase']=='complete','successful0600 receipt')
    check(all(installed_receipt[k]==summary[k] for k in ['digest','release','selector','receipt']),'receipt matches stdout')
    check(installed_receipt['server_started'] is False and installed_receipt['existing_commands_changed'] is False,'receipt declared scope')
    check(SELECTOR.is_symlink() and os.readlink(SELECTOR)==str(RELEASE/'towerops-explorer'),'exclusive absolute version selector')
    expected_names={r['path'] for r in authority['files']}|{'towerops-explorer','installation.json'}
    installed_before=tree(RELEASE)
    check(set(installed_before)==expected_names|{'.','web'},'exact10-file release plus web directory')
    for row in content['files']:
        got=ident(RELEASE/row['path'])
        check(got['kind']=='file' and all(got[k]==row[k] for k in ['bytes','sha256','mode']),'installed exact '+row['path'])
    wrapper=('#!/bin/sh\nexec /usr/bin/python3 -B '+shlex.quote(str(RELEASE/'explorer.py'))+' serve "$@"\n').encode()
    check((RELEASE/'towerops-explorer').read_bytes()==wrapper and ident(RELEASE/'towerops-explorer')['mode']==0o755,'exact executable native wrapper')
    provenance=json.loads((RELEASE/'installation.json').read_bytes())
    check(ident(RELEASE/'installation.json')['mode']==0o644 and provenance['schema']=='towerops.explorer-staged-version.v1' and provenance['digest']==DIGEST and provenance['manifest']==content and provenance['wrapper']==dig(wrapper) and provenance['python']=='/usr/bin/python3','exact provenance/content/wrapper binding')
    check(isinstance(provenance['installed_at'],str) and provenance['purpose']=='Additional foreground loopback Synthetic Explorer; content identity only.','provenance date and scope')
    check(set(installed_receipt['inputs'])=={r['path'] for r in authority['files']} and set(installed_receipt['installed'])==expected_names,'receipt identities exact membership')
    for name,record in installed_receipt['inputs'].items():
        got=ident(source/name);check(all(got[k]==v for k,v in record.items()),'receipt source identity '+name)
    for name,record in installed_receipt['installed'].items():
        got=ident(RELEASE/name);check(all(got[k]==v for k,v in record.items()),'receipt installed identity '+name)
    expected_created=[str(receipt_path)]
    if 'explorer/releases' not in before_namespace:expected_created.append(str(NAMESPACE/'explorer/releases'))
    expected_created.extend([str(RELEASE),str(RELEASE/'web')])
    expected_created.extend(str(RELEASE/r['path']) for r in content['files'])
    expected_created.extend([str(RELEASE/'towerops-explorer'),str(RELEASE/'installation.json'),str(SELECTOR)])
    check(installed_receipt['created']==expected_created,'created-path receipt records only actual new entries in order')
    check(shutil.which(NAME)==str(SELECTOR),'new command resolves through unchanged PATH')
    code,stdout,stderr=command('help',[NAME,'--help'])
    check(code==0 and stderr==b'' and b'usage: explorer.py serve' in stdout and b'--port PORT' in stdout and b'--help' in stdout,'actual PATH help')
    so=out/'server.stdout';se=out/'server.stderr';row={'name':'server','argv':[NAME,'--port','0'],'cwd':str(cwd),'stdout_path':str(so),'stderr_path':str(se),'started_ns':time.time_ns()};receipt['commands'].append(row)
    with so.open('xb') as stdout,se.open('xb') as stderr:
        active=subprocess.Popen(row['argv'],cwd=cwd,env=env,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,start_new_session=True);row['pid']=active.pid
        end=time.monotonic()+12;match=None
        while time.monotonic()<end:
            match=re.search(rb'Synthetic explorer: http://127\.0\.0\.1:(\d+)',so.read_bytes())
            if match or active.poll() is not None:break
            time.sleep(.025)
        check(match is not None and active.poll() is None,'foreground PATH server prints allocated loopback URL')
        port=int(match.group(1));receipt['port']=port;check(0<port<65536,'allocated port is usable')
        client=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        for route,name,mime in [('/','web/index.html','text/html'),('/app.js','web/app.js','text/javascript'),('/style.css','web/style.css','text/css')]:
            with client.open('http://127.0.0.1:'+str(port)+route,timeout=5) as response:
                body=response.read();status=response.status;headers=dict(response.headers);ctype=response.headers.get_content_type()
            path=out/('http-'+Path(name).name+'.body')
            with path.open('xb') as f:f.write(body)
            receipt['http'].append({'method':'GET','path':route,'status':status,'headers':headers,'body':str(path),'identity':ident(path)})
            check(status==200 and body==(source/name).read_bytes() and ctype==mime,'exact static HTTP '+route)
        row['closure']=cleanup(active,signal.SIGINT);active=None
        check(row['closure']=={'exit':0,'actions':['SIGINT'],'group_absent':True},'normal own SIGINT closes server and process group')
    row.update(stdout=ident(so),stderr=ident(se),finished_ns=time.time_ns())
    with socket.socket() as connection:
        connection.settimeout(.5)
        check(connection.connect_ex(('127.0.0.1',port))==111,'exact loopback listener closed')
    check(tree(RELEASE)==installed_before,'new release unchanged by help/static serving')
    check(SELECTOR.is_symlink() and os.readlink(SELECTOR)==str(RELEASE/'towerops-explorer'),'new selector retained after stop')
    receipt['installed_before_commands']=installed_before;receipt['installed_after_commands']=tree(RELEASE)
except BaseException as exc:
    receipt['error']=traceback.format_exc()
finally:
    if active is not None:
        try:receipt['failure_cleanup']=cleanup(active)
        except BaseException:receipt['cleanup_error']=traceback.format_exc()
    try:
        for row in receipt['commands']:
            row['stdout']=ident(row['stdout_path']);row['stderr']=ident(row['stderr_path'])
        receipt['after']=inventory(controlpaths);check(receipt['after']==before,'all offered sources/tools/controls preserved')
        receipt['neighbors_after']=inventory(neighbor_paths);check(receipt['neighbors_after']==before_neighbors,'all five original selectors and targets preserved')
        after_namespace=tree(NAMESPACE);receipt['namespace_after']=after_namespace
        for name,old in before_namespace.items():
            now=after_namespace[name]
            if name=='explorer' and 'explorer/releases' not in before_namespace:
                fields=['present','kind','device','inode','mode','uid','gid']
                check(all(now[k]==old[k] for k in fields),'old explorer directory custody with expected new-child metadata')
            elif name=='explorer/releases':
                fields=['present','kind','device','inode','mode','uid','gid']
                check(all(now[k]==old[k] for k in fields),'existing releases directory custody with new-child metadata')
            else:check(now==old,'old namespace entry preserved '+name)
        allowed_new={'explorer/releases','explorer/releases/'+DIGEST}
        allowed_new.update('explorer/releases/'+DIGEST+'/'+n for n in ({r['path'] for r in authority['files']}|{'web','towerops-explorer','installation.json'}))
        check(set(after_namespace)-set(before_namespace)<=allowed_new,'no unrelated namespace additions')
        check(not list(cwd.iterdir()),'foreign working directory unchanged')
    except BaseException:receipt['preservation_error']=traceback.format_exc()
    receipt['accepted']=not any(k in receipt for k in ['error','preservation_error','failure_cleanup','cleanup_error']) and all(c['passed'] for c in receipt['checks'])
    receipt['finished_ns']=time.time_ns()
    with (out/'receipt.json').open('x') as f:f.write(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'accepted':receipt['accepted'],'checks':len(receipt['checks']),'failed':[c['name'] for c in receipt['checks'] if not c['passed']],'commands':len(receipt['commands']),'http':len(receipt['http']),'receipt':dig((out/'receipt.json').read_bytes())}))
    if not receipt['accepted']:raise SystemExit(1)
