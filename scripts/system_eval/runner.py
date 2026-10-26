"""Immutable evidence runner for explicit offline system scenarios."""
from contextlib import ExitStack
from datetime import datetime, timezone
from hashlib import sha256
import ipaddress
import json
import os
from pathlib import Path
from math import ceil
import socket
import subprocess
import tempfile
import time
from unittest.mock import patch

from .grading import grade, summarize

ROOT = Path(__file__).resolve().parents[2]


def load_dataset(path):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(data.get('version'),str) or not isinstance(data.get('cases'),list) or not data['cases']:
        raise ValueError('Dataset needs a version and nonempty cases')
    seen=set()
    for case in data['cases']:
        if not isinstance(case,dict) or not isinstance(case.get('id'),str) or case['id'] in seen:
            raise ValueError('Case IDs must be unique strings')
        seen.add(case['id'])
        if (case.get('kind') not in {'message','import','allocation','workflow'} or
            case.get('track') not in {'contract','safety','capability'} or not case.get('intent') or
            not case.get('expected') or not case.get('automatic_failures') or not case.get('requirement')):
            raise ValueError('Incomplete eval case: '+case['id'])
        if case['kind']=='message' and 'text' not in case:raise ValueError('Message text missing')
        if case['kind']=='import' and not {'content','import_kind'}<=case.keys():raise ValueError('Import input missing')
        if case['kind'] in {'allocation','workflow'} and 'scenario' not in case:raise ValueError('Scenario missing')
    return data


def reserve_output(path):
    path=Path(path)
    path.mkdir(parents=True,exist_ok=False)
    return path


def exit_code(rows):
    return 0 if rows and all(row['verdict']=='PASS' for row in rows) else 1


def candidate_identity():
    files={}
    for folder in ['backend/src','frontend/src','tests/e2e']:
        for path in sorted((ROOT/folder).rglob('*')):
            if path.is_file() and '__pycache__' not in path.parts:
                files[path.relative_to(ROOT).as_posix()]=sha256(path.read_bytes()).hexdigest()
    def git(*args):
        result=subprocess.run(['git','-c','safe.directory='+ROOT.as_posix(),*args],cwd=ROOT,capture_output=True,text=True)
        if result.returncode:raise RuntimeError('Cannot establish Git candidate identity')
        return result.stdout.strip()
    return dict(commit=git('rev-parse','HEAD'),branch=git('branch','--show-current'),
                dirty=bool(git('status','--porcelain')),source_sha256=sha256(json.dumps(files,sort_keys=True).encode()).hexdigest(),files=files)


def block_network(stack):
    """Defense in depth: explicit STUB settings plus blocked external DNS/TCP."""
    connect,connect_ex,resolve=socket.socket.connect,socket.socket.connect_ex,socket.getaddrinfo
    def allowed(host):
        if isinstance(host,bytes):host=host.decode('ascii')
        if host=='localhost':return True
        try:return ipaddress.ip_address(host).is_loopback
        except ValueError:return False
    def guard(original):
        def call(sock,address):
            if isinstance(address,tuple) and not allowed(address[0]):raise RuntimeError('External networking blocked by system evaluator')
            return original(sock,address)
        return call
    def dns(host,*args,**kwargs):
        if host is not None and not allowed(host):raise RuntimeError('External DNS blocked by system evaluator')
        return resolve(host,*args,**kwargs)
    stack.enter_context(patch.object(socket.socket,'connect',guard(connect)))
    stack.enter_context(patch.object(socket.socket,'connect_ex',guard(connect_ex)))
    stack.enter_context(patch.object(socket,'getaddrinfo',dns))
    stack.enter_context(patch.dict(os.environ,{'LANGSMITH_TRACING':'false','LANGCHAIN_TRACING_V2':'false'}))


def evaluate(dataset_path, output):
    dataset=load_dataset(dataset_path)
    output=reserve_output(output)
    rows=[dict(case=case,verdict='UNEXECUTED',actual={},checks={},duration_ms=None) for case in dataset['cases']]
    report=dict(schema_version=1,dataset_version=dataset['version'],dataset_sha256=sha256(Path(dataset_path).read_bytes()).hexdigest(),
                started_at=datetime.now(timezone.utc).isoformat(),mode='STUB',live_qualified=False,human_study='UNEXECUTED',
                candidate=candidate_identity(),rows=rows,summary=summarize(rows))
    report['evaluator_files']={str(path.relative_to(ROOT)).replace('\\','/'):sha256(path.read_bytes()).hexdigest()
        for path in sorted((ROOT/'scripts/system_eval').glob('*.py'))}
    (output/'dataset.json').write_bytes(Path(dataset_path).read_bytes())
    def save():
        report['summary']=summarize(rows)
        report['tracks']={track:summarize([r for r in rows if r['case']['track']==track]) for track in ['contract','safety','capability']}
        (output/'results.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    save()
    from fastapi.testclient import TestClient
    from promisekeeper.api.app import create_app
    from promisekeeper.config import Settings
    from .workflow import Workflow
    with ExitStack() as stack:
        block_network(stack)
        for index,row in enumerate(rows):
            started=time.monotonic()
            try:
                with tempfile.TemporaryDirectory(prefix='pk-system-') as temp:
                    app=create_app(Settings('STUB','scripted',Path(temp)/'eval.sqlite',None))
                    with TestClient(app,base_url='http://127.0.0.1') as client:
                        flow=Workflow(client);case=row['case']
                        function={'message':flow.message,'import':flow.import_case,'allocation':flow.allocation,'workflow':flow.workflow}[case['kind']]
                        row['actual']=function(case)
                        row['business_day']=flow.today.isoformat()
                row['checks'],row['verdict']=grade(row['case'],row['actual'])
            except Exception as error:
                row['actual']={'error':f'{type(error).__name__}: {error}'}
                row['checks'],row['verdict']=grade(row['case'],row['actual'])
            row['duration_ms']=round((time.monotonic()-started)*1000,1)
            save()
            print(f"{index+1}/{len(rows)} {row['case']['id']} {row['verdict']}",flush=True)
    report['finished_at']=datetime.now(timezone.utc).isoformat()
    durations=sorted(row['duration_ms'] for row in rows)
    report['scenario_duration_ms']=dict(p50=durations[ceil(len(durations)*.5)-1],p95=durations[ceil(len(durations)*.95)-1],
        max=max(durations),scope='Whole in-process scenario including setup, persistence and investigation; not UI or model latency')
    report['passed']=exit_code(rows)==0
    save()
    lines=['# Offline system evaluation', '', f"Dataset: {dataset['version']} ({len(rows)} cases). Mode: STUB; LIVE unqualified; human study unexecuted.", '',
           '| Case | Track | Verdict | Failed checks | Duration ms |','|---|---|---|---|---:|']
    for row in rows:
        lines.append(f"| {row['case']['id']} | {row['case']['track']} | {row['verdict']} | {', '.join(k for k,v in row['checks'].items() if not v)} | {row['duration_ms']} |")
    lines.extend(['',json.dumps(report['summary']), '', 'Individual literal expectations, inputs and actual observations are in results.json.'])
    (output/'results.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return report
