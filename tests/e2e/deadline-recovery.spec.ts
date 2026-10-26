import { test,expect } from './support/test';
import { isolatedServer } from './support/server';
import { createCopy,confirmScenarioEvent } from './support/scenarioEvents';
import { caseView,command,post } from './support/fixtures';

test('wall clock retry exhaustion is terminal and a late provider result cannot overwrite it',async({playwright,page})=>{
  test.setTimeout(85_000);
  const server=await isolatedServer(0,'late-provider');await server.start();
  const request=await playwright.request.newContext({baseURL:server.url});
  try {
    const copy=await createCopy(request);const cid=copy.cases[0].id;
    const view=await caseView(request,copy.id,cid);const wallStart=Date.now();
    const response=await post(request,copy.id,cid,'investigations',command(view,{retry_of:null}));expect(response.status()).toBe(202);
    const receipt=await response.json();const attemptPath=`/api/v1/investigations/${receipt.investigation_id}?demonstration_id=${copy.id}`;
    await page.addInitScript(id=>localStorage.setItem('selected_demonstration_id',id),copy.id);await page.goto(`${server.url}/#/cases/${cid}`);
    let terminal:any;
    await expect.poll(async()=>{terminal=await (await request.get(attemptPath)).json();return terminal.status;},{timeout:58_000,intervals:[500]}).toBe('INCOMPLETE');
    const elapsed=Date.now()-wallStart;expect(elapsed).toBeGreaterThanOrEqual(39_000);expect(elapsed).toBeLessThan(60_000);
    expect(terminal.failure_code).toBe('INVESTIGATOR_TIMEOUT');expect(terminal.result).toBeNull();
    const extraction=terminal.progress.filter((s:any)=>s.step_name==='EXTRACTION');
    expect(extraction.map((s:any)=>s.invocation_kind)).toEqual(['INITIAL','AUTO_RETRY']);
    expect(extraction.every((s:any)=>s.outcome==='TRANSIENT_FAILURE')).toBe(true);
    await expect(page.getByText(/Investigation incomplete:/)).toBeVisible();
    await expect.poll(async()=> (await server.faultMetadata()).provider_returns,{timeout:12_000,intervals:[250]}).toBe(1);
    // The first callback returns at 45 real seconds, after both 20-second reservations expired.
    await new Promise(resolve=>setTimeout(resolve,300));
    expect(await (await request.get(attemptPath)).json()).toEqual(terminal);
    expect((await caseView(request,copy.id,cid)).latest_completed_result).toBeNull();
    expect((await server.faultMetadata()).provider_calls).toBe(1);
  }finally{await request.dispose();await server.stop();}
});

test('real retry exhaustion keeps the reference business clock independent from execution deadlines',async({playwright})=>{
  const server=await isolatedServer(0,'retry-exhaustion');await server.start();
  const request=await playwright.request.newContext({baseURL:server.url});
  try {
    const copy=await createCopy(request,'FV-18-A');const cid=copy.cases[1].id;
    const catalogue=await (await request.get('/api/v1/catalogue')).json();const clock=catalogue.events.find((e:any)=>e.id.startsWith('FV-18-A'));
    const run=async()=>{
      const before=Date.now();const result=await post(request,copy.id,cid,'investigations',command(await caseView(request,copy.id,cid),{retry_of:null}));expect(result.status()).toBe(202);
      const started=await result.json();let terminal:any;
      await expect.poll(async()=>{terminal=await (await request.get(`/api/v1/investigations/${started.investigation_id}?demonstration_id=${copy.id}`)).json();return terminal.status;}).toBe('INCOMPLETE');
      expect(Date.parse(started.deadline_at)-before).toBeGreaterThan(50_000);expect(Date.parse(started.deadline_at)-before).toBeLessThan(56_000);
      expect(terminal.progress.filter((s:any)=>s.step_name==='EXTRACTION').map((s:any)=>s.invocation_kind)).toEqual(['INITIAL','AUTO_RETRY']);return started;
    };
    const first=await run();await confirmScenarioEvent(request,copy.id,cid,clock.id);const second=await run();
    expect(first.evaluation_at).not.toBe(second.evaluation_at);expect(Date.parse(second.deadline_at)-Date.parse(first.deadline_at)).toBeLessThan(10_000);
    expect((await server.faultMetadata()).provider_calls).toBe(4);
  }finally{await request.dispose();await server.stop();}
});

test('unreachable server visibly limits the real running UI within sixty seconds without inventing a result',async({playwright,page})=>{
  test.setTimeout(80_000);
  const server=await isolatedServer(0,'blocked-provider');await server.start();
  const request=await playwright.request.newContext({baseURL:server.url});
  try {
    const copy=await createCopy(request);const cid=copy.cases[0].id;
    await page.addInitScript(id=>localStorage.setItem('selected_demonstration_id',id),copy.id);await page.goto(`${server.url}/#/cases/${cid}`);
    const startButton=page.getByRole('button',{name:'Investigate case',exact:true});
    await startButton.evaluate(button=>{
      const timing={clicked:0,limited:0};(window as any).__recoveryTiming=timing;
      button.addEventListener('click',()=>{timing.clicked=Date.now();},{once:true,capture:true});
      const observer=new MutationObserver(()=>{
        if(!timing.limited&&document.querySelector('.investigation-controls .notice')?.textContent?.includes('Connection limitation:')) {
          timing.limited=Date.now();observer.disconnect();
        }
      });observer.observe(document.body,{subtree:true,childList:true,characterData:true,attributes:true});
    });
    const started=Date.now();await startButton.click();
    await expect(page.getByRole('button',{name:'Investigation running',exact:true})).toBeVisible();
    await server.kill();
    await expect(page.getByText(/Connection unavailable|Connection limitation/).first()).toBeVisible({timeout:9_000});
    expect(Date.now()-started).toBeLessThan(60_000);
    // Wait for the production watchdog using the real browser clock, allowing only scheduler tolerance.
    await expect(page.getByText(/Connection limitation: no terminal result confirmed within 60 seconds/)).toBeVisible({timeout:62_000});
    const timing=await page.evaluate(()=>(window as any).__recoveryTiming);
    expect(timing.clicked).toBeGreaterThan(0);expect(timing.limited-timing.clicked).toBeLessThan(62_000);
    await expect(page.getByRole('button',{name:'Check saved investigation status'})).toBeVisible();
    await server.start();const after=await caseView(request,copy.id,cid);expect(after.latest_completed_result).toBeNull();expect(after.freshness).toBe('INCOMPLETE');expect(after.running_attempt).toBeNull();
  }finally{await request.dispose();await server.stop();}
});
