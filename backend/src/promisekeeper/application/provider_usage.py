"""Local application-provider metadata only; never prompts, text, or credentials."""
import json
from pathlib import Path
import threading
from promisekeeper.application.operations import instant,utcnow

_lock=threading.Lock()

def usage_recorder(path):
    path=Path(path)
    def record(metadata):
        allowed={k:metadata[k] for k in ('provider','requested_model','returned_model','response_id','prompt_version','schema_version','adapter_version','request_parameters','usage') if k in metadata}
        allowed['recorded_at']=instant(utcnow())
        with _lock:
            path.parent.mkdir(parents=True,exist_ok=True)
            with path.open('a',encoding='utf-8') as stream:stream.write(json.dumps(allowed,sort_keys=True)+'\n')
    return record
