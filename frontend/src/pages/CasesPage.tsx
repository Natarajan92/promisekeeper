import {CaseList} from '../cases/CaseList';
import {money} from '../components/format';
import {collectTotals, summedCount} from '../dashboard/totals';
import type {PageProps} from '../store/useWorkspace';
import {WorkspaceStatus} from './WorkspaceStatus';
import './pages.css';

export function CasesPage({ws,navigate}:PageProps) {
  const cases=ws.list?.cases??[];
  const open=cases.filter(item=>item.lifecycle==='OPEN').length;
  const totals=collectTotals(cases);
  return <div className="cases-page">
    <div className="page-head">
      <div><h1>Cases</h1><p>Every invoice case in this workspace, those needing attention first.</p></div>
      {ws.list&&<ul className="page-head-stats" aria-label="Case totals">
        <li><span>Open cases</span><strong>{open}</strong></li>
        <li><span>Closed</span><strong>{cases.length-open}</strong></li>
        <li><span>Still to collect</span><strong>{summedCount(cases,totals)===0&&totals.unknownCount+totals.otherCurrencyCount>0?'Unknown':money({currency:'INR',minor_units:totals.inrMinor.toString()})}</strong>{totals.unknownCount>0&&<small>plus {totals.unknownCount} unknown</small>}</li>
      </ul>}
    </div>
    <WorkspaceStatus ws={ws}/>
    {ws.selected&&ws.list&&<CaseList cases={ws.list.cases} evaluationAt={ws.evaluationAt} plan={ws.plan} selected={null} onSelect={id=>navigate({page:'case',caseId:id})}/>}
  </div>;
}
