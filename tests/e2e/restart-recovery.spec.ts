import { test,expect } from './support/test';
import { isolatedServer } from './support/server';
import { createCopy,investigate,confirmScenarioEvent } from './support/scenarioEvents';
import { caseView,command,post,readyDraft,history,type FaultPreset } from './support/fixtures';

for(const boundary of ['start','result','draft','approval','closure'] as const) {
  test(`actual process kill after ${boundary} commit reconciles once and preserves earlier state`,async({playwright,page})=>{
    test.setTimeout(60_000); // Three independent startups and two real process exits per journey.
    const server=await isolatedServer();await server.start();
    const request=await playwright.request.newContext({baseURL:server.url});
    try {
      const copy=await createCopy(request);const cid=copy.cases[boundary==='closure'?2:0].id;
      const earlier=await investigate(request,copy.id,cid);
      let view=await caseView(request,copy.id,cid);
      if(boundary!=='closure') {
        view=await readyDraft(request,copy.id,cid);
        if(boundary!=='approval') {
          expect((await post(request,copy.id,cid,'draft-reviews',command(view,{draft_version_id:view.draft.id,payload_hash:view.draft.payload_hash,expected_review_epoch:view.review_epoch,decision:'APPROVE'}))).status()).toBe(200);
          expect((await caseView(request,copy.id,cid)).review_state).toBe('APPROVED');
        }
      } else {
        await confirmScenarioEvent(request,copy.id,cid,'PK-003-U1');await investigate(request,copy.id,cid);
      }
      view=await caseView(request,copy.id,cid);
      const priorHistory=await history(request,copy.id,cid);
      const priorDraft=view.draft;
      const priorReviews=view.draft_reviews;
      // Arm a fresh process, never a runtime control endpoint. Only the selected next commit kills it.
      await server.stop();await server.start(`kill-after-${boundary}` as FaultPreset);
      let endpoint='investigations';let data:any=command(view,{retry_of:null});
      if(boundary==='draft') {endpoint='draft-versions';data=command(view,{investigation_id:view.draft.investigation_id,parent_version_id:view.draft.id,recipient:view.draft.recipient,exact_text:view.draft.exact_text.replace('Hello ','Hi ')});}
      if(boundary==='approval') {endpoint='draft-reviews';data=command(view,{draft_version_id:view.draft.id,payload_hash:view.draft.payload_hash,expected_review_epoch:view.review_epoch,decision:'APPROVE'});}
      if(boundary==='closure') {endpoint='closure';data=command(view,{investigation_id:view.current_result.investigation_id,confirmed_result_hash:view.current_result.result_hash,confirm:true});}
      // Start may return before asynchronous result commit; all other responses are deliberately lost.
      let returned:any;try{returned=await post(request,copy.id,cid,endpoint,data);}catch{}
      if(boundary==='result'&&returned)expect(returned.status()).toBe(202);
      await server.waitForExit();
      expect((await server.faultMetadata()).event).toBe({start:'INVESTIGATION_STARTED',result:'INVESTIGATION_COMPLETED',draft:'DRAFT_SAVED',approval:'DRAFT_REVIEWED',closure:'CASE_CLOSED'}[boundary]);
      await server.start();
      const receipt=await (await request.get(`/api/v1/operations/${data.operation_id}?demonstration_id=${copy.id}`)).json();
      expect(receipt.receipt.operation_id).toBe(data.operation_id);
      const replay=await post(request,copy.id,cid,endpoint,data);expect(await replay.json()).toEqual(receipt);
      const after=await caseView(request,copy.id,cid);
      expect(after.draft_reviews.slice(0,priorReviews.length)).toEqual(priorReviews);
      if(priorDraft) {
        const exact=await request.get(`/api/v1/draft-versions/${priorDraft.id}?demonstration_id=${copy.id}`);
        expect(exact.status()).toBe(200);expect((await exact.json()).draft_version).toEqual(priorDraft);
      }
      expect((await (await request.get(`/api/v1/investigations/${earlier.investigation_id}?demonstration_id=${copy.id}`)).json()).result).toEqual(earlier.result);
      let events=await history(request,copy.id,cid);
      expect(events.slice(0,priorHistory.length)).toEqual(priorHistory);
      const selected={start:'INVESTIGATION_STARTED',result:'INVESTIGATION_COMPLETED',draft:'DRAFT_SAVED',approval:'DRAFT_REVIEWED',closure:'CASE_CLOSED'}[boundary];
      expect(events.filter((e:any)=>e.event_type===selected&&e.operation_id===data.operation_id)).toHaveLength(1);
      if(boundary==='start') {expect(after.latest_completed_result).toEqual(earlier.result);const attempt=await (await request.get(`/api/v1/investigations/${receipt.investigation_id}?demonstration_id=${copy.id}`)).json();expect(attempt.status).toBe('INCOMPLETE');expect(attempt.failure_code).toBe('PROCESS_RESTARTED');}
      if(boundary==='result') {expect(after.latest_completed_result.investigation_id).toBe(receipt.investigation_id);expect(after.draft_generation_state).toBe('FAILED');}
      if(boundary==='draft')expect(after.draft.version).toBe(2);
      if(boundary==='closure')expect(after.lifecycle).toBe('CLOSED');
      else if(boundary==='approval') {
        expect(after.review_state).toBe('APPROVED');
        expect(after.draft_reviews).toHaveLength(1);
        await confirmScenarioEvent(request,copy.id,cid,'PK-001-U1');
        expect((await caseView(request,copy.id,cid)).review_state).toBe('INVALIDATED');
        events=await history(request,copy.id,cid);
      } else expect(after.review_state).not.toBe('APPROVED');
      await page.addInitScript(id=>localStorage.setItem('selected_demonstration_id',id),copy.id);await page.goto(server.url);
      if(boundary==='closure')await page.getByRole('button',{name:/PK-003/}).first().click();
      await expect(page.getByRole('button',{name:'History',exact:true})).toBeVisible();
      await server.kill();await server.start();
      expect(await history(request,copy.id,cid)).toEqual(events);
      if(boundary!=='closure')expect((await caseView(request,copy.id,cid)).review_state).not.toBe('APPROVED');
    }finally{await request.dispose();await server.stop();}
  });
}

test('unsaved browser wording survives actual backend hard restart without a saved version or approval',async({playwright,page})=>{
  test.setTimeout(60_000);
  const server=await isolatedServer();await server.start();
  const request=await playwright.request.newContext({baseURL:server.url});
  try {
    const copy=await createCopy(request);const cid=copy.cases[0].id;
    await investigate(request,copy.id,cid);const before=await readyDraft(request,copy.id,cid);
    const beforeHistory=await history(request,copy.id,cid);
    await page.addInitScript(id=>localStorage.setItem('selected_demonstration_id',id),copy.id);await page.goto(server.url);
    await page.getByRole('button',{name:'Review',exact:true}).click();
    const unsaved=before.draft.exact_text.replace('Hello ','Hi ');
    expect(unsaved).not.toBe(before.draft.exact_text);
    await page.getByLabel('Draft text').fill(unsaved);
    await expect(page.getByText('Unsaved wording. Save it as a new unapproved version before approval.',{exact:true})).toBeVisible();
    await server.kill();await server.start();await page.reload();
    await page.getByRole('button',{name:'Review',exact:true}).click();
    await expect(page.getByLabel('Draft text')).toHaveValue(unsaved);
    await expect(page.getByText('Unsaved wording. Save it as a new unapproved version before approval.',{exact:true})).toBeVisible();
    await expect(page.getByRole('button',{name:'Approve exact saved version'})).toBeDisabled();
    const after=await caseView(request,copy.id,cid);
    expect(after.draft).toEqual(before.draft);expect(after.draft_reviews).toEqual([]);expect(after.review_state).toBe('UNAPPROVED');
    expect(await history(request,copy.id,cid)).toEqual(beforeHistory);
  }finally{await request.dispose();await server.stop();}
});
