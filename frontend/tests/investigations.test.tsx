import React from 'react';
import { afterEach, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { FindingsView } from '../src/investigations/FindingsView';
import { Timeline } from '../src/investigations/Timeline';
import { InvestigationControls } from '../src/investigations/InvestigationControls';
import { ApiClient, stableOperation } from '../src/api/client';
import { caseView, did, cid, source, facts } from './fixtures';
afterEach(() => {cleanup(); localStorage.clear(); vi.restoreAllMocks();});
it('keeps the sixty-second limitation visible when a later poll request times out',async()=>{
  vi.useFakeTimers();
  try {
    const api=new ApiClient(()=>new Promise<Response>(()=>{}));
    render(<InvestigationControls api={api} view={{...caseView,running_attempt:'running'} as any} onRefresh={()=>{}}/>);
    await act(async()=>{await vi.advanceTimersByTimeAsync(64_000);});
    expect(screen.getByText(/Connection limitation: no terminal result confirmed within 60 seconds/)).toBeInTheDocument();
  }finally {vi.useRealTimers();}
});
export const result = {investigation_id:'44444444-4444-4444-8444-444444444444',snapshot_id:'55555555-5555-4555-8555-555555555555',snapshot_hash:'a'.repeat(64),evaluation_at:'2026-10-24T00:00:00Z',status:'LIMITED',financial_facts:facts,financial_label:'RECORDED_REMAINDER',commitments:[],claims:[],timeline:[{source_id:source.stable_source_id,evidence_version_id:source.id,event_at:null,arrived_at:source.arrived_at,kind:'MESSAGE',undated:true}],contradictions:[],unresolved_questions:[{field:'ATTRIBUTION',sources:[]}],limitations:[],action:'WAIT',reason_code:'FUTURE_PROMISE',explanation:{text:'A promise is still active.',sources:[source.id]},next_step:'Review the evidence at the next boundary.',review_at:'2026-10-24T18:30:00Z',result_hash:'b'.repeat(64)};
it('shows one WAIT action and marks review required at exact equality', () => {
  render(<FindingsView result={result as any} view={{...caseView,evaluation_at:result.review_at} as any} onSource={() => {}} />);
  expect(screen.getByRole('heading',{name:'Wait until the review date'})).toBeInTheDocument();
  expect(screen.getByText(/Review required: the review date has arrived/)).toBeInTheDocument();
  expect(screen.getByText(/25 Oct 2026, 00:00/)).toBeInTheDocument();
  expect(screen.getByText('Which payment belongs to this promise')).toBeInTheDocument();
});
it('separates undated evidence from chronological events and exposes arrival time', () => {
  render(<Timeline evidence={[source,{...source,id:'dated',stable_source_id:'invoice',event_at:'2026-10-20T00:00:00Z'}] as any} onSource={() => {}} />);
  expect(screen.getByRole('heading',{name:'Undated evidence'})).toBeInTheDocument();
  expect(screen.getAllByText(/Arrived/)).toHaveLength(2);
});
it('scopes stable operation payloads to the originating copy and case', () => {
  const one = stableOperation(did,cid,'investigation',{expected_case_revision:0,retry_of:null});
  expect(stableOperation(did,cid,'investigation',{expected_case_revision:0,retry_of:null})).toEqual(one);
  expect(stableOperation('other',cid,'investigation',{expected_case_revision:0,retry_of:null}).operation_id).not.toBe(one.operation_id);
  expect(() => stableOperation(did,cid,'investigation',{expected_case_revision:1,retry_of:null})).toThrow(/pending operation/i);
});
it('retains the previous completed findings when a new start fails', async () => {
  const fetcher = vi.fn(async () => new Response(JSON.stringify({schema_version:'1',error:{code:'INVESTIGATOR_BUSY',message:'Investigator busy',retryable:true}}),{status:503}));
  const api = new ApiClient(fetcher);
  render(<><InvestigationControls api={api} view={caseView as any} onRefresh={() => {}} /><FindingsView result={result as any} view={caseView as any} onSource={() => {}} /></>);
  fireEvent.click(screen.getByRole('button',{name:'Investigate case'}));
  expect(await screen.findByText(/Investigator busy/)).toBeInTheDocument();
  expect(screen.getByRole('heading',{name:'Wait until the review date'})).toBeInTheDocument();
});
it('acknowledges persisted starts after a StrictMode effect remount', async () => {
  const api=new ApiClient(async(url)=>new Response(JSON.stringify(String(url).includes('/investigations?')?{schema_version:'1',receipt:{operation_id:'operation',operation_type:'START_INVESTIGATION',target_id:cid,committed_at:result.evaluation_at,outcome:'STARTED',case_revision:1},investigation_id:result.investigation_id}:{schema_version:'1',id:result.investigation_id,investigation_id:result.investigation_id,demonstration_id:did,case_id:cid,status:'INCOMPLETE',snapshot_id:result.snapshot_id,snapshot_hash:result.snapshot_hash,evaluation_at:result.evaluation_at,deadline_at:'2026-10-24T00:00:55Z',limitations:[],failure_code:'INTERRUPTED',result:null,action:null,draft_status:'NOT_IMPLEMENTED',progress:[]})));
  render(<React.StrictMode><InvestigationControls api={api} view={caseView as any} onRefresh={()=>{}}/></React.StrictMode>);
  fireEvent.click(screen.getByRole('button',{name:'Investigate case'}));
  expect(await screen.findByText(/Investigation incomplete: interrupted/)).toBeInTheDocument();
});
it('shows a connection limitation within 60 seconds when start never acknowledges', async () => {
  vi.useFakeTimers();
  try {
    const api=new ApiClient(async()=>new Promise<Response>(()=>{}));
    render(<InvestigationControls api={api} view={caseView as any} onRefresh={()=>{}}/>);
    fireEvent.click(screen.getByRole('button',{name:'Investigate case'}));
    await act(async()=>{await vi.advanceTimersByTimeAsync(60_000);});
    expect(screen.getByRole('status')).toHaveTextContent(/connection|outcome is unknown/i);
  } finally {vi.useRealTimers();}
});
it('bounds a start response whose headers arrive but whose body stalls', async () => {
  vi.useFakeTimers();
  try {
    const api=new ApiClient(async()=>({ok:true,status:202,json:()=>new Promise(()=>{})}) as Response);
    render(<InvestigationControls api={api} view={caseView as any} onRefresh={()=>{}}/>);
    fireEvent.click(screen.getByRole('button',{name:'Investigate case'}));
    await act(async()=>{await vi.advanceTimersByTimeAsync(60_000);});
    expect(screen.getByRole('status')).toHaveTextContent(/Connection unavailable|outcome is unknown/i);
    expect(screen.getByRole('button',{name:'Retry original start'})).toBeEnabled();
    expect(localStorage.getItem(`promisekeeper.operation.${did}.${cid}.investigation`)).not.toBe(null);
  } finally {vi.useRealTimers();}
});
it('looks up an unknown start before resubmitting the exact original payload', async () => {
  const pending=stableOperation(did,cid,'investigation',{expected_case_revision:0,retry_of:null});
  const calls:{url:string;body?:string}[]=[];
  const api=new ApiClient(async(url,init)=>{
    calls.push({url:String(url),body:init?.body as string|undefined});
    if(String(url).includes('/operations/'))return new Response(JSON.stringify({schema_version:'1',error:{code:'NOT_RECORDED',message:'Not recorded',retryable:false}}),{status:404});
    return new Response(JSON.stringify({schema_version:'1',error:{code:'INVESTIGATOR_BUSY',message:'Investigator busy',retryable:true}}),{status:503});
  });
  render(<InvestigationControls api={api} view={caseView as any} onRefresh={()=>{}}/>);
  await screen.findByText(/Start not recorded/);
  fireEvent.click(screen.getByRole('button',{name:'Retry original start'}));
  await screen.findByText(/Investigator busy/);
  expect(calls.map(item=>item.url.includes('/operations/')?'lookup':'start')).toEqual(['lookup','lookup','start']);
  expect(JSON.parse(calls[2].body!)).toEqual(pending);
});
it('keeps a running attempt read-only and shows a visible terminal connection limitation', async () => {
  vi.useFakeTimers();
  try {
    const api=new ApiClient(async()=>new Response(JSON.stringify({schema_version:'1',id:result.investigation_id,investigation_id:result.investigation_id,demonstration_id:did,case_id:cid,status:'RUNNING',snapshot_id:result.snapshot_id,snapshot_hash:result.snapshot_hash,evaluation_at:result.evaluation_at,deadline_at:'2026-10-24T00:00:55Z',limitations:[],failure_code:null,result:null,action:null,draft_status:'NOT_IMPLEMENTED',progress:[]})));
    render(<InvestigationControls api={api} view={{...caseView,running_attempt:result.investigation_id} as any} onRefresh={()=>{}}/>);
    expect(screen.getByRole('button',{name:'Investigation running'})).toBeDisabled();
    await act(async()=>{await vi.advanceTimersByTimeAsync(60_000);});
    expect(screen.getByRole('status')).toHaveTextContent(/Connection limitation/);
    expect(screen.getByRole('button',{name:'Check saved investigation status'})).toBeEnabled();
  } finally {vi.useRealTimers();}
});
