import type { Action, Money } from '../api/types';
// Rupees show the symbol with Indian grouping; any other currency keeps its code. Backend text is never rewritten.
export function money(value:Money|{currency:string;minor_units:string}|null|undefined):string {
  if(!value) return 'Unknown';
  const raw=BigInt(value.minor_units); const magnitude=raw<0n?-raw:raw;
  const amount=`${(magnitude/100n).toLocaleString('en-IN')}.${(magnitude%100n).toString().padStart(2,'0')}`;
  if(value.currency==='INR')return `${raw<0n?'-':''}₹${amount}`;
  return `${value.currency} ${raw<0n?'-':''}${amount}`;
}
export function instant(value:string|null|undefined):string {
  if(!value) return 'Unknown date';
  return new Intl.DateTimeFormat('en-GB',{day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit',hourCycle:'h23',timeZone:'Asia/Kolkata'}).format(new Date(value))+' IST';
}
const labels:Record<string,string> = {
  FOLLOW_UP:'Follow up', WAIT:'Wait until the review date', VERIFY_PAYMENT:'Verify the payment', CLOSE:'Review case closure',
  WAIT_NO_CUSTOMER_DRAFT:'No message is needed yet. Return on the review date shown in the suggestion.',
  INTERNAL_VERIFICATION_NO_CUSTOMER_DRAFT:'Check the payment records first. No customer message is needed for this step.',
  CLOSE_NO_CUSTOMER_DRAFT:'Review the settlement and confirm closure in Case actions. No customer message is needed.',
  EVIDENCE_CHANGED:'Evidence changed. Investigate again before acting',
  TIME_EXPIRED:'The review date has arrived. Investigate again before acting',
  INVESTIGATION_RUNNING:'An investigation is in progress',
  SENDER_REVIEW_REQUIRED:'Review senders in a new imported workspace; the original evidence and history are retained',
  NO_COMPLETED_RESULT:'Investigate the case first', CASE_CLOSED:'The case is closed',
  ATTRIBUTION:'Which payment belongs to this promise',
  NOTE_HAS_DIGITS:'The personal note contains a number. Amounts and dates belong only in the fact lines.',
  NOTE_PAYMENT_TOPIC:'The personal note mentions payment, money, dates or contact details. Keep it to warmth; the fact lines carry those.',
  NOTE_INSTRUCTION_LIKE:'The personal note reads like an instruction. Keep it to a friendly, factual sentence.',
  NOTE_TOO_LONG:'The personal note is longer than 400 characters. Shorten it.',
  NOTE_MULTI_PARAGRAPH:'The personal note must be a single paragraph.',
  UNSUPPORTED_CLAUSE:'A paragraph is not one of the supported clauses. Keep the fact lines as written and add at most one note after the greeting.',
  UNSUPPORTED_FEE_OR_THREAT:'Remove fees, interest, penalties or legal threats; they are not supported by the records.',
  UNSUPPORTED_PAYMENT_INSTRUCTION:'Remove bank, account or transfer instructions; the draft cannot add payment details.',
  UNSUPPORTED_PAYMENT_ASSERTION:'Remove claims about whether payment was made; only verified records decide that.',
  UNSUPPORTED_CURRENCY:'Use only the invoice currency shown in the fact lines.',
  UNSUPPORTED_AMOUNT:'Remove amounts that are not the verified balance in the fact lines.',
  UNRESOLVED_PLACEHOLDER:'Replace placeholders such as [NAME] or {amount} before approval.',
  MISSING_REQUIRED_CLAUSE:'A required fact line was removed or changed. Restore it from the suggested draft.',
  PROVIDER_CIRCUIT_OPEN:'The AI provider is failing repeatedly, so it is paused briefly and the standard template is used.',
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
