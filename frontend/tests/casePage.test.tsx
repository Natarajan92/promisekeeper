import {afterEach,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,screen,waitFor,within} from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import App from '../src/App';
import {ApiClient} from '../src/api/client';
import type {CaseView, Evidence} from '../src/api/types';
import {before} from './comparisonFixtures';
import {caseView,cid,demo,did,source} from './fixtures';

afterEach(()=>{cleanup();localStorage.clear();window.location.hash='';vi.restoreAllMocks();});

const promise:Evidence={...source,id:'promise-version',stable_source_id:'PK-001-M1',original_content:'Namaste. We will pay INR 30,000 by 20 October 2026. Thanks.',event_at:'2026-10-13T05:30:00Z',
  commitment_anchors:[{id:'anchor-1',evidence_version_id:'promise-version',commitment_key:'PK-001-M1-C1',clause_start:9,clause_end:51}]} as Evidence;
const invoice:Evidence={...source,id:'invoice-version',stable_source_id:'PK-001-I1',kind:'INVOICE',authoritative:true,original_content:'Fictional invoice INV-001; INR 50,000.00.',
  data:{invoice_id:'INV-001',amount_text:'50,000.00',currency_text:'INR',due_text:'20 October 2026'}} as Evidence;
const result={...before,action:'FOLLOW_UP' as const,financial_label:'VERIFIED_REMAINDER' as const,claims:[],
  financial_facts:{...before.financial_facts,invoice:{currency:'INR' as const,minor_units:'5000000'},paid:{currency:'INR' as const,minor_units:'2000000'},balance:{currency:'INR' as const,minor_units:'3000000'}},
  commitments:[{commitment_stable_id:'anchor-1',commitment_key:'PK-001-M1-C1',source_id:'PK-001-M1',evidence_version_id:'promise-version',amount:{currency:'INR' as const,minor_units:'3000000'},expires_at:'2026-10-20T18:30:00Z',fulfilled:false,fulfillment_unresolved:false,credited:{currency:'INR' as const,minor_units:'0'},superseded:false}],
  timeline:[{source_id:'PK-001-M1',evidence_version_id:'promise-version',kind:'MESSAGE',event_at:'2026-10-13T05:30:00Z',arrived_at:'2026-10-13T05:30:00Z',undated:false}],
  explanation:{text:'Verified evidence supports following up on the overdue remainder.',sources:['PK-001-M1']},next_step:'Review a follow-up draft.'};
const view={...caseView,evidence:[invoice,promise],latest_completed_result:result,current_result:result,freshness:'CURRENT',
  allowed_commands:{...caseView.allowed_commands,disposition:{allowed:true,blocking_reasons:[]}}} as unknown as CaseView;

function caseApi(detail:CaseView=view) {
  const evidence=vi.fn();
  const api=new ApiClient(async input=>{
    const url=String(input);
    if(url.includes('/evidence-versions/')){evidence(url);return new Response(JSON.stringify(promise));}
    const body=url.endsWith('/health')?{ready:true,agent_mode:'STUB'}:url.endsWith('/catalogue')?{catalogue_version:'release-0.1',variant_ids:[]}:url.endsWith('/demonstrations')?{demonstrations:[demo]}
      :url.endsWith('/cases')?{demonstration_id:did,clock_mode:'REFERENCE',evaluation_at:caseView.evaluation_at,cases:[{...caseView,currency:'INR',due_at:null,has_previous_investigation:true,balance:{currency:'INR',minor_units:'3000000'},balance_label:'VERIFIED_REMAINDER',recommended_action:'FOLLOW_UP',review_at:null}]}
      :url.includes('/morning-reviews/latest')?{morning_review:null}:url.includes('/history')?{events:[],next_cursor:null}:url.includes('/investigations')?{investigations:[],next_cursor:null}:detail;
    return new Response(JSON.stringify({schema_version:'1',...body}));
  });
  return {api,evidence};
}

it("explains a case that isn't in the current workspace",async()=>{
  window.location.hash='#/cases/somewhere-else';
  render(<App api={caseApi().api}/>);
  expect(await screen.findByRole('heading',{level:1,name:"This case isn't in the current workspace"})).toBeInTheDocument();
  expect(screen.getByRole('link',{name:'Back to Cases'})).toHaveAttribute('href','#/cases');
});

it('shows the case header with breadcrumb, status chip and the three money figures',async()=>{
  window.location.hash=`#/cases/${cid}`;
  render(<App api={caseApi().api}/>);
  await screen.findByRole('heading',{level:1,name:'Studio North'});
  expect(screen.getByRole('link',{name:'All cases'})).toHaveAttribute('href','#/cases');
  const figures=screen.getByRole('list',{name:'Money for this invoice'});
  expect(within(figures).getByText('Invoice').closest('li')).toHaveTextContent('₹50,000.00');
  expect(within(figures).getByText('Received').closest('li')).toHaveTextContent('₹20,000.00');
  expect(within(figures).getByText('Still to collect').closest('li')).toHaveTextContent('₹30,000.00');
  expect(screen.getAllByRole('heading',{level:1})).toHaveLength(1);
});

it('opens on the Overview with the story, the highlighted promise and View original',async()=>{
  window.location.hash=`#/cases/${cid}`;
  const {api,evidence}=caseApi();
  render(<App api={api}/>);
  await screen.findByRole('heading',{level:1,name:'Studio North'});
  expect(screen.getByRole('button',{name:'Overview'})).toHaveAttribute('aria-current','page');
  const story=screen.getByRole('list',{name:'What happened'});
  expect(within(story).getByText('We will pay INR 30,000 by 20 October 2026.').tagName).toBe('MARK');
  expect(within(story).getByText(/Invoice INV-001 raised for ₹50,000.00/)).toBeInTheDocument();
  expect(within(story).getByText(/Promised date passed/)).toBeInTheDocument();
  fireEvent.click(within(story).getByRole('button',{name:'View original'}));
  await waitFor(()=>expect(evidence).toHaveBeenCalled());
  expect(await screen.findByRole('dialog')).toBeInTheDocument();
  // The suggestion, the decision and the reminder draft share the Overview.
  expect(screen.getByRole('heading',{name:'Follow up on the overdue balance'})).toBeInTheDocument();
  expect(screen.getByRole('button',{name:'Accept recommendation'})).toBeInTheDocument();
  expect(screen.getByRole('heading',{name:'Communication review'})).toBeInTheDocument();
  expect(screen.getByRole('button',{name:'Investigate case'})).toBeInTheDocument();
});

it('writes the open section to the hash without moving focus, and restores it on refresh',async()=>{
  window.location.hash=`#/cases/${cid}`;
  const {api}=caseApi();
  const first=render(<App api={api}/>);
  const heading=await screen.findByRole('heading',{level:1,name:'Studio North'});
  fireEvent.click(screen.getByRole('button',{name:'Evidence (2)'}));
  expect(window.location.hash).toBe(`#/cases/${cid}?section=evidence`);
  expect(screen.getByRole('heading',{name:'Saved evidence'})).toBeInTheDocument();
  expect(screen.getByRole('heading',{name:'Evidence timeline'})).toBeInTheDocument();
  expect(heading).not.toHaveFocus();
  fireEvent.click(screen.getByRole('button',{name:'History'}));
  expect(window.location.hash).toBe(`#/cases/${cid}?section=history`);
  expect(await screen.findByRole('heading',{name:'Saved history'})).toBeInTheDocument();
  first.unmount();
  render(<App api={api}/>);
  await screen.findByRole('heading',{level:1,name:'Studio North'});
  expect(screen.getByRole('button',{name:'History'})).toHaveAttribute('aria-current','page');
});

it('maps the old journey destinations onto the new sections and offers Compare',async()=>{
  window.location.hash=`#/cases/${cid}?section=compare`;
  render(<App api={caseApi().api}/>);
  await screen.findByRole('heading',{level:1,name:'Studio North'});
  expect(screen.getByRole('button',{name:'Compare'})).toHaveAttribute('aria-current','page');
  expect(screen.getByRole('heading',{name:'What changed'})).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button',{name:'Overview'}));
  const journey=()=>within(screen.getByRole('navigation',{name:'Case journey'}));
  fireEvent.click(journey().getByRole('button',{name:'Inspect evidence'}));
  expect(window.location.hash).toBe(`#/cases/${cid}?section=evidence`);
  expect(screen.getByRole('heading',{name:'Saved evidence'})).toBeInTheDocument();
  fireEvent.click(journey().getByRole('button',{name:'View recommendation'}));
  expect(window.location.hash).toBe(`#/cases/${cid}?section=overview`);
  expect(screen.getByRole('button',{name:'Overview'})).toHaveAttribute('aria-current','page');
});

it('offers no Compare section before any completed investigation',async()=>{
  window.location.hash=`#/cases/${cid}`;
  render(<App api={caseApi({...caseView} as unknown as CaseView).api}/>);
  await screen.findByRole('heading',{level:1,name:'Studio North'});
  expect(screen.queryByRole('button',{name:'Compare'})).not.toBeInTheDocument();
  expect(screen.getByRole('heading',{name:'No suggestion yet'})).toBeInTheDocument();
});

it('uses the original receipt reference rather than an internal allocation id in the payment story',async()=>{
  window.location.hash=`#/cases/${cid}`;
  const allocation:Evidence={...source,id:'allocation-source',kind:'LEDGER',authoritative:true,data:{transaction_ref:'CSV-ALLOCATION:internal-id',original_transaction_ref:'UPI-552104',amount_text:'12000.00',currency_text:'INR',verification_status:'VERIFIED',settled:true}} as Evidence;
  render(<App api={caseApi({...view,evidence:[invoice,promise,allocation]} as CaseView).api}/>);
  await screen.findByRole('heading',{level:1,name:'Studio North'});
  const story=screen.getByRole('list',{name:'What happened'});
  expect(story).toHaveTextContent('Bank reference UPI-552104');
  expect(story).not.toHaveTextContent('CSV-ALLOCATION:internal-id');
});

it.each(['EVIDENCE_CHANGED','TIME_EXPIRED'])('does not restate old promise fulfillment or questions as current facts when %s',async freshness=>{
  window.location.hash=`#/cases/${cid}`;
  const changed={...view,current_result:null,freshness,financial_facts:{...view.financial_facts,paid:{currency:'INR',minor_units:'5000000'},balance:{currency:'INR',minor_units:'0'}}} as unknown as CaseView;
  render(<App api={caseApi(changed).api}/>);
  await screen.findByRole('heading',{level:1,name:'Studio North'});
  const story=screen.getByRole('list',{name:'What happened'});
  expect(story).not.toHaveTextContent('not received');
  expect(story).not.toHaveTextContent('Checked against the verified bank records');
  expect(story).toHaveTextContent('Earlier investigation');
  const facts=screen.getByRole('region',{name:'Key facts'});
  expect(within(facts).getByText('Promise').nextElementSibling).toHaveTextContent('Needs a fresh check');
  expect(within(facts).getByText('Open questions').nextElementSibling).toHaveTextContent('Needs a fresh check');
  expect(within(facts).getByText('Last checked').nextElementSibling).toHaveTextContent('Earlier check');
});
