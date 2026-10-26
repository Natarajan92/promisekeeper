import { afterEach,expect,it,vi } from 'vitest';
import { act,cleanup,fireEvent,render,screen } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { OwnerDecisions } from '../src/history/OwnerDecisions';
import { ScenarioUpdate } from '../src/history/ScenarioUpdate';
import { CaseHistory } from '../src/history/CaseHistory';
import { ApiClient } from '../src/api/client';
import { caseView,cid,did } from './fixtures';
afterEach(()=>{cleanup();localStorage.clear();vi.restoreAllMocks();});
const result={investigation_id:'44444444-4444-4444-8444-444444444444',result_hash:'a'.repeat(64),action:'CLOSE',status:'COMPLETE',financial_label:'VERIFIED_REMAINDER',next_step:'Review the exact settlement.',limitations:[],commitments:[],claims:[],contradictions:[],unresolved_questions:[],timeline:[],financial_facts:{...caseView.financial_facts,balance:{currency:'INR',minor_units:'0'}},explanation:{text:'Verified settlement.',sources:[]},evaluation_at:'2026-10-24T00:00:00Z'};
const allowed={allowed:true,blocking_reasons:[]};
const view={...caseView,current_result:result,latest_completed_result:result,allowed_commands:{close:allowed,reopen:{allowed:false,blocking_reasons:['CASE_OPEN']},disposition:allowed},owner_dispositions:[]};
const committed={schema_version:'1',receipt:{operation_id:'op',operation_type:'CLOSE_CASE',target_id:cid,committed_at:'2026-10-24T00:00:00Z',outcome:'CLOSED',case_revision:1}};
it('requires explicit exact-result closure confirmation before sending a command',async()=>{
  const calls:any[]=[];const api=new ApiClient(async(_url,init)=>{calls.push(JSON.parse(init!.body as string));return new Response(JSON.stringify(committed));});
  render(<OwnerDecisions api={api} view={view as any} onRefresh={()=>{}}/>);
  fireEvent.click(screen.getByRole('button',{name:'Review case closure'}));
  expect(screen.getByRole('button',{name:'Confirm case closure'})).toBeDisabled();expect(calls).toHaveLength(0);
  fireEvent.click(screen.getByLabelText('Confirm closure of invoice INV-001'));
  fireEvent.click(screen.getByRole('button',{name:'Confirm case closure'}));await screen.findByText('Decision saved.');
  expect(calls[0]).toMatchObject({confirm:true,investigation_id:result.investigation_id,confirmed_result_hash:result.result_hash,expected_case_revision:0});
});
it('shows stale closure blocking reasons and never closes by accepting advice',async()=>{
  let payload:any;const api=new ApiClient(async(_url,init)=>{payload=JSON.parse(init!.body as string);return new Response(JSON.stringify(committed));});
  render(<OwnerDecisions api={api} view={{...view,allowed_commands:{...view.allowed_commands,close:{allowed:false,blocking_reasons:['EVIDENCE_CHANGED']}}} as any} onRefresh={()=>{}}/>);
  expect(screen.getByText(/evidence changed/i)).toBeInTheDocument();expect(screen.getByRole('button',{name:'Review case closure'})).toBeDisabled();
  fireEvent.change(screen.getByLabelText('Advice decision reason (optional)'),{target:{value:'Reviewing the settlement'}});
  fireEvent.click(screen.getByRole('button',{name:'Accept recommendation'}));await screen.findByText('Decision saved.');
  expect(payload).toMatchObject({decision:'ACCEPT',reason:'Reviewing the settlement'});expect(payload).not.toHaveProperty('confirm');
});

it('reopens only after an explicit confirmation and retains its optional owner reason',async()=>{
  let payload:any;const api=new ApiClient(async(_url,init)=>{payload=JSON.parse(init!.body as string);return new Response(JSON.stringify(committed));});
  render(<OwnerDecisions api={api} view={{...view,lifecycle:'CLOSED',allowed_commands:{...view.allowed_commands,reopen:allowed}} as any} onRefresh={()=>{}}/>);
  fireEvent.change(screen.getByLabelText('Advice decision reason (optional)'),{target:{value:'New conflicting evidence'}});
  fireEvent.click(screen.getByRole('button',{name:'Review case reopening'}));expect(screen.getByRole('button',{name:'Confirm case reopening'})).toBeDisabled();
  fireEvent.click(screen.getByLabelText('Confirm reopening of invoice INV-001'));fireEvent.click(screen.getByRole('button',{name:'Confirm case reopening'}));await screen.findByText('Decision saved.');expect(payload).toMatchObject({expected_case_revision:0,confirm:true,reason:'New conflicting evidence'});
});
it('invalidates checked closure when the result changes without a revision change',()=>{
  const api=new ApiClient();const {rerender}=render(<OwnerDecisions api={api} view={view as any} onRefresh={()=>{}}/>);
  fireEvent.click(screen.getByRole('button',{name:'Review case closure'}));fireEvent.click(screen.getByLabelText('Confirm closure of invoice INV-001'));
  rerender(<OwnerDecisions api={api} view={{...view,current_result:{...result,result_hash:'c'.repeat(64)}} as any} onRefresh={()=>{}}/>);
  expect(screen.queryByRole('button',{name:'Confirm case closure'})).not.toBeInTheDocument();
});
it('recovers a committed deletion receipt once while preserving another copy pending work',async()=>{
  const other='other-copy';localStorage.setItem(`promisekeeper.pending.${other}.${cid}`,'other payload');
  localStorage.setItem(`promisekeeper.pending.${did}.${cid}`,JSON.stringify({kind:'deletion',path:`/demonstrations/${did}/deletion`,operation:{schema_version:'1',operation_id:'pending-delete',confirm:true,confirmed_demonstration_id:did}}));
  const api=new ApiClient(async()=>new Response(JSON.stringify({...committed,receipt:{...committed.receipt,outcome:'DELETED'}})));
  render(<OwnerDecisions api={api} view={view as any} onRefresh={()=>{}}/>);await screen.findByText('Selected demonstration deleted.');expect(localStorage.getItem(`promisekeeper.pending.${did}.${cid}`)).toBeNull();expect(localStorage.getItem(`promisekeeper.pending.${other}.${cid}`)).toBe('other payload');
});

it('inspects an exact historical review and source without altering the current record',async()=>{
  const onSource=vi.fn();const review={id:'review-old',draft_version_id:'draft-old',decision:'REJECT',decided_at:result.evaluation_at,recipient:'Original recipient',invoice_id:'INV-001',exact_text:'Reviewed old exact text.',payload_hash:'old-hash',review_epoch:1,investigation_id:result.investigation_id};
  const api=new ApiClient(async()=>new Response(JSON.stringify({schema_version:'1',result:{...result,timeline:[{source_id:'original-message',evidence_version_id:'source-old',event_at:null,arrived_at:result.evaluation_at}]}})));
  render(<CaseHistory api={api} view={{...view,draft_reviews:[review]} as any} events={[{id:'old',sequence:1,event_type:'DRAFT_REVIEWED',occurred_at:result.evaluation_at,payload:{draft_review_id:review.id,investigation_id:result.investigation_id}}] as any} cursor={null} onMore={()=>{}} onSource={onSource}/>);
  fireEvent.click(screen.getByText('Inspect exact draft review'));expect(screen.getByText('Reviewed old exact text.')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button',{name:'Inspect investigation'}));await screen.findByText('Historical recommendation: CLOSE');fireEvent.click(screen.getByRole('button',{name:'Inspect historical source original-message'}));expect(onSource).toHaveBeenCalledWith('source-old');
});
it('shows full historical findings, original commitments and unresolved questions',async()=>{
  const prior={...result,next_step:'Original investigation next step.',limitations:['ORIGINAL_LIMITATION'],commitments:[{source_id:'old-message',evidence_version_id:'source-old',amount:{currency:'INR',minor_units:'100'},expires_at:null,fulfilled:false,fulfillment_unresolved:true,credited:{currency:'INR',minor_units:'0'},superseded:false,commitment_stable_id:'original-commitment'}],unresolved_questions:[{field:'ORIGINAL_QUESTION',sources:[]}]};
  const api=new ApiClient(async()=>new Response(JSON.stringify({schema_version:'1',result:prior})));
  render(<CaseHistory api={api} view={view as any} events={[{id:'old',sequence:1,event_type:'INVESTIGATION_COMPLETED',occurred_at:result.evaluation_at,payload:{investigation_id:result.investigation_id}}] as any} cursor={null} onMore={()=>{}} onSource={()=>{}}/>);fireEvent.click(screen.getByRole('button',{name:'Inspect investigation'}));await screen.findByText('Historical recommendation: CLOSE');expect(screen.getByText('Original investigation next step.')).toBeInTheDocument();expect(screen.getByText('original-commitment')).toBeInTheDocument();expect(screen.getByText('original question')).toBeInTheDocument();
});
it('ignores a historical response after navigating to another case',async()=>{
  let finish!:(value:Response)=>void;const api=new ApiClient(()=>new Promise(resolve=>{finish=resolve;}));
  const events=[{id:'old',sequence:1,event_type:'DRAFT_SAVED',occurred_at:result.evaluation_at,payload:{draft_version_id:'draft-old'}}];
  const props={api,view:view as any,events:events as any,cursor:null,onMore:()=>{},onSource:()=>{}};const {rerender}=render(<CaseHistory {...props}/>);
  fireEvent.click(screen.getByRole('button',{name:'Inspect saved draft'}));rerender(<CaseHistory {...props} view={{...view,id:'another-case'} as any}/>);
  await act(async()=>finish(new Response(JSON.stringify({schema_version:'1',draft_version:{id:'draft-old',exact_text:'Stale response text'}}))));expect(screen.queryByText('Stale response text')).not.toBeInTheDocument();
});
it('allows a fresh scenario preview after case revision changes during a preview request',async()=>{
  let finish!:(value:Response)=>void;const api=new ApiClient(()=>new Promise(resolve=>{finish=resolve;}));
  const props={api,view:view as any,selectedVariantId:null,events:[{id:'U1',case_id:'PK-001',kind:'CLOCK' as const,eligible_variant_ids:[null],evaluation_at:'2026-10-25T00:00:00Z'}],onRefresh:()=>{}};
  const {rerender}=render(<ScenarioUpdate {...props}/>);fireEvent.click(screen.getByRole('button',{name:'Preview selected fictional update'}));
  rerender(<ScenarioUpdate {...props} view={{...view,case_revision:1} as any}/>);
  await act(async()=>finish(new Response(JSON.stringify({schema_version:'1',demonstration_id:did,case_id:cid,event_id:'U1',expected_case_revision:0}))));
  expect(screen.queryByText('Exact update preview')).not.toBeInTheDocument();expect(screen.getByRole('button',{name:'Preview selected fictional update'})).toBeEnabled();
});
it('requires the exact visible fixture preview before confirmation and discards stale previews',async()=>{
  const posts:any[]=[];const preview={schema_version:'1',catalogue_version:'release-0.1',demonstration_id:did,case_id:cid,event_id:'U1',expected_case_revision:0,evidence_changes:[],clock_change:{from:'2026-10-24T00:00:00Z',to:'2026-10-25T00:00:00Z'},preview_hash:'b'.repeat(64)};
  const api=new ApiClient(async(_url,init)=>{if(!init?.body)return new Response(JSON.stringify(preview));posts.push(JSON.parse(init.body as string));return new Response(JSON.stringify({schema_version:'1',error:{code:'PREVIEW_CHANGED',message:'Preview changed. Review again.'}}),{status:409});});
  render(<ScenarioUpdate api={api} view={view as any} selectedVariantId={null} events={[{id:'U1',case_id:'PK-001',kind:'CLOCK',eligible_variant_ids:[null],evaluation_at:'2026-10-25T00:00:00Z'}]} onRefresh={()=>{}}/>);
  fireEvent.click(screen.getByRole('button',{name:'Preview selected fictional update'}));await screen.findByText(/Exact update preview/);
  fireEvent.click(screen.getByLabelText('I reviewed this exact fictional update'));
  fireEvent.click(screen.getByRole('button',{name:'Confirm fictional update'}));await screen.findByText('Preview changed. Review again.');
  expect(posts[0]).toMatchObject({expected_case_revision:0,confirmed_preview_hash:preview.preview_hash,event_id:'U1'});
  expect(screen.queryByRole('button',{name:'Confirm fictional update'})).not.toBeInTheDocument();
});
it('opens prior exact result and draft from immutable event references',async()=>{
  const api=new ApiClient(async(url)=>new Response(JSON.stringify(String(url).includes('draft-versions')?{schema_version:'1',draft_version:{id:'draft-old',recipient:'Studio North',invoice_id:'INV-001',version:1,exact_text:'Original exact draft.'}}:{schema_version:'1',result:{...result,action:'FOLLOW_UP'}})));
  const events=[{id:'event-1',sequence:1,event_type:'DRAFT_SAVED',occurred_at:result.evaluation_at,payload:{draft_version_id:'draft-old',investigation_id:result.investigation_id}}];
  render(<CaseHistory api={api} view={view as any} events={events as any} cursor={null} onMore={()=>{}} onSource={()=>{}}/>);
  fireEvent.click(screen.getByRole('button',{name:'Inspect saved draft'}));await screen.findByText('Original exact draft.');
  fireEvent.click(screen.getByRole('button',{name:'Inspect investigation'}));await screen.findByText('Historical recommendation: FOLLOW_UP');
});
