import React from 'react';
import {afterEach,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import App from '../src/App';
import {ApiClient} from '../src/api/client';
import {executeIntake,pendingIntake,clearIntakeState,intakeFenceKey} from '../src/intake/commands';
import {caseIsUpdating} from '../src/api/caseActivity';
import {IntakePanel} from '../src/intake/IntakePanel';

afterEach(()=>{cleanup();localStorage.clear();vi.restoreAllMocks();window.location.hash='';});

it('offers separate file samples and never creates a workspace or imports on opening',async()=>{
  const fetcher=vi.fn(async(url:RequestInfo|URL,_init?:RequestInit)=>new Response(JSON.stringify(String(url).endsWith('/health')?
    {schema_version:'1',ready:true,agent_mode:'STUB'}:String(url).endsWith('/catalogue')?
    {schema_version:'1',catalogue_version:'release-0.1',variant_ids:[]}:{schema_version:'1',demonstrations:[]})));
  window.location.hash='#/upload?step=1';render(<App api={new ApiClient(fetcher)}/>);
  fireEvent.click(await screen.findByText('Download separate sample files'));
  expect(screen.getByRole('link',{name:'Customers CSV'})).toHaveAttribute('href','/api/v1/intake/samples/customers.csv');
  expect(screen.getByRole('link',{name:'Remittance email'})).toHaveAttribute('href','/api/v1/intake/samples/remittance-email.eml');
  expect(screen.getByRole('link',{name:'WhatsApp payment claim'})).toHaveAttribute('href','/api/v1/intake/samples/whatsapp-paid.txt');
  expect(screen.getByLabelText('Upload file')).toBeInTheDocument();
  expect(fetcher.mock.calls.every(call=>call.length===1 || !(call[1] as RequestInit|undefined)?.method)).toBe(true);
});

it('retains an uncertain import and replays exactly its original payload before releasing the revision barrier',async()=>{
  const bodies:string[]=[];let fail=true;
  const api=new ApiClient(async(_url,init)=>{
    bodies.push(String(init?.body));
    if(fail)throw new Error('lost response');
    return new Response(JSON.stringify({schema_version:'1',demonstration_id:'workspace',case_revisions:{invoice:8},receipt:{outcome:'APPLIED'}}));
  });
  await expect(executeIntake(api,'workspace','new','import','/intake/commits',{content:'actual original'})).rejects.toThrow();
  expect(pendingIntake('workspace','new','import')).not.toBeNull();
  expect(caseIsUpdating('workspace','invoice',7)).toBe(true);
  await expect(executeIntake(api,'workspace','receipt','allocation','/allocation',{amount:'1'})).rejects.toThrow('unknown outcome');
  expect(pendingIntake('workspace','receipt','allocation')).toBeNull();
  fail=false;await executeIntake(api,'workspace','new','import','/intake/commits');
  expect(bodies[1]).toBe(bodies[0]);
  expect(pendingIntake('workspace','new','import')).toBeNull();
  expect(localStorage.getItem(intakeFenceKey('workspace'))).toBeNull();
  expect(caseIsUpdating('workspace','invoice',7)).toBe(true);
  expect(caseIsUpdating('workspace','invoice',8)).toBe(false);
});

it('clears deleted workspace upload state without erasing another workspace or investigation',()=>{
  localStorage.setItem('promisekeeper.operation.a.new.intake-import','saved');
  localStorage.setItem('promisekeeper.operation.b.new.intake-import','other');
  localStorage.setItem('promisekeeper.operation.a.invoice.investigation','investigation');
  localStorage.setItem(intakeFenceKey('a'),'pending');
  clearIntakeState('a');
  expect(localStorage.getItem('promisekeeper.operation.a.new.intake-import')).toBeNull();
  expect(localStorage.getItem(intakeFenceKey('a'))).toBeNull();
  expect(localStorage.getItem('promisekeeper.operation.b.new.intake-import')).toBe('other');
  expect(localStorage.getItem('promisekeeper.operation.a.invoice.investigation')).toBe('investigation');
});

it('discards a slow file read after its type changes',async()=>{
  const fetcher=vi.fn(async(url:RequestInfo|URL)=>new Response(JSON.stringify(String(url).endsWith('/health')?
    {schema_version:'1',ready:true,agent_mode:'STUB'}:String(url).endsWith('/catalogue')?
    {schema_version:'1',catalogue_version:'release-0.1',variant_ids:[]}:{schema_version:'1',demonstrations:[]})));
  window.location.hash='#/upload?step=1';render(<App api={new ApiClient(fetcher)}/>);await screen.findByLabelText('Upload file');
  let finish!:(value:string)=>void;
  const file=new File(['customer_id,customer_name\nECON,Econcity\n'],'customers.csv');
  Object.defineProperty(file,'text',{value:()=>new Promise<string>(resolve=>{finish=resolve;})});
  fireEvent.change(screen.getByLabelText('Upload file'),{target:{files:[file]}});
  expect(screen.getByRole('button',{name:'Reading file…'})).toBeDisabled();
  fireEvent.change(screen.getByLabelText('File type'),{target:{value:'invoices'}});
  finish('customer_id,customer_name\nECON,Econcity\n');
  await waitFor(()=>expect(screen.getByRole('button',{name:'Preview file'})).toBeDisabled());
  expect(fetcher.mock.calls.every(call=>!String(call[0]).endsWith('/intake/previews'))).toBe(true);
});

it('keeps a manually supplied source date in the displayed business timezone',async()=>{
  const writes:Record<string,unknown>[]=[];
  const api=new ApiClient(async(_url,init)=>{
    if(init?.method){writes.push(JSON.parse(String(init.body)));return new Response(JSON.stringify({schema_version:'1',rows:[],errors:[],warnings:[],duplicates:0,extraction:null}));}
    return new Response(JSON.stringify({schema_version:'1',as_of:'2026-10-25T00:00:00Z',customers:[],payments:[],documents:[],files:[],cases:[{id:'invoice',invoice_id:'EC-101',client:'Econcity',invoice_minor:'10000000',allocated_minor:'0',remaining_minor:'10000000',case_revision:1,ledger_complete:false}]}));
  });
  render(<IntakePanel api={api} did="workspace" reloadKey={0} onCreated={()=>{}} onChanged={()=>{}} onOpenCase={()=>{}}/>);
  fireEvent.change(screen.getByLabelText('File type'),{target:{value:'whatsapp'}});
  await screen.findByText('EC-101 · Econcity',{selector:'option'});
  fireEvent.change(screen.getByLabelText('Attach communication to invoice'),{target:{value:'invoice'}});
  fireEvent.change(screen.getByLabelText('Upload file'),{target:{files:[new File(['We paid INR 25000 on 20 October 2026.'],'message.txt')]}});
  await waitFor(()=>expect(screen.getByLabelText('Who sent this message?')).toBeEnabled());
  fireEvent.change(screen.getByLabelText('Who sent this message?'),{target:{value:'CUSTOMER'}});
  fireEvent.change(screen.getByLabelText(/Source message date/),{target:{value:'2026-10-20T00:30'}});
  await waitFor(()=>expect(screen.getByRole('button',{name:'Preview file'})).toBeEnabled());
  fireEvent.click(screen.getByRole('button',{name:'Preview file'}));
  await waitFor(()=>expect(writes).toHaveLength(1));
  expect(writes[0].event_at).toBe('2026-10-20T00:30:00+05:30');
  expect(writes[0].sender_role).toBe('CUSTOMER');
});

it('requires sender review, shows interpreted facts beside the quote and discards preview on role change',async()=>{
  const writes:Record<string,unknown>[]=[];
  const api=new ApiClient(async(_url,init)=>{
    if(init?.method){writes.push(JSON.parse(String(init.body)));return new Response(JSON.stringify({schema_version:'1',rows:[],errors:[],warnings:['Reviewed weekday rule: next Friday means 2026-10-30.'],duplicates:0,preview_hash:'a'.repeat(64),extraction:{speaker:'Customer accounts',event_at:'2026-10-25T10:00:00+05:30',sender_role:'CUSTOMER',candidates:[{kind:'COMMITMENT',clause:'We will pay \u20b91000 by next Friday.',amount_text:'1000',currency_text:'\u20b9',date_text:'next Friday',interpreted_currency:'INR',interpreted_date:'2026-10-30'}]}}));}
    return new Response(JSON.stringify({schema_version:'1',as_of:'2026-10-25T00:00:00Z',customers:[],payments:[],documents:[],files:[],cases:[{id:'invoice',invoice_id:'EC-101',client:'Econcity',invoice_minor:'100000',allocated_minor:'0',remaining_minor:'100000',case_revision:1,ledger_complete:false}]}));
  });
  render(<IntakePanel api={api} did="workspace" reloadKey={0} onCreated={()=>{}} onChanged={()=>{}} onOpenCase={()=>{}}/>);
  fireEvent.change(screen.getByLabelText('File type'),{target:{value:'whatsapp'}});
  await screen.findByText('EC-101 · Econcity',{selector:'option'});
  fireEvent.change(screen.getByLabelText('Attach communication to invoice'),{target:{value:'invoice'}});
  fireEvent.change(screen.getByLabelText('Upload file'),{target:{files:[new File(['We will pay \u20b91000 by next Friday.'],'promise.txt')]}});
  await waitFor(()=>expect(screen.getByLabelText('Who sent this message?')).toBeEnabled());
  await waitFor(()=>expect(screen.getByRole('button',{name:'Preview file'})).toBeDisabled());
  fireEvent.change(screen.getByLabelText('Who sent this message?'),{target:{value:'CUSTOMER'}});
  await waitFor(()=>expect(screen.getByRole('button',{name:'Preview file'})).toBeEnabled());
  fireEvent.click(screen.getByRole('button',{name:'Preview file'}));
  await screen.findByText('Interpreted currency');
  expect(screen.getByText('2026-10-30',{selector:'dd'})).toBeInTheDocument();
  expect(screen.getByText('We will pay \u20b91000 by next Friday.',{selector:'blockquote'})).toBeInTheDocument();
  expect(writes[0].sender_role).toBe('CUSTOMER');
  fireEvent.change(screen.getByLabelText('Who sent this message?'),{target:{value:'OWNER'}});
  expect(screen.queryByText('Import preview')).not.toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('Who sent this message?'),{target:{value:'CUSTOMER'}});
  fireEvent.change(screen.getByLabelText('Upload file'),{target:{files:[new File(['A different owner document.'],'owner.txt')]}});
  await waitFor(()=>expect(screen.getByLabelText('Who sent this message?')).toHaveValue('UNVERIFIED'));
  expect(screen.getByRole('button',{name:'Preview file'})).toBeDisabled();
});

it('reads an actual file and sends only a preview before explicit import confirmation',async()=>{
  const writes:{path:string;body:Record<string,unknown>}[]=[];
  const fetcher=vi.fn(async(url:RequestInfo|URL,init?:RequestInit)=>{
    const path=String(url);
    if(init?.method){writes.push({path,body:JSON.parse(String(init.body))});return new Response(JSON.stringify({schema_version:'1',kind:'customers',rows:[{customer_id:'ECON',customer_name:'Econcity'}],errors:[],warnings:[],duplicates:0,extraction:null,preview_hash:'a'.repeat(64),scope_revision:'new'}));}
    return new Response(JSON.stringify(path.endsWith('/health')?{schema_version:'1',ready:true,agent_mode:'STUB'}:path.endsWith('/catalogue')?{schema_version:'1',catalogue_version:'release-0.1',variant_ids:[]}:{schema_version:'1',demonstrations:[]}));
  });
  window.location.hash='#/upload?step=1';render(<App api={new ApiClient(fetcher)}/>);
  await screen.findByLabelText('Upload file');
  const text='customer_id,customer_name\nECON,Econcity\n';
  fireEvent.change(screen.getByLabelText('Upload file'),{target:{files:[new File([text],'customers.csv',{type:'text/csv'})]}});
  await waitFor(()=>expect(screen.getByRole('button',{name:'Preview file'})).toBeEnabled());
  fireEvent.click(screen.getByRole('button',{name:'Preview file'}));
  await screen.findByText('Econcity');
  expect(writes).toHaveLength(1);expect(writes[0].path).toBe('/api/v1/intake/previews');
  expect(writes[0].body.content).toBe(text);
  expect(screen.getByRole('button',{name:'Confirm import'})).toBeDisabled();
  fireEvent.click(screen.getByLabelText('I reviewed this preview and confirm these are fictional sample records.'));
  expect(screen.getByRole('button',{name:'Confirm import'})).toBeEnabled();
  fireEvent.change(screen.getByLabelText('File type'),{target:{value:'invoices'}});
  expect(screen.queryByRole('button',{name:'Confirm import'})).not.toBeInTheDocument();
});
