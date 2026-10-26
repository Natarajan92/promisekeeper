import type {Demonstration} from '../api/types';
import {instant} from '../components/format';

export function workspaceName(workspace:Demonstration|undefined):string {
  if(!workspace)return 'None selected';
  return workspace.selected_variant_id==='csv-demo'?'Imported records':'Saved workspace';
}

export function WorkspacePicker({workspaces,selected,onSelect}:{workspaces:Demonstration[];selected:string|null;onSelect:(id:string)=>void}) {
  const current=workspaces.find(workspace=>workspace.id===selected);
  return <section className="workspace-picker" aria-label="Saved workspaces">
    {workspaces.length>0?<div className="workspace-selection">
      <label htmlFor="saved-workspace">Workspace</label>
      <select id="saved-workspace" value={selected??''} onChange={event=>onSelect(event.target.value)}>
        <option value="" disabled>Choose a workspace</option>
        {workspaces.map((workspace,index)=><option value={workspace.id} key={workspace.id}>{index+1}. {workspaceName(workspace)} · saved {instant(workspace.created_at)} · {workspace.id.slice(0,8)}</option>)}
      </select>
      {current&&<details className="workspace-reference"><summary>Workspace details</summary><p>Workspace ID: {current.id}</p><p>Created {instant(current.created_at)}</p></details>}
    </div>:<p>No saved workspaces. Upload records to get started.</p>}
  </section>;
}
