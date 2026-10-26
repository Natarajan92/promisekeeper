import type {Workspace} from '../store/useWorkspace';

// Case-list load state for list pages; the case page shows its own combined status.
export function WorkspaceStatus({ws}:{ws:Workspace}) {
  return <>
    {ws.listError&&<div role="alert" className="notice"><p>{ws.listError}</p><button onClick={ws.refresh}>Refresh saved case</button></div>}
    {ws.listLoading&&!ws.list&&<p role="status">Loading saved cases…</p>}
  </>;
}
