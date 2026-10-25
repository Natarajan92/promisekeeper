import type { Attempt, CaseView, DeterministicResult, HistoryEvent, Result } from '../src/api/types';
import { caseView, cid, did } from './fixtures';

export const before:DeterministicResult={
  investigation_id:'before',snapshot_id:'snapshot-before',snapshot_hash:'a'.repeat(64),result_hash:'b'.repeat(64),
  evaluation_at:'2026-10-23T05:00:00Z',status:'COMPLETE',action:'VERIFY_PAYMENT',reason_code:'UNVERIFIED_CLAIM',
  financial_facts:{certainty:'KNOWN',invoice:{currency:'INR',minor_units:'9000000'},paid:{currency:'INR',minor_units:'3000000'},balance:{currency:'INR',minor_units:'6000000'},due_at:'2026-10-15T18:30:00Z',issues:[]},
  financial_label:'RECORDED_REMAINDER',commitments:[],claims:[{source_id:'PK-003-M1',evidence_version_id:'message',resolved:false,customer_clarification:false}],
  timeline:[{source_id:'PK-003-M1',evidence_version_id:'message',kind:'MESSAGE',event_at:'2026-10-22T10:30:00Z',arrived_at:'2026-10-22T10:30:00Z',undated:false}],
  contradictions:[],unresolved_questions:[],limitations:[],explanation:{text:'Payment is claimed but not verified.',sources:['PK-003-M1']},next_step:'Verify the payment.',review_at:null,
  findings_version:'deterministic-1',commitment_issues:[],evidence_observations:[],
};
export const after:DeterministicResult={...before,investigation_id:'after',snapshot_id:'snapshot-after',result_hash:'c'.repeat(64),evaluation_at:'2026-10-23T05:35:00Z',action:'CLOSE',reason_code:'BALANCE_ZERO',financial_label:'VERIFIED_REMAINDER',financial_facts:{...before.financial_facts,paid:{currency:'INR',minor_units:'9000000'},balance:{currency:'INR',minor_units:'0'}},claims:[{...before.claims[0],resolved:true}],timeline:[...before.timeline,{source_id:'PK-003-L2',evidence_version_id:'settlement',kind:'LEDGER',event_at:'2026-10-22T08:30:00Z',arrived_at:'2026-10-23T05:30:00Z',undated:false}],explanation:{text:'Verified payments cover the invoice.',sources:['PK-003-L2']},next_step:'Review case closure.'};
export const completed=(id:string,sequence:number):HistoryEvent=>({id:`event-${sequence}`,demonstration_id:did,case_id:cid,sequence,event_type:'INVESTIGATION_COMPLETED',payload:{investigation_id:id},operation_id:null,occurred_at:'2026-10-23T00:00:00Z'});
export const attempt=(result:Result):Attempt=>({schema_version:'1',id:result.investigation_id,investigation_id:result.investigation_id,demonstration_id:did,case_id:cid,status:result.status,snapshot_id:result.snapshot_id,snapshot_hash:result.snapshot_hash,evaluation_at:result.evaluation_at,deadline_at:result.evaluation_at,limitations:[],failure_code:null,result,action:result.action,draft_status:'NONE',progress:[]});
export const comparisonView:CaseView={...caseView,client:'Cedar Retail Labs',catalogue_case_id:'PK-003',latest_completed_result:after,current_result:after,freshness:'CURRENT'} as CaseView;
