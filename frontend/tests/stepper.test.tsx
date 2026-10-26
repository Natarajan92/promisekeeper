import React from 'react';
import {afterEach,describe,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,screen,waitFor,within} from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import App from '../src/App';
import {ApiClient} from '../src/api/client';
import {stepStates} from '../src/intake/stepper';
import type {ImportCase,ImportPayment,IntakeOverview} from '../src/intake/types';

afterEach(()=>{cleanup();localStorage.clear();sessionStorage.clear();vi.restoreAllMocks();window.location.hash='';});

const invoice=(n:number,minor:string,extra:Partial<ImportCase>={}):ImportCase=>({id:`case-${n}`,invoice_id:`INV-${n}`,client:`Client ${n}`,case_revision:1,ledger_complete:false,reviewed_through:null,invoice_minor:minor,allocated_minor:'0',remaining_minor:minor,...extra});
const receipt=(ref:string,amount:string,remaining:string,status='SETTLED'):ImportPayment=>({id:`p-${ref}`,transaction_ref:ref,payer_name:'Payer',payer_alias:'',address:'',status,paid_at:'2026-10-20T00:00:00Z',invoice_reference:'',amount_minor:amount,remaining_minor:remaining,batch_id:'b',allocations:[],candidates:[]});
const overview=(extra:Partial<IntakeOverview>={}):IntakeOverview=>({schema_version:'1',demonstration_id:'w',as_of:'2026-10-26T04:00:00Z',scope_revision:'1',needs_sender_review:false,customers:[],cases:[],payments:[],documents:[],files:[],...extra});
const customers=[1,2,3].map(n=>({customer_id:`C${n}`,customer_name:`Client ${n}`,customer_alias:'',address:''}));
// Six invoices totalling INR 3,15,000.00.
const sixInvoices=['6000000','3250000','4000000','7500000','8000000','2750000'].map((minor,index)=>invoice(index+1,minor));
const doc={id:'d1',case_id:'case-1',kind:'customer_email' as const,batch_id:'b',created_at:'2026-10-26T04:00:00Z',extraction:null};

describe('stepStates',()=>{
  it('starts a new upload at Customers when there is no imported workspace',()=>{
    const steps=stepStates(null,[],false);
    expect(steps.map(step=>step.label)).toEqual(['Customers','Invoices','Bank receipts','Customer messages','Match payments','Confirm & check']);
    expect(steps.map(step=>step.state)).toEqual(['current','todo','todo','todo','todo','todo']);
    expect(steps[0].summary).toBe('Creates a new upload workspace');
    expect(steps.map(step=>step.step)).toEqual([1,2,3,4,5,6]);
  });
  it('summarises imported customers and invoices and points to the next step',()=>{
    const steps=stepStates(overview({customers,cases:sixInvoices}),[],false);
    expect(steps[0]).toMatchObject({state:'done',summary:'3 customers added'});
    expect(steps[1]).toMatchObject({state:'done',summary:'6 invoices · ₹3,15,000.00'});
    expect(steps[2].state).toBe('current');
    expect(steps.slice(3).map(step=>step.state)).toEqual(['todo','todo','todo']);
  });
  it('asks for review when a message needs sender review, never marking it done',()=>{
    const steps=stepStates(overview({customers,cases:sixInvoices,documents:[doc],needs_sender_review:true}),[],false);
    expect(steps[3].state).toBe('attention');
    expect(steps[3].summary).toBe('Needs your review');
    expect(stepStates(overview({customers,cases:sixInvoices,documents:[doc]}),[],false)[3]).toMatchObject({state:'done',summary:'1 message attached'});
  });
  it('treats a receipt left unallocated after Continue as a choice, not an error',()=>{
    const payments=[receipt('T1','1200000','0'),receipt('T2','4000000','4000000')];
    const base=overview({customers,cases:sixInvoices,payments,documents:[doc]});
    expect(stepStates(base,[],false)[4]).toMatchObject({state:'current',summary:'1 of 2 receipts still to match'});
    expect(stepStates(base,[],false,1)[4]).toMatchObject({state:'done',summary:'1 matched · 1 left unallocated'});
    const all=overview({customers,cases:sixInvoices,payments:[receipt('T1','1200000','0')]});
    expect(stepStates(all,[],false)[4]).toMatchObject({state:'done',summary:'All 1 receipt matched'});
  });
  it('reopens Match payments when more receipts need matching after the owner moved past it',()=>{
    const later=overview({customers,cases:sixInvoices,documents:[doc],payments:[receipt('T1','1200000','0'),receipt('T2','4000000','4000000'),receipt('T3','500000','500000')]});
    // The owner continued with one receipt open; a later statement adds a second open receipt.
    expect(stepStates(later,[],false,1)[4]).toMatchObject({state:'current',summary:'2 of 3 receipts still to match'});
    expect(stepStates(later,[],false,2)[4]).toMatchObject({state:'done',summary:'1 matched · 2 left unallocated'});
  });
  it('counts pending and reversed receipts as not allocatable instead of matched',()=>{
    const held=overview({customers,cases:sixInvoices,payments:[receipt('T1','1200000','0'),receipt('P1','300000','300000','PENDING'),receipt('R1','200000','200000','REVERSED')]});
    expect(stepStates(held,[],false)[4]).toMatchObject({state:'done',summary:'1 matched · 2 not allocatable'});
    const mixed=overview({customers,cases:sixInvoices,payments:[receipt('T1','1200000','0'),receipt('T2','4000000','4000000'),receipt('P1','300000','300000','PENDING')]});
    expect(stepStates(mixed,[],false)[4].summary).toBe('1 of 3 receipts still to match');
    expect(stepStates(mixed,[],false,1)[4]).toMatchObject({state:'done',summary:'1 matched · 1 left unallocated · 1 not allocatable'});
  });
  it('finishes Confirm & check only after full coverage and a later completed morning review',()=>{
    const covered=sixInvoices.map(row=>({...row,ledger_complete:true,reviewed_through:'2026-10-26T04:00:00Z'}));
    const partly=[...covered.slice(0,2),...sixInvoices.slice(2)];
    expect(stepStates(overview({customers,cases:partly}),[],false)[5].summary).toBe('2 of 6 invoices confirmed');
    expect(stepStates(overview({customers,cases:covered}),[],false)[5]).toMatchObject({summary:'Coverage confirmed · start the morning check'});
    expect(stepStates(overview({customers,cases:covered}),[],false)[5].state).not.toBe('done');
    expect(stepStates(overview({customers,cases:covered}),[],true)[5]).toMatchObject({state:'done',summary:'Morning check complete'});
  });
});

const workspace='44444444-4444-4444-8444-444444444444';
function server(copy:{selected_variant_id:string|null}|null,data:IntakeOverview=overview({demonstration_id:workspace,customers,cases:sixInvoices})) {
  const demonstrations=copy?[{id:workspace,catalogue_version:'release-0.1',created_at:'2026-10-26T00:00:00Z',clock_mode:'REAL',...copy}]:[];
  return vi.fn(async(url:RequestInfo|URL,_init?:RequestInit)=>{
    const path=String(url);
    const body=path.endsWith('/health')?{schema_version:'1',ready:true,agent_mode:'STUB'}:
      path.endsWith('/catalogue')?{schema_version:'1',catalogue_version:'release-0.1',variant_ids:[]}:
      path.endsWith('/demonstrations')?{schema_version:'1',demonstrations}:
      path.endsWith('/intake')?data:
      path.endsWith('/morning-reviews/latest')?{schema_version:'1',morning_review:null}:
      path.endsWith('/cases')?{schema_version:'1',demonstration_id:workspace,clock_mode:'REAL',evaluation_at:'2026-10-26T04:00:00Z',cases:[]}:
      {schema_version:'1'};
    return new Response(JSON.stringify(body));
  });
}

describe('Upload page',()=>{
  it('starts a separate workspace from New upload workspace even when an imported workspace is selected',async()=>{
    const fetcher=server({selected_variant_id:'csv-demo'});
    window.location.hash='#/upload?step=3';render(<App api={new ApiClient(fetcher)}/>);
    await waitFor(()=>expect(screen.getByLabelText('File type')).toHaveValue('payments'));
    expect(localStorage.getItem('selected_demonstration_id')).toBe(workspace);
    fireEvent.click(screen.getByRole('button',{name:/^Workspace/}));
    fireEvent.click(screen.getByRole('link',{name:'New upload workspace'}));
    expect(await screen.findByRole('heading',{level:2,name:'Step 1 · Customers'})).toBeInTheDocument();
    expect(screen.getByText('Confirming a customer or invoice file creates a separate imported workspace.')).toBeInTheDocument();
    expect(localStorage.getItem('selected_demonstration_id')).toBeNull();
    expect(screen.getByRole('button',{name:/^Workspace/})).toHaveTextContent('None selected');
    expect(fetcher.mock.calls.every(call=>!call[1]?.method||call[1].method==='GET')).toBe(true);
  });
  it('starts a new upload workspace when a demonstration copy is selected',async()=>{
    const fetcher=server({selected_variant_id:null});
    window.location.hash='#/upload';render(<App api={new ApiClient(fetcher)}/>);
    expect(await screen.findByRole('heading',{level:1,name:'Bring in your records'})).toBeInTheDocument();
    const steps=screen.getByRole('navigation',{name:'Upload steps'});
    await waitFor(()=>expect(within(steps).getByRole('link',{name:/^Step 1/})).toHaveTextContent('Creates a new upload workspace'));
    expect(screen.getByText('Confirming a customer or invoice file creates a separate imported workspace.')).toBeInTheDocument();
    expect(screen.getByText('Demo files: docs/demo-import/course-demo (see START-HERE.md)')).toBeInTheDocument();
    expect(fetcher.mock.calls.some(call=>String(call[0]).endsWith('/intake'))).toBe(false);
  });
  it('never opens the workspace chooser by itself, so the Upload step card stays clear',async()=>{
    window.location.hash='#/upload';render(<App api={new ApiClient(server(null))}/>);
    expect(await screen.findByRole('heading',{level:2,name:'Step 1 · Customers'})).toBeInTheDocument();
    const toggle=screen.getByRole('button',{name:/^Workspace/});
    expect(toggle).toHaveTextContent('None selected');
    expect(toggle).toBeEnabled();expect(toggle).toHaveAttribute('aria-expanded','false');
    expect(screen.queryByText(/No saved demonstrations/)).not.toBeInTheDocument();
    expect(document.getElementById('workspace-panel')).toBeNull();
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded','true');
    expect(await screen.findByText(/No saved demonstrations/)).toBeInTheDocument();
    expect(screen.getByRole('button',{name:'Create fictional demonstration'})).toBeInTheDocument();
  });
  it('presets the bank receipts kind at step 3 and moves with Back and Continue',async()=>{
    window.location.hash='#/upload?step=3';render(<App api={new ApiClient(server({selected_variant_id:'csv-demo'}))}/>);
    await waitFor(()=>expect(screen.getByLabelText('File type')).toHaveValue('payments'));
    expect(screen.getByRole('heading',{level:2,name:'Step 3 · Bank receipts'})).toBeInTheDocument();
    const steps=screen.getByRole('navigation',{name:'Upload steps'});
    expect(within(steps).getByRole('link',{name:/^Step 3/})).toHaveAttribute('aria-current','step');
    await waitFor(()=>expect(within(steps).getByRole('link',{name:/^Step 2/})).toHaveTextContent('6 invoices · ₹3,15,000.00'));
    fireEvent.click(screen.getByRole('button',{name:'Continue to Customer messages'}));
    expect(window.location.hash).toBe('#/upload?step=4');
    await waitFor(()=>expect(screen.getByLabelText('File type')).toHaveValue('customer_email'));
    fireEvent.click(screen.getByRole('button',{name:'Back to Bank receipts'}));
    expect(window.location.hash).toBe('#/upload?step=3');
    await waitFor(()=>expect(screen.getByLabelText('File type')).toHaveValue('payments'));
    fireEvent.click(within(steps).getByRole('link',{name:/^Step 5/}));
    expect(window.location.hash).toBe('#/upload?step=5');
    expect(await screen.findByRole('heading',{name:'Review receipts and invoice allocations'})).toBeInTheDocument();
    expect(screen.getByText('Optional: import existing allocations')).toBeInTheDocument();
  });
  it('shows coverage review, the morning review start control and the Dashboard link at step 6',async()=>{
    window.location.hash='#/upload?step=6';render(<App api={new ApiClient(server({selected_variant_id:'csv-demo'}))}/>);
    expect(await screen.findByRole('heading',{name:'Review coverage and open a case'})).toBeInTheDocument();
    expect(await screen.findByRole('button',{name:'Start morning review'})).toBeInTheDocument();
    expect(screen.getByRole('link',{name:'Go to Dashboard'})).toHaveAttribute('href','#/dashboard');
    expect(screen.getByRole('button',{name:'Confirm ledger review for INV-1'})).toBeDisabled();
  });
});

describe('IntakePanel without a step',()=>{
  it('keeps the original single-page import',async()=>{
    const {IntakePanel}=await import('../src/intake/IntakePanel');
    const api=new ApiClient(async()=>new Response(JSON.stringify(overview({customers,cases:sixInvoices}))));
    render(<IntakePanel api={api} did="w" reloadKey={0} onCreated={()=>{}} onChanged={()=>{}} onOpenCase={()=>{}}/>);
    expect(screen.getByText('Import separate files',{selector:'summary'})).toBeInTheDocument();
    expect(screen.getByRole('heading',{name:'1. Upload and preview'})).toBeInTheDocument();
    expect(await screen.findByRole('heading',{name:'2. Review receipts and invoice allocations'})).toBeInTheDocument();
    expect(screen.getByRole('heading',{name:'3. Review coverage and open a case'})).toBeInTheDocument();
    expect(screen.getByLabelText('File type')).toHaveValue('customers');
    expect(screen.queryByText('Optional: import existing allocations')).not.toBeInTheDocument();
  });
});
