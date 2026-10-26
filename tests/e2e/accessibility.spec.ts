import { test, expect, type Page } from './support/test';
import { createCopy, investigate } from './support/scenarioEvents';
import { fileURLToPath } from 'node:url';

// Reach every control by Tab; activation and editing use keyboard input only.
async function keyControl(page:Page, role:'button'|'checkbox'|'textbox'|'link', name:string|RegExp, key='Enter') {
  const target=page.getByRole(role,{name,exact:typeof name==='string'}).first();
  await expect(target).toBeEnabled();
  for(let i=0;i<180;i++) {
    if(await target.evaluate(element=>element===document.activeElement)) {
      expect(await target.evaluate(element=>{
        const style=getComputedStyle(element);return style.outlineStyle!=='none'&&parseFloat(style.outlineWidth)>0;
      })).toBe(true);
      if(key)await page.keyboard.press(key);return;
    }
    await page.keyboard.press('Tab');
  }
  throw new Error(`Control was not reachable by keyboard: ${name}`);
}
// Each case has its own page: open the copy directly on one case (the first by default).
async function open(page:Page,copy:{id:string;cases:{id:string;client:string}[]},index=0) {
  await page.addInitScript(id=>localStorage.setItem('selected_demonstration_id',id),copy.id);
  await page.goto(`/#/cases/${copy.cases[index].id}`);await expect(page.getByRole('heading',{name:copy.cases[index].client})).toBeVisible();
}

test('keyboard-only evidence, investigation, exact review, history and lifecycle controls',async({page,request})=>{
  test.setTimeout(120_000);
  const copy=await createCopy(request);await open(page,copy);
  await page.keyboard.press('Tab');await expect(page.getByRole('link',{name:'Skip to case workspace'})).toBeFocused();
  await page.keyboard.press('Enter');
  const sourceName=/^Inspect exact source version: PK-001-I1/;
  await keyControl(page,'button',/^Evidence \(\d+\)$/);
  await keyControl(page,'button',sourceName);await expect(page.getByRole('dialog')).toBeVisible();
  await page.keyboard.press('Escape');await expect(page.getByRole('dialog')).not.toBeVisible();
  await expect(page.getByRole('button',{name:sourceName}).first()).toBeFocused();
  await keyControl(page,'button','Investigate case');
  await expect(page.getByText(/COMPLETE result saved/).first()).toBeVisible();
  await keyControl(page,'button','Overview');await expect(page.getByRole('heading',{name:'Follow up on the overdue balance',exact:true})).toBeVisible();
  await keyControl(page,'button','Review suggested message');await expect(page.getByLabel('Draft text')).toBeVisible();
  const original=await page.getByLabel('Draft text').inputValue();
  await keyControl(page,'textbox','Draft text','');await page.keyboard.press('Control+A');
  await page.keyboard.insertText(original.replace('Hello ','Hi '));
  await keyControl(page,'button','Save unapproved version');
  await expect(page.locator('#case-draft').getByText('New unapproved version saved.')).toBeVisible();
  await keyControl(page,'button','Approve exact saved version');await expect(page.locator('#case-draft').getByText(/Approval recorded/)).toBeVisible();
  await keyControl(page,'button','Reject exact saved version');await expect(page.locator('#case-draft').getByText(/Rejection recorded/)).toBeVisible();
  await keyControl(page,'button','History');await keyControl(page,'button','Accept recommendation');
  await expect(page.getByText('Decision saved.').first()).toBeVisible();
  await keyControl(page,'link',/^Cases/);await keyControl(page,'button',/PK-003/);await keyControl(page,'button','Investigate case');
  await expect(page.getByText(/COMPLETE result saved/).first()).toBeVisible();
  await keyControl(page,'button','History');await keyControl(page,'button','Preview selected fictional update');
  await expect(page.getByRole('heading',{name:'Exact update preview'})).toBeVisible();
  await keyControl(page,'checkbox','I reviewed this exact fictional update','Space');
  await keyControl(page,'button','Confirm fictional update');await expect(page.getByText('Decision saved.').first()).toBeVisible();
  await keyControl(page,'button','Investigate case');await expect(page.getByText(/COMPLETE result saved/).first()).toBeVisible();
  await keyControl(page,'button','Overview');await keyControl(page,'button','Review case closure');await keyControl(page,'checkbox','Confirm closure of invoice CR-312','Space');
  await keyControl(page,'button','Confirm case closure');await expect(page.locator('.case-heading')).toContainText('CLOSED');
  await keyControl(page,'button','Review case reopening');await keyControl(page,'checkbox','Confirm reopening of invoice CR-312','Space');
  await keyControl(page,'button','Confirm case reopening');await expect(page.locator('.case-heading')).toContainText('OPEN');
});

test('all case sections remain readable at 200 percent text with textual status',async({page,request})=>{
  test.setTimeout(60_000);
  const copy=await createCopy(request);await investigate(request,copy.id,copy.cases[0].id);await open(page,copy);
  await page.setViewportSize({width:400,height:900});await page.addStyleTag({content:'html{font-size:200%}'});
  for(const [section,name] of [['overview','Overview'],['evidence',/^Evidence \(\d+\)$/],['history','History'],['compare','Compare']] as const) {
    await page.getByRole('button',{name,exact:typeof name==='string'}).click();
    await expect(page.locator('.view-content')).toBeVisible();
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
    await page.screenshot({path:fileURLToPath(new URL(`../../.runtime/accessibility-${section}.png`,import.meta.url)),fullPage:true});
  }
  await page.addStyleTag({content:'*{color:#000!important;background-color:#fff!important;border-color:#000!important}'});
  await page.getByRole('button',{name:'Overview',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Follow up on the overdue balance',exact:true})).toBeVisible();
  await expect(page.getByText(/Saved recommendation/).first()).toBeVisible();
  await expect(page.getByText(/Fictional demonstration/).first()).toBeVisible();
  await expect(page.getByText(/No customer messages are sent/).first()).toBeVisible();
});

test('uncertainty and limited outcomes remain explicit without color',async({page,request})=>{
  const copy=await createCopy(request,'FV-05');await investigate(request,copy.id,copy.cases[2].id);
  await open(page,copy,2);
  await page.getByRole('button',{name:'Overview',exact:true}).click();
  await page.addStyleTag({content:'*{color:#000!important;background-color:#fff!important}'});
  await expect(page.getByRole('heading',{name:'Verify the payment',exact:true})).toBeVisible();
  await expect(page.getByText(/Limited investigation/)).toBeVisible();
  await expect(page.getByText(/Unknown/).first()).toBeVisible();
  await page.getByRole('button',{name:'Overview',exact:true}).click();
  await expect(page.getByText(/No customer message is needed/i).first()).toBeVisible();
});
