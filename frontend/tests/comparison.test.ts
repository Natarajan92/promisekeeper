import {expect,it} from 'vitest';
import {compareResults,completedInvestigations} from '../src/investigations/comparison';
import type {Result} from '../src/api/types';
import {before,after,completed} from './comparisonFixtures';
import {cid,did} from './fixtures';

it('orders completed results by server sequence, excludes incomplete attempts, and rejects another scope',()=>{
  expect(completedInvestigations([completed('after',20),{...completed('failed',30),event_type:'INVESTIGATION_INCOMPLETE'},completed('before',2),completed('after',20)],did,cid)).toEqual(['before','after']);
  expect(()=>completedInvestigations([{...completed('foreign',1),demonstration_id:'other'}],did,cid)).toThrow(/another copy or case/);
});
it('shows the Cedar action change and exact newly included ledger version without changing saved results',()=>{
  const original=JSON.stringify([before,after]);const diff=compareResults(before,after);
  expect(diff.kind).toBe('action');expect(diff.sources).toEqual([{source_id:'PK-003-L2',before:[],after:['settlement']}]);
  expect(diff.changed).toContain('Payment claims');expect(JSON.stringify([before,after])).toBe(original);
});
it('distinguishes identical, evaluation-only, review-boundary and same-action evidence changes',()=>{
  expect(compareResults(before,{...before,investigation_id:'other',result_hash:'d'}).kind).toBe('identical');
  expect(compareResults(before,{...before,evaluation_at:after.evaluation_at}).kind).toBe('time');
  expect(compareResults(before,{...before,review_at:after.evaluation_at}).kind).toBe('findings');
  expect(compareResults(before,{...before,timeline:after.timeline}).kind).toBe('evidence');
});
it('tracks replaced and removed source versions by stable identity even when order changes',()=>{
  const replaced={...before,timeline:[{...before.timeline[0],evidence_version_id:'message-v2'}]};
  expect(compareResults(before,replaced).sources).toEqual([{source_id:'PK-003-M1',before:['message'],after:['message-v2']}]);
  expect(compareResults(before,{...before,timeline:[]}).sources).toEqual([{source_id:'PK-003-M1',before:['message'],after:[]}]);
  expect(compareResults(after,{...after,timeline:[...after.timeline].reverse()}).kind).toBe('identical');
});
it('preserves unknown versus zero and arbitrary precision saved money',()=>{
  expect(compareResults(before,{...before,financial_facts:{...before.financial_facts,balance:null,certainty:'UNKNOWN'}}).changed).toContain('Financial basis');
  const large={...before,financial_facts:{...before.financial_facts,balance:{currency:'INR' as const,minor_units:'900719925474099200'}}};
  expect(compareResults(large,{...large,financial_facts:{...large.financial_facts,balance:{currency:'INR',minor_units:'900719925474099201'}}}).kind).toBe('findings');
});
it('matches commitments by stable identity rather than position and reports unresolved identity',()=>{
  const a={commitment_stable_id:'promise-a',commitment_key:'a',source_id:'M',evidence_version_id:'m',amount:null,expires_at:null,fulfilled:false,fulfillment_unresolved:false,credited:{currency:'INR' as const,minor_units:'0'},superseded:false};
  const b={...a,commitment_stable_id:'promise-b',commitment_key:'b'};
  const result={...before,commitments:[a,b]};
  expect(compareResults(result,{...result,commitments:[b,a]}).kind).toBe('identical');
  expect(compareResults(result,{...result,commitments:[b,{...a,fulfilled:true}]}).changed).toContain('Commitments');
  expect(compareResults({...before,commitments:[{...a,commitment_stable_id:null}]},before).limitations.join(' ')).toMatch(/identity/);
});
it('never claims no changes for unsupported, legacy or different finding profiles',()=>{
  for(const profile of [undefined,'future-2']){
    const legacy={...before,findings_version:profile} as Result;
    expect(compareResults(legacy,legacy).kind).toBe('limited');
    expect(compareResults(legacy,before).limitations.join(' ')).toMatch(/profile/i);
  }
});
it('does not treat snapshot provenance changes as an observed finding change',()=>{
  const observation={subject:'LEDGER' as const,field:'complete' as const,value:true,source:null,snapshot_id:'s1',snapshot_hash:'h1'};
  expect(compareResults({...before,evidence_observations:[observation]},{...before,evidence_observations:[{...observation,snapshot_id:'s2',snapshot_hash:'h2'}]}).kind).toBe('identical');
});
