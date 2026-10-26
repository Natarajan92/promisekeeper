import type {CaseView, Money} from '../api/types';
import {actionTitle, localDates} from '../components/format';
import type {CaseEntry} from '../store/useWorkspace';

export type ApprovalKind='REMINDER'|'CLOSURE'|'PAYMENT_CHECK'|'SUGGESTION';
export interface ApprovalItem {id:string; caseId:string; kind:ApprovalKind; title:string; client:string; amount:Money|null; reason:string}

export const KIND_ORDER:readonly ApprovalKind[]=['REMINDER','CLOSURE','PAYMENT_CHECK','SUGGESTION'];
export const KIND_CHIP:Record<ApprovalKind,string>={REMINDER:'Reminder',CLOSURE:'Closure',PAYMENT_CHECK:'Payment check',SUGGESTION:'Suggestion'};

const SEPARATOR='~';
/** Item ids name their case, so a decided item can still show its case after it leaves the queue. */
export const itemId=(caseId:string,kind:ApprovalKind)=>`${kind.toLowerCase()}${SEPARATOR}${caseId}`;
export function parseItemId(id:string):{caseId:string;kind:ApprovalKind}|null {
  const split=id.indexOf(SEPARATOR);
  if(split<0)return null;
  const kind=id.slice(0,split).toUpperCase() as ApprovalKind;
  const caseId=id.slice(split+1);
  return KIND_ORDER.includes(kind)&&caseId?{caseId,kind}:null;
}

/** An owner decision is waiting only on an open case with a current result and no running investigation. */
export function hasCurrentResult(view:CaseView) {
  return view.lifecycle==='OPEN'&&view.freshness==='CURRENT'&&!view.running_attempt&&!!view.current_result;
}

function kindsFor(view:CaseView):ApprovalKind[] {
  const result=view.current_result;
  if(!result||!hasCurrentResult(view))return [];
  const kinds:ApprovalKind[]=[];
  const draft=view.draft;
  if(draft&&draft.validation_status==='VALID'&&view.review_state!=='APPROVED'&&view.review_state!=='REJECTED')kinds.push('REMINDER');
  const decided=(view.owner_dispositions??[]).some(item=>item.investigation_id===result.investigation_id);
  // A closure stays until the case is closed: confirming closure is its own decision.
  if(result.action==='CLOSE'&&view.allowed_commands.close?.allowed)kinds.push('CLOSURE');
  // A payment check is the owner's accept/reject of the recommendation, so a recorded disposition settles it.
  if(result.action==='VERIFY_PAYMENT'&&!decided)kinds.push('PAYMENT_CHECK');
  // An undecided recommendation is folded into the item above when there is one.
  if(!kinds.length&&!decided)kinds.push('SUGGESTION');
  return kinds;
}

function titleFor(kind:ApprovalKind,view:CaseView) {
  switch(kind) {
    case 'REMINDER':return 'Reminder draft to review';
    case 'CLOSURE':return 'Closure ready for review';
    case 'PAYMENT_CHECK':return 'Payment to verify';
    case 'SUGGESTION':return `Recommendation: ${actionTitle(view.current_result!.action)}`;
  }
}

function reasonFor(kind:ApprovalKind,view:CaseView) {
  const step=localDates(view.current_result!.next_step);
  if(kind==='REMINDER'&&view.draft)return `Version ${view.draft.version} of the reminder is waiting for your decision. ${step}`;
  return step;
}

/** Every decision waiting for the owner, in case-list order (spec: "Approval queue membership"). */
export function buildQueue(cases:CaseEntry[]):ApprovalItem[] {
  return cases.flatMap(({view})=>{
    if(!view)return [];
    const amount=view.current_result?.financial_facts.balance??view.financial_facts.balance??null;
    return kindsFor(view).map(kind=>({id:itemId(view.id,kind),caseId:view.id,kind,title:titleFor(kind,view),client:view.client,amount,reason:reasonFor(kind,view)}));
  });
}
