import React from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { resolveSelection } from '../src/api/demonstrationSelection';
import { ApiClient } from '../src/api/client';
import { CaseEvidence } from '../src/cases/CaseEvidence';
import App from '../src/App';
import { caseView, demo, did, cid, source } from './fixtures';
import { act } from '@testing-library/react';
afterEach(() => { cleanup(); localStorage.clear(); vi.restoreAllMocks(); });
describe('saved demonstration discovery', () => {
  it('restores valid preference, otherwise selects only a sole copy', () => {
    expect(resolveSelection([demo], did)).toBe(did);
    expect(resolveSelection([demo], 'deleted')).toBe(did);
    expect(resolveSelection([], did)).toBe(null);
    expect(resolveSelection([demo, {...demo,id:'other'}], null)).toBe(null);
    expect(resolveSelection([demo, {...demo,id:'other'}], did)).toBe(did);
  });
  it('preserves preference on listing failure and never creates implicitly', async () => {
    localStorage.setItem('selected_demonstration_id', did);
    const fetcher = vi.fn(async (url: RequestInfo | URL, _init?:RequestInit) => new Response(JSON.stringify(String(url).endsWith('/health') ? {schema_version:'1',ready:true,agent_mode:'STUB'} : {schema_version:'1',error:{code:'STORAGE_UNAVAILABLE',message:'Saved copies unavailable',retryable:true}}), {status:String(url).endsWith('/health')?200:503}));
    render(<App api={new ApiClient(fetcher)} />);
    expect(await screen.findByText(/Saved copies unavailable/)).toBeInTheDocument();
    expect(localStorage.getItem('selected_demonstration_id')).toBe(did);
    expect(fetcher.mock.calls.every(call => !(call[1] as RequestInit | undefined)?.method)).toBe(true);
  });
  it('requires an explicit create action when no copies exist', async () => {
    const fetcher = vi.fn(async (url: RequestInfo | URL, _init?:RequestInit) => new Response(JSON.stringify(String(url).endsWith('/health') ? {schema_version:'1',ready:true,agent_mode:'STUB'} : String(url).endsWith('/catalogue') ? {schema_version:'1',catalogue_version:'release-0.1',variant_ids:[]} : {schema_version:'1',demonstrations:[]})));
    render(<App api={new ApiClient(fetcher)} />);
    expect(await screen.findByText(/No saved demonstrations/)).toBeInTheDocument();
    expect(screen.getByRole('button',{name:'Create fictional demonstration'})).toBeEnabled();
    expect(screen.getByText(/No authentication/)).toBeInTheDocument();
    expect(fetcher.mock.calls.every(call => !(call[1] as RequestInit | undefined)?.method)).toBe(true);
  });
});
it('opens exact evidence versions by keyboard-accessible buttons without investigation', () => {
  const open = vi.fn();
  render(<CaseEvidence view={caseView as any} onSource={open} />);
  expect(screen.getByText(/Customer wording is a claim/)).toBeInTheDocument();
  expect(screen.getByText(/Ledger complete/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button',{name:/^Inspect exact source version: message-1, version 1/}));
  expect(open).toHaveBeenCalledWith(source.id);
});
it('binds all case and evidence reads to the selected copy', async () => {
  const fetcher = vi.fn(async (_url: RequestInfo | URL, _init?:RequestInit) => new Response(JSON.stringify(caseView)));
  const api = new ApiClient(fetcher);
  await api.case(did,cid); await api.evidence(did,source.id); await api.history(did,cid);
  expect(fetcher.mock.calls.every(call => String(call[0]).includes(`demonstration_id=${did}`))).toBe(true);
});
it.each([null,'FV-17-EVIDENCE'])('offers only events registered for saved variant %s',async(selectedVariant)=>{
  const api=new ApiClient(async(url)=>{
    const path=String(url);
    const events=[{id:'PK-001-U1',kind:'EVIDENCE',case_id:'PK-001',evaluation_at:caseView.evaluation_at,eligible_variant_ids:[null,'FV-17-EVIDENCE']},{id:'FV-17-EVIDENCE-RUN-START',kind:'CLOCK',case_id:'PK-001',evaluation_at:caseView.evaluation_at,eligible_variant_ids:['FV-17-EVIDENCE']}];
    const response=path.endsWith('/health')?{schema_version:'1',ready:true,agent_mode:'STUB'}:path.endsWith('/catalogue')?{schema_version:'1',catalogue_version:'release-0.1',variant_ids:['FV-17-EVIDENCE'],events}:path.endsWith('/demonstrations')?{schema_version:'1',demonstrations:[{...demo,selected_variant_id:selectedVariant}]}:path.endsWith('/cases')?{schema_version:'1',demonstration_id:did,clock_mode:'REFERENCE',evaluation_at:caseView.evaluation_at,cases:[{...caseView,currency:'INR',due_at:null,has_previous_investigation:false}]}:path.includes('/history')?{schema_version:'1',events:[],next_cursor:null}:caseView;
    return new Response(JSON.stringify(response));
  });
  render(<App api={api}/>);await screen.findByRole('heading',{name:'Studio North'});
  fireEvent.click(screen.getByRole('button',{name:'History'}));
  expect(screen.getByRole('option',{name:/PK-001-U1/})).toBeInTheDocument();
  if(selectedVariant===null)expect(screen.queryByRole('option',{name:/FV-17-EVIDENCE-RUN-START/})).not.toBeInTheDocument();
  else expect(screen.getByRole('option',{name:/FV-17-EVIDENCE-RUN-START/})).toBeInTheDocument();
});
it('keeps the saved detail visible when the selected case is clicked again', async () => {
  const summaries=['PK-001','PK-002','PK-003'].map((code,index)=>({id:index===0?cid:`case-${index}`,catalogue_case_id:code,client:index===0?'Studio North':`Studio ${index}`,invoice_id:`INV-${index+1}`,currency:'INR',due_at:caseView.financial_facts.due_at,lifecycle:'OPEN',case_revision:0,has_previous_investigation:false,review_required:false}));
  const api=new ApiClient(async(url)=>{
    const path=String(url);
    const response=path.endsWith('/health')?{schema_version:'1',ready:true,agent_mode:'STUB'}:path.endsWith('/catalogue')?{schema_version:'1',catalogue_version:'release-0.1',variant_ids:[]}:path.endsWith('/demonstrations')?{schema_version:'1',demonstrations:[demo]}:path.endsWith('/cases')?{schema_version:'1',demonstration_id:did,clock_mode:'REFERENCE',evaluation_at:caseView.evaluation_at,cases:summaries}:caseView;
    return new Response(JSON.stringify(response));
  });
  render(<App api={api}/>);
  expect(await screen.findByRole('heading',{name:'Studio North'})).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button',{name:/PK-001.*Studio North/}));
  expect(screen.getByRole('heading',{name:'Studio North'})).toBeInTheDocument();
  expect(screen.getByRole('button',{name:'Findings'})).toBeInTheDocument();
});
it('discards a delayed source reply after navigating away and back within the same copy', async () => {
  let resolveSource!:(value:Response)=>void;
  const secondId='66666666-6666-4666-8666-666666666666';
  const summaries=[{...caseView,has_previous_investigation:false,currency:'INR',due_at:null},{...caseView,id:secondId,catalogue_case_id:'PK-002',client:'Second Studio',has_previous_investigation:false,currency:'INR',due_at:null},{...caseView,id:'third',catalogue_case_id:'PK-003',client:'Third Studio',has_previous_investigation:false,currency:'INR',due_at:null}];
  const api=new ApiClient(async(url)=>{
    const path=String(url);
    if(path.includes('/evidence-versions/'))return new Promise<Response>(resolve=>{resolveSource=resolve;});
    const response=path.endsWith('/health')?{schema_version:'1',ready:true,agent_mode:'STUB'}:path.endsWith('/catalogue')?{schema_version:'1',catalogue_version:'release-0.1',variant_ids:[]}:path.endsWith('/demonstrations')?{schema_version:'1',demonstrations:[demo]}:path.endsWith('/cases')?{schema_version:'1',demonstration_id:did,clock_mode:'REFERENCE',evaluation_at:caseView.evaluation_at,cases:summaries}:path.includes(secondId)?{...caseView,id:secondId,client:'Second Studio'}:caseView;
    return new Response(JSON.stringify(response));
  });
  render(<App api={api}/>);
  await screen.findByRole('heading',{name:'Studio North'});
  fireEvent.click(screen.getByRole('button',{name:/^Inspect exact source version: message-1/}));
  fireEvent.click(screen.getByRole('button',{name:/Show all \d+ cases/}));
  fireEvent.click(screen.getByRole('button',{name:/PK-002.*Second Studio/}));
  await screen.findByRole('heading',{name:'Second Studio'});
  fireEvent.click(screen.getByRole('button',{name:/PK-001.*Studio North/}));
  await screen.findByRole('heading',{name:'Studio North'});
  await act(async()=>{resolveSource(new Response(JSON.stringify(source)));});
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
});
it('does not append a delayed history page under another case', async () => {
  let resolvePage!:(value:Response)=>void;
  const secondId='66666666-6666-4666-8666-666666666666';
  const summaries=[{...caseView,has_previous_investigation:false,currency:'INR',due_at:null},{...caseView,id:secondId,catalogue_case_id:'PK-002',client:'Second Studio',has_previous_investigation:false,currency:'INR',due_at:null},{...caseView,id:'third',catalogue_case_id:'PK-003',client:'Third Studio',has_previous_investigation:false,currency:'INR',due_at:null}];
  const event=(id:string,type:string)=>({id,demonstration_id:did,case_id:id,sequence:1,event_type:type,operation_id:null,payload:{},occurred_at:caseView.evaluation_at});
  const api=new ApiClient(async(url)=>{
    const path=String(url);
    if(path.includes('cursor=10'))return new Promise<Response>(resolve=>{resolvePage=resolve;});
    const response=path.includes('/history')?{schema_version:'1',events:[event(path.includes(secondId)?secondId:cid,path.includes(secondId)?'SECOND_CASE_EVENT':'FIRST_CASE_EVENT')],next_cursor:path.includes(secondId)?null:10}:path.endsWith('/health')?{schema_version:'1',ready:true,agent_mode:'STUB'}:path.endsWith('/catalogue')?{schema_version:'1',catalogue_version:'release-0.1',variant_ids:[]}:path.endsWith('/demonstrations')?{schema_version:'1',demonstrations:[demo]}:path.endsWith('/cases')?{schema_version:'1',demonstration_id:did,clock_mode:'REFERENCE',evaluation_at:caseView.evaluation_at,cases:summaries}:path.includes(secondId)?{...caseView,id:secondId,client:'Second Studio'}:caseView;
    return new Response(JSON.stringify(response));
  });
  render(<App api={api}/>);
  await screen.findByRole('heading',{name:'Studio North'});
  fireEvent.click(screen.getByRole('button',{name:'History'}));
  fireEvent.click(await screen.findByRole('button',{name:'Load more history'}));
  fireEvent.click(screen.getByRole('button',{name:/Show all \d+ cases/}));
  fireEvent.click(screen.getByRole('button',{name:/PK-002.*Second Studio/}));
  await screen.findByRole('heading',{name:'Second Studio'});
  fireEvent.click(screen.getByRole('button',{name:'History'}));
  await screen.findByText('second case event');
  await act(async()=>{resolvePage(new Response(JSON.stringify({schema_version:'1',events:[event(cid,'DELAYED_FIRST_CASE_EVENT')],next_cursor:null})));});
  expect(screen.queryByText('delayed first case event')).not.toBeInTheDocument();
  expect(screen.getByText('second case event')).toBeInTheDocument();
  expect(screen.queryByRole('button',{name:'Load more history'})).not.toBeInTheDocument();
});
