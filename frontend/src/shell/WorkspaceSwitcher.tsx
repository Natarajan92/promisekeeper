import {useEffect, useRef, useState} from 'react';
import {pendingOperation} from '../api/client';
import {subscribeCaseActivity} from '../api/caseActivity';
import {readPending, subscribeCommitted, subscribePending, WORKSPACE_SCOPE} from '../api/pendingOperations';
import {WorkspacePicker,workspaceName} from '../cases/WorkspacePicker';
import {DeleteWorkspace} from '../history/DeleteWorkspace';
import {useDraftReview} from '../reviews/useDraftReview';
import {routeLink, type Route} from '../routing';
import type {PageProps, Workspace} from '../store/useWorkspace';

export {WORKSPACE_SCOPE,workspaceName};


// Any retained case request (a draft, decision or investigation start) must be reconciled before its copy is deleted.
function casePending(did:string,caseIds:string[]):boolean {
  try {return caseIds.some(cid=>readPending(did,cid)!==null||pendingOperation(did,cid,'investigation')!==null);}
  catch {return true;}
}

export interface WorkspaceDeletion {
  did:string|null; commands:ReturnType<typeof useDraftReview>; locked:boolean; blocked:string; status:string;
  remove():void; clear():void;
}

// The only selected-copy deletion command. It lives in the shell so an uncertain outcome stays visible on every page.
export function useWorkspaceDeletion(ws:Workspace):WorkspaceDeletion {
  const did=ws.selected;
  const commands=useDraftReview(ws.api,did??'',WORKSPACE_SCOPE,ws.refresh);
  const caseIds=ws.list?.cases.map(item=>item.id)??[];const caseKey=caseIds.join('\n');
  const [,setTick]=useState(0);const [blocked,setBlocked]=useState('');const [deleted,setDeleted]=useState('');
  useEffect(()=>{
    if(!did)return;
    const changed=()=>setTick(value=>value+1);
    const unwatch=caseKey.split('\n').filter(Boolean).flatMap(cid=>[subscribePending(did,cid,changed),subscribeCaseActivity(did,cid,changed)]);
    return ()=>unwatch.forEach(stop=>stop());
  },[did,caseKey]);
  useEffect(()=>subscribeCommitted(outcome=>{
    if(outcome.command.kind==='deletion'&&outcome.response.receipt.outcome==='DELETED')setDeleted('Selected workspace deleted.');
  }),[]);
  const locked=commands.busy||!!commands.pending||(!!did&&casePending(did,caseIds));
  return {did,commands,locked,blocked,status:commands.message||deleted,
    remove:()=>{
      if(!did)return;
      // Checked again at click time: a case request may have been retained since this control rendered.
      if(casePending(did,caseIds)){setBlocked('Reconcile the pending case request before deleting this workspace.');return;}
      setBlocked('');setDeleted('');
      void commands.execute('deletion',`/demonstrations/${encodeURIComponent(did)}/deletion`,{confirm:true,confirmed_demonstration_id:did});
    },
    clear:()=>{setBlocked('');setDeleted('');},
  };
}

// Shown in the page area whenever a deletion outcome is unknown, so it is never hidden inside the closed switcher.
export function WorkspaceDeletionNotice({deletion}:{deletion:WorkspaceDeletion}) {
  const {commands}=deletion;
  return <>
    {commands.pending&&<section className="notice workspace-pending" aria-label="Pending workspace deletion"><p>A deletion of this workspace is pending. Its exact payload is retained, and case actions stay locked until its outcome is known.</p><button disabled={commands.busy} onClick={()=>void commands.reconcile()}>Check saved request outcome</button> <button disabled={commands.busy} onClick={()=>void commands.retryOriginal()}>Retry original request</button></section>}
    {commands.error&&<p className="notice" role="alert">{commands.error}</p>}
    {deletion.status&&<p className="workspace-deletion-status" role="status" aria-live="polite">{deletion.status}</p>}
  </>;
}

function SwitcherDeletion({deletion}:{deletion:WorkspaceDeletion}) {
  const [open,setOpen]=useState(false);
  if(!deletion.did)return null;
  return <div className="workspace-delete">
    <DeleteWorkspace did={deletion.did} locked={deletion.locked} open={open} onReview={()=>{deletion.clear();setOpen(true);}} onDelete={deletion.remove}/>
    {deletion.blocked&&<p className="notice" role="alert">{deletion.blocked}</p>}
  </div>;
}

// Leaving a workspace from a page scoped to one of its cases or items returns to that page's list.
function unscoped(route:Route):Route|null {
  if(route.page==='case')return {page:'cases'};
  if(route.page==='assistant'&&route.caseId)return {page:'assistant'};
  if(route.page==='approvals'&&route.itemId)return {page:'approvals'};
  return null;
}

export function WorkspaceSwitcher({ws,route,navigate,deletion}:PageProps&{deletion:WorkspaceDeletion}) {
  const [open,setOpen]=useState(false);
  const toggle=useRef<HTMLButtonElement>(null);
  // The chooser never opens by itself: with no workspace chosen, the closed toggle says so and the
  // Dashboard empty state and Upload step 1 guide the owner; the picker is one click away.
  const expanded=open;
  const current=ws.copies.find(copy=>copy.id===ws.selected);
  function leave(id:string) {
    const leaving=id!==ws.selected?unscoped(route):null;
    deletion.clear();setOpen(false);
    if(leaving)navigate(leaving);
  }
  return <div className="workspace-switcher" onKeyDown={event=>{if(event.key==='Escape'&&open){event.stopPropagation();setOpen(false);toggle.current?.focus();}}}>
    <button ref={toggle} type="button" className="workspace-toggle" aria-expanded={expanded} aria-controls={expanded?'workspace-panel':undefined} onClick={()=>setOpen(value=>!value)}>
      <span className="workspace-toggle-label">Workspace</span> <strong>{ws.discovering&&!current?'Loading…':workspaceName(current)}</strong>{current&&<> <span className="workspace-toggle-id">{current.id.slice(0,8)}</span></>}
    </button>
    {expanded&&!ws.discovering&&!ws.discoveryError&&<div id="workspace-panel" className="workspace-panel">
      <WorkspacePicker workspaces={ws.copies} selected={ws.selected} onSelect={id=>{leave(id);ws.select(id);}}/>
      <p className="workspace-upload"><a {...routeLink({page:'upload',step:1},navigate,()=>{ws.select(null);deletion.clear();setOpen(false);})}>New workspace</a><span className="subtle"> Upload records into a separate workspace.</span></p>
      {ws.selected&&<SwitcherDeletion key={ws.selected} deletion={deletion}/>}
    </div>}
  </div>;
}
