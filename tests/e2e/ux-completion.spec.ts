import {mkdirSync,writeFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {test,expect} from './support/test';
import {createCopy} from './support/scenarioEvents';
import {caseView,history,showAllCases} from './support/fixtures';

test('Phase 3 STUB rehearsal: morning briefing, exact approval, Cedar comparison, closure and saved fallback',async({page,request})=>{
  test.setTimeout(120_000); // Complete multi-case route plus visual checks; product deadlines are unchanged.
  const folder=fileURLToPath(new URL('../../.runtime/owner-ux-phase3/',import.meta.url));mkdirSync(folder,{recursive:true});
  const started=performance.now(),startedAt=new Date().toISOString();const checkpoints:{name:string;elapsed_ms:number}[]=[];
  const checkpoint=(name:string)=>checkpoints.push({name,elapsed_ms:Math.round(performance.now()-started)});
  const health=await (await request.get('/api/v1/health')).json();expect(health.agent_mode).toBe('STUB');
  const copy=await createCopy(request),north=copy.cases.find(item=>item.catalogue_case_id==='PK-001')!.id,cedar=copy.cases.find(item=>item.catalogue_case_id==='PK-003')!.id;
  const view=(cid:string)=>caseView(request,copy.id,cid);
  await page.setViewportSize({width:1280,height:800});
  await page.addInitScript(id=>localStorage.setItem('selected_demonstration_id',id),copy.id);
  await page.goto('/');await expect(page.getByText('Scripted sample (STUB)',{exact:true})).toBeVisible();
  await expect(page.getByText('Fixed sample date (REFERENCE)',{exact:true})).toBeVisible();
  await page.screenshot({path:`${folder}workspace-desktop.png`});checkpoint('Fictional STUB/REFERENCE scope visible');

  await page.getByRole('button',{name:'Start morning review'}).click();
  await expect(page.getByText('Review complete. Choose a case to see its recommendation.')).toBeVisible({timeout:30_000});
  await page.getByRole('button',{name:/Northstar Analytics.*draft ready/}).click();
  await expect(page.getByRole('heading',{name:'Northstar Analytics',exact:true})).toBeFocused();
  await expect(page.locator('.findings .financial-summary').first()).toBeInViewport({ratio:1});
  await expect(page.getByRole('button',{name:'Review suggested message'})).toBeInViewport({ratio:1});
  const northSaved=await view(north);expect(northSaved.current_result.financial_facts.balance.minor_units).toBe('8000000');
  for(const id of ['PK-001-I1','PK-001-L1','PK-001-M1']){
    const record=northSaved.evidence.find((item:any)=>item.stable_source_id===id);
    const button=page.getByRole('button',{name:`${id} / v${record.version}`,exact:true}).first();
    await button.click();await expect(page.getByRole('dialog').locator('pre')).toHaveText(record.original_content);
    await page.keyboard.press('Escape');await expect(button).toBeFocused();
  }
  await page.locator('.case-heading').scrollIntoViewIfNeeded();await page.screenshot({path:`${folder}findings-desktop.png`});
  await page.getByRole('button',{name:'Review suggested message'}).click();
  expect(await page.getByLabel('Draft text').inputValue()).toBe(northSaved.draft.exact_text);
  await page.getByRole('button',{name:'Approve exact saved version'}).click();
  await expect(page.getByRole('button',{name:'Copy approved message'})).toBeEnabled();
  expect((await view(north)).draft.exact_text).toBe(northSaved.draft.exact_text);checkpoint('Northstar sources and exact saved message approved; nothing sent');

  await page.getByRole('button',{name:/PK-003.*Cedar Retail Labs/}).click();await page.getByRole('button',{name:'Findings',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Verify the payment',exact:true})).toBeVisible();
  await expect(page.getByText(/Check your bank statement or accounting records outside PromiseKeeper/)).toBeVisible();
  const before=await view(cedar);expect(before.current_result.action).toBe('VERIFY_PAYMENT');
  expect(before.current_result.financial_facts.balance.minor_units).toBe('6000000');
  const claim=before.evidence.find((item:any)=>item.stable_source_id==='PK-003-M1');
  await page.getByRole('button',{name:`PK-003-M1 / v${claim.version}`,exact:true}).first().click();
  await expect(page.getByRole('dialog').locator('pre')).toHaveText(claim.original_content);await page.keyboard.press('Escape');
  checkpoint('Cedar payment claim distinguished from verified ledger evidence');
  await page.getByRole('button',{name:'History',exact:true}).click();
  await page.getByLabel('Fictional update').selectOption('PK-003-U1');await page.getByRole('button',{name:'Preview selected fictional update'}).click();
  await expect(page.locator('.confirmation-panel pre')).toContainText('CR-T2');
  await page.getByLabel('I reviewed this exact fictional update').check();await page.getByRole('button',{name:'Confirm fictional update'}).click();
  await expect(page.getByText(/evidence changed/i).first()).toBeVisible();
  await page.getByRole('button',{name:'Findings',exact:true}).click();await expect(page.getByText(/Historical result: evidence changed/i)).toBeVisible();
  await page.getByRole('button',{name:'Investigate case',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Review case closure',exact:true})).toBeVisible();
  const after=await view(cedar);expect(after.current_result.action).toBe('CLOSE');expect(after.current_result.financial_facts.balance.minor_units).toBe('0');expect(after.lifecycle).toBe('OPEN');
  checkpoint('Confirmed U1 and reinvestigation saved verified zero remainder; case still open');

  const noWriteHistory=await history(request,copy.id,cedar),writes:string[]=[];
  const watch=(req:{method:()=>string;url:()=>string})=>{if(req.method()==='POST'&&req.url().includes('/api/v1/'))writes.push(req.url());};page.on('request',watch);
  await page.getByRole('button',{name:'Compare saved investigations'}).click();const panel=page.locator('.what-changed');
  await expect(panel.getByText('Recommendation changed',{exact:true})).toBeVisible();
  await expect(panel.getByLabel('Earlier saved values')).toContainText('INR 60,000.00');await expect(panel.getByLabel('Later saved values')).toContainText('INR 0.00');
  await panel.getByRole('button',{name:/Inspect later source PK-003-L2/}).click();await expect(page.getByRole('dialog').locator('pre')).toContainText('CR-T2');await page.keyboard.press('Escape');
  for(const side of ['earlier','later']){await panel.getByRole('button',{name:`Open ${side} investigation`}).click();await expect(panel.locator('.historical-record')).toContainText(side==='earlier'?before.current_result.result_hash:after.current_result.result_hash);}
  for(const result of [before.current_result,after.current_result])expect((await (await request.get(`/api/v1/investigations/${result.investigation_id}?demonstration_id=${copy.id}`)).json()).result).toEqual(result);
  expect(await history(request,copy.id,cedar)).toEqual(noWriteHistory);expect(writes).toEqual([]);page.off('request',watch);
  checkpoint('Comparison and exact originals inspected with GETs only and immutable results');
  await page.getByRole('button',{name:'Review case closure',exact:true}).click();await expect(page.getByRole('button',{name:'Confirm case closure'})).toBeDisabled();
  await page.getByLabel('Confirm closure of invoice CR-312').check();await page.getByRole('button',{name:'Confirm case closure'}).click();
  await expect(page.locator('.case-heading')).toContainText('CLOSED');checkpoint('Owner explicitly confirmed closure');

  const savedHistory=await history(request,copy.id,cedar);writes.length=0;page.on('request',watch);
  await page.reload();await showAllCases(page);await page.getByRole('button',{name:/PK-003.*Cedar Retail Labs/}).click();await page.getByRole('button',{name:'Findings',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Review case closure',exact:true})).toBeVisible();expect(await history(request,copy.id,cedar)).toEqual(savedHistory);
  expect(writes).toEqual([]);checkpoint('Labelled saved-result fallback reopened without an investigation');
  await page.getByRole('button',{name:/PK-001.*Northstar Analytics/}).click();await page.getByRole('button',{name:'Findings',exact:true}).click();
  await page.setViewportSize({width:390,height:844});await page.addStyleTag({content:'html{font-size:200%!important}'});
  expect(await page.evaluate(()=>getComputedStyle(document.documentElement).fontSize)).toBe('32px');
  for(const section of ['Evidence','Findings','Timeline','Review','History']){
    await page.getByRole('button',{name:section,exact:true}).click();await page.locator('.view-tabs').scrollIntoViewIfNeeded();
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
    await page.locator('.view-content').screenshot({path:`${folder}${section.toLowerCase()}-mobile-200.png`});
  }
  expect(writes).toEqual([]);page.off('request',watch);checkpoint('All five sections inspected at390px and actual200% text without writes or overflow');
  const elapsedMs=Math.round(performance.now()-started);
  writeFileSync(`${folder}rehearsal.json`,JSON.stringify({mode:'STUB',clock_mode:'REFERENCE',operator:'AUTOMATED_AGENT',started_at:startedAt,finished_at:new Date().toISOString(),elapsed_ms:elapsedMs,checkpoints,human_narration_measured:false,human_study:false,live_qualification:false,publication:false},null,2));
  expect(elapsedMs).toBeLessThan(300_000);
});
