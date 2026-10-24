import {afterEach,expect,it,vi} from 'vitest';
import {act,cleanup,fireEvent,render,screen,within} from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import App from '../src/App';
import {ApiClient} from '../src/api/client';
import {CaseList} from '../src/cases/CaseList';
import {FindingsView} from '../src/investigations/FindingsView';
import {OwnerDecisions} from '../src/history/OwnerDecisions';
import {caseView, demo, did, cid, facts} from './fixtures';
import type {Result,FinancialFacts} from '../src/api/types';

afterEach(()=>{cleanup();localStorage.clear();vi.restoreAllMocks();});
const saved:Result={investigation_id:'44444444-4444-4444-8444-444444444444',snapshot_id:'55555555-5555-4555-8555-555555555555',snapshot_hash:'a'.repeat(64),evaluation_at:caseView.evaluation_at,status:'COMPLETE',financial_facts:facts as FinancialFacts,financial_label:'VERIFIED_REMAINDER',commitments:[],claims:[],timeline:[],contradictions:[],unresolved_questions:[],limitations:[],action:'FOLLOW_UP',reason_code:'EXPIRED_PROMISE',explanation:{text:'Follow up on the verified balance.',sources:[]},next_step:'Review a follow-up draft.',review_at:null,result_hash:'b'.repeat(64)};
const summary={...caseView,currency:'INR',has_previous_investigation:true,balance:facts.balance,balance_label:'VERIFIED_REMAINDER',recommended_action:'FOLLOW_UP',review_at:null};

it('does not invent a payment promise when the invoice is not yet due',()=>{
  render(<FindingsView result={{...saved,action:'WAIT',reason_code:'ACTIVE_PROMISE_OR_NOT_DUE',review_at:'2026-10-25T18:30:00Z'}} view={{...caseView,freshness:'CURRENT'} as any} onSource={()=>{}}/>);
  expect(screen.getByRole('heading',{name:'Wait until the review date'})).toBeInTheDocument();
});

it('requires a current result for decisions beside findings while retaining historical decisions in History',()=>{
  const view={...caseView,freshness:'EVIDENCE_CHANGED',latest_completed_result:saved,current_result:null,allowed_commands:{disposition:{allowed:true,blocking_reasons:[]}}};
  render(<OwnerDecisions contextual view={view as any} api={new ApiClient()} onRefresh={()=>{}}/>);
  expect(screen.getByRole('button',{name:'Accept recommendation'})).toBeDisabled();
});

it('shows balances and current actions in the case overview, with unknown kept distinct',()=>{
  render(<CaseList cases={[summary,{...summary,id:'other',client:'Missing ledger',balance:null,balance_label:'UNKNOWN_REMAINDER',recommended_action:null,review_required:true}] as any} selected={cid} onSelect={()=>{}}/>);
  const first=screen.getByRole('button',{name:/Studio North/});
  expect(within(first).getByText('INR 30,000.00')).toBeInTheDocument();
  expect(within(first).getByText('Follow up')).toBeInTheDocument();
  expect(within(screen.getByRole('button',{name:/Missing ledger/})).getByText('Unknown')).toBeInTheDocument();
});

it('formats saved wait instructions in IST while retaining the saved result unchanged',()=>{
  const wait={...saved,action:'WAIT',review_at:'2026-10-25T18:30:00+00:00',next_step:'Review the case at 2026-10-25T18:30:00+00:00.'};
  render(<FindingsView result={wait as any} view={{...caseView,freshness:'CURRENT'} as any} onSource={()=>{}}/>);
  expect(screen.getByRole('heading',{name:'Wait until the review date'})).toBeInTheDocument();
  expect(screen.getByText('Review the case at 26 Oct 2026, 00:00 IST.')).toBeInTheDocument();
  expect(screen.queryByText(/2026-10-25T18:30/)).not.toBeInTheDocument();
  expect(wait.next_step).toContain('2026-10-25T18:30');
});

it('guides a completed investigation to findings and keeps decisions beside the recommendation',async()=>{
  const view={...caseView,freshness:'CURRENT',current_result:saved,latest_completed_result:saved,allowed_commands:{...caseView.allowed_commands,disposition:{allowed:true,blocking_reasons:[]}}};
  const api=new ApiClient(async input=>{
    const url=String(input);
    const body=url.endsWith('/health')?{schema_version:'1',ready:true,agent_mode:'STUB'}:url.endsWith('/catalogue')?{schema_version:'1',catalogue_version:'release-0.1',variant_ids:[]}:url.endsWith('/demonstrations')?{schema_version:'1',demonstrations:[demo]}:url.endsWith('/cases')?{schema_version:'1',demonstration_id:did,clock_mode:'REFERENCE',evaluation_at:caseView.evaluation_at,cases:[summary]}:view;
    return new Response(JSON.stringify(Object.assign({schema_version:"1"},body)));
  });
  render(<App api={api}/>);
  fireEvent.click(await screen.findByRole('button',{name:'View recommendation'}));
  expect(screen.getByRole('heading',{name:'Follow up on the overdue balance'})).toBeInTheDocument();
  expect(screen.getByRole('button',{name:'Accept recommendation'})).toBeInTheDocument();
  expect(screen.getByRole('button',{name:'Review suggested message'})).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button',{name:'Review suggested message'}));
  expect(screen.getByRole('heading',{name:'Communication review'})).toBeInTheDocument();
});

it('refreshes a waiting overview at its review time even when a different case is selected',async()=>{
  vi.useFakeTimers();
  let lists=0;
  const reviewAt=new Date(Date.parse(caseView.evaluation_at)+1_000).toISOString();
  const api=new ApiClient(async input=>{
    const url=String(input);
    const body=url.endsWith('/health')?{ready:true,agent_mode:'STUB'}:url.endsWith('/catalogue')?{catalogue_version:'release-0.1',variant_ids:[]}:url.endsWith('/demonstrations')?{demonstrations:[{...demo,clock_mode:'REAL'}]}:url.endsWith('/cases')?{demonstration_id:did,clock_mode:'REAL',evaluation_at:caseView.evaluation_at,cases:[summary,{...summary,id:'waiting',client:'Waiting client',recommended_action:++lists>1?null:'WAIT',review_required:lists>1,review_at:lists>1?null:reviewAt}]}:caseView;
    return new Response(JSON.stringify(Object.assign({schema_version:"1"},body)));
  });
  try {
    await act(async()=>{render(<App api={api}/>);});
    expect(within(screen.getByRole('button',{name:/Waiting client/})).getByText('Wait until the review date')).toBeInTheDocument();
    await act(async()=>{await vi.advanceTimersByTimeAsync(1_000);});
    expect(within(screen.getByRole('button',{name:/Waiting client/})).getByText('Review required')).toBeInTheDocument();
  }finally {vi.useRealTimers();}
});

it('suppresses already-expired overview advice and makes only one immediate recovery refresh',async()=>{
  let lists=0;
  const api=new ApiClient(async input=>{
    const url=String(input);
    const body=url.endsWith('/health')?{ready:true,agent_mode:'STUB'}:url.endsWith('/catalogue')?{catalogue_version:'release-0.1',variant_ids:[]}:url.endsWith('/demonstrations')?{demonstrations:[{...demo,clock_mode:'REAL'}]}:url.endsWith('/cases')?(lists++,{demonstration_id:did,clock_mode:'REAL',evaluation_at:caseView.evaluation_at,cases:[summary,{...summary,id:'waiting',client:'Expired client',recommended_action:'WAIT',review_at:caseView.evaluation_at}]}):caseView;
    return new Response(JSON.stringify(Object.assign({schema_version:'1'},body)));
  });
  await act(async()=>{render(<App api={api}/>);});
  expect(within(screen.getByRole('button',{name:/Expired client/})).getByText('Review required')).toBeInTheDocument();
  expect(lists).toBe(2);
});
