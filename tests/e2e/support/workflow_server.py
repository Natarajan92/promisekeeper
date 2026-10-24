"""Fixed offline schedules and private process controls for isolated browser tests."""
import argparse
import os
from pathlib import Path
import time
import sys
import threading

import uvicorn
from promisekeeper.agents.protocol import InvestigatorFailure
from promisekeeper.agents.scripted import ScriptedInvestigator
from promisekeeper.api.app import create_app
from promisekeeper.config import Settings

parser=argparse.ArgumentParser()
parser.add_argument('--port',type=int,required=True)
from fault_scenarios import REGISTERED_PRESETS, install_fault_scenario
parser.add_argument('--mode',choices=['normal','draft-fails-once','rerun-fails','closed-conflict',*REGISTERED_PRESETS],required=True)
args=parser.parse_args()
app=create_app(Settings('STUB','scripted',Path(os.environ['PK_DB_PATH']),None))
if args.mode in REGISTERED_PRESETS:
    install_fault_scenario(app,args.mode,Path(os.environ['PK_DB_PATH']).with_name('fault.json'))
elif args.mode=='draft-fails-once':
    invocations=0
    def generator(plan):
        global invocations
        invocations+=1
        if invocations==1:raise InvestigatorFailure('SCRIPTED_DRAFT_FAILURE')
        return plan.exact_text
    app.state.draft_generator=generator
elif args.mode=='rerun-fails':
    class FailedRerun(ScriptedInvestigator):
        def extract(self,request,*,timeout):
            if self.calls:
                time.sleep(1)
                raise InvestigatorFailure('SCRIPTED_RERUN_FAILURE')
            return super().extract(request,timeout=timeout)
    app.state.investigator=FailedRerun()
elif args.mode=='closed-conflict':
    from closed_conflict import install_closed_conflict_event
    install_closed_conflict_event()
server = uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=args.port,workers=1))
def process_control():
    # An inherited private pipe reaches the actual interpreter through Windows' venv launcher.
    # It accepts fixed STOP/KILL commands, never code, paths, SQL or runtime writes.
    for line in sys.stdin:
        if line.strip() == 'KILL':
            os._exit(88)
        if line.strip() == 'STOP':
            server.should_exit = True
            return
    # The owning harness vanished. Do not leave an orphan listening on loopback.
    os._exit(89)

threading.Thread(target=process_control,daemon=True).start()
server.run()
