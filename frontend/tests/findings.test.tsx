import { useState } from 'react';
import { afterEach, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import type { CaseView, Evidence, EvidenceObservation, Result } from '../src/api/types';
import { FindingsView } from '../src/investigations/FindingsView';
import { SourceViewer } from '../src/cases/SourceViewer';
import { caseView, source } from './fixtures';

afterEach(cleanup);

const oldSource = source as Evidence;
const updatedSource: Evidence = {...oldSource, id:'66666666-6666-4666-8666-666666666666', version:2, original_content:'Updated source wording.', supersedes_version_id:oldSource.id};
const view: CaseView = {...caseView, evidence:[updatedSource, oldSource], freshness:'EVIDENCE_CHANGED'} as CaseView;
const saved = {
  investigation_id:'44444444-4444-4444-8444-444444444444',
  snapshot_id:'55555555-5555-4555-8555-555555555555', snapshot_hash:'a'.repeat(64),
  evaluation_at:'2026-10-24T00:00:00Z', status:'COMPLETE',
  financial_facts:{certainty:'KNOWN', invoice:{currency:'INR',minor_units:'5000000'}, paid:{currency:'INR',minor_units:'5000000'}, balance:{currency:'INR',minor_units:'0'}, due_at:'2026-10-20T18:30:00Z', issues:[]},
  financial_label:'VERIFIED_REMAINDER', commitments:[], claims:[],
  timeline:[{source_id:'message-1',evidence_version_id:'33333333-3333-4333-8333-333333333333',event_at:null,arrived_at:'2026-10-24T00:00:00Z',kind:'MESSAGE',undated:true}],
  contradictions:[], unresolved_questions:[], limitations:[], action:'CLOSE', reason_code:'BALANCE_ZERO',
  explanation:{text:'Verified recorded payments cover the invoice.', sources:[]},
  next_step:'Review the saved evidence.', review_at:null, result_hash:'b'.repeat(64),
  findings_version:'deterministic-1', commitment_issues:[],
  evidence_observations:[
    {subject:'LEDGER',field:'availability',value:'AVAILABLE',snapshot_id:'55555555-5555-4555-8555-555555555555',snapshot_hash:'a'.repeat(64),source:null},
    {subject:'LEDGER',field:'complete',value:true,snapshot_id:'55555555-5555-4555-8555-555555555555',snapshot_hash:'a'.repeat(64),source:null},
  ],
} satisfies Result;
const financialIssue = {code:'DUPLICATE_PAYMENT',detail:'Payment records may be duplicated.',sources:['message-1'],source_versions:[{source_id:'message-1',evidence_version_id:'33333333-3333-4333-8333-333333333333'}]};
const commitmentIssue = {code:'INVALID_ATTRIBUTION',detail:'A payment link needs review.',sources:['message-1'],source_versions:[{source_id:'message-1',evidence_version_id:'33333333-3333-4333-8333-333333333333'}]};

function SourceHarness({result,caseData=view}:{result:Result;caseData?:CaseView}) {
  const [selected,setSelected]=useState<Evidence|null>(null);
  return <><FindingsView result={result} view={caseData} onSource={id=>setSelected(caseData.evidence.find(record=>record.id===id) ?? null)}/>{selected&&<SourceViewer source={selected} onClose={()=>setSelected(null)}/>}</>;
}

it('shows every financial and commitment issue once for COMPLETE CLOSE without limitations', () => {
  render(<FindingsView result={{...saved,financial_facts:{...saved.financial_facts,issues:[financialIssue,{code:'INVALID_REVERSAL',detail:'A reversal record needs review.',sources:[],source_versions:[]}]},commitment_issues:[commitmentIssue,{code:'MISSING_IDENTITY',detail:'A promise identity needs review.',sources:[],source_versions:[]}]}} view={view} onSource={()=>{}}/>);
  expect(screen.getByRole('heading',{name:'Review case closure'})).toBeInTheDocument();
  expect(screen.getByRole('heading',{name:'Financial issues'})).toBeInTheDocument();
  expect(screen.getByRole('heading',{name:'Commitment issues'})).toBeInTheDocument();
  expect(screen.getAllByText('Payment records may be duplicated.')).toHaveLength(1);
  expect(screen.getAllByText('A payment link needs review.')).toHaveLength(1);
  expect(screen.getAllByText('A reversal record needs review.')).toHaveLength(1);
  expect(screen.getAllByText('A promise identity needs review.')).toHaveLength(1);
  expect(screen.getByText(/This recommendation does not close the case/)).toBeInTheDocument();
  expect(screen.queryByRole('heading',{name:'Limitations'})).not.toBeInTheDocument();
  fireEvent.click(screen.getByText('Saved investigation provenance'));
  expect(screen.getByText(/Findings profile: deterministic-1/)).toBeInTheDocument();
  expect(screen.queryByText(/Legacy findings/)).not.toBeInTheDocument();
});

it.each(['financial','commitment'] as const)('opens the exact retained version from a %s issue after an update and returns focus', kind => {
  const result = {...saved,financial_facts:{...saved.financial_facts,issues:kind==='financial'?[financialIssue]:[]},commitment_issues:kind==='commitment'?[commitmentIssue]:[]};
  render(<SourceHarness result={result}/>);
  const button=screen.getByRole('button',{name:'message-1 / v1'});
  button.focus();
  fireEvent.click(button);
  const dialog=screen.getByRole('dialog');
  expect(within(dialog).getByRole('heading',{name:'message-1 / version 1'})).toBeInTheDocument();
  expect(within(dialog).getByText('I have sent INR 20,000. Please check.')).toBeInTheDocument();
  expect(within(dialog).queryByText('Updated source wording.')).not.toBeInTheDocument();
  fireEvent.click(within(dialog).getByRole('button',{name:'Close source viewer'}));
  expect(button).toHaveFocus();
});

it('does not substitute the latest source when an issue version is missing from the view', () => {
  render(<FindingsView result={{...saved,commitment_issues:[commitmentIssue]}} view={{...view,evidence:[updatedSource]}} onSource={()=>{}}/>);
  expect(screen.getByText('A payment link needs review.')).toBeInTheDocument();
  expect(screen.queryByRole('button')).not.toBeInTheDocument();
  expect(screen.getByText(/Source message-1.*unavailable in this view/)).toBeInTheDocument();
});

it('shows source-less ledger availability and completeness without fabricating source buttons', () => {
  render(<FindingsView result={{...saved,evidence_observations:[
    {subject:'LEDGER',field:'availability',value:'UNAVAILABLE',snapshot_id:saved.snapshot_id,snapshot_hash:saved.snapshot_hash,source:null},
    {subject:'LEDGER',field:'complete',value:false,snapshot_id:saved.snapshot_id,snapshot_hash:saved.snapshot_hash,source:null},
  ] satisfies EvidenceObservation[]}} view={view} onSource={()=>{}}/>);
  expect(screen.getByRole('heading',{name:'Evidence observations'})).toBeInTheDocument();
  expect(screen.getByText('Saved ledger availability: unavailable.')).toBeInTheDocument();
  expect(screen.getByText('Saved ledger is incomplete.')).toBeInTheDocument();
  expect(screen.queryByRole('button')).not.toBeInTheDocument();
});

it('explains empty original content without a quotation or readable-source button', () => {
  render(<FindingsView result={{...saved,evidence_observations:[...saved.evidence_observations,{subject:'SOURCE',field:'content_present',value:false,snapshot_id:saved.snapshot_id,snapshot_hash:saved.snapshot_hash,source:{source_id:'message-1',evidence_version_id:oldSource.id}} satisfies EvidenceObservation]}} view={{...view,evidence:[{...oldSource,original_content:''}]}} onSource={()=>{}}/>);
  expect(screen.getByText('Source message-1 has no readable original content.')).toBeInTheDocument();
  expect(screen.queryByRole('button')).not.toBeInTheDocument();
  expect(document.querySelector('blockquote')).not.toBeInTheDocument();
});

it('opens a readable availability observation at its exact retained version', () => {
  render(<SourceHarness result={{...saved,evidence_observations:[...saved.evidence_observations,{subject:'SOURCE',field:'availability',value:'UNAVAILABLE',snapshot_id:saved.snapshot_id,snapshot_hash:saved.snapshot_hash,source:{source_id:'message-1',evidence_version_id:oldSource.id}} satisfies EvidenceObservation]}} caseData={{...view,evidence:[updatedSource,{...oldSource,availability:'UNAVAILABLE'}]}}/>);
  expect(screen.getByText('Source message-1 availability: unavailable.')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button',{name:'message-1 / v1'}));
  expect(within(screen.getByRole('dialog')).getByText('I have sent INR 20,000. Please check.')).toBeInTheDocument();
});

it('keeps an availability observation readable when its original content is empty', () => {
  render(<FindingsView result={{...saved,evidence_observations:[...saved.evidence_observations,{subject:'SOURCE',field:'availability',value:'UNREADABLE',snapshot_id:saved.snapshot_id,snapshot_hash:saved.snapshot_hash,source:{source_id:'message-1',evidence_version_id:oldSource.id}} satisfies EvidenceObservation]}} view={{...view,evidence:[{...oldSource,availability:'UNREADABLE',original_content:''}]}} onSource={()=>{}}/>);
  expect(screen.getByText('Source message-1 availability: unreadable.')).toBeInTheDocument();
  expect(screen.queryByRole('button')).not.toBeInTheDocument();
});

it('labels legacy findings and requests reinvestigation without adding fields to the saved payload', () => {
  const {findings_version,commitment_issues,evidence_observations,...legacy}=saved;
  const result={...legacy,financial_facts:{...legacy.financial_facts,issues:[{code:'DUPLICATE_PAYMENT',detail:'Legacy payment issue.',sources:['message-1']}]}};
  const original=JSON.stringify(result);
  render(<SourceHarness result={result}/>);
  expect(screen.getByText(/Legacy findings.*Reinvestigate/i)).toBeInTheDocument();
  expect(screen.getByText('Legacy payment issue.')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button',{name:'message-1 / v1'}));
  expect(within(screen.getByRole('dialog')).getByRole('heading',{name:'message-1 / version 1'})).toBeInTheDocument();
  expect(JSON.stringify(result)).toBe(original);
});
