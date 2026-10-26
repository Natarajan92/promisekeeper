import {useEffect, useState} from 'react';

// The exact selected-copy deletion confirmation, shared by Case actions and the workspace switcher.
// The caller owns the command (and its pending-request lock); this component only gathers explicit confirmation.
export function DeleteWorkspace({did,locked,open,onReview,onDelete}:{did:string;locked:boolean;open:boolean;onReview:()=>void;onDelete:()=>void}) {
  const [confirmed,setConfirmed]=useState(false);
  useEffect(()=>{if(!open)setConfirmed(false);},[open,did]);
  return <>
    <details><summary>Delete workspace</summary><p>Deletion removes all saved cases and history in this workspace. This cannot be undone.</p><button disabled={locked} onClick={()=>{setConfirmed(false);onReview();}}>Review workspace deletion</button></details>
    {open&&<div className="confirmation-panel"><h3>Delete this workspace</h3><p>Workspace ID: <strong>{did}</strong></p><label className="confirmation-check"><input type="checkbox" checked={confirmed} onChange={event=>setConfirmed(event.target.checked)}/>Confirm deletion of this workspace</label><button disabled={locked||!confirmed} onClick={onDelete}>Delete this workspace</button></div>}
  </>;
}
