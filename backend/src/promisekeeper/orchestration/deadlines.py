"""Execution budgets use monotonic time; business time is never a timeout clock."""
from datetime import datetime, timezone
import queue
import threading
import time
from promisekeeper.agents.protocol import InvestigatorFailure

_provider_lock=threading.Lock()

class Budget:
    def __init__(self, deadline_at):
        remaining=(datetime.fromisoformat(deadline_at)-datetime.now(timezone.utc)).total_seconds()
        self.ends=time.monotonic()+min(55,max(0,remaining))
    def remaining(self):
        value=self.ends-time.monotonic()
        if value<=0: raise InvestigatorFailure('INVESTIGATION_DEADLINE')
        return value

def bounded_call(call, timeout):
    result=queue.Queue(maxsize=1)
    cancelled=threading.Event()
    def run():
        with _provider_lock:
            if cancelled.is_set(): return
            try: result.put((True,call()))
            except Exception as exc: result.put((False,exc))
    threading.Thread(target=run,daemon=True).start()
    try: ok,value=result.get(timeout=timeout)
    except queue.Empty:
        cancelled.set()
        raise InvestigatorFailure('INVESTIGATOR_TIMEOUT',transient=True)
    if not ok: raise value
    return value
