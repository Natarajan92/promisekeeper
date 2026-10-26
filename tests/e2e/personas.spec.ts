import {mkdirSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {test,expect,type Page} from './support/test';
import {createCopy,confirmScenarioEvent,investigate} from './support/scenarioEvents';
import {showAllCases} from './support/fixtures';

// Simulated persona walkthroughs (agent-run, STUB mode, fictional data). Not a real-user study.
const shots=fileURLToPath(new URL('../../.runtime/personas/',import.meta.url));
mkdirSync(shots,{recursive:true});
const shot=(page:Page,name:string)=>page.screenshot({path:`${shots}${name}.png`,fullPage:true});
async function open(page:Page,id:string){await page.addInitScript(copy=>localStorage.setItem('selected_demonstration_id',copy),id);await page.goto('/');}
async function noSideways(page:Page){expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1)).toBe(true);}

test('P1 busy owner: one morning review gives a briefing and a ready follow-up draft',async({page,request})=>{
  await page.setViewportSize({width:1280,height:800});
  const copy=await createCopy(request);await open(page,copy.id);
  await shot(page,'p1-first-run');
  await page.getByRole('button',{name:'Start morning review'}).click();
  await expect(page.getByText('Review complete. Choose a case to see its recommendation.')).toBeVisible({timeout:30_000});
  await expect(page.locator('.briefing-text')).not.toBeVisible();
  await page.getByText('Read saved briefing',{exact:true}).click();
  await expect(page.locator('.briefing-text')).toContainText('Northstar Analytics');
  await shot(page,'p1-briefing');
  await page.getByRole('button',{name:/Northstar Analytics.*draft ready/}).click();
  await expect(page.getByRole('heading',{name:'Follow up on the overdue balance'})).toBeVisible();
  await expect(page.getByRole('heading',{name:'Northstar Analytics',exact:true})).toBeFocused();
  await expect(page.locator('.findings .financial-summary')).toBeInViewport({ratio:1});
  await expect(page.getByRole('button',{name:'Review suggested message'})).toBeInViewport({ratio:1});
  await expect(page.getByRole('region',{name:'How your AI team worked on this case'})).toHaveCount(0);
  await page.screenshot({path:`${shots}owner-phase1-desktop.png`});
  let writes=0;page.on('request',request=>{if(request.method()==='POST')writes++;});
  await page.getByText('Processing details',{exact:true}).click();
  await expect(page.getByRole('region',{name:'How your AI team worked on this case'})).toContainText('Tone reviewer');
  expect(writes).toBe(0);
  await shot(page,'p1-findings-trace');
  await page.getByRole('button',{name:'Overview',exact:true}).click();
  await expect(page.getByLabel('Draft text')).toHaveValue(/We truly value working with your team/);
  await shot(page,'p1-review');
});

test('P2 relationship-protective owner: an "already paid" claim never becomes a demand',async({page,request})=>{
  const copy=await createCopy(request);const cedar=copy.cases[2];
  await investigate(request,copy.id,cedar.id);await open(page,copy.id);
  await page.getByRole('link',{name:/^Cases/}).click();await page.getByRole('button',{name:/PK-003.*Cedar Retail Labs/}).click();
  await page.getByRole('button',{name:'Overview',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Verify the payment'})).toBeVisible();
  await expect(page.locator('main')).not.toContainText(/you owe|overdue amount due|legal action/i);
  await shot(page,'p2-verify-payment');
  await page.getByRole('button',{name:'Overview',exact:true}).click();
  await shot(page,'p2-review');
});

test('P3 returning owner: new evidence makes the old result historical and the supervisor re-investigates',async({page,request})=>{
  const copy=await createCopy(request);const northstar=copy.cases[0];
  await investigate(request,copy.id,northstar.id);
  await confirmScenarioEvent(request,copy.id,northstar.id,'PK-001-U1');
  await open(page,copy.id);
  await page.getByRole('link',{name:/^Cases/}).click();await page.getByRole('button',{name:/PK-001.*Northstar Analytics/}).click();
  await shot(page,'p3-stale');
  await page.getByRole('link',{name:/^Dashboard/}).click();await page.getByRole('button',{name:'Start morning review'}).click();
  await expect(page.getByText('Review complete. Choose a case to see its recommendation.')).toBeVisible({timeout:30_000});
  await expect(page.getByRole('button',{name:/Northstar Analytics.*investigated now/})).toBeVisible();
  await page.getByRole('button',{name:/Northstar Analytics.*investigated now/}).click();await page.getByRole('button',{name:'History',exact:true}).click();
  await shot(page,'p3-history');
});

test('P4 bookkeeper: settlement evidence leads to a supported closure only after confirmation',async({page,request})=>{
  const copy=await createCopy(request);const cedar=copy.cases[2];
  await investigate(request,copy.id,cedar.id);
  await confirmScenarioEvent(request,copy.id,cedar.id,'PK-003-U1');
  await investigate(request,copy.id,cedar.id);
  await open(page,copy.id);
  await page.getByRole('link',{name:/^Cases/}).click();await showAllCases(page);
  await page.getByRole('button',{name:/PK-003.*Cedar Retail Labs/}).click();
  await page.getByRole('button',{name:'Overview',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Review case closure'})).toBeVisible();
  await expect(page.getByRole('button',{name:'Confirm case closure'})).toHaveCount(0);
  await page.getByRole('link',{name:/^Cases/}).click();await showAllCases(page);
  await expect(page.getByRole('button',{name:/PK-003.*Cedar Retail Labs/})).toContainText('open');
  await page.getByRole('button',{name:/PK-003.*Cedar Retail Labs/}).click();
  await page.getByRole('button',{name:/^Evidence \(\d+\)$/}).click();
  await page.getByRole('button',{name:'Inspect exact source version'}).first().click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await shot(page,'p4-source');
});

test('P5 sceptical owner: unsafe edits are blocked, feedback is saved and the trace shows hand-offs',async({page,request})=>{
  const copy=await createCopy(request);const northstar=copy.cases[0];
  await investigate(request,copy.id,northstar.id);await open(page,copy.id);
  await page.getByRole('link',{name:/^Cases/}).click();await page.getByRole('button',{name:/PK-001.*Northstar Analytics/}).click();
  await page.getByRole('button',{name:'Overview',exact:true}).click();
  await page.getByText('Processing details',{exact:true}).click();
  await expect(page.getByText('→ Safety check: personal note')).toBeVisible();
  await page.getByRole('region',{name:'Was this recommendation useful?'}).getByRole('button',{name:'Needs work'}).click();
  await page.getByLabel('What should be better? (optional)').fill('Please mention the earlier promise date.');
  await page.getByRole('button',{name:'Send feedback'}).click();
  await expect(page.getByText(/Feedback saved/)).toBeVisible();
  await page.getByRole('button',{name:'Overview',exact:true}).click();
  const text=await page.getByLabel('Draft text').inputValue();
  await page.getByLabel('Draft text').fill(text.replace('We truly value working with your team.','A late fee of INR 500 applies.'));
  await page.getByRole('button',{name:'Save unapproved version'}).click();
  await expect(page.getByRole('button',{name:'Approve exact saved version'})).toBeDisabled();
  await shot(page,'p5-blocked');
});

test('P6 small laptop, keyboard and large text: the morning review is reachable and nothing scrolls sideways',async({page,request})=>{
  await page.setViewportSize({width:390,height:844});
  const copy=await createCopy(request,'FV-12');await open(page,copy.id);
  await page.evaluate(()=>{document.documentElement.style.fontSize='200%';});
  await noSideways(page);
  const skip=await page.locator('.skip-link').boundingBox();
  expect(skip===null||skip.y+skip.height<=0).toBe(true);
  expect(await page.locator('.wordmark').evaluate(el=>{const box=el.getBoundingClientRect();return el.scrollWidth<=el.clientWidth+1&&box.right<=window.innerWidth+1;})).toBe(true);
  await page.screenshot({path:`${shots}p6-viewport-top.png`});
  const start=page.getByRole('button',{name:'Start morning review'});
  for(let i=0;i<40&&!(await start.evaluate(el=>el===document.activeElement));i++)await page.keyboard.press('Tab');
  await expect(start).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page.getByText('Review complete. Choose a case to see its recommendation.')).toBeVisible({timeout:30_000});
  await noSideways(page);
  await shot(page,'p6-mobile-zoom');
  await page.getByRole('button',{name:/Northstar Analytics.*investigated now/}).click();
  await expect(page.getByRole('heading',{name:'Northstar Analytics',exact:true})).toBeFocused();
  await noSideways(page);
  await page.locator('.findings .financial-summary').scrollIntoViewIfNeeded();
  await page.screenshot({path:`${shots}owner-phase1-mobile-zoom.png`});
});
