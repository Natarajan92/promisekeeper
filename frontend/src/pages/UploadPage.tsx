import {useEffect,useState} from 'react';
import {MorningReview} from '../agents/MorningReview';
import type {MorningReviewView} from '../api/types';
import {IntakePanel} from '../intake/IntakePanel';
import {Stepper} from '../intake/UploadStepper';
import {isUploadStep,openReceiptCount,STEP_LABEL,stepStates,type UploadStep} from '../intake/stepper';
import type {IntakeOverview} from '../intake/types';
import {routeLink} from '../routing';
import type {PageProps} from '../store/useWorkspace';
import '../intake/upload.css';

const GUIDE:Record<UploadStep,string>={
  1:'Upload your customer list, a CSV export from your accounting tool. You see a preview first; nothing is saved until you confirm.',
  2:'Upload the invoices you are waiting to be paid for. Each invoice becomes a case that PromiseKeeper keeps track of.',
  3:'Upload your bank statement or receipts export. We only read it. Nothing is matched to an invoice until you say so in step 5.',
  4:'Add customer emails or WhatsApp chats, one file at a time. Choose the invoice each message is about and confirm who sent it. Promises are only taken from customer messages.',
  5:'Tell PromiseKeeper which receipt pays which invoice. Suggestions are hints from names only; you confirm every match. You may leave a receipt unallocated.',
  6:'Confirm that you checked the payment records for each invoice, then start the morning check to get a suggested next step for every case.',
};

// How many receipts were still open when the owner moved past Match payments with Continue.
const passedKey=(did:string)=>`promisekeeper.upload.match-passed.${did}`;
function readPassed(did:string|null):number|null {
  if(!did)return null;
  try {const saved=JSON.parse(sessionStorage.getItem(passedKey(did))??'null');return Number.isInteger(saved)&&saved>=0?saved:null;}
  catch {return null;}
}
function writePassed(did:string,open:number|null) {
  try {if(open===null)sessionStorage.removeItem(passedKey(did));else sessionStorage.setItem(passedKey(did),JSON.stringify(open));}
  catch {/* storage is only a convenience */}
}

export function UploadPage({ws,route,navigate}:PageProps) {
  // Uploads only modify imported workspaces; other saved workspaces remain read-only to intake.
  const did=ws.imported?ws.selected:null;
  const [overview,setOverview]=useState<{did:string;data:IntakeOverview}|null>(null);
  const [review,setReview]=useState<{did:string;view:MorningReviewView|null}|null>(null);
  const [passed,setPassed]=useState<{did:string|null;open:number|null}>(()=>({did,open:readPassed(did)}));
  const [autoStep,setAutoStep]=useState<UploadStep|null>(null);
  useEffect(()=>{
    if(!did)return;
    let cancelled=false;
    void ws.api.intakeOverview(did).then(data=>{if(!cancelled)setOverview({did,data});}).catch(()=>undefined);
    void ws.api.latestMorningReview(did).then(latest=>{if(!cancelled)setReview({did,view:latest.morning_review});}).catch(()=>undefined);
    return ()=>{cancelled=true;};
  },[ws.api,did,ws.refreshTick]);
  const data=did&&overview?.did===did?overview.data:null;
  const passedOpen=passed.did===did?passed.open:readPassed(did);
  const openReceipts=openReceiptCount(data);
  // More open receipts than when the owner moved on (a later statement) means Match payments needs a fresh look.
  useEffect(()=>{if(did&&data&&passedOpen!==null&&openReceipts>passedOpen){setPassed({did,open:null});writePassed(did,null);}},[did,data,passedOpen,openReceipts]);
  // Confirm & check is done only after a completed morning review left every open case with a current result.
  const latest=review?.did===did?review.view:null;
  const openCases=ws.cases.filter(entry=>entry.summary.lifecycle==='OPEN');
  const latestReviewDone=!!data&&latest?.status==='COMPLETE'&&Date.parse(latest.started_at)>=Date.parse(data.as_of)
    &&openCases.length>0&&openCases.every(entry=>entry.view?.freshness==='CURRENT');
  const steps=stepStates(data,ws.list?.cases??[],latestReviewDone,passedOpen);
  const resolved=!ws.discovering&&(!did||!!data);
  // Opening Upload without a step shows the next step once, from the saved state; it never jumps afterwards.
  useEffect(()=>{
    if(autoStep||route.page!=='upload'||route.step!==undefined||!resolved)return;
    setAutoStep((steps.find(item=>item.state==='current')??steps.find(item=>item.state==='attention')??steps[5]).step);
  },[autoStep,route,resolved,steps]);
  const requested=route.page==='upload'&&isUploadStep(route.step)?route.step:null;
  const active:UploadStep|null=requested??autoStep;
  function go(step:UploadStep){navigate({page:'upload',step});}
  function next(step:UploadStep) {
    if(step===5&&did&&data){setPassed({did,open:openReceipts});writePassed(did,openReceipts);}
    go((step+1) as UploadStep);
  }
  const allCovered=!!data&&data.cases.length>0&&data.cases.every(row=>row.ledger_complete);
  return <div className="upload-page">
    <div className="upload-head">
      <div><h1>Bring in your records</h1><p>Use the CSV exports from your accounting tool and bank, plus any customer messages. Go step by step; nothing is saved until you confirm.</p></div>
    </div>
    {!active?<p role="status">Loading your upload progress…</p>:<div className="upload-layout">
      <aside className="upload-steps-card"><Stepper steps={steps} active={active} navigate={navigate}/></aside>
      <section className="upload-step-card" aria-labelledby="upload-step-heading">
        <header className="upload-step-head">
          <h2 id="upload-step-heading">Step {active} · {STEP_LABEL[active]}</h2>
          <p>{GUIDE[active]}</p>
          {ws.selected&&!ws.imported&&active<=2&&<p className="upload-kind-note">Uploading here creates a new workspace. Use the Workspace menu to return to your saved records.</p>}
          {active===6&&allCovered&&<p className="upload-ready">Every invoice is confirmed. <button className="text-button" onClick={()=>document.getElementById('morning-heading')?.scrollIntoView?.({block:'start'})}>Jump to the morning check</button></p>}
        </header>
        {!did&&active>=3?<div className="upload-needs-workspace notice"><p>This step adds to an upload workspace, and none is selected yet. Start with step 1, Customers, to create one.</p><button onClick={()=>go(1)}>Go to step 1, Customers</button></div>:
          <IntakePanel key={`intake:${ws.selected??'new'}`} step={active} api={ws.api} did={did} reloadKey={ws.refreshTick} onCreated={id=>{ws.select(id);void ws.discover(id);}} onChanged={ws.refresh} onOpenCase={id=>navigate({page:'case',caseId:id})}/>}
        {active===6&&did&&<div className="upload-morning">
          {data&&!allCovered&&<p className="upload-kind-note">Confirm coverage for every invoice above first, so each case can use a verified balance.</p>}
          <MorningReview key={`morning:${did}`} api={ws.api} did={did} cases={ws.list?.cases} evaluationAt={ws.evaluationAt} onPlan={ws.setPlan} onOpenCase={id=>navigate({page:'case',caseId:id,section:'overview'})} onDone={ws.refresh}/>
        </div>}
        <div className="upload-nav">
          {active>1&&<button onClick={()=>go((active-1) as UploadStep)}><span aria-hidden="true">← </span>Back to {STEP_LABEL[(active-1) as UploadStep]}</button>}
          {active<6?<button className="primary" onClick={()=>next(active)}>Continue to {STEP_LABEL[(active+1) as UploadStep]}<span aria-hidden="true"> →</span></button>:
            <a className={`upload-dashboard-link${latestReviewDone?'':' secondary'}`} {...routeLink({page:'dashboard'},navigate)}>Go to Dashboard</a>}
        </div>
      </section>
    </div>}
  </div>;
}
