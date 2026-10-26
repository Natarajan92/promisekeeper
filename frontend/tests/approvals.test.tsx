import {afterEach,describe,expect,it,vi} from 'vitest';
import {act,cleanup,fireEvent,render,screen,waitFor,within} from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import App from '../src/App';
import {ApiClient} from '../src/api/client';
import {buildQueue} from '../src/approvals/queue';
import type {CaseEntry} from '../src/store/useWorkspace';
import {caseView,demo,did,facts} from './fixtures';

afterEach(()=>{cleanup();localStorage.clear();window.location.hash='';vi.restoreAllMocks();});

const allowed={allowed:true,blocking_reasons:[]};
const result=(id:string,action:string)=>({investigation_id:`inv-${id}`,snapshot_id:'s',snapshot_hash:'h',evaluation_at:caseView.evaluation_at,status:'COMPLETE',financial_facts:facts,financial_label:'VERIFIED_REMAINDER',commitments:[],claims:[],timeline:[],contradictions:[],unresolved_questions:[],limitations:[],action,reason_code:'R',explanation:{text:'Saved explanation.',sources:[]},next_step:`Next step for ${id}.`,review_at:null,result_hash:'r'.repeat(64)});
const draftFor=(id:string)=>({id:`draft-${id}`,demonstration_id:did,case_id:id,investigation_id:`inv-${id}`,parent_version_id:null,recipient:`Client ${id}`,invoice_id:`INV-${id}`,exact_text:`Hello Client ${id},\nPlease review the invoice.\nThank you.`,version:1,payload_hash:'a'.repeat(64),created_at:caseView.evaluation_at,validation_status:'VALID',validation_reasons:[]});
const disposition=(id:string)=>({id:`disp-${id}`,demonstration_id:did,case_id:id,operation_id:'op',investigation_id:`inv-${id}`,decision:'ACCEPT',reason:null,decided_at:caseView.evaluation_at});
// A case with a current FOLLOW_UP result and an unapproved valid draft, its recommendation already accepted.
function view(id:string,changes:Record<string,unknown>={}) {
  const current=result(id,'FOLLOW_UP');
  return {...caseView,id,client:`Client ${id}`,invoice_id:`INV-${id}`,freshness:'CURRENT',running_attempt:null,latest_completed_result:current,current_result:current,
    draft:draftFor(id),current_draft_version_id:`draft-${id}`,review_state:'UNAPPROVED',draft_reviews:[],draft_generation_attempt:null,no_draft_reason:null,
    owner_dispositions:[disposition(id)],
    allowed_commands:{...caseView.allowed_commands,edit_draft:allowed,approve_draft:allowed,reject_draft:allowed,disposition:allowed,close:{allowed:false,blocking_reasons:['NOT_SETTLED']},reopen:{allowed:false,blocking_reasons:['CASE_NOT_CLOSED']}},
    ...changes};
}
const summary=(id:string)=>({...caseView,id,client:`Client ${id}`,invoice_id:`INV-${id}`,currency:'INR',due_at:null,has_previous_investigation:false,balance:facts.balance,balance_label:'VERIFIED_REMAINDER',recommended_action:'FOLLOW_UP',review_at:null});
const entry=(changes:Record<string,unknown>={},id='a'):CaseEntry=>({summary:summary(id) as never,view:view(id,changes) as never,error:null});
const kinds=(cases:CaseEntry[])=>buildQueue(cases).map(item=>item.kind);

describe('buildQueue',()=>{
  it('lists a valid unapproved draft on a current follow-up as a reminder',()=>{
    const [item]=buildQueue([entry()]);
    expect(item).toMatchObject({kind:'REMINDER',caseId:'a',client:'Client a',amount:facts.balance});
    expect(item.id).toBeTruthy();expect(item.title).toBeTruthy();expect(item.reason).toBeTruthy();
  });
  it('lists nothing for an approved or rejected draft once the recommendation is decided',()=>{
    expect(kinds([entry({review_state:'APPROVED'})])).toEqual([]);
    expect(kinds([entry({review_state:'REJECTED'})])).toEqual([]);
  });
  it('lists an approved draft as a suggestion while the current recommendation has no disposition',()=>{
    expect(kinds([entry({review_state:'APPROVED',owner_dispositions:[]})])).toEqual(['SUGGESTION']);
    // A disposition for an older investigation is not a decision on the current result.
    expect(kinds([entry({review_state:'APPROVED',owner_dispositions:[{...disposition('a'),investigation_id:'inv-old'}]})])).toEqual(['SUGGESTION']);
  });
  it('folds the suggestion into the reminder rather than listing the case twice',()=>{
    expect(kinds([entry({owner_dispositions:[]})])).toEqual(['REMINDER']);
  });
  it('does not list an invalid draft as a reminder',()=>{
    expect(kinds([entry({draft:{...draftFor('a'),validation_status:'INVALID'}})])).toEqual([]);
  });
  it('lists a CLOSE recommendation only when closure is allowed',()=>{
    const close=result('a','CLOSE');
    const closing={current_result:close,latest_completed_result:close,draft:null,current_draft_version_id:null,review_state:'NONE'};
    expect(kinds([entry({...closing,allowed_commands:{...view('a').allowed_commands,close:allowed}})])).toEqual(['CLOSURE']);
    expect(kinds([entry(closing)])).toEqual([]);
  });
  it('keeps an accepted CLOSE recommendation as a closure until the case is closed',()=>{
    const close=result('a','CLOSE');
    const closing={current_result:close,latest_completed_result:close,draft:null,current_draft_version_id:null,review_state:'NONE',allowed_commands:{...view('a').allowed_commands,close:allowed}};
    expect(kinds([entry({...closing,owner_dispositions:[disposition('a')]})])).toEqual(['CLOSURE']);
    expect(kinds([entry({...closing,owner_dispositions:[]})])).toEqual(['CLOSURE']);
  });
  it('lists an undecided VERIFY_PAYMENT recommendation as a payment check, and drops it once accepted or rejected',()=>{
    const verify=result('a','VERIFY_PAYMENT');
    const checking={current_result:verify,latest_completed_result:verify,draft:null,current_draft_version_id:null,review_state:'NONE'};
    expect(kinds([entry({...checking,owner_dispositions:[]})])).toEqual(['PAYMENT_CHECK']);
    expect(kinds([entry({...checking,owner_dispositions:[disposition('a')]})])).toEqual([]);
    expect(kinds([entry({...checking,owner_dispositions:[{...disposition('a'),decision:'REJECT'}]})])).toEqual([]);
    // A disposition on an older investigation does not settle the current check.
    expect(kinds([entry({...checking,owner_dispositions:[{...disposition('a'),investigation_id:'inv-old'}]})])).toEqual(['PAYMENT_CHECK']);
  });
  it('lists nothing while an investigation runs or when the result is not current',()=>{
    expect(kinds([entry({running_attempt:'attempt-1'})])).toEqual([]);
    expect(kinds([entry({freshness:'EVIDENCE_CHANGED'})])).toEqual([]);
    expect(kinds([entry({freshness:'TIME_EXPIRED',owner_dispositions:[]})])).toEqual([]);
  });
  it('lists nothing for a closed case',()=>{
    const close=result('a','CLOSE');
    expect(kinds([entry({lifecycle:'CLOSED',current_result:close,latest_completed_result:close,owner_dispositions:[],allowed_commands:{...view('a').allowed_commands,close:allowed}})])).toEqual([]);
  });
  it('lists nothing for a case without a current result',()=>{
    expect(kinds([entry({current_result:null,owner_dispositions:[]})])).toEqual([]);
    expect(kinds([entry({current_result:null,latest_completed_result:null,owner_dispositions:[]})])).toEqual([]);
  });
  it('skips entries whose view is missing (loading or failed)',()=>{
    expect(buildQueue([{summary:summary('a') as never,view:null,error:'Case unavailable'}])).toEqual([]);
  });
});

const reply=(value:unknown,status=200)=>new Response(JSON.stringify({schema_version:'1',...(value as object)}),{status});
const receipt=(cid:string)=>({receipt:{operation_id:'op',operation_type:'REVIEW_DRAFT',target_id:cid,committed_at:caseView.evaluation_at,outcome:'APPROVED',case_revision:1}});
// Two cases wait: "a" has a reminder draft and "b" a payment check. Case "c" fails to load.
function workspaceApi({failing,undecided,closure,gate}:{failing?:string;undecided?:boolean;closure?:boolean;gate?:Promise<void>}={}) {
  const views:Record<string,Record<string,unknown>>={a:view('a',undecided?{owner_dispositions:[]}:{}),b:view('b',{current_result:result('b','VERIFY_PAYMENT'),latest_completed_result:result('b','VERIFY_PAYMENT'),draft:null,current_draft_version_id:null,review_state:'NONE',owner_dispositions:[]})};
  if(closure)views.d=view('d',{current_result:result('d','CLOSE'),latest_completed_result:result('d','CLOSE'),draft:null,current_draft_version_id:null,review_state:'NONE',allowed_commands:{...view('d').allowed_commands,close:allowed}});
  const posts:{url:string;body:Record<string,unknown>}[]=[];
  const api=new ApiClient(async(input,init)=>{
    const url=String(input);
    if(init?.method==='POST'){
      const body=JSON.parse(String(init.body));posts.push({url,body});
      if(url.includes('/cases/a/draft-reviews')){views.a={...views.a,review_state:'APPROVED',case_revision:1,draft_reviews:[{id:'rev-1',draft_version_id:'draft-a',decision:body.decision,decided_at:caseView.evaluation_at,recipient:'Client a',invoice_id:'INV-a',exact_text:'x',payload_hash:'a'.repeat(64),review_epoch:0,investigation_id:'inv-a'}]};return reply(receipt('a'));}
      return reply({error:{code:'UNEXPECTED',message:'Unexpected write'}},500);
    }
    if(url.endsWith('/health'))return reply({ready:true,agent_mode:'STUB'});
    if(url.endsWith('/catalogue'))return reply({catalogue_version:'release-0.1',variant_ids:[]});
    if(url.endsWith('/demonstrations'))return reply({demonstrations:[demo]});
    if(url.endsWith('/cases'))return reply({demonstration_id:did,clock_mode:'REFERENCE',evaluation_at:caseView.evaluation_at,cases:['a','b',...(closure?['d']:[]),...(failing?[failing]:[])].map(summary)});
    const match=/\/cases\/([^/?]+)\?/.exec(url);
    if(match){
      if(gate)await gate;
      if(match[1]===failing)return reply({error:{code:'STORAGE_UNAVAILABLE',message:'Case unavailable'}},503);
      return reply(views[match[1]]);
    }
    return reply({});
  });
  return {api,posts,views};
}
const badge=()=>within(screen.getByRole('link',{name:/^Approvals/})).queryByText(/^\d+$/);

describe('ApprovalsPage',()=>{
  it('shows the same draft review for a reminder and recomputes the queue and badge after approval',async()=>{
    localStorage.setItem('selected_demonstration_id',did);window.location.hash='#/approvals';
    const {api,posts}=workspaceApi();
    render(<App api={api}/>);
    expect(await screen.findByRole('heading',{level:1,name:'Your approvals'})).toBeInTheDocument();
    const queue=await screen.findByRole('list',{name:'Waiting for you'});
    await waitFor(()=>expect(within(queue).getAllByRole('link')).toHaveLength(2));
    expect(badge()).toHaveTextContent('2');
    fireEvent.click(within(queue).getByRole('link',{name:/Client a/}));
    await waitFor(()=>expect(window.location.hash).toMatch(/^#\/approvals\?item=/));
    const approve=await screen.findByRole('button',{name:'Approve exact saved version'});
    expect(screen.getByRole('heading',{name:'Communication review'})).toBeInTheDocument();
    expect(screen.getByRole('link',{name:'Open full case →'})).toHaveAttribute('href','#/cases/a');
    fireEvent.click(approve);
    await waitFor(()=>expect(posts).toHaveLength(1));
    expect(posts[0].url).toContain('/cases/a/draft-reviews');expect(posts[0].body.decision).toBe('APPROVE');
    // The shared store refreshes: the reminder leaves the queue and the badge drops without a reload.
    await waitFor(()=>expect(within(screen.getByRole('list',{name:'Waiting for you'})).getAllByRole('link')).toHaveLength(1));
    expect(within(screen.getByRole('list',{name:'Waiting for you'})).queryByRole('link',{name:/Client a/})).not.toBeInTheDocument();
    await waitFor(()=>expect(badge()).toHaveTextContent('1'));
    // The decided case stays open in the pane so the approved hand-off (copy) remains available.
    expect(await screen.findByText(/no longer waiting for you/i)).toBeInTheDocument();
    expect(screen.getByRole('button',{name:'Copy approved message'})).toBeInTheDocument();
  });

  it('keeps the approved draft open and highlights the same case when its recommendation is still undecided',async()=>{
    localStorage.setItem('selected_demonstration_id',did);window.location.hash='#/approvals';
    const {api}=workspaceApi({undecided:true});
    render(<App api={api}/>);
    const queue=await screen.findByRole('list',{name:'Waiting for you'});
    await waitFor(()=>expect(within(queue).getAllByRole('link')).toHaveLength(2));
    fireEvent.click(within(queue).getByRole('link',{name:/Client a.*Reminder draft to review/}));
    fireEvent.click(await screen.findByRole('button',{name:'Approve exact saved version'}));
    // The reminder is decided, but the approved draft's recommendation still waits: same count, same case highlighted.
    await waitFor(()=>expect(within(screen.getByRole('list',{name:'Waiting for you'})).getByRole('link',{name:/Client a.*Recommendation: Follow up/})).toHaveAttribute('aria-current','true'));
    expect(badge()).toHaveTextContent('2');
    expect(screen.getByText(/The reminder is no longer waiting for you. This case still has a recommendation waiting for you below./)).toBeInTheDocument();
    expect(screen.getByRole('button',{name:'Copy approved message'})).toBeInTheDocument();
    expect(screen.getByRole('button',{name:'Accept recommendation'})).toBeEnabled();
  });

  it('shows the evidence and the recommendation decision for a payment check',async()=>{
    localStorage.setItem('selected_demonstration_id',did);window.location.hash='#/approvals';
    const {api}=workspaceApi();
    render(<App api={api}/>);
    const queue=await screen.findByRole('list',{name:'Waiting for you'});
    await waitFor(()=>expect(within(queue).getAllByRole('link')).toHaveLength(2));
    fireEvent.click(within(queue).getByRole('link',{name:/Client b/}));
    expect(await screen.findByRole('heading',{name:'Saved evidence'})).toBeInTheDocument();
    expect(screen.getByRole('button',{name:'Accept recommendation'})).toBeInTheDocument();
    expect(screen.getByRole('button',{name:'Reject recommendation'})).toBeInTheDocument();
    expect(screen.queryByRole('button',{name:'Approve exact saved version'})).not.toBeInTheDocument();
  });

  it('shows the exact closure review for a closure item',async()=>{
    localStorage.setItem('selected_demonstration_id',did);window.location.hash='#/approvals';
    const {api}=workspaceApi({closure:true});
    render(<App api={api}/>);
    const queue=await screen.findByRole('list',{name:'Waiting for you'});
    await waitFor(()=>expect(within(queue).getAllByRole('link')).toHaveLength(3));
    fireEvent.click(within(queue).getByRole('link',{name:/Client d.*Closure ready for review/}));
    fireEvent.click(await screen.findByRole('button',{name:'Review case closure'}));
    expect(screen.getByRole('heading',{name:'Exact closure review'})).toBeInTheDocument();
    expect(screen.getByRole('button',{name:'Confirm case closure'})).toBeDisabled();
    fireEvent.click(screen.getByLabelText('Confirm closure of invoice INV-d'));
    expect(screen.getByRole('button',{name:'Confirm case closure'})).toBeEnabled();
    expect(screen.queryByRole('button',{name:'Approve exact saved version'})).not.toBeInTheDocument();
  });

  it('shows no badge number after the case list loads but before every case view resolves',async()=>{
    localStorage.setItem('selected_demonstration_id',did);window.location.hash='#/approvals';
    let release!:()=>void;const gate=new Promise<void>(resolve=>{release=resolve;});
    const {api}=workspaceApi({gate});
    render(<App api={api}/>);
    // The Cases badge comes from the list, so the list has loaded while the views are still held back.
    await waitFor(()=>expect(within(screen.getByRole('link',{name:/^Cases/})).getByText('2')).toBeInTheDocument());
    expect(badge()).toBeNull();
    expect(screen.getByText('Loading your approvals…')).toBeInTheDocument();
    await act(async()=>{release();});
    await waitFor(()=>expect(badge()).toHaveTextContent('2'));
  });

  it('filters by kind and hides filters that have no items',async()=>{
    localStorage.setItem('selected_demonstration_id',did);window.location.hash='#/approvals';
    const {api}=workspaceApi();
    render(<App api={api}/>);
    const queue=await screen.findByRole('list',{name:'Waiting for you'});
    await waitFor(()=>expect(within(queue).getAllByRole('link')).toHaveLength(2));
    const filters=screen.getByRole('group',{name:'Show'});
    expect(within(filters).getAllByRole('button').map(button=>button.textContent)).toEqual(['All 2','Reminders 1','Payments 1']);
    fireEvent.click(within(filters).getByRole('button',{name:'Payments 1'}));
    expect(within(filters).getByRole('button',{name:'Payments 1'})).toHaveAttribute('aria-pressed','true');
    expect(within(screen.getByRole('list',{name:'Waiting for you'})).getAllByRole('link').map(link=>link.textContent)).toEqual([expect.stringContaining('Client b')]);
  });

  it('lists a case that could not load with a retry instead of dropping it, and shows no badge number while loading',async()=>{
    localStorage.setItem('selected_demonstration_id',did);window.location.hash='#/approvals';
    const {api}=workspaceApi({failing:'c'});
    const fetches=vi.spyOn(api,'cases');
    render(<App api={api}/>);
    expect(badge()).toBeNull();
    expect(await screen.findByText(/Client c/)).toBeInTheDocument();
    expect(screen.getByText(/couldn.t load/i)).toBeInTheDocument();
    const before=fetches.mock.calls.length;
    await act(async()=>{fireEvent.click(screen.getByRole('button',{name:'Retry loading cases'}));});
    await waitFor(()=>expect(fetches.mock.calls.length).toBeGreaterThan(before));
  });
});
