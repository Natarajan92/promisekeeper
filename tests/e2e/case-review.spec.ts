import { test, expect, type Page } from "./support/test";
import { createCopy, mutationHeaders } from "./support/scenarioEvents";
import { isolatedServer } from "./support/server";
import { fileURLToPath } from "node:url";
import { randomUUID } from "node:crypto";

// Navigation only: the workspace chooser never opens by itself, so open it from the top bar.
async function openWorkspace(page: Page) {
  await page.getByRole("button", {name:/^Workspace/}).click();
}
async function select(page: Page, id: string) {
  await page.addInitScript(copy => localStorage.setItem("selected_demonstration_id", copy), id);
  await page.goto("/");
}

test("empty discovery guides uploads without writes, then preserves an explicitly seeded workspace on reload", async ({ page, playwright }) => {
  const server=await isolatedServer();
  await server.start();
  const request=await playwright.request.newContext({baseURL:server.url});
  try {
  expect((await (await request.get("/api/v1/demonstrations")).json()).demonstrations).toEqual([]);
  await page.goto(server.url);
  await openWorkspace(page);
  await expect(page.getByRole("link", {name:"New workspace"})).toBeVisible();
  await expect(page.getByRole("button",{name:/create.*demonstration/i})).toHaveCount(0);
  expect((await (await request.get("/api/v1/demonstrations")).json()).demonstrations).toEqual([]);
  await createCopy(request);
  await page.reload();
  await expect(page.getByText("Northstar Analytics", {exact:true}).first()).toBeVisible();
  const copies = (await (await request.get("/api/v1/demonstrations")).json()).demonstrations;
  expect(copies).toHaveLength(1);
  await page.reload();
  await expect(page.getByText("Northstar Analytics", {exact:true}).first()).toBeVisible();
  expect((await (await request.get("/api/v1/demonstrations")).json()).demonstrations).toEqual(copies);
  } finally {await request.dispose();await server.stop();}
});

test("multiple copies need selection and valid saved selection opens exact raw evidence", async ({ page, request }) => {
  await createCopy(request);
  const copy = await createCopy(request);
  await page.goto("/");
  await openWorkspace(page);
  await expect(page.getByRole("combobox",{name:"Workspace",exact:true})).toBeVisible();
  await select(page, copy.id);
  await page.getByRole('link',{name:/^Cases/}).click();await page.getByRole("button", {name:/PK-001|Northstar Analytics/i}).first().click();await page.getByRole('button',{name:/^Evidence \(\d+\)$/}).click();
  await expect(page.getByText(/Fictional invoice NS-104; client Northstar Analytics/)).toBeVisible();
  await expect(page.getByText(/VERIFIED|Verified/).first()).toBeVisible();
  await expect(page.getByText(/We will pay INR 80,000 by 20 October 2026/)).toBeVisible();
  expect(await page.evaluate(() => localStorage.getItem("selected_demonstration_id"))).toBe(copy.id);
  await page.screenshot({path:fileURLToPath(new URL("../../.runtime/gate-iii/case-workspace.png",import.meta.url)),fullPage:true});
});

test("the three release cases expose their originals and verification labels without investigation",async({page,request})=> {
  const copy=await createCopy(request);
  await select(page,copy.id);
  const messages=["We will pay INR 80,000 by 20 October 2026.","We will pay INR 50,000 by 25 October 2026.","We paid the remaining INR 60,000 today; reference CR-T2."];
  for(const [index,item] of copy.cases.slice(0,3).entries()) {
    await page.getByRole("link",{name:/^Cases/}).click();
    await page.getByRole("button",{name:new RegExp(item.catalogue_case_id)}).first().click();await page.getByRole('button',{name:/^Evidence \(\d+\)$/}).click();
    await expect(page.getByText(messages[index],{exact:true})).toBeVisible();
    await expect(page.getByText(/Customer wording is a claim until supported/)).toBeVisible();
    await expect(page.getByText("AVAILABLE · VERIFIED",{exact:true})).toBeVisible();
    await expect(page.getByText("Non-authoritative source",{exact:true})).toBeVisible();
    const detail=await (await request.get(`/api/v1/cases/${item.id}?demonstration_id=${copy.id}`)).json();
    expect(detail.latest_completed_result).toBeNull();
    expect(detail.case_revision).toBe(0);
  }
});

test("Hinglish cases show the original customer wording exactly and stay uninvestigated",async({page,request})=> {
  const copy=await createCopy(request);
  expect(copy.cases.map((item:any)=>item.catalogue_case_id)).toEqual(["PK-001","PK-002","PK-003","PK-004","PK-005","PK-006"]);
  await select(page,copy.id);
  const hinglish:Record<string,string>={"PK-004":"Sir, INR 60,000 pakka 15 October 2026 tak transfer kar denge.","PK-005":"Sir, INR 45,000 ka payment today kar diya hai, reference LI-T9."};
  for(const [code,text] of Object.entries(hinglish)) {
    await page.getByRole("link",{name:/^Cases/}).click();
    await page.getByRole("button",{name:new RegExp(code)}).first().click();await page.getByRole('button',{name:/^Evidence \(\d+\)$/}).click();
    await expect(page.getByText(text,{exact:true})).toBeVisible();
    await expect(page.getByText("Non-authoritative source",{exact:true})).toBeVisible();
  }
});

test("case dates and status remain visible at narrow width and 200 percent text",async({page,request})=> {
  const copy=await createCopy(request);
  await page.setViewportSize({width:400,height:900});
  await select(page,copy.id);
  await page.evaluate(()=>document.documentElement.style.fontSize="200%");
  await page.getByRole('link',{name:/^Cases/}).click();const first=page.getByRole("button",{name:/PK-001.*Northstar Analytics/}).first();
  await expect(first.getByText(/10 October 2026/)).toBeVisible();
  await expect(first.getByText("Not investigated")).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=document.documentElement.clientWidth+1)).toBe(true);
  await first.click();await page.getByRole('button',{name:/^Evidence \(\d+\)$/}).click();
  await expect(page.getByRole("heading",{name:"Saved evidence",exact:true})).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=document.documentElement.clientWidth+1)).toBe(true);
  expect(await page.locator(".financial-summary dd").first().evaluate(element=>
    element.getBoundingClientRect().right<=element.closest(".case-workspace")!.getBoundingClientRect().right)).toBe(true);
  await page.locator(".financial-summary").screenshot({path:fileURLToPath(new URL("../../.runtime/gate-iii/zoom-financial-summary.png",import.meta.url))});
  await page.screenshot({path:fileURLToPath(new URL("../../.runtime/gate-iii/narrow-200-percent.png",import.meta.url)),fullPage:true});
});

test("listing failure preserves saved selection and never creates or resets", async ({ page, request }) => {
  const copy = await createCopy(request);
  const before = (await (await request.get("/api/v1/demonstrations")).json()).demonstrations;
  await page.addInitScript(id => localStorage.setItem("selected_demonstration_id", id), copy.id);
  await page.route("**/api/v1/demonstrations", route => route.fulfill({status:503,contentType:"application/json",
    body:JSON.stringify({schema_version:"1",error:{code:"STORAGE_UNAVAILABLE",message:"Storage unavailable",operation_id:null,retryable:true,blocking_reasons:[]}})}));
  await page.goto("/");
  await expect(page.getByRole("alert").first()).toBeVisible();
  expect(await page.evaluate(() => localStorage.getItem("selected_demonstration_id"))).toBe(copy.id);
  expect((await (await request.get("/api/v1/demonstrations")).json()).demonstrations).toEqual(before);
});

test("missing saved selection clears it and offers a chooser for retained copies", async ({ page }) => {
  await select(page, "00000000-0000-0000-0000-000000000000");
  await openWorkspace(page);
  await expect(page.getByRole("combobox",{name:"Workspace",exact:true})).toBeVisible();
  expect(await page.evaluate(() => localStorage.getItem("selected_demonstration_id"))).not.toBe("00000000-0000-0000-0000-000000000000");
});

test("confirmed deletion clears the removed browser selection without creating a replacement",async({page,request})=> {
  const copy=await createCopy(request);
  await select(page,copy.id);
  await expect(page.getByText("Northstar Analytics",{exact:true}).first()).toBeVisible();
  const removed=await request.post(`/api/v1/demonstrations/${copy.id}/deletion`,{headers:mutationHeaders,data:{
    schema_version:"1",operation_id:randomUUID(),confirmed_demonstration_id:copy.id,confirm:true,
  }});
  expect(removed.status()).toBe(200);
  const retained=(await (await request.get("/api/v1/demonstrations")).json()).demonstrations;
  await page.reload();
  await openWorkspace(page);
  await expect(page.getByRole("combobox",{name:"Workspace",exact:true})).toBeVisible();
  expect(await page.evaluate(()=>localStorage.getItem("selected_demonstration_id"))).not.toBe(copy.id);
  expect((await (await request.get("/api/v1/demonstrations")).json()).demonstrations).toEqual(retained);
});

test("saved browser selection and invoice evidence survive a real backend restart", async ({ page, playwright }) => {
  const server=await isolatedServer();
  await server.start();
  const request=await playwright.request.newContext({baseURL:server.url});
  try {
    const copy=await createCopy(request);
    await page.goto(server.url);
    await expect(page.getByText("Northstar Analytics",{exact:true}).first()).toBeVisible();
    await page.getByRole('link',{name:/^Cases/}).click();await page.getByRole("button",{name:/PK-001|Northstar Analytics/i}).first().click();await page.getByRole('button',{name:/^Evidence \(\d+\)$/}).click();
    await expect(page.getByText(/Fictional invoice NS-104; client Northstar Analytics/)).toBeVisible();
    expect(await page.evaluate(()=>localStorage.getItem("selected_demonstration_id"))).toBe(copy.id);
    await server.stop();
    await server.start();
    await page.reload();
    await expect(page.getByText("Northstar Analytics",{exact:true}).first()).toBeVisible();
    expect(await page.evaluate(()=>localStorage.getItem("selected_demonstration_id"))).toBe(copy.id);
    expect((await (await request.get("/api/v1/demonstrations")).json()).demonstrations).toHaveLength(1);
  } finally {
    await request.dispose();
    await server.stop();
  }
});
