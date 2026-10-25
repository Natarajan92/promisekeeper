import { test, expect, type APIRequestContext } from "./support/test";
import { createCopy, confirmScenarioEvent, investigate } from "./support/scenarioEvents";
import { isolatedServer } from "./support/server";
import { fileURLToPath } from "node:url";
import { createHash } from "node:crypto";

test("deterministic findings retain invoice issue source after an approved evidence update",async({page,request})=> {
  const copy=await createCopy(request,"FV-14-INVOICE");
  const cid=copy.cases.find(c=>c.catalogue_case_id==="PK-001")!.id;
  const saved=await investigate(request,copy.id,cid);
  const issue=saved.result.financial_facts.issues.find((item:any)=>item.code==="CONFLICTING_INVOICES");
  expect(issue.detail).toBe("Preserve and review both invoice authorities.");
  expect([...issue.sources].sort()).toEqual(["PK-001-FV-14-I1","PK-001-I1"]);
  const exact=issue.source_versions.find((ref:any)=>ref.source_id==="PK-001-FV-14-I1");
  expect(saved.result.timeline).toEqual(expect.arrayContaining([expect.objectContaining(exact)]));
  await confirmScenarioEvent(request,copy.id,cid,"PK-001-U1");
  const view=await (await request.get(`/api/v1/cases/${cid}?demonstration_id=${copy.id}`)).json();
  expect(view.freshness).toBe("EVIDENCE_CHANGED");
  expect(view.latest_completed_result).toEqual(saved.result);
  expect(view.evidence).toEqual(expect.arrayContaining([expect.objectContaining({stable_source_id:"PK-001-M2"})]));
  const retained=view.evidence.find((source:any)=>source.id===exact.evidence_version_id);
  expect(retained).toMatchObject({stable_source_id:"PK-001-FV-14-I1",version:1,
    original_content:"Fictional invoice NS-104; client Northstar Analytics; INR 125,000.00; due 10 October 2026."});
  await page.setViewportSize({width:400,height:900});
  await page.addInitScript(id=>localStorage.setItem("selected_demonstration_id",id),copy.id);
  await page.goto("/");
  await page.getByRole("button",{name:"Findings",exact:true}).click();
  await expect(page.getByText(/Historical result: evidence changed/i)).toBeVisible();
  await expect(page.getByRole("heading",{name:"Financial issues",exact:true})).toBeVisible();
  const row=page.locator(".findings li").filter({hasText:"Preserve and review both invoice authorities."});
  await expect(row).toHaveCount(1);
  const source=row.getByRole("button",{name:"PK-001-FV-14-I1 / v1",exact:true});
  await source.focus();
  await page.keyboard.press("Enter");
  const dialog=page.getByRole("dialog");
  await expect(dialog.getByRole("heading",{name:"PK-001-FV-14-I1 / version 1",exact:true})).toBeVisible();
  await expect(dialog.getByText(exact.evidence_version_id,{exact:true})).toBeVisible();
  await expect(dialog.locator("pre")).toHaveText(retained.original_content);
  await expect(dialog).not.toContainText("We explicitly replace our 20 October promise");
  await page.keyboard.press("Escape");
  await expect(dialog).not.toBeVisible();
  await expect(source).toBeFocused();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=document.documentElement.clientWidth+1)).toBe(true);
  expect(await source.evaluate(element=>element.getBoundingClientRect().right<=document.documentElement.clientWidth)).toBe(true);
  await page.screenshot({path:fileURLToPath(new URL("../../.runtime/gate-iii/deterministic-findings-narrow.png",import.meta.url)),fullPage:true});
  const reread=await (await request.get(`/api/v1/investigations/${saved.investigation_id}?demonstration_id=${copy.id}`)).json();
  expect(reread.result).toEqual(saved.result);
});

test("deterministic findings show unavailable ledger observations without invented source links",async({page,request})=> {
  const copy=await createCopy(request,"FV-05");
  const cid=copy.cases.find(c=>c.catalogue_case_id==="PK-003")!.id;
  const saved=await investigate(request,copy.id,cid);
  expect(saved.result.findings_version).toBe("deterministic-1");
  expect(saved.result.evidence_observations.filter((item:any)=>item.subject==="LEDGER")).toEqual([
    {subject:"LEDGER",field:"availability",value:"UNAVAILABLE",source:null,snapshot_id:saved.result.snapshot_id,snapshot_hash:saved.result.snapshot_hash},
    {subject:"LEDGER",field:"complete",value:true,source:null,snapshot_id:saved.result.snapshot_id,snapshot_hash:saved.result.snapshot_hash},
  ]);
  await page.addInitScript(id=>localStorage.setItem("selected_demonstration_id",id),copy.id);
  await page.goto("/");
  await page.getByRole("button",{name:/PK-003/}).first().click();
  await page.getByRole("button",{name:"Findings",exact:true}).click();
  await expect(page.getByRole("heading",{name:"Evidence observations",exact:true})).toBeVisible();
  for(const text of ["Saved ledger availability: unavailable.","Saved ledger is complete."]) {
    const observation=page.locator(".findings li").filter({has:page.getByText(text,{exact:true})});
    await expect(observation).toHaveCount(1);
    await expect(observation.getByRole("button")).toHaveCount(0);
    await expect(observation.locator("blockquote, q, pre")).toHaveCount(0);
  }
});

test("deterministic findings preserve literal legacy SQLite bytes through GET restart and reinvestigation",async({page,playwright})=> {
  test.setTimeout(60_000); // Three bounded backend startups plus stopped-fixture byte inspections, as in restart-recovery.
  const server=await isolatedServer();
  let requestContext: APIRequestContext | undefined;
  try {
    await server.start();
    const request=requestContext=await playwright.request.newContext({baseURL:server.url});
    const copy=await createCopy(request,"FV-07-PRECISION");
    const cid=copy.cases.find(c=>c.catalogue_case_id==="PK-003")!.id;
    const original=await investigate(request,copy.id,cid);
    expect(original.result.findings_version).toBe("deterministic-1");
    await server.stop();
    const seeded=await server.legacyFixture("seed",[original.investigation_id]);
    const literal=JSON.parse(seeded.legacy.result_json);
    expect(literal).not.toHaveProperty("findings_version");
    expect(literal).not.toHaveProperty("commitment_issues");
    expect(literal).not.toHaveProperty("evidence_observations");
    expect(literal.financial_facts.issues.length).toBeGreaterThan(0);
    for(const issue of literal.financial_facts.issues)expect(issue).not.toHaveProperty("source_versions");
    const {result_hash,...hashInput}=literal;
    const canonical=(value:any):string=>Array.isArray(value)?`[${value.map(canonical).join(",")}]`
      :value!==null&&typeof value==="object"?`{${Object.keys(value).sort().map(key=>`${JSON.stringify(key)}:${canonical(value[key])}`).join(",")}}`:JSON.stringify(value);
    expect(createHash("sha256").update(canonical(hashInput),"utf8").digest("hex")).toBe(result_hash);
    expect(Buffer.from(seeded.legacy.utf8_hex,"hex").toString("utf8")).toBe(seeded.legacy.result_json);
    const query=`demonstration_id=${copy.id}`;
    const assertLegacy=async()=> {
      const response=await request.get(`/api/v1/investigations/${seeded.investigation_id}?${query}`);
      expect(response.status()).toBe(200);
      expect((await response.json()).result).toEqual(literal);
    };
    const assertStored=async()=>expect(await server.legacyFixture("inspect",[original.investigation_id,seeded.investigation_id])).toEqual({
      [original.investigation_id]:seeded.original,[seeded.investigation_id]:seeded.legacy,
    });
    await server.start();
    await assertLegacy();
    expect((await (await request.get(`/api/v1/cases/${cid}?${query}`)).json()).latest_completed_result).toEqual(literal);
    await page.addInitScript(id=>localStorage.setItem("selected_demonstration_id",id),copy.id);
    await page.goto(server.url);
    await page.getByRole("button",{name:/PK-003/}).first().click();
    await page.getByRole("button",{name:"Findings",exact:true}).click();
    await expect(page.getByText(/Legacy findings: saved before the current findings profile\. Reinvestigate/)).toBeVisible();
    await server.stop();
    await assertStored();
    await server.start();
    await assertLegacy();
    await page.reload();
    await page.getByRole("button",{name:/PK-003/}).first().click();
    await page.getByRole("button",{name:"Findings",exact:true}).click();
    await expect(page.getByText(/Legacy findings: saved before/)).toBeVisible();
    const renewed=await investigate(request,copy.id,cid);
    expect(renewed.result.findings_version).toBe("deterministic-1");
    expect(renewed.investigation_id).not.toBe(seeded.investigation_id);
    expect(renewed.result).toHaveProperty("commitment_issues");
    expect(renewed.result.evidence_observations.length).toBeGreaterThanOrEqual(2);
    for(const issue of renewed.result.financial_facts.issues)expect(issue.source_versions.length).toBeGreaterThan(0);
    await assertLegacy();
    await server.stop();
    await assertStored();
  } finally {
    try { await requestContext?.dispose(); }
    finally { await server.stop(); }
  }
});

const financialVariants: [string,string,string|null][] = [
  ["FV-01","VERIFY_PAYMENT",null], ["FV-02-PROMISE","FOLLOW_UP","8000000"],
  ["FV-02-INVOICE","VERIFY_PAYMENT",null], ["FV-03","VERIFY_PAYMENT","6000000"],
  ["FV-04","VERIFY_PAYMENT","5000000"], ["FV-05","VERIFY_PAYMENT",null],
  ["FV-06-DUPLICATE","CLOSE","0"], ["FV-06-REVERSAL","VERIFY_PAYMENT","6000000"],
  ["FV-07-OVERPAYMENT","VERIFY_PAYMENT","-1000000"], ["FV-07-CURRENCY","VERIFY_PAYMENT",null],
  ["FV-07-MISSING","VERIFY_PAYMENT",null], ["FV-07-NEGATIVE","VERIFY_PAYMENT",null],
  ["FV-07-PRECISION","VERIFY_PAYMENT",null], ["FV-08-SOON","VERIFY_PAYMENT","5000000"],
  ["FV-08-TOMORROW","VERIFY_PAYMENT","5000000"], ["FV-14-INVOICE","VERIFY_PAYMENT",null],
  ["FV-14-PAYMENT","VERIFY_PAYMENT",null], ["FV-15-UNDATED","FOLLOW_UP","8000000"],
  ["FV-15-TIE","FOLLOW_UP","8000000"],
];

for (const [variant,action,balance] of financialVariants) {
  test(`${variant} retains exact financial truth through the real investigation API`,async({request})=> {
    const copy=await createCopy(request,variant);
    const catalogueCase=variant.startsWith("FV-01")||variant.startsWith("FV-02")||variant.startsWith("FV-14")||variant.startsWith("FV-15")
      ?"PK-001":variant.startsWith("FV-04")||variant.startsWith("FV-08")?"PK-002":"PK-003";
    const cid=copy.cases.find(c=>c.catalogue_case_id===catalogueCase)!.id;
    const attempt=await investigate(request,copy.id,cid);
    expect(["COMPLETE","LIMITED"]).toContain(attempt.status);
    expect(attempt.result.action).toBe(action);
    expect(attempt.result.financial_facts.balance?.minor_units??null).toBe(balance);
  });
}

test("owner starts an investigation and opens exact source versions from its findings",async({page,request})=> {
  const copy=await createCopy(request);
  await page.addInitScript(id=>localStorage.setItem("selected_demonstration_id",id),copy.id);
  await page.goto("/");
  await page.getByRole("button",{name:/PK-001|Northstar Analytics/i}).first().click();
  await page.getByRole("button",{name:"Findings",exact:true}).click();
  await page.getByRole("button",{name:"Investigate case",exact:true}).click();
  await expect(page.getByRole("heading",{name:"Follow up on the overdue balance",exact:true})).toBeVisible();
  await expect(page.getByText(/80,000/).first()).toBeVisible();
  const source=page.getByRole("button",{name:"PK-001-I1 / v1",exact:true}).first();
  await source.click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByRole("dialog").getByText(/Fictional invoice NS-104/)).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await expect(source).toBeFocused();
});

test("lost start response reconciles the original operation after reload without another start",async({page,request})=> {
  const copy=await createCopy(request);
  const cid=copy.cases[0].id;
  await page.addInitScript(id=>localStorage.setItem("selected_demonstration_id",id),copy.id);
  let operationId:string|undefined;
  await page.route(`**/api/v1/cases/${cid}/investigations?*`,async route=> {
    operationId=route.request().postDataJSON().operation_id;
    const accepted=await route.fetch();
    expect(accepted.status()).toBe(202);
    await route.abort("connectionreset");
  });
  await page.goto("/");
  await page.getByRole("button",{name:"Investigate case",exact:true}).click();
  await expect(page.getByText(/outcome is unknown|Connection unavailable/i).first()).toBeVisible();
  expect(operationId).toBeTruthy();
  await page.unroute(`**/api/v1/cases/${cid}/investigations?*`);
  await page.reload();
  await page.getByRole("button",{name:"Findings",exact:true}).click();
  await expect(page.getByRole("heading",{name:"Follow up on the overdue balance",exact:true})).toBeVisible();
  const history=await (await request.get(`/api/v1/cases/${cid}/history?demonstration_id=${copy.id}`)).json();
  expect(history.events.filter((e:any)=>e.event_type==="INVESTIGATION_STARTED")).toHaveLength(1);
  expect((await request.get(`/api/v1/operations/${operationId}?demonstration_id=${copy.id}`)).status()).toBe(200);
});

test("baseline actions and staged settlement preserve the earlier result and source history", async ({ request }) => {
  const copy = await createCopy(request);
  const expected = ["FOLLOW_UP","WAIT","VERIFY_PAYMENT","FOLLOW_UP","VERIFY_PAYMENT","CLOSE"];
  for (const [i, item] of copy.cases.entries()) {
    const attempt = await investigate(request,copy.id,item.id);
    expect(attempt.status).toBe("COMPLETE");
    expect(attempt.result.action).toBe(expected[i]);
    expect(attempt.result.financial_facts.balance.minor_units).toBe(["8000000","5000000","6000000","6000000","4500000","0"][i]);
  }
  const cedar = copy.cases[2].id;
  await confirmScenarioEvent(request,copy.id,cedar,"PK-003-U1");
  const current = await investigate(request,copy.id,cedar);
  expect(current.result.action).toBe("CLOSE");
  expect(current.result.financial_facts.balance.minor_units).toBe("0");
  const view = await (await request.get(`/api/v1/cases/${cedar}?demonstration_id=${copy.id}`)).json();
  expect(view.lifecycle).toBe("OPEN");
  expect(view.evidence.some((e:any) => e.stable_source_id==="PK-003-M1")).toBe(true);
  expect(view.evidence.some((e:any) => e.stable_source_id==="PK-003-L2")).toBe(true);
});

for (const variant of ["FV-16-LINKED","FV-16-UNLINKED"]) {
  test(`${variant} keeps invoice allocation separate from commitment credit`, async ({ request }) => {
    const copy = await createCopy(request,variant);
    const attempt = await investigate(request,copy.id,copy.cases[1].id);
    expect(attempt.result.financial_facts.balance.minor_units).toBe("3000000");
    expect(attempt.result.action).toBe(variant.endsWith("UNLINKED")?"VERIFY_PAYMENT":"FOLLOW_UP");
  });
}

for (const variant of ["FV-18-A","FV-18-B"]) {
  test(`${variant} WAITs again at the first boundary and follows up only at the last boundary`, async ({ request }) => {
    const copy=await createCopy(request,variant);
    const catalogue=await (await request.get("/api/v1/catalogue")).json();
    const clocks=catalogue.events.filter((e:any)=>e.id.startsWith(variant)).sort((a:any,b:any)=>a.evaluation_at.localeCompare(b.evaluation_at));
    const cid=copy.cases.find(c=>c.catalogue_case_id===clocks[0].case_id)!.id;
    const first=await investigate(request,copy.id,cid);
    expect(first.result.action).toBe("WAIT");
    expect(first.result.review_at).toBe("2026-10-24T18:30:00+00:00");
    await confirmScenarioEvent(request,copy.id,cid,clocks[0].id);
    const second=await investigate(request,copy.id,cid);
    expect(second.result.action).toBe("WAIT");
    expect(second.result.review_at).toBe("2026-10-26T18:30:00+00:00");
    await confirmScenarioEvent(request,copy.id,cid,clocks[1].id);
    expect((await investigate(request,copy.id,cid)).result.action).toBe("FOLLOW_UP");
  });
}
