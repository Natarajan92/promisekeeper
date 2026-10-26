import {test,expect} from './support/test';
import {createCopy,investigate,confirmScenarioEvent} from './support/scenarioEvents';
import {fileURLToPath} from 'node:url';

test('guided follow-up shows a useful overview and copies only the approved exact message',async({page,request,context})=>{
  const copy=await createCopy(request);
  await page.addInitScript(id=>localStorage.setItem('selected_demonstration_id',id),copy.id);
  await context.grantPermissions(['clipboard-read','clipboard-write']);
  await page.goto('/#/cases');
  const card=page.getByRole('button',{name:/PK-001.*Northstar Analytics/});
  await expect(card).toContainText('₹80,000.00');
  await expect(card).toContainText('Not investigated');
  await card.click();
  await page.getByRole('button',{name:'Investigate case',exact:true}).click();
  await expect(page.getByText('COMPLETE result saved.',{exact:true})).toBeVisible();
  await page.getByRole('link',{name:/^Cases/}).click();
  await expect(card).toContainText('Follow up');
  await card.click();
  await page.getByRole('button',{name:'View recommendation',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Follow up on the overdue balance',exact:true})).toBeVisible();
  await expect(page.getByRole('button',{name:'Accept recommendation',exact:true})).toBeVisible();
  await page.screenshot({path:fileURLToPath(new URL('../../.runtime/ux-phase1-desktop.png',import.meta.url)),fullPage:true});
  await page.getByRole('button',{name:'Review suggested message',exact:true}).click();
  await expect(page.getByRole('button',{name:'Copy approved message'})).toHaveCount(0);
  await page.getByRole('button',{name:'Approve exact saved version'}).click();
  await expect(page.getByRole('button',{name:'Copy approved message'})).toBeEnabled();
  const view=await (await request.get(`/api/v1/cases/${copy.cases[0].id}?demonstration_id=${copy.id}`)).json();
  await page.getByRole('button',{name:'Copy approved message'}).click();
  await expect(page.getByText('Version 1 copied. Nothing has been sent.',{exact:true})).toBeVisible();
  // Native Windows clipboard reads use CRLF; the application writes the exact saved string.
  expect((await page.evaluate(()=>navigator.clipboard.readText())).replaceAll('\r\n','\n')).toBe(view.draft.exact_text);
  await page.getByLabel('Draft text').fill(view.draft.exact_text.replace('Hello ','Hi '));
  await expect(page.getByRole('button',{name:'Copy approved message'})).toBeDisabled();
});

test('wait and verification journeys explain the next action in IST without demanding a message',async({page,request})=>{
  const copy=await createCopy(request);
  await investigate(request,copy.id,copy.cases[1].id);
  await investigate(request,copy.id,copy.cases[2].id);
  await page.addInitScript(id=>localStorage.setItem('selected_demonstration_id',id),copy.id);
  await page.goto('/#/cases');await page.getByRole('button',{name:/Show all \d+ cases/}).click();await page.getByRole('button',{name:/PK-002.*Meridian Software/}).click();
  await page.getByRole('button',{name:'View recommendation',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Wait until the review date'})).toBeVisible();
  await expect(page.locator('.next-step')).toContainText('26 Oct 2026, 00:00 IST');
  await expect(page.locator('.next-step')).not.toContainText('T18:30');
  await expect(page.getByRole('button',{name:'Review suggested message'})).toHaveCount(0);
  await page.getByRole('link',{name:/^Cases/}).click();
  await page.getByRole('button',{name:/PK-003.*Cedar Retail Labs/}).click();
  await page.getByRole('button',{name:'View recommendation',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Verify the payment'})).toBeVisible();
  await page.getByRole('button',{name:'Inspect payment evidence',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Saved evidence'})).toBeVisible();
  await page.setViewportSize({width:400,height:900});
  await page.addStyleTag({content:'html{font-size:200%}'});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
  await page.screenshot({path:fileURLToPath(new URL('../../.runtime/ux-phase1-narrow.png',import.meta.url)),fullPage:true});
});

test('changed evidence labels old advice as previous and clears its overview action',async({page,request})=>{
  const copy=await createCopy(request);await investigate(request,copy.id,copy.cases[0].id);
  await confirmScenarioEvent(request,copy.id,copy.cases[0].id,'PK-001-U1');
  await page.addInitScript(id=>localStorage.setItem('selected_demonstration_id',id),copy.id);
  await page.goto('/#/cases');
  const card=page.getByRole('button',{name:/PK-001.*Northstar Analytics/});
  await expect(card).toContainText('Review required');await expect(card).not.toContainText('Follow up');
  await card.click();
  await page.getByRole('button',{name:'View previous recommendation'}).click();
  await expect(page.getByText(/Historical result:/)).toBeVisible();
  await expect(page.getByRole('button',{name:'Review suggested message'})).toHaveCount(0);
  await expect(page.getByRole('button',{name:'Accept recommendation'})).toBeDisabled();
});

test('a lost investigation start response keeps the earlier approved message fenced',async({page,request})=>{
  const copy=await createCopy(request);await investigate(request,copy.id,copy.cases[0].id);
  await page.addInitScript(id=>localStorage.setItem('selected_demonstration_id',id),copy.id);
  await page.goto(`/#/cases/${copy.cases[0].id}`);await page.getByRole('button',{name:'Overview',exact:true}).click();
  await page.getByRole('button',{name:'Approve exact saved version'}).click();
  await expect(page.getByRole('button',{name:'Copy approved message'})).toBeEnabled();
  const pattern=`**/api/v1/cases/${copy.cases[0].id}/investigations?*`;
  await page.route(pattern,async route=>{await route.fetch();await route.abort('connectionreset');});
  await page.getByRole('button',{name:'Investigate case',exact:true}).click();
  await expect(page.getByText(/Connection unavailable/).first()).toBeVisible();
  await expect(page.getByRole('button',{name:'Copy approved message'})).toBeDisabled();
  await page.unroute(pattern);await page.reload();
  await page.getByRole('button',{name:'Overview',exact:true}).click();
  await expect(page.getByLabel('Draft text')).toBeVisible();
  await expect(page.getByRole('button',{name:'Copy approved message'})).toHaveCount(0);
});

test('a rejection receipt with a failed case refresh cannot revive approved copying',async({page,request})=>{
  const copy=await createCopy(request);await investigate(request,copy.id,copy.cases[0].id);
  await page.addInitScript(id=>localStorage.setItem('selected_demonstration_id',id),copy.id);
  await page.goto(`/#/cases/${copy.cases[0].id}`);await page.getByRole('button',{name:'Overview',exact:true}).click();
  await page.getByRole('button',{name:'Approve exact saved version'}).click();
  await expect(page.getByRole('button',{name:'Copy approved message'})).toBeEnabled();
  const pattern=`**/api/v1/cases/${copy.cases[0].id}?*`;
  await page.route(pattern,route=>route.abort('connectionreset'));
  await page.getByRole('button',{name:'Reject exact saved version'}).click();
  await expect(page.locator('#case-draft').getByText(/Rejection recorded/)).toBeVisible();
  await expect(page.getByRole('button',{name:'Refresh saved case'})).toBeVisible();
  await expect(page.getByRole('button',{name:'Copy approved message'})).toBeDisabled();
  await page.unroute(pattern);await page.getByRole('button',{name:'Refresh saved case'}).click();
  await expect(page.getByRole('button',{name:'Copy approved message'})).toHaveCount(0);
});
