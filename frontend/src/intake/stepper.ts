import type {CaseSummary} from '../api/types';
import {money} from '../components/format';
import type {IntakeKind,IntakeOverview} from './types';

export type UploadStep=1|2|3|4|5|6;
export type StepState='done'|'current'|'todo'|'attention';
export interface StepStatus {step:UploadStep;label:string;state:StepState;summary:string}

export const UPLOAD_STEPS:readonly UploadStep[]=[1,2,3,4,5,6];
export const STEP_LABEL:Record<UploadStep,string>={1:'Customers',2:'Invoices',3:'Bank receipts',4:'Customer messages',5:'Match payments',6:'Confirm & check'};
/** The file kind each upload step starts with; the File type select stays available for any other kind. */
export const STEP_KIND:Partial<Record<UploadStep,IntakeKind>>={1:'customers',2:'invoices',3:'payments',4:'customer_email',5:'allocations'};
/** What each step asks for before anything has been added. */
const HINT:Record<UploadStep,string>={1:'Who you sell to',2:'Bills waiting to be paid',3:'Payments you received',4:'Emails & WhatsApp',5:'Which receipt pays which invoice',6:'Start the morning check'};

const plural=(count:number,one:string,many=`${one}s`)=>`${count} ${count===1?one:many}`;
const total=(minors:string[])=>money({currency:'INR',minor_units:minors.reduce((sum,minor)=>sum+BigInt(minor),0n).toString()});
const held=(status:string)=>['PENDING','REVERSED'].includes(status);
/** Receipts that can still be matched to an invoice (pending and reversed receipts cannot be allocated). */
export function openReceiptCount(overview:IntakeOverview|null):number {
  return overview?overview.payments.filter(payment=>payment.remaining_minor!=='0'&&!held(payment.status)).length:0;
}

export function isUploadStep(value:unknown):value is UploadStep {return typeof value==='number'&&UPLOAD_STEPS.includes(value as UploadStep);}

/**
 * Stepper state from saved workspace data only (never from clicks), except that Match payments also
 * counts as done once the owner has moved past it with Continue, because a receipt may be left
 * unallocated on purpose. `passedWithOpen` is the number of open receipts when the owner continued;
 * more open receipts than that (a later statement) reopen the step. The first step to do is current.
 */
export function stepStates(overview:IntakeOverview|null,cases:CaseSummary[],latestReviewDone:boolean,passedWithOpen:number|null=null):StepStatus[] {
  const rows:{state:Exclude<StepState,'current'>;summary:string}[]=UPLOAD_STEPS.map(step=>({state:'todo',summary:HINT[step]}));
  if(!overview)rows[0].summary='Creates a new upload workspace';
  else {
    const {customers,cases:invoices,payments,documents}=overview;
    if(customers.length)rows[0]={state:'done',summary:`${plural(customers.length,'customer')} added`};
    if(invoices.length)rows[1]={state:'done',summary:`${plural(invoices.length,'invoice')} · ${total(invoices.map(row=>row.invoice_minor))}`};
    if(payments.length)rows[2]={state:'done',summary:`${plural(payments.length,'receipt')} · ${total(payments.map(row=>row.amount_minor))}`};
    if(overview.needs_sender_review)rows[3]={state:'attention',summary:'Needs your review'};
    else if(documents.length)rows[3]={state:'done',summary:`${plural(documents.length,'message')} attached`};
    if(payments.length) {
      const left=openReceiptCount(overview);
      const blocked=payments.filter(payment=>payment.remaining_minor!=='0'&&held(payment.status)).length;
      const matched=payments.length-left-blocked;
      const notAllocatable=blocked?` · ${blocked} not allocatable`:'';
      if(!left&&!blocked)rows[4]={state:'done',summary:`All ${plural(payments.length,'receipt')} matched`};
      else if(!left)rows[4]={state:'done',summary:`${matched} matched${notAllocatable}`};
      else if(passedWithOpen!==null&&left<=passedWithOpen)rows[4]={state:'done',summary:`${matched} matched · ${left} left unallocated${notAllocatable}`};
      else rows[4]={state:'todo',summary:`${left} of ${plural(payments.length,'receipt')} still to match`};
    }
    if(invoices.length) {
      const covered=invoices.filter(row=>row.ledger_complete).length;
      if(covered<invoices.length)rows[5]={state:'todo',summary:`${covered} of ${plural(invoices.length,'invoice')} confirmed`};
      else if(latestReviewDone) {
        const ready=cases.filter(row=>row.lifecycle==='OPEN'&&row.recommended_action).length;
        rows[5]={state:'done',summary:`Morning check complete${ready?` · ${plural(ready,'suggestion')} ready`:''}`};
      }
      else rows[5]={state:'todo',summary:'Coverage confirmed · start the morning check'};
    }
  }
  const next=rows.findIndex(row=>row.state==='todo');
  return rows.map((row,index)=>({step:UPLOAD_STEPS[index],label:STEP_LABEL[UPLOAD_STEPS[index]],state:index===next?'current':row.state,summary:row.summary}));
}
