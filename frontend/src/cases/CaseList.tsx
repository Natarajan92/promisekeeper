import { useState } from 'react';
import type { CaseSummary } from '../api/types';
import { instant, money, words } from '../components/format';
import { Avatar } from '../components/Avatar';
import { caseChip } from '../components/Chip';
import { attentionOrder, needsAttention, reviewDue, statusLabel } from './caseStatus';

export { needsAttention } from './caseStatus';

export function CaseList({cases,selected,onSelect,evaluationAt,plan}:{cases:CaseSummary[];selected:string|null;onSelect:(id:string)=>void;evaluationAt?:string;plan?:Record<string,number>}) {
  const [showAll,setShowAll]=useState(false);
  const ordered=attentionOrder(cases,evaluationAt,plan);
  const urgent=ordered.filter(item=>needsAttention(item,evaluationAt));
  // The open case stays visible even when it does not need attention, so opening it from the review never hides it.
  const visible=showAll?ordered:ordered.filter(item=>needsAttention(item,evaluationAt)||item.id===selected);
  const hidden=cases.length-visible.length;
  return <nav aria-label="Cases" className="case-list">
    <h2>Case overview <span>{showAll?`${cases.length} cases`:`${urgent.length} need attention`}</span></h2>
    <p className="case-filter-note">{showAll?'Showing every case; those needing attention come first.':`Showing cases that need your attention${hidden?`; ${hidden} more can wait`:''}.`}</p>
    <button className="text-button case-filter" aria-pressed={showAll} onClick={()=>setShowAll(value=>!value)}>{showAll?'Show only cases needing attention':`Show all ${cases.length} cases`}</button>
    <p className="mobile-case-hint">Scroll through the cases to choose one.</p>
    {visible.length===0&&<p className="empty-state">Nothing needs your attention right now.</p>}
    <div className="case-cards">{visible.map(item=>{
      const {expired,needsReview}=reviewDue(item,evaluationAt);
      return <button key={item.id} className={`case-select ${selected===item.id?'selected':''}`} aria-current={selected===item.id?'page':undefined} onClick={()=>onSelect(item.id)}>
      <span className="case-code">{item.catalogue_case_id} <span>{words(item.lifecycle)}</span></span>
      <span className="case-who"><Avatar name={item.client}/><span className="case-who-text"><strong>{item.client}</strong>
      <span>{item.invoice_id} · {item.currency ?? 'Unknown currency'}</span></span></span>
      <span className="case-balance"><span>{words(item.balance_label ?? 'RECORDED_REMAINDER')}</span><strong>{money(item.balance)}</strong></span>
      <span className="case-status-row"><span className={`${needsReview?'review-label':'case-action'} chip chip-${caseChip(item,evaluationAt).tone}`}>{statusLabel(item,evaluationAt)}</span></span>
      {item.review_at&&<span className="case-review-at">{expired?'Review due':'Next review'}: {instant(item.review_at)}</span>}
      <span className="case-date">Due date: {item.due_text ?? 'Unknown due date'}</span>
      <span className="case-date">Overdue from {instant(item.due_at)}</span>
      <span className="case-open">Open case →</span>
    </button>;})}</div>
  </nav>;
}
