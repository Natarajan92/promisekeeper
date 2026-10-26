import { afterEach, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import App from '../src/App';
import { ApiClient } from '../src/api/client';
import { caseView, cid, demo, did } from './fixtures';

afterEach(()=>{cleanup();localStorage.clear();vi.restoreAllMocks();window.location.hash='';});
// Each case has its own page; these flows start on the case page and reach other copies through the workspace switcher.
const caseHash=`#/cases/${cid}`;
const openSwitcher=()=>fireEvent.click(screen.getByRole('button',{name:/^Workspace/}));
async function goTo(hash:string){await act(async()=>{window.location.hash=hash;});}
const second='77777777-7777-4777-8777-777777777777';
const pendingKey=(copy=did)=>`promisekeeper.pending.${copy}.${cid}`;
const bufferKey=(copy=did)=>`promisekeeper.unsaved-draft.${copy}.${cid}`;
const allowed={allowed:true,blocking_reasons:[]};
const draft={id:'draft-one',demonstration_id:did,case_id:cid,investigation_id:'investigation-one',parent_version_id:null,recipient:'Studio North',invoice_id:'INV-001',exact_text:'Original saved wording',version:1,payload_hash:'a'.repeat(64),created_at:caseView.evaluation_at,validation_status:'VALID',validation_reasons:[]};
const reply=(value:unknown,status=200)=>new Response(JSON.stringify(value),{status});
const absent=()=>reply({schema_version:'1',error:{code:'NOT_RECORDED',message:'Not recorded'}},404);
function workspace({twoCopies=false,delayedLookups=false}={}) {
  let copies=twoCopies?[demo,{...demo,id:second}]:[demo];
  let saved=draft,revision=0;
  let finish!:(outcome?:string)=>void;
  const lookups:((response:Response)=>void)[]=[];
  const api=new ApiClient(async(url,init)=>{
    const path=String(url);
    if(path.includes('/operations/'))return delayedLookups?new Promise<Response>(resolve=>lookups.push(resolve)):absent();
    if(init?.body){
      const operation=JSON.parse(init.body as string);
      return new Promise<Response>(resolve=>{finish=(outcome='SAVED')=>{
        if(outcome==='DELETED')copies=copies.filter(copy=>copy.id!==did);
        else if(operation.exact_text){saved={...draft,id:'draft-two',version:2,exact_text:operation.exact_text};revision=1;}
        resolve(reply({schema_version:'1',receipt:{operation_id:operation.operation_id,operation_type:outcome==='DELETED'?'DELETE_DEMONSTRATION':'SAVE_DRAFT',target_id:outcome==='DELETED'?did:cid,committed_at:caseView.evaluation_at,outcome,case_revision:revision}}));
      };});
    }
    const copy=path.includes(second)?second:did;
    const view={...caseView,demonstration_id:copy,client:copy===second?'Other Studio':'Studio North',case_revision:revision,draft:{...saved,demonstration_id:copy},current_draft_version_id:saved.id,draft_state:'READY',review_state:'UNAPPROVED',allowed_commands:{...caseView.allowed_commands,reopen:allowed,edit_draft:allowed,approve_draft:allowed,reject_draft:allowed}};
    if(path.endsWith('/health'))return reply({schema_version:'1',ready:true,agent_mode:'STUB'});
    if(path.endsWith('/catalogue'))return reply({schema_version:'1',catalogue_version:'release-0.1',variant_ids:[],events:[{id:'U1',kind:'CLOCK',eligible_variant_ids:[null],case_id:'PK-001',evaluation_at:caseView.evaluation_at}]});
    if(path.endsWith('/demonstrations'))return reply({schema_version:'1',demonstrations:copies});
    if(path.endsWith('/cases'))return reply({schema_version:'1',demonstration_id:copy,clock_mode:'REFERENCE',evaluation_at:caseView.evaluation_at,cases:[view,{...view,id:'case-two',catalogue_case_id:'PK-002',client:'Second client'},{...view,id:'case-three',catalogue_case_id:'PK-003',client:'Third client'}].map(item=>({...item,currency:'INR',due_at:null,has_previous_investigation:false}))});
    if(path.includes('/history'))return reply({schema_version:'1',events:[],next_cursor:null});
    return reply(view);
  });
  return {api,lookups,complete:(outcome?:string)=>finish(outcome)};
}
async function openHistory() {
  await screen.findByRole('heading',{name:'Studio North'});
  fireEvent.click(screen.getByRole('button',{name:'History'}));
}
// Selected-copy deletion lives only in the Workspace switcher.
function deleteSelected() {
  openSwitcher();
  fireEvent.click(screen.getByRole('button',{name:'Review workspace deletion'}));
  fireEvent.click(screen.getByLabelText('Confirm deletion of this workspace'));
  fireEvent.click(screen.getByRole('button',{name:'Delete this workspace'}));
}

it('unlocks both History consumers when the unmounted Review save later commits',async()=>{
  const app=workspace();window.location.hash=caseHash;render(<App api={app.api}/>);
  await screen.findByRole('heading',{name:'Studio North'});
  fireEvent.click(screen.getByRole('button',{name:'Overview'}));
  fireEvent.change(screen.getByLabelText('Draft text'),{target:{value:'Committed wording A'}});
  fireEvent.click(screen.getByRole('button',{name:'Save unapproved version'}));
  fireEvent.click(screen.getByRole('button',{name:'History'}));
  await screen.findAllByText(/Request not recorded/);
  openSwitcher();expect(screen.getByRole('button',{name:'Review workspace deletion'})).toBeDisabled();
  expect(screen.getByRole('button',{name:'Review case reopening'})).toBeDisabled();
  await act(async()=>app.complete());
  await waitFor(()=>expect(screen.getByRole('button',{name:'Review workspace deletion'})).toBeEnabled());
  expect(screen.getByRole('button',{name:'Review case reopening'})).toBeEnabled();
  expect(screen.queryByRole('button',{name:'Retry original request'})).not.toBeInTheDocument();
  expect(screen.getByText(/Business time.*revision 1/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button',{name:'Overview'}));
  expect(screen.getByLabelText('Draft text')).toHaveValue('Committed wording A');
  expect(screen.getByText(/Version 2/)).toBeInTheDocument();
  expect(screen.queryByText(/Unsaved wording/)).not.toBeInTheDocument();
  expect(screen.getByRole('button',{name:'Approve exact saved version'})).toBeEnabled();
});

it('preserves newer unsaved wording after an older save commits outside Review',async()=>{
  const app=workspace();window.location.hash=caseHash;render(<App api={app.api}/>);
  await screen.findByRole('heading',{name:'Studio North'});
  fireEvent.click(screen.getByRole('button',{name:'Overview'}));
  fireEvent.change(screen.getByLabelText('Draft text'),{target:{value:'Committed wording A'}});
  fireEvent.click(screen.getByRole('button',{name:'Save unapproved version'}));
  fireEvent.change(screen.getByLabelText('Draft text'),{target:{value:'Newer unsaved wording B'}});
  fireEvent.click(screen.getByRole('button',{name:/^Evidence \(\d+\)$/}));
  await act(async()=>app.complete());
  await screen.findByText(/revision 1/);
  fireEvent.click(screen.getByRole('button',{name:'Overview'}));
  expect(screen.getByLabelText('Draft text')).toHaveValue('Newer unsaved wording B');
  expect(localStorage.getItem(bufferKey())).toContain('Newer unsaved wording B');
  expect(screen.getByText(/A newer saved version exists/)).toBeInTheDocument();
});

it('a known receipt unlocks the current view while another recovery lookup is outstanding',async()=>{
  const app=workspace({delayedLookups:true});
  localStorage.setItem(pendingKey(),JSON.stringify({kind:'closure',path:'/closure',operation:{schema_version:'1',operation_id:'shared-operation'}}));
  window.location.hash=`${caseHash}?section=history`;render(<App api={app.api}/>);await screen.findByRole('heading',{name:'Studio North'});
  await waitFor(()=>expect(app.lookups).toHaveLength(1));
  fireEvent.click(screen.getByRole('button',{name:'Overview'}));
  await waitFor(()=>expect(app.lookups).toHaveLength(2));
  await act(async()=>app.lookups[0](reply({schema_version:'1',receipt:{operation_id:'shared-operation',operation_type:'CLOSE_CASE',target_id:cid,committed_at:caseView.evaluation_at,outcome:'CLOSED',case_revision:1}})));
  fireEvent.click(screen.getByRole('button',{name:'History'}));
  await waitFor(()=>expect(screen.getByRole('button',{name:'Review case reopening'})).toBeEnabled());
  openSwitcher();expect(screen.getByRole('button',{name:'Review workspace deletion'})).toBeEnabled();
  await act(async()=>app.lookups[1](absent()));
  expect(screen.queryByText(/Request not recorded/)).not.toBeInTheDocument();
  expect(screen.queryByRole('button',{name:'Retry original request'})).not.toBeInTheDocument();
});

it('checking a disappeared pending record releases stale local controls without claiming a commit',async()=>{
  const app=workspace();
  localStorage.setItem(pendingKey(),JSON.stringify({kind:'closure',path:'/closure',operation:{schema_version:'1',operation_id:'removed-operation'}}));
  window.location.hash=caseHash;render(<App api={app.api}/>);await openHistory();
  await screen.findAllByText(/Request not recorded/);
  localStorage.removeItem(pendingKey());
  fireEvent.click(screen.getAllByRole('button',{name:'Check saved request outcome'})[0]);
  openSwitcher();await waitFor(()=>expect(screen.getByRole('button',{name:'Review workspace deletion'})).toBeEnabled());
  expect(screen.getByRole('button',{name:'Review case reopening'})).toBeEnabled();
  expect(screen.queryByText('Decision saved.')).not.toBeInTheDocument();
});

it('confirmed deletion rediscovery clears its selected scope after navigating away from History',async()=>{
  const app=workspace();window.location.hash=caseHash;render(<App api={app.api}/>);await openHistory();deleteSelected();
  fireEvent.click(screen.getByRole('button',{name:'Overview'}));
  expect(screen.getByRole('heading',{name:'Studio North'})).toBeInTheDocument();
  await act(async()=>app.complete('DELETED'));
  expect(await screen.findByText(/No saved workspaces/)).toBeInTheDocument();
  expect(screen.queryByRole('heading',{name:'Studio North'})).not.toBeInTheDocument();
  expect(localStorage.getItem('selected_demonstration_id')).toBeNull();
});

it('deletion of the previous copy preserves the new selected copy and its unsaved pending work',async()=>{
  localStorage.setItem('selected_demonstration_id',did);
  const otherPending=JSON.stringify({kind:'edit',path:'/draft-versions',operation:{schema_version:'1',operation_id:'other-operation',exact_text:'Other pending text'}});
  const otherBuffer=JSON.stringify({text:'Other unsaved wording',recipient:'Other Studio',base:'draft-one'});
  localStorage.setItem(pendingKey(second),otherPending);localStorage.setItem(bufferKey(second),otherBuffer);
  const app=workspace({twoCopies:true});window.location.hash=caseHash;render(<App api={app.api}/>);await openHistory();deleteSelected();
  fireEvent.change(screen.getByLabelText('Workspace'),{target:{value:second}});
  await goTo(caseHash);
  await screen.findByRole('heading',{name:'Other Studio'});
  fireEvent.click(screen.getByRole('button',{name:'Overview'}));
  await screen.findByDisplayValue('Other unsaved wording');
  await act(async()=>app.complete('DELETED'));
  await waitFor(()=>expect(screen.queryByText('Loading saved workspaces…')).not.toBeInTheDocument());openSwitcher();
  await waitFor(()=>expect(screen.getByLabelText('Workspace').querySelectorAll('option')).toHaveLength(2));
  expect(screen.getByLabelText('Workspace')).toHaveValue(second);
  expect(screen.getByRole('heading',{name:'Other Studio'})).toBeInTheDocument();
  expect(screen.getByLabelText('Draft text')).toHaveValue('Other unsaved wording');
  expect(localStorage.getItem('selected_demonstration_id')).toBe(second);
  expect(localStorage.getItem(pendingKey(second))).toBe(otherPending);
  expect(localStorage.getItem(bufferKey(second))).toBe(otherBuffer);
});
