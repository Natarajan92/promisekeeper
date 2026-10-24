"""Fixed offline failure schedules for isolated Gate IV browser journeys only."""
import argparse
import os
from pathlib import Path
import time

import uvicorn
from promisekeeper.agents.protocol import InvestigatorFailure
from promisekeeper.agents.scripted import ScriptedInvestigator
from promisekeeper.api.app import create_app
from promisekeeper.config import Settings

parser=argparse.ArgumentParser()
parser.add_argument('--port',type=int,required=True)
parser.add_argument('--mode',choices=['draft-fails-once','rerun-fails','closed-conflict'],required=True)
args=parser.parse_args()
app=create_app(Settings('STUB','scripted',Path(os.environ['PK_DB_PATH']),None))
if args.mode=='draft-fails-once':
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
else:
    from closed_conflict import install_closed_conflict_event
    install_closed_conflict_event()
uvicorn.run(app,host='127.0.0.1',port=args.port,workers=1)
