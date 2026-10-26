import {afterEach,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import {ApiClient} from '../src/api/client';
import {IntakePanel} from '../src/intake/IntakePanel';
import type {IntakeKind} from '../src/intake/types';

afterEach(()=>{cleanup();localStorage.clear();});
const quote='Hum ₹48000 18 October 2026 ko payment kar denge.';
const body=`Sender: Meera Textiles accounts\nSent: 2026-10-14T10:30:00+05:30\n\nNamaste,\nInvoice: MT-1001\n${quote}\nThank you,\nSuresh Mehta\nMeera Textiles\n`;
const contextLabel='I reviewed unsupported wording as supporting context only; no payment claim or promise should be extracted.';
const confirmation='I reviewed this preview and confirm the records are correct.';

function workspace(mode:'promise'|'context'|'invalid'='promise',legacy=false){
  const previews:Record<string,unknown>[]=[],commits:Record<string,unknown>[]=[];
  const onChanged=vi.fn();
  const api=new ApiClient(async(_url,init)=>{
    const url=String(_url);
    if(init?.method){
      const payload=JSON.parse(String(init.body));
      if(url.endsWith('/commits')){commits.push(payload);return Response.json({schema_version:'1',demonstration_id:'workspace',imported:1,duplicates:0,receipt:{outcome:'IMPORTED'}});}
      previews.push(payload);
      const code=mode==='invalid'?undefined:mode==='promise'&&payload.context_only?'PAYMENT_REVIEW_REQUIRED':mode==='context'&&!payload.context_only?'CONTEXT_REVIEW_REQUIRED':undefined;
      const blocked=!!code||mode==='invalid';
      return Response.json({schema_version:'1',kind:payload.kind,rows:[],errors:blocked?[{row:0,code:legacy?undefined:code,message:code==='PAYMENT_REVIEW_REQUIRED'?'Recognized payment wording must be reviewed as a claim/promise, not hidden as context.':code==='CONTEXT_REVIEW_REQUIRED'?'No supported payment claim or promise found. Review the original and explicitly choose supporting context only if appropriate.':'Conditional payment wording is unsupported.'}]:[],warnings:[],duplicates:0,preview_hash:blocked?'b'.repeat(64):'a'.repeat(64),scope_revision:'current',extraction:blocked?null:{speaker:'Meera Textiles accounts',event_at:'2026-10-14T10:30:00+05:30',context_only:!!payload.context_only,candidates:mode==='context'?[]:[{kind:'COMMITMENT',clause:quote,amount_text:'48000',currency_text:'₹',date_text:'18 October 2026',interpreted_date:'2026-10-18'}]}});
    }
    return Response.json({schema_version:'1',as_of:'2026-10-26T00:00:00Z',customers:[],payments:[],documents:[],files:[],cases:[{id:'invoice',invoice_id:'MT-1001',client:'Meera Textiles',invoice_minor:'6000000',allocated_minor:'0',remaining_minor:'6000000',case_revision:1,ledger_complete:false}]});
  });
  render(<IntakePanel api={api} did="workspace" step={4} reloadKey={0} onCreated={()=>{}} onChanged={onChanged} onOpenCase={()=>{}}/>);
  return {previews,commits,onChanged};
}
async function selectMessage(kind:IntakeKind,text=body){
  await screen.findByRole('option',{name:'MT-1001 · Meera Textiles'});
  fireEvent.change(screen.getByLabelText('File type'),{target:{value:kind}});
  fireEvent.change(screen.getByLabelText('Attach communication to invoice'),{target:{value:'invoice'}});
  fireEvent.change(screen.getByLabelText('Upload file'),{target:{files:[new File([text],kind==='whatsapp'?'message.txt':'message.eml')]}});
  await waitFor(()=>expect(screen.getByRole('button',{name:'Preview file'})).toBeDisabled());
  fireEvent.change(screen.getByLabelText('Who sent this message?'),{target:{value:'CUSTOMER'}});
  await waitFor(()=>expect(screen.getByRole('button',{name:'Preview file'})).toBeEnabled());
}

it.each([{kind:'customer_email',legacy:false},{kind:'remittance_email',legacy:false},{kind:'whatsapp',legacy:false},{kind:'whatsapp',legacy:true}] as const)('recovers a context-only mistake and explicitly adds $kind (legacy=$legacy) to the same workspace',async({kind,legacy})=>{
  const app=workspace('promise',legacy);await selectMessage(kind);
  expect(screen.getByLabelText(contextLabel)).not.toBeVisible();
  fireEvent.click(screen.getByText('Optional: supporting context only'));
  fireEvent.click(screen.getByLabelText(contextLabel));
  fireEvent.click(screen.getByRole('button',{name:'Preview file'}));
  await screen.findByRole('alert');
  expect(app.commits).toHaveLength(0);
  fireEvent.click(screen.getByRole('button',{name:'Review payment wording'}));
  await screen.findByText(quote,{selector:'blockquote'});
  expect(screen.queryByText(/CSV row/)).not.toBeInTheDocument();
  expect(screen.getByText(/1 message/)).toBeInTheDocument();
  expect(screen.getByLabelText(contextLabel)).not.toBeChecked();
  expect(screen.getByLabelText('Who sent this message?')).toHaveValue('CUSTOMER');
  expect(screen.getByLabelText('Attach communication to invoice')).toHaveValue('invoice');
  expect(app.previews.map(p=>p.context_only)).toEqual([true,false]);
  expect(app.commits).toHaveLength(0);
  expect(screen.getByRole('button',{name:'Confirm import'})).toBeDisabled();
  fireEvent.click(screen.getByLabelText(confirmation));
  fireEvent.click(screen.getByRole('button',{name:'Confirm import'}));
  await waitFor(()=>expect(app.onChanged).toHaveBeenCalledOnce());
  expect(app.commits).toEqual([expect.objectContaining({content:body,demonstration_id:'workspace',case_id:'invoice',sender_role:'CUSTOMER',context_only:false,confirmed_preview_hash:'a'.repeat(64),confirm:true})]);
});

it('offers explicit context review for an informational message without inventing a payment promise',async()=>{
  const app=workspace('context');await selectMessage('whatsapp','Sender: Meera accounts\nSent: 2026-10-14T10:30:00+05:30\nPlease call our accountant about the project.\n');
  fireEvent.click(screen.getByRole('button',{name:'Preview file'}));
  await screen.findByRole('alert');
  fireEvent.click(screen.getByRole('button',{name:'Preview as supporting context'}));
  await screen.findByRole('button',{name:'Confirm import'});
  expect(screen.queryByText('Customer payment promise')).not.toBeInTheDocument();
  expect(app.previews.map(p=>p.context_only)).toEqual([false,true]);
  expect(app.commits).toHaveLength(0);
  fireEvent.click(screen.getByLabelText(confirmation));
  fireEvent.click(screen.getByRole('button',{name:'Confirm import'}));
  await waitFor(()=>expect(app.commits[0]).toMatchObject({context_only:true,sender_role:'CUSTOMER',case_id:'invoice'}));
});

it('keeps ambiguous or conditional wording blocked without offering a context bypass',async()=>{
  const app=workspace('invalid');await selectMessage('whatsapp',body.replace(quote,'We will pay INR 48000 by 18 October 2026 after finance approval.'));
  fireEvent.click(screen.getByRole('button',{name:'Preview file'}));
  await screen.findByRole('alert');
  expect(screen.queryByRole('button',{name:'Preview as supporting context'})).not.toBeInTheDocument();
  expect(screen.queryByRole('button',{name:'Review payment wording'})).not.toBeInTheDocument();
  expect(screen.queryByRole('button',{name:'Confirm import'})).not.toBeInTheDocument();
  expect(app.commits).toHaveLength(0);
});
