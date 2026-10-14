#!/usr/bin/env python3
"""Retain the sole controller process and its original streams."""
import datetime
import json
import os
from pathlib import Path
import subprocess

here=Path(__file__).resolve().parent
argv=['/usr/bin/python3','-B',str(here/'receive-releases-v1.py'),str(here/'candidate-spec-v1.json')]
launch={'schema':'forge.towerops-release-launch.v1','argv':argv,'wrapper_pid':os.getpid(),
        'started':datetime.datetime.now(datetime.timezone.utc).isoformat()}
with (here/'controller-v1.stdout').open('xb') as out,(here/'controller-v1.stderr').open('xb') as err:
    child=subprocess.Popen(argv,cwd=here,stdin=subprocess.DEVNULL,stdout=out,stderr=err)
    launch['pid']=child.pid
    (here/'controller-launch-v1.json').write_text(json.dumps(launch,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'pid':child.pid,'wrapper_pid':os.getpid()}),flush=True)
    launch['exit_code']=child.wait()
launch['finished']=datetime.datetime.now(datetime.timezone.utc).isoformat()
(here/'controller-launch-v1.json').write_text(json.dumps(launch,sort_keys=True,indent=2)+'\n')
print(json.dumps(launch),flush=True)
raise SystemExit(launch['exit_code'])
