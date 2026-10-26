import {MorningReview, type MorningReviewParts} from '../agents/MorningReview';
import {useApprovalQueue} from '../approvals/useApprovalQueue';
import type {CaseSummary, MorningReviewView} from '../api/types';
import {attentionOrder, needsAttention, statusLabel} from '../cases/caseStatus';
import {Avatar} from '../components/Avatar';
import {CaseChip} from '../components/Chip';
import {instant, localDates, money, words} from '../components/format';
import {collectTotals, summedCount} from '../dashboard/totals';
import {routeLink, type Route} from '../routing';
import type {CaseEntry, PageProps, Workspace} from '../store/useWorkspace';
import {WorkspaceStatus} from './WorkspaceStatus';
import './pages.css';

const inr=(minor:bigint)=>money({currency:'INR',minor_units:minor.toString()});
const plural=(count:number,one:string,many=`${one}s`)=>`${count} ${count===1?one:many}`;

// "How is my money doing and what needs me today?" Every number comes from the saved case list or case views.
export function DashboardPage({ws,route,navigate}:PageProps) {
  const cases=ws.list?.cases??[];
  const empty=!ws.discovering&&!ws.discoveryError&&(!ws.selected||(!!ws.list&&cases.length===0));
  if(empty)return <EmptyDashboard ws={ws} route={route} navigate={navigate}/>;
  if(!ws.selected||!ws.list)return <>
    <div className="workspace-intro"><h1>Your payment casebook</h1><p>Inspect the record. Find the next responsible step.</p></div>
    <WorkspaceStatus ws={ws}/>
  </>;
  const did=ws.selected;
  return <div className="dashboard">
    <WorkspaceStatus ws={ws}/>
    <MorningReview key={`morning:${did}`} api={ws.api} did={did} cases={ws.list.cases} evaluationAt={ws.evaluationAt} onPlan={ws.setPlan}
      onOpenCase={id=>navigate({page:'case',caseId:id,section:'overview'})} onDone={ws.refresh}
      layout={parts=><DashboardLayout ws={ws} cases={cases} parts={parts} navigate={navigate}/>}/>
  </div>;
}

function DashboardLayout({ws,cases,parts,navigate}:{ws:Workspace;cases:CaseSummary[];parts:MorningReviewParts;navigate:PageProps['navigate']}) {
  const open=cases.filter(item=>item.lifecycle==='OPEN');
  const urgent=attentionOrder(cases,ws.evaluationAt,ws.plan).filter(item=>needsAttention(item,ws.evaluationAt));
  const senderReview=ws.cases.filter(entry=>entry.view?.allowed_commands.start_investigation?.blocking_reasons.includes('SENDER_REVIEW_REQUIRED'));
  return <>
    <section className="dash-hero" aria-labelledby="dashboard-title">
      <div className="dash-hero-main">
        <p className="dash-eyebrow"><span aria-hidden="true">🙏</span> Namaste Anand · records as of {instant(ws.evaluationAt)}</p>
        <h1 id="dashboard-title">Your payment casebook</h1>
        <p className="dash-summary">{urgent.length
          ?`${plural(urgent.length,'case')} of ${cases.length} ${urgent.length===1?'needs':'need'} your attention today. Your assistant does the homework; nothing is sent without you.`
          :`Nothing needs your attention right now across ${plural(cases.length,'case')}. Run the morning check to look again.`}</p>
        <div className="dash-morning">
          <div className="dash-morning-action">{parts.button}</div>
          {parts.description}
          {parts.live}
        </div>
      </div>
      <StillToCollect cases={cases}/>
    </section>
    {senderReview.length>0&&<p className="notice dash-sender" role="note">{plural(senderReview.length,'case')} cannot be checked yet: {words('SENDER_REVIEW_REQUIRED')}.</p>}
    <Tiles ws={ws} open={open} navigate={navigate}/>
    <div className="dash-columns">
      <section className="pk-card" aria-labelledby="follow-up-heading">
        <div className="pk-card-head"><h2 id="follow-up-heading">Follow up today</h2><a className="pk-link" {...routeLink({page:'cases'},navigate)}>See all cases →</a></div>
        <p className="pk-card-sub">The cases that need you, in your assistant's plan order.</p>
        {urgent.length===0?<p className="dash-calm">Nothing needs your attention right now. Every open case can wait until its review date.</p>:
        <ul className="follow-list" aria-label="Follow up today">{urgent.map(item=>
          <li key={item.id}><FollowRow item={item} entry={ws.cases.find(entry=>entry.summary.id===item.id)} evaluationAt={ws.evaluationAt} navigate={navigate}/></li>)}</ul>}
      </section>
      <AssistantMorning review={parts.review} running={parts.running} navigate={navigate}/>
    </div>
    {parts.results&&<section className="pk-card dash-results" aria-labelledby="results-heading">
      <h2 id="results-heading">This morning, case by case</h2>
      {parts.results}
    </section>}
  </>;
}

function StillToCollect({cases}:{cases:CaseSummary[]}) {
  const totals=collectTotals(cases);
  const summed=summedCount(cases,totals);
  // An unknown is never shown as zero: with nothing known to sum, the total itself is unknown.
  const unknownOnly=summed===0&&totals.unknownCount+totals.otherCurrencyCount>0;
  return <section className="dash-total" aria-labelledby="still-to-collect">
    <p id="still-to-collect" className="dash-total-label">Still to collect</p>
    <p className="dash-total-amount">{unknownOnly?'Unknown':inr(totals.inrMinor)}</p>
    <ul className="dash-total-notes">
      {totals.recordedMinor>0n&&<li>{`${inr(totals.recordedMinor)} of this is recorded but not yet verified`}</li>}
      {totals.unknownCount>0&&<li>{`plus ${totals.unknownCount} with unknown balance`}</li>}
      {totals.otherCurrencyCount>0&&<li>{`${totals.otherCurrencyCount} in other currencies`}</li>}
      <li className="dash-total-basis">{`From ${plural(summed,'open case')} with a known rupee balance`}</li>
    </ul>
  </section>;
}

function Tiles({ws,open,navigate}:{ws:Workspace;open:CaseSummary[];navigate:PageProps['navigate']}) {
  const queue=useApprovalQueue(ws).items;
  const viewsReady=!ws.detailsLoading&&ws.cases.every(entry=>entry.view||entry.error);
  const fresh=viewsReady?ws.cases.filter(entry=>needsFreshCheck(entry)).length:null;
  const tiles:{icon:string;tone:string;label:string;value:number|null;hint:string;link:Route}[]=[
    {icon:'🤝',tone:'coral',label:'Follow-ups due',value:open.filter(item=>item.recommended_action==='FOLLOW_UP').length,hint:'Overdue and ready for a reminder',link:{page:'cases'}},
    {icon:'🏦',tone:'amber',label:'Payments to verify',value:open.filter(item=>item.recommended_action==='VERIFY_PAYMENT').length,hint:'Customer says paid; check the bank',link:{page:'cases'}},
    {icon:'✅',tone:'indigo',label:'Waiting for you',value:queue?.length??null,hint:'Drafts and decisions to approve',link:{page:'approvals'}},
    {icon:'🔄',tone:'green',label:'Needs a fresh check',value:fresh,hint:'No current recommendation yet',link:{page:'cases'}},
  ];
  return <ul className="dash-tiles" aria-label="Today at a glance">{tiles.map(tile=><li key={tile.label}>
    <a className="dash-tile" {...routeLink(tile.link,navigate)}>
      <span className={`dash-tile-icon tone-${tile.tone}`} aria-hidden="true">{tile.icon}</span>
      <span className="dash-tile-text"><span className="dash-tile-label">{tile.label}</span><strong className="dash-tile-value">{tile.value===null?'…':tile.value}</strong>{tile.value===null&&<span className="visually-hidden">Loading</span>}<span className="dash-tile-hint">{tile.hint}</span></span>
    </a>
  </li>)}</ul>;
}

// Open and not being checked right now, but without a current result: the morning check or Investigate case will refresh it.
function needsFreshCheck({view}:CaseEntry) {
  return !!view&&view.lifecycle==='OPEN'&&!view.running_attempt&&(!view.current_result||view.freshness!=='CURRENT');
}

function FollowRow({item,entry,evaluationAt,navigate}:{item:CaseSummary;entry?:CaseEntry;evaluationAt?:string;navigate:PageProps['navigate']}) {
  const result=entry?.view?.current_result;
  const reason=result&&entry?.view?.freshness==='CURRENT'?localDates(result.next_step):statusLabel(item,evaluationAt);
  return <a className="follow-row" {...routeLink({page:'case',caseId:item.id},navigate)}>
    <Avatar name={item.client}/>
    <span className="follow-who"><strong><span className="follow-client">{item.client}</span> · {money(item.balance)}{item.balance_label==='RECORDED_REMAINDER'?' recorded':''}</strong><span>{reason}</span></span>
    <CaseChip item={item} evaluationAt={evaluationAt}/>
    <span className="follow-go">Open →</span>
  </a>;
}

function AssistantMorning({review,running,navigate}:{review:MorningReviewView|null;running:boolean;navigate:PageProps['navigate']}) {
  const outcomes=review?.outcomes??[];
  const count=(kind:'INVESTIGATED'|'SKIPPED'|'FAILED')=>outcomes.filter(outcome=>outcome.outcome===kind).length;
  const drafts=outcomes.filter(outcome=>outcome.draft_ready).length;
  return <section className="pk-card dash-assistant" aria-labelledby="assistant-morning-heading">
    <div className="pk-card-head"><h2 id="assistant-morning-heading">Assistant's morning</h2></div>
    {running?<p className="pk-card-sub">Your morning check is running. Progress shows at the top of this page.</p>
    :!review?<p className="pk-card-sub">No morning check has run in this workspace yet. Start one above: your assistant checks every case, plans who to follow up first and drafts reminders for you to approve.</p>
    :<>
      <p className="pk-card-sub">{review.status==='COMPLETE'?`Finished ${instant(review.terminal_at)}`:review.status==='FAILED'?`Stopped ${instant(review.terminal_at)}`:`Started ${instant(review.started_at)}`}{review.started_by==='AUTONOMOUS'?' · started automatically':''}</p>
      <ul className="dash-feed">
        <li><span aria-hidden="true">🔎</span> Checked {plural(outcomes.length,'case')}</li>
        <li><span aria-hidden="true">🧠</span> {count('INVESTIGATED')} investigated now, {count('SKIPPED')} needed no change</li>
        {count('FAILED')>0&&<li className="dash-feed-warn"><span aria-hidden="true">⚠️</span> {count('FAILED')} need your retry</li>}
        <li><span aria-hidden="true">✍️</span> {plural(drafts,'reminder draft')} ready for your review</li>
        <li className="dash-feed-safe"><span aria-hidden="true">🔒</span> <strong>Nothing sent.</strong> Every message waits for your approval.</li>
      </ul>
    </>}
    <a className="pk-link" {...routeLink({page:'assistant'},navigate)}>See the assistant at work →</a>
  </section>;
}

function EmptyDashboard({ws,navigate}:PageProps) {
  return <div className="dashboard">
    <section className="dash-hero dash-hero-empty" aria-labelledby="dashboard-title">
      <div className="dash-hero-main">
        <p className="dash-eyebrow"><span aria-hidden="true">🙏</span> Namaste Anand</p>
        <h1 id="dashboard-title">Your payment casebook</h1>
        <p className="dash-summary">PromiseKeeper reads your invoices, bank receipts and customer messages, then tells you who to follow up today. Nothing is ever sent without you.</p>
      </div>
    </section>
    <WorkspaceStatus ws={ws}/>
    <section className="pk-card dash-empty" aria-labelledby="empty-heading">
      <span className="dash-empty-icon" aria-hidden="true">📂</span>
      <div>
        <h2 id="empty-heading">Start by uploading your records</h2>
        <p>Bring in your customers, invoices, bank receipts and customer messages in six short steps. You check every file before it is saved.</p>
        <p><a className="pk-button" {...routeLink({page:'upload'},navigate)}>Upload your records</a></p>
        <p className="pk-card-sub">Already uploaded records? Choose <strong>Workspace</strong> to return to your saved work.</p>
      </div>
    </section>
  </div>;
}
