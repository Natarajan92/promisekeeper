import { test, expect } from './support/test';
import { spawn } from 'node:child_process';
import { createServer } from 'node:net';
import { mkdirSync, existsSync, writeFileSync } from 'node:fs';
import { randomUUID } from 'node:crypto';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
test('LIVE browser thirty opens, acknowledgements and visible terminal outcomes',async({page,playwright})=>{
  test.skip(process.env.PROMISEKEEPER_LIVE_MEASUREMENT!=='1','Explicit opt-in LIVE provider calls; STUB cannot qualify latency.');
  test.setTimeout(2_100_000);
  const output=process.env.PROMISEKEEPER_LIVE_BROWSER_REPORT??path.join(root,'reports/live-browser-responsiveness.json');
  if(existsSync(output))throw new Error('Preserve the existing measurement report; choose a fresh output path.');
  const folder=path.join(root,'.runtime/live-browser',randomUUID());mkdirSync(folder,{recursive:true});
  const port=await new Promise<number>(resolve=>{const server=createServer();server.listen(0,'127.0.0.1',()=>{const address=server.address();const port=typeof address==='object'&&address?address.port:0;server.close(()=>resolve(port));});});
  const child=spawn(path.join(root,'backend/.venv/Scripts/python.exe'),[path.join(root,'tests/e2e/support/live_server.py'),'--database',path.join(folder,'fresh.sqlite'),'--port',String(port)],{cwd:root,windowsHide:true,stdio:['pipe','ignore','ignore'],env:{...process.env,PYTHONPATH:path.join(root,'backend/src')}});
  const base=`http://127.0.0.1:${port}`;
  const report:any={schema_version:'1',suite:'responsiveness-browser',agent_mode:'LIVE',provider:'NEBIUS',requested_model:'zai-org/GLM-5.3-Flash',clock_mode:'REAL',browser:'installed Chrome/headless',viewport:{width:1280,height:720},started_at:new Date().toISOString(),status:'RUNNING',requested_trials:30,unexecuted_trials:30,trials:[],thresholds:{open_seconds:3,acknowledgement_seconds:2,terminal_seconds:60,required_fast_opens:29,required_fast_acknowledgements:29},integrity_qualification:false};
  const save=()=>writeFileSync(output,JSON.stringify(report,null,2)+'\n');save();
  const request=await playwright.request.newContext({baseURL:base});
  try {
    await expect.poll(async()=>{try{return (await request.get('/api/v1/health',{timeout:500})).ok();}catch{return false;}},{timeout:15_000}).toBe(true);
    const health=await (await request.get('/api/v1/health')).json();expect(health.agent_mode).toBe('LIVE');report.health=health;
    await page.setViewportSize(report.viewport);
    for(let trial=1;trial<=10;trial++) {
      const created=await request.post('/api/v1/demonstrations',{headers:{'X-PromiseKeeper-Request':'1'},data:{schema_version:'1',operation_id:randomUUID(),catalogue_version:'release-0.1',variant_id:null,clock_mode:'REAL'}});
      expect(created.status()).toBe(201);const did=(await created.json()).demonstration_id;
      const cases=(await (await request.get(`/api/v1/demonstrations/${did}/cases`)).json()).cases;
      await page.addInitScript(id=>localStorage.setItem('selected_demonstration_id',id),did);await page.goto(base);
      for(const item of cases) {
        const row:any={trial,case:item.catalogue_case_id,copy_id:did};report.in_progress={trial,case:item.catalogue_case_id,phase:'PREPARE_SAVED_CASE_OPEN'};save();
        const other=cases.find((candidate:any)=>candidate.id!==item.id);
        await page.getByRole('button',{name:new RegExp(other.catalogue_case_id)}).first().click();
        await expect(page.locator('.case-heading')).toContainText(other.client);
        report.in_progress.phase='SAVED_CASE_OPEN';save();
        const opening=Date.now();await page.getByRole('button',{name:new RegExp(item.catalogue_case_id)}).first().click();
        await expect(page.locator('.case-heading')).toContainText(item.client);await expect(page.getByRole('heading',{name:'Saved evidence',exact:true})).toBeVisible();
        row.open_seconds=(Date.now()-opening)/1000;
        report.in_progress.phase='INVESTIGATION_START';save();
        const began=Date.now();const receiptPromise=page.waitForResponse(response=>response.url().includes(`/cases/${item.id}/investigations?`)&&response.request().method()==='POST');
        await page.getByRole('button',{name:'Investigate case',exact:true}).click();
        const response=await receiptPromise;expect(response.status()).toBe(202);const receipt=await response.json();row.http_acknowledgement_seconds=(Date.now()-began)/1000;row.investigation_id=receipt.investigation_id;
        await expect.poll(async()=>/Investigation start saved|result saved|Investigation incomplete/.test(await page.locator('.investigation-controls').innerText()),{timeout:10_000,intervals:[20,50,100]}).toBe(true);
        row.acknowledgement_seconds=(Date.now()-began)/1000;
        report.in_progress.phase='VISIBLE_TERMINAL';save();
        let visible=false;
        try {await expect.poll(async()=>/result saved|Investigation incomplete|Connection limitation/.test(await page.locator('.investigation-controls').innerText()),{timeout:61_000,intervals:[50,100,250]}).toBe(true);visible=true;}catch{row.visible_terminal_missing=true;}
        row.terminal_seconds=(Date.now()-began)/1000;row.visible_terminal=visible;
        const attempt=await (await request.get(`/api/v1/investigations/${receipt.investigation_id}?demonstration_id=${did}`)).json();
        row.attempt_status=attempt.status;row.failure_code=attempt.failure_code;row.result_present=!!attempt.result;row.displayed_status=await page.locator('.investigation-controls').innerText();
        report.trials.push(row);report.unexecuted_trials=30-report.trials.length;report.in_progress=null;save();
        // Provider errors are measured terminal outcomes; they never qualify extraction quality.
        if(attempt.status==='RUNNING'){report.blocking_reason='SERVER_STILL_RUNNING_AFTER_VISIBLE_LIMITATION';break;}
      }
      if(report.blocking_reason)break;
    }
    report.fast_opens=report.trials.filter((r:any)=>r.open_seconds<=3).length;
    report.fast_acknowledgements=report.trials.filter((r:any)=>r.acknowledgement_seconds<=2).length;
    report.all_visible_within_60_seconds=report.trials.every((r:any)=>r.visible_terminal&&r.terminal_seconds<=60);
    report.status=report.trials.length===30&&report.fast_opens>=29&&report.fast_acknowledgements>=29&&report.all_visible_within_60_seconds?'PASS':'FAIL';
    report.finished_at=new Date().toISOString();save();expect(report.status).toBe('PASS');
  }catch(error){report.status='FAIL';report.failure='LIVE_BROWSER_MEASUREMENT_DID_NOT_COMPLETE';report.failure_phase=report.in_progress;report.failure_type=error instanceof Error?error.name:'UNKNOWN';report.finished_at=new Date().toISOString();save();throw error;}
  finally {await request.dispose();if(child.exitCode===null){const done=new Promise<void>(resolve=>child.once('exit',()=>resolve()));child.stdin?.end('stop\n');await done;}}
});
