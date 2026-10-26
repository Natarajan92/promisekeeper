import type {ReactNode} from 'react';
import type {CaseSummary} from '../api/types';
import {reviewDue} from '../cases/caseStatus';

export type ChipTone='red'|'amber'|'green'|'indigo';

/** Status pill: red = overdue or follow up, amber = check or verify, green = paid or close, indigo = wait or info. */
export function Chip({tone,children}:{tone:ChipTone;children:ReactNode}) {
  return <span className={`chip chip-${tone}`}>{children}</span>;
}

type ChipCase=Pick<CaseSummary,'lifecycle'|'recommended_action'|'review_required'|'review_at'>;
/** The business-language status of a case, from the same facts the case overview uses. */
export function caseChip(item:ChipCase,evaluationAt?:string):{tone:ChipTone;label:string} {
  if(item.lifecycle==='CLOSED')return {tone:'green',label:'Closed'};
  if(reviewDue(item as CaseSummary,evaluationAt).needsReview)return {tone:'amber',label:'Needs a fresh check'};
  switch(item.recommended_action) {
    case 'FOLLOW_UP':return {tone:'red',label:'Overdue · follow up'};
    case 'VERIFY_PAYMENT':return {tone:'amber',label:'Check payment'};
    case 'WAIT':return {tone:'indigo',label:'Wait for review date'};
    case 'CLOSE':return {tone:'green',label:'Paid · ready to close'};
    default:return {tone:'indigo',label:'Not checked yet'};
  }
}

export function CaseChip({item,evaluationAt}:{item:ChipCase;evaluationAt?:string}) {
  const {tone,label}=caseChip(item,evaluationAt);
  return <Chip tone={tone}>{label}</Chip>;
}
