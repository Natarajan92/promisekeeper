import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { DraftReview } from '../src/reviews/DraftReview';
import { ApiClient } from '../src/api/client';
import { caseView, cid, did } from './fixtures';

afterEach(() => { cleanup(); localStorage.clear(); vi.restoreAllMocks(); });
const draft = { id:'44444444-4444-4444-8444-444444444444',demonstration_id:did,case_id:cid,investigation_id:'55555555-5555-4555-8555-555555555555',parent_version_id:null,recipient:'Studio North',invoice_id:'INV-001',exact_text:'Hello Studio North,\nPlease review invoice INV-001.\nThank you.',version:1,payload_hash:'a'.repeat(64),created_at:'2026-10-24T00:00:00Z',validation_status:'VALID',validation_reasons:[] };
const eligibility = { allowed:true,blocking_reasons:[] };
const view = { ...caseView,draft,draft_state:'READY',draft_reviews:[],review_state:'UNAPPROVED',draft_generation_attempt:null,no_draft_reason:null,current_draft_version_id:draft.id,allowed_commands:{...caseView.allowed_commands,edit_draft:eligibility,approve_draft:eligibility,reject_draft:eligibility} };
const receipt = { schema_version:'1',receipt:{operation_id:'op',operation_type:'SAVE_DRAFT',target_id:cid,committed_at:'2026-10-24T00:00:00Z',outcome:'SAVED',case_revision:1} };
it('displays exact recipient, invoice and version, with explicit review actions and no Send', () => {
  render(<DraftReview api={new ApiClient()} view={view as any} onRefresh={()=>{}} />);
  expect(screen.getByLabelText('Draft recipient')).toHaveValue('Studio North');
  expect(screen.getByLabelText('Draft text')).toHaveValue(draft.exact_text);
  expect(screen.getByText(/Version 1/)).toBeInTheDocument();
  expect(screen.getByRole('button',{name:'Approve exact saved version'})).toBeEnabled();
  expect(screen.queryByRole('button',{name:/send/i})).not.toBeInTheDocument();
});
it('preserves unsaved text and its original head through unmount and copy switches', () => {
  const one=render(<DraftReview api={new ApiClient()} view={view as any} onRefresh={()=>{}} />);
  fireEvent.change(screen.getByLabelText('Draft text'),{target:{value:'Hi Studio North,\nPlease review invoice INV-001.\nThank you.'}});
  one.unmount();
  const other=render(<DraftReview api={new ApiClient()} view={{...view,demonstration_id:'other'} as any} onRefresh={()=>{}} />);
  expect(screen.getByLabelText('Draft text')).toHaveValue(draft.exact_text);other.unmount();
  render(<DraftReview api={new ApiClient()} view={view as any} onRefresh={()=>{}} />);
  expect(screen.getByLabelText('Draft text')).toHaveValue('Hi Studio North,\nPlease review invoice INV-001.\nThank you.');
  expect(screen.getByRole('button',{name:'Approve exact saved version'})).toBeDisabled();
});
it('keeps unsaved text on a failed save and never claims it was saved', async () => {
  const api=new ApiClient(async()=>new Response(JSON.stringify({schema_version:'1',error:{code:'REVISION_CONFLICT',message:'Refresh the changed case.'}}),{status:409}));
  render(<DraftReview api={api} view={view as any} onRefresh={()=>{}} />);
  fireEvent.change(screen.getByLabelText('Draft text'),{target:{value:'My unsaved text'}});
  fireEvent.click(screen.getByRole('button',{name:'Save unapproved version'}));
  expect(await screen.findByRole('alert')).toHaveTextContent('Refresh the changed case.');
  expect(screen.getByLabelText('Draft text')).toHaveValue('My unsaved text');
  expect(screen.queryByText('New unapproved version saved.')).not.toBeInTheDocument();
});
it('binds approval to the exact saved hash, version and current epoch', async () => {
  let sent:any;
  const api=new ApiClient(async(_url,init)=>{sent=JSON.parse(init?.body as string);return new Response(JSON.stringify(receipt));});
  render(<DraftReview api={api} view={{...view,review_epoch:7,case_revision:9} as any} onRefresh={()=>{}} />);
  fireEvent.click(screen.getByRole('button',{name:'Approve exact saved version'}));
  await screen.findByText(/Approval recorded/);
  expect(sent).toMatchObject({expected_case_revision:9,draft_version_id:draft.id,payload_hash:draft.payload_hash,expected_review_epoch:7,decision:'APPROVE'});
});
it('shows clause reasons and server stale blocking reasons, with approval disabled', () => {
  render(<DraftReview api={new ApiClient()} view={{...view,draft:{...draft,validation_status:'INVALID',validation_reasons:['UNSUPPORTED_CLAUSE_2']},allowed_commands:{...view.allowed_commands,approve_draft:{allowed:false,blocking_reasons:['EVIDENCE_CHANGED']}}} as any} onRefresh={()=>{}} />);
  expect(screen.getByText(/unsupported clause 2/i)).toBeInTheDocument();
  expect(screen.getByText(/evidence changed/i)).toBeInTheDocument();
  expect(screen.getByRole('button',{name:'Approve exact saved version'})).toBeDisabled();
});
it('explains why no customer draft is needed without inventing a draft', () => {
  render(<DraftReview api={new ApiClient()} view={{...view,draft:null,no_draft_reason:'WAIT_NO_CUSTOMER_DRAFT'} as any} onRefresh={()=>{}} />);
  expect(screen.getByText(/wait no customer draft/i)).toBeInTheDocument();
  expect(screen.queryByLabelText('Draft text')).not.toBeInTheDocument();
});
it('checks an unknown save outcome and retries only its exact original request', async () => {
  const calls:{url:string,body?:string}[]=[];let fail=true;
  const api=new ApiClient(async(url,init)=>{
    calls.push({url:String(url),body:init?.body as string|undefined});
    if(String(url).includes('/operations/')) return new Response(JSON.stringify({schema_version:'1',error:{code:'NOT_RECORDED',message:'Not recorded'}}),{status:404});
    if(fail){fail=false;throw new Error('lost');}
    return new Response(JSON.stringify(receipt));
  });
  render(<DraftReview api={api} view={view as any} onRefresh={()=>{}} />);
  fireEvent.change(screen.getByLabelText('Draft text'),{target:{value:'Hi Studio North'}});
  fireEvent.click(screen.getByRole('button',{name:'Save unapproved version'}));
  await screen.findByRole('button',{name:'Retry original request'});
  fireEvent.click(screen.getByRole('button',{name:'Retry original request'}));
  await waitFor(()=>expect(calls.filter(c=>c.body)).toHaveLength(2));
  const posts=calls.filter(c=>c.body);expect(posts[1].body).toBe(posts[0].body);
  expect(calls[1].url).toContain('/operations/');
});
it('reconciles a committed save on remount without losing or falsely resaving its text', async () => {
  const written='Hi Studio North';
  const { draftBufferKey,retainPending }=await import('../src/api/pendingOperations');
  localStorage.setItem(draftBufferKey(did,cid),JSON.stringify({text:written,recipient:draft.recipient,base:draft.id}));
  retainPending(did,cid,{kind:'edit',path:'/draft-versions',operation:{schema_version:'1',operation_id:'old-operation',parent_version_id:draft.id,exact_text:written,recipient:draft.recipient}});
  const api=new ApiClient(async()=>new Response(JSON.stringify(receipt)));
  render(<DraftReview api={api} view={{...view,draft:{...draft,id:'new-head',version:2,exact_text:written}} as any} onRefresh={()=>{}} />);
  await screen.findByText('New unapproved version saved.');
  await waitFor(()=>expect(localStorage.getItem(draftBufferKey(did,cid))).toBeNull());
  expect(screen.queryByText(/A newer saved version exists/)).not.toBeInTheDocument();
});
it('retains newer typing when an earlier saved payload commits', async () => {
  let finish!:(response:Response)=>void;
  const api=new ApiClient(async()=>new Promise<Response>(resolve=>{finish=resolve;}));
  render(<DraftReview api={api} view={view as any} onRefresh={()=>{}} />);
  fireEvent.change(screen.getByLabelText('Draft text'),{target:{value:'Text A'}});
  fireEvent.click(screen.getByRole('button',{name:'Save unapproved version'}));
  fireEvent.change(screen.getByLabelText('Draft text'),{target:{value:'Newer unsaved text B'}});
  finish(new Response(JSON.stringify(receipt)));
  await screen.findByText('New unapproved version saved.');
  expect(screen.getByLabelText('Draft text')).toHaveValue('Newer unsaved text B');
  expect(localStorage.getItem(`promisekeeper.unsaved-draft.${did}.${cid}`)).toContain('Newer unsaved text B');
});
it('keeps conflicted unsaved wording until an explicit decision to adopt the current saved head', () => {
  localStorage.setItem(`promisekeeper.unsaved-draft.${did}.${cid}`,JSON.stringify({text:'Unsaved older wording',recipient:draft.recipient,base:'older-head'}));
  render(<DraftReview api={new ApiClient()} view={view as any} onRefresh={()=>{}} />);
  expect(screen.getByLabelText('Draft text')).toHaveValue('Unsaved older wording');
  fireEvent.click(screen.getByRole('button',{name:'Discard unsaved wording and use saved version'}));
  expect(screen.getByLabelText('Draft text')).toHaveValue(draft.exact_text);
  expect(screen.getByRole('button',{name:'Approve exact saved version'})).toBeEnabled();
});
