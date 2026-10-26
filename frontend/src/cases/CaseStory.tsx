import type {ReactNode} from 'react';
import type {CaseView, Evidence} from '../api/types';
import {actionTitle, instant, money, words} from '../components/format';

type Tone='indigo'|'blue'|'green'|'red'|'amber'|'grey';
interface StoryItem {key:string; at:number|null; first?:boolean; icon:string; tone:Tone; title:string; detail:string; quote?:Evidence}

const DAY=86_400_000;
const time=(value:string|null|undefined)=>value&&Number.isFinite(Date.parse(value))?Date.parse(value):null;
const text=(value:unknown)=>typeof value==='string'&&value.trim()?value.trim():null;

/** A saved amount_text such as "120,000.00" shown with the app's money format; anything else stays as written. */
function recordedAmount(record:Evidence):string|null {
  const amount=text(record.data.amount_text);const currency=text(record.data.currency_text);
  if(!amount)return null;
  const match=/^(\d{1,3}(?:,\d{2,3})*|\d+)(?:\.(\d{2}))?$/.exec(amount);
  if(!match||!currency)return `${currency??''} ${amount}`.trim();
  return money({currency,minor_units:`${match[1].replaceAll(',','')}${match[2]??'00'}`.replace(/^0+(?=\d)/,'')});
}

function evidenceItem(record:Evidence,view:CaseView):StoryItem {
  const at=time(record.event_at);const amount=recordedAmount(record);
  const unavailable=record.availability==='AVAILABLE'?'':` · source ${words(record.availability)}`;
  const base={key:record.id,at};
  switch(record.kind) {
    case 'INVOICE':return {...base,first:true,icon:'🧾',tone:'indigo',title:`Invoice ${text(record.data.invoice_id)??view.invoice_id} raised${amount?` for ${amount}`:''}`,
      detail:`${text(record.data.due_text)?`Due ${text(record.data.due_text)}`:'Due date not recorded'} · from your invoice records${unavailable}`};
    case 'LEDGER':{
      const verified=record.data.verification_status==='VERIFIED';const settled=record.data.settled===true;
      const transaction=text(record.data.transaction_ref);
      const bankReference=text(record.data.original_transaction_ref)??(transaction?.startsWith('CSV-ALLOCATION:')?null:transaction);
      return {...base,icon:'🏦',tone:verified&&settled?'green':'amber',
        title:verified&&settled?`${amount??'A payment'} received`:`${amount??'A payment'} recorded, not yet verified`,
        detail:`${bankReference?`Bank reference ${bankReference}`:transaction?.startsWith('CSV-ALLOCATION:')?'Owner-confirmed receipt allocation':'Bank record'}${record.data.verification_status?` · ${words(String(record.data.verification_status))}`:''}${unavailable}`};
    }
    case 'MESSAGE':return {...base,icon:'💬',tone:'blue',title:`Message from ${text(record.data.speaker)??'the customer'}`,
      detail:`${record.authoritative?'Designated source':'Customer wording is a claim until the bank records confirm it'}${unavailable}`,quote:record};
    case 'REVERSAL':return {...base,icon:'↩️',tone:'red',title:`${amount??'A payment'} reversed`,detail:`Reversal record${unavailable}`};
    case 'ATTRIBUTION':return {...base,icon:'🔗',tone:'indigo',title:'Payment matched to this invoice',detail:`Recorded allocation${unavailable}`};
  }
}

function storyItems(view:CaseView):StoryItem[] {
  const replaced=new Set(view.evidence.map(record=>record.supersedes_version_id).filter(Boolean));
  const items=view.evidence.filter(record=>!replaced.has(record.id)).map(record=>evidenceItem(record,view));
  const facts=view.financial_facts;const evaluated=time(view.evaluation_at);
  const due=time(facts.due_at);
  if(due!==null)items.push({key:'due',at:due,icon:'📅',tone:evaluated!==null&&due<=evaluated&&view.lifecycle==='OPEN'?'amber':'grey',
    title:evaluated!==null&&due<=evaluated?'Invoice due date passed':'Invoice due date',detail:'Any unpaid balance counts as overdue from here'});
  const result=view.freshness==='CURRENT'&&!view.running_attempt?view.current_result:null;
  if(result) {
    result.commitments.filter(item=>!item.superseded).forEach((item,index)=>{
      const expires=time(item.expires_at);const passed=expires!==null&&evaluated!==null&&expires<=evaluated;
      const promised=item.amount?money(item.amount):'Payment';
      items.push({key:`promise-${item.commitment_stable_id??index}`,at:expires,icon:item.fulfilled?'🤝':passed?'⏰':'🤝',
        tone:item.fulfilled?'green':item.fulfillment_unresolved?'amber':passed?'red':'indigo',
        title:item.fulfilled?`Promise kept: ${promised}`:passed?(item.fulfillment_unresolved?`Promised date passed for ${promised}; which payment belongs to it is not clear yet`:`Promised date passed: ${promised} not received`):`${promised} promised by ${instant(item.expires_at)}`,
        detail:item.fulfilled?'Verified payments cover this promise':passed?'Checked against the verified bank records':'Your assistant waits for this date before following up'});
    });
    items.push({key:'checked',at:time(result.evaluation_at),icon:'✨',tone:'indigo',title:`Checked by your assistant: ${actionTitle(result.action)}`,
      detail:view.freshness==='CURRENT'?'This is the current suggestion':'An earlier check; evidence or time has changed since'});
    if(result.review_at&&view.freshness==='CURRENT')items.push({key:'review',at:time(result.review_at),icon:'🔔',tone:'indigo',title:'Next review',detail:`${instant(result.review_at)} · nothing is sent meanwhile`});
  } else if(view.latest_completed_result) {
    const earlier=view.latest_completed_result;
    items.push({key:'earlier-check',at:time(earlier.evaluation_at),icon:'🔄',tone:'amber',
      title:`Earlier investigation: ${actionTitle(earlier.action)}`,
      detail:`Saved ${instant(earlier.evaluation_at)}. Evidence or time has changed; run a fresh check before using its findings. The saved result remains in History and Compare.`});
  }
  const rank=(item:StoryItem)=>item.first&&item.at===null?-Infinity:item.at??Infinity;
  return items.map((item,index)=>({item,index})).sort((a,b)=>rank(a.item)-rank(b.item)||a.index-b.index).map(entry=>entry.item);
}

/** The customer's wording with each saved promise clause highlighted. */
function Quote({record}:{record:Evidence}) {
  const chars=Array.from(record.original_content);
  if(!chars.length)return <p className="story-quote">No readable source content.</p>;
  const anchors=[...record.commitment_anchors].sort((a,b)=>a.clause_start-b.clause_start);
  const parts:ReactNode[]=[];let at=0;
  anchors.forEach(anchor=>{
    const start=Math.max(anchor.clause_start,at);const end=Math.min(anchor.clause_end,chars.length);
    if(end<=start)return;
    if(start>at)parts.push(chars.slice(at,start).join(''));
    parts.push(<mark key={anchor.id}>{chars.slice(start,end).join('')}</mark>);
    at=end;
  });
  if(at<chars.length)parts.push(chars.slice(at).join(''));
  return <blockquote className="story-quote">{parts}</blockquote>;
}

export function CaseStory({view,onSource}:{view:CaseView;onSource:(id:string)=>void}) {
  const items=storyItems(view);
  return <section className="pk-card case-story" aria-labelledby="story-heading">
    <h2 id="story-heading">What happened</h2>
    <p className="pk-card-sub">Built from your invoices, bank records and customer messages, oldest first.</p>
    {items.length===0?<p>No saved records yet.</p>:<ol className="story" aria-label="What happened">{items.map(item=><li key={item.key} className={`story-${item.tone}`}>
      <span className="story-dot" aria-hidden="true">{item.icon}</span>
      <div className="story-body">
        <p className="story-title">{item.title}</p>
        <p className="story-detail">{item.at===null?(item.first?'':'Date unknown · '):`${instant(new Date(item.at).toISOString())} · `}{item.detail}</p>
        {item.quote&&<><Quote record={item.quote}/><button className="text-button story-source" onClick={()=>onSource(item.quote!.id)}>View original</button></>}
      </div>
    </li>)}</ol>}
  </section>;
}

function promiseFact(view:CaseView):string {
  const result=view.freshness==='CURRENT'&&!view.running_attempt?view.current_result:null;
  if(!result)return view.latest_completed_result?'Needs a fresh check':'Not checked yet';
  const open=result.commitments.filter(item=>!item.superseded);
  const latest=open[open.length-1];
  if(!latest)return 'None recorded';
  return `${latest.amount?money(latest.amount):'Payment'} by ${instant(latest.expires_at)}`;
}

function daysOverdue(view:CaseView):string {
  const due=time(view.financial_facts.due_at);const now=time(view.evaluation_at);
  if(due===null||now===null)return 'Unknown';
  if(view.lifecycle==='CLOSED')return 'Case closed';
  if(now<due)return 'Not yet due';
  const days=Math.floor((now-due)/DAY);
  return days===1?'1 day':`${days} days`;
}

/** Only facts backed by a saved record or the saved investigation; anything missing says so. */
export function KeyFacts({view}:{view:CaseView}) {
  const result=view.freshness==='CURRENT'&&!view.running_attempt?view.current_result:null;
  const earlier=!result?view.latest_completed_result:null;
  const verified=view.evidence.filter(record=>record.kind==='LEDGER'&&record.data.verification_status==='VERIFIED').length;
  const questions=result?result.unresolved_questions.length+result.contradictions.length+result.claims.filter(claim=>!claim.resolved).length:null;
  const facts:{label:string;value:string}[]=[
    {label:'Days overdue',value:daysOverdue(view)},
    {label:'Promise',value:promiseFact(view)},
    {label:'Verified payments',value:verified?String(verified):'None yet'},
    {label:'Open questions',value:questions===null?(earlier?'Needs a fresh check':'Not checked yet'):questions?String(questions):'None'},
    {label:'Bank records',value:`${view.ledger_complete?'Complete':'Incomplete'} · ${words(view.ledger_availability)}`},
    {label:'Last checked',value:result?instant(result.evaluation_at):earlier?`Earlier check · ${instant(earlier.evaluation_at)}`:'Not yet'},
  ];
  return <section className="pk-card key-facts" aria-labelledby="facts-heading">
    <h2 id="facts-heading">Key facts</h2>
    <p className="pk-card-sub">Only facts backed by a saved record.</p>
    <dl className="fact-grid">{facts.map(fact=><div key={fact.label}><dt>{fact.label}</dt><dd>{fact.value}</dd></div>)}</dl>
  </section>;
}
