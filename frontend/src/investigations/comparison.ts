import type {HistoryEvent,Result} from '../api/types';

export interface SourceDifference {source_id:string;before:string[];after:string[]}
export interface ResultComparison {kind:'action'|'evidence'|'findings'|'time'|'identical'|'limited';sources:SourceDifference[];changed:string[];limitations:string[]}
export function completedInvestigations(events:HistoryEvent[],did:string,cid:string):string[] {
  if(events.some(event=>event.demonstration_id!==did||event.case_id!==cid))throw new Error('History belongs to another workspace or case.');
  const ids=new Set<string>();
  return [...events].sort((a,b)=>a.sequence-b.sequence).flatMap(event=>{
    const id=event.payload.investigation_id;
    if(event.event_type!=='INVESTIGATION_COMPLETED'||typeof id!=='string'||ids.has(id))return [];
    ids.add(id);return [id];
  });
}

// Unordered saved collections are compared without mutating them. No money or
// eligibility is calculated here, and snapshot metadata is not a finding.
function canonical(value:unknown):string {
  if(Array.isArray(value))return `[${value.map(canonical).sort().join(',')}]`;
  if(value&&typeof value==='object')return `{${Object.entries(value).sort(([a],[b])=>a.localeCompare(b)).map(([key,item])=>`${JSON.stringify(key)}:${canonical(item)}`).join(',')}}`;
  return JSON.stringify(value) ?? 'undefined';
}
function sourceMap(result:Result) {
  const map=new Map<string,Set<string>>();
  for(const item of result.timeline){
    if(!map.has(item.source_id))map.set(item.source_id,new Set());
    map.get(item.source_id)!.add(item.evidence_version_id);
  }
  return map;
}
export function compareResults(before:Result,after:Result):ResultComparison {
  const limitations:string[]=[];
  const compatible=before.findings_version==='deterministic-1'&&after.findings_version==='deterministic-1';
  if(!compatible)limitations.push('Detailed comparison is limited by a legacy, unsupported or different findings profile. Inspect both saved originals.');
  for(const result of [before,after]){
    const ids=result.commitments.map(item=>item.commitment_stable_id);
    if(ids.some(id=>!id)||new Set(ids).size!==ids.length){limitations.push('Some commitments have no unique saved identity. They cannot be reliably paired; inspect the originals.');break;}
  }
  const left=sourceMap(before),right=sourceMap(after);
  const sources=[...new Set([...left.keys(),...right.keys()])].sort().flatMap(source_id=>{
    const previous=[...(left.get(source_id)??[])].sort(),next=[...(right.get(source_id)??[])].sort();
    return canonical(previous)===canonical(next)?[]:[{source_id,before:previous,after:next}];
  });
  const changed:string[]=[];
  const check=(label:string,a:unknown,b:unknown)=>{if(canonical(a)!==canonical(b))changed.push(label);};
  check('Financial basis',[before.financial_label,before.financial_facts],[after.financial_label,after.financial_facts]);
  check('Saved status',before.status,after.status);
  check('Recorded reason',before.reason_code,after.reason_code);
  check('Review date',before.review_at,after.review_at);
  check('Recorded advice',[before.explanation,before.next_step],[after.explanation,after.next_step]);
  if(compatible){
    check('Commitments',before.commitments,after.commitments);
    check('Payment claims',before.claims,after.claims);
    check('Contradictions',before.contradictions,after.contradictions);
    check('Unresolved facts',before.unresolved_questions,after.unresolved_questions);
    check('Limitations',before.limitations,after.limitations);
    check('Commitment issues',before.commitment_issues,after.commitment_issues);
    const observations=(result:Result)=>result.evidence_observations?.map(({snapshot_id:_,snapshot_hash:__,...saved})=>saved);
    check('Evidence observations',observations(before),observations(after));
    check('Evidence timing',before.timeline,after.timeline);
  }
  const kind=before.action!==after.action?'action':sources.length?'evidence':changed.length?'findings':limitations.length?'limited':before.evaluation_at!==after.evaluation_at?'time':'identical';
  return {kind,sources,changed,limitations};
}
