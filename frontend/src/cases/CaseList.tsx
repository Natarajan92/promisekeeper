import type { CaseSummary } from '../api/types';
import { instant, money, words } from '../components/format';
export function CaseList({cases,selected,onSelect,evaluationAt}:{cases:CaseSummary[];selected:string|null;onSelect:(id:string)=>void;evaluationAt?:string}) {
  return <nav aria-label="Fictional cases" className="case-list">
    <h2>Case overview <span>{cases.length}</span></h2>
    <p className="mobile-case-hint">Scroll through the cases to choose one.</p>
    {cases.length!==3 && <p role="alert">Expected three fictional cases. Refresh the saved copy.</p>}
    <div className="case-cards">{cases.map(item=>{
      const expired=!!item.review_at&&!!evaluationAt&&Date.parse(item.review_at)<=Date.parse(evaluationAt);
      const needsReview=item.review_required||expired;
      return <button key={item.id} className={`case-select ${selected===item.id?'selected':''}`} aria-current={selected===item.id?'page':undefined} onClick={()=>onSelect(item.id)}>
      <span className="case-code">{item.catalogue_case_id} <span>{words(item.lifecycle)}</span></span>
      <strong>{item.client}</strong>
      <span>{item.invoice_id} · {item.currency ?? 'Unknown currency'}</span>
      <span className="case-balance"><span>{words(item.balance_label ?? 'RECORDED_REMAINDER')}</span><strong>{money(item.balance)}</strong></span>
      <span className={needsReview?'review-label':'case-action'}>{item.lifecycle==='CLOSED'?'Case closed':needsReview?'Review required':item.recommended_action?words(item.recommended_action):item.has_previous_investigation?'Investigate again for a current recommendation':'Not investigated'}</span>
      {item.review_at&&<span>{expired?'Review due':'Next review'}: {instant(item.review_at)}</span>}
      <span className="case-date">Due date: {item.due_text ?? 'Unknown due date'}</span>
      <span className="case-date">Overdue from {instant(item.due_at)}</span>
    </button>;})}</div>
  </nav>;
}
