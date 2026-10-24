import type { Action, Money } from '../api/types';
export function money(value:Money|null|undefined):string {
  if(!value) return 'Unknown';
  const raw=BigInt(value.minor_units); const magnitude=raw<0n?-raw:raw;
  return `${value.currency} ${raw<0n?'-':''}${(magnitude/100n).toLocaleString('en-IN')}.${(magnitude%100n).toString().padStart(2,'0')}`;
}
export function instant(value:string|null|undefined):string {
  if(!value) return 'Unknown date';
  return new Intl.DateTimeFormat('en-GB',{day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit',hourCycle:'h23',timeZone:'Asia/Kolkata'}).format(new Date(value))+' IST';
}
const labels:Record<string,string> = {
  FOLLOW_UP:'Follow up', WAIT:'Wait until the review date', VERIFY_PAYMENT:'Verify the payment', CLOSE:'Review case closure',
  WAIT_NO_CUSTOMER_DRAFT:'No message is needed yet. Return on the review date shown in Findings.',
  INTERNAL_VERIFICATION_NO_CUSTOMER_DRAFT:'Check the payment records first. No customer message is needed for this step.',
  CLOSE_NO_CUSTOMER_DRAFT:'Review the settlement and confirm closure in Case actions. No customer message is needed.',
  EVIDENCE_CHANGED:'Evidence changed. Investigate again before acting',
  TIME_EXPIRED:'The review date has arrived. Investigate again before acting',
  INVESTIGATION_RUNNING:'An investigation is in progress',
  NO_COMPLETED_RESULT:'Investigate the case first', CASE_CLOSED:'The case is closed',
  ATTRIBUTION:'Which payment belongs to this promise',
  VERIFIED_REMAINDER:'Verified remainder', RECORDED_REMAINDER:'Recorded remainder', UNKNOWN_REMAINDER:'Remainder unknown',
};
export function words(value:string) {return labels[value] ?? value.toLowerCase().replaceAll('_',' ');}
export function actionTitle(action:Action):string {
  return action==='FOLLOW_UP'?'Follow up on the overdue balance':words(action);
}
export function localDates(text:string):string {
  return text.replace(/\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})/g,value=>
    Number.isFinite(Date.parse(value))?instant(value):value);
}
