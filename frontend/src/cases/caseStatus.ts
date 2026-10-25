import type { CaseSummary } from '../api/types';
import { words } from '../components/format';

// One definition shared by the case overview and the morning review strip, so both always agree.

export function reviewDue(item:CaseSummary,evaluationAt?:string) {
  const expired=!!item.review_at&&!!evaluationAt&&Date.parse(item.review_at)<=Date.parse(evaluationAt);
  return {expired,needsReview:item.review_required||expired};
}

// Needs the owner now: not yet investigated, evidence changed, review date reached, or a follow-up or payment check is due.
export function needsAttention(item:CaseSummary,evaluationAt?:string) {
  if (item.lifecycle!=='OPEN') return false;
  return reviewDue(item,evaluationAt).needsReview||item.recommended_action===null||item.recommended_action==='FOLLOW_UP'||item.recommended_action==='VERIFY_PAYMENT';
}

export function statusLabel(item:CaseSummary,evaluationAt?:string) {
  if (item.lifecycle==='CLOSED') return 'Case closed';
  if (reviewDue(item,evaluationAt).needsReview) return 'Review required';
  if (item.recommended_action) return words(item.recommended_action);
  return item.has_previous_investigation?'Investigate again for a current recommendation':'Not investigated';
}

/** Cases needing attention first, each group in the supervisor's latest plan order, then catalogue order. */
export function attentionOrder(cases:CaseSummary[],evaluationAt?:string,plan:Record<string,number>={}) {
  const rank=(item:CaseSummary)=>plan[item.id]??Number.MAX_SAFE_INTEGER;
  return cases.map((item,index)=>({item,index})).sort((a,b)=>
    Number(needsAttention(b.item,evaluationAt))-Number(needsAttention(a.item,evaluationAt))
    ||rank(a.item)-rank(b.item)||a.index-b.index).map(entry=>entry.item);
}
