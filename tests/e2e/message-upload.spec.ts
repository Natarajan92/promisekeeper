import {randomUUID} from 'node:crypto';
import {mkdirSync} from 'node:fs';
import {test,expect} from './support/test';
import {mutationHeaders} from './support/scenarioEvents';

const body='Namaste,\nInvoice: MT-1001\nHum ₹48000 18 October 2026 ko payment kar denge.\nThank you,\nSuresh Mehta\nMeera Textiles\n';
mkdirSync('.runtime/message-upload',{recursive:true});

for(const kind of ['customer_email','remittance_email','whatsapp']){
  test(`${kind} can recover from context-only preview and save the original message to its workspace`,async({page,request})=>{
    const command={schema_version:'1',operation_id:randomUUID(),kind:'invoices',filename:'invoices.csv',demonstration_id:null,content:'invoice_id,customer_name,amount,currency,issued_at,due_at\nMT-1001,Meera Textiles,60000,INR,2026-10-01,2026-10-10\n'};
    const checked=await request.post('/api/v1/intake/previews',{headers:mutationHeaders,data:command});
    expect(checked.status()).toBe(200);
    const imported=await request.post('/api/v1/intake/commits',{headers:mutationHeaders,data:{...command,operation_id:randomUUID(),confirmed_preview_hash:(await checked.json()).preview_hash,confirm:true,fictional_data:true}});
    expect(imported.status()).toBe(200);
    const did=(await imported.json()).demonstration_id;
    const state=async()=>{
      const response=await request.get(`/api/v1/demonstrations/${did}/intake`);
      expect(response.status()).toBe(200);return response.json();
    };
    const cid=(await state()).cases[0].id;
    const headers=kind==='whatsapp'?'Sender: Meera Textiles accounts\nSent: 2026-10-14T10:30:00+05:30\n':'From: Suresh <accounts@meera.example>\nDate: Wed, 14 Oct 2026 10:30:00 +0530\nSubject: Payment for invoice MT-1001\nContent-Type: text/plain; charset=utf-8\n';
    const content=headers+'\n'+body;
    const filename=kind==='whatsapp'?'message.txt':'message.eml';
    await page.addInitScript(id=>localStorage.setItem('selected_demonstration_id',id),did);
    await page.goto('/#/upload?step=4');
    await page.getByRole('combobox',{name:'File type',exact:true}).selectOption(kind);
    await page.getByRole('combobox',{name:'Attach communication to invoice',exact:true}).selectOption(cid);
    await page.getByLabel('Upload file',{exact:true}).setInputFiles({name:filename,mimeType:'text/plain',buffer:Buffer.from(content)});
    await expect(page.getByText(new RegExp(`Selected ${filename}`))).toBeVisible();
    await page.getByRole('combobox',{name:'Who sent this message?',exact:true}).selectOption('CUSTOMER');
    const context=page.getByLabel('I reviewed unsupported wording as supporting context only; no payment claim or promise should be extracted.',{exact:true});
    await expect(context).not.toBeVisible();
    await page.getByText('Optional: supporting context only',{exact:true}).click();
    await context.check();
    await page.getByRole('button',{name:'Preview file',exact:true}).click();
    await expect(page.locator('.intake-preview [role=alert]')).toBeVisible();
    await expect(page.getByRole('button',{name:'Confirm import',exact:true})).toHaveCount(0);
    expect((await state()).documents).toEqual([]);
    await page.screenshot({path:`.runtime/message-upload/${kind}-needs-review.png`,fullPage:true});
    await page.getByRole('button',{name:'Review payment wording',exact:true}).click();
    await expect(page.locator('.intake-extracted blockquote')).toHaveText('Hum ₹48000 18 October 2026 ko payment kar denge.');
    await expect(context).not.toBeChecked();
    await expect(page.getByRole('combobox',{name:'Attach communication to invoice',exact:true})).toHaveValue(cid);
    await expect(page.getByRole('combobox',{name:'Who sent this message?',exact:true})).toHaveValue('CUSTOMER');
    await expect(page.locator('.intake-preview')).toContainText('1 message');
    await expect(page.locator('.intake-preview')).not.toContainText('CSV row');
    await expect(page.getByRole('button',{name:'Confirm import',exact:true})).toBeDisabled();
    expect((await state()).documents).toEqual([]);
    if(kind==='whatsapp')await page.setViewportSize({width:390,height:844});
    await page.screenshot({path:`.runtime/message-upload/${kind}-ready-to-add.png`,fullPage:true});
    await page.getByLabel('I reviewed this preview and confirm the records are correct.',{exact:true}).check();
    await page.getByRole('button',{name:'Confirm import',exact:true}).click();
    await expect(page.getByRole('heading',{name:'Import preview',exact:true})).toHaveCount(0);
    await expect.poll(async()=>(await state()).documents.length).toBe(1);
    const document=(await state()).documents[0];
    expect(document.case_id).toBe(cid);expect(document.kind).toBe(kind);
    expect(document.extraction.context_only).toBe(false);
    expect(document.extraction.candidates[0].amount_text).toBe('48000');
    const original=await request.get(`/api/v1/demonstrations/${did}/intake/files/${document.batch_id}`);
    expect((await original.json()).content).toBe(content);
    await page.reload();
    await expect(page.locator('.intake-workspace-summary')).toContainText('1 communication documents');
    await page.getByText('Original uploaded files and communication (2)',{exact:true}).click();
    await page.getByText(`Inspect original file: ${filename}`,{exact:true}).click();
    await expect(page.locator('.intake-original pre').last()).toHaveText(content);
  });
}
