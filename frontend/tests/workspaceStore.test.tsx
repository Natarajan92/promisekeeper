import {afterEach,expect,it,vi} from 'vitest';
import {act,cleanup,renderHook,waitFor} from '@testing-library/react';
import {ApiClient} from '../src/api/client';
import {completePending} from '../src/api/pendingOperations';
import {useWorkspace} from '../src/store/useWorkspace';
import {caseView,demo,did} from './fixtures';

afterEach(()=>{cleanup();localStorage.clear();vi.restoreAllMocks();});
const ids=['case-a','case-b','case-c'];
const summary=(id:string)=>({...caseView,id,client:`Client ${id}`,currency:'INR',due_at:null,has_previous_investigation:false,balance:null,balance_label:'UNKNOWN_REMAINDER',recommended_action:null,review_at:null});
const reply=(value:unknown,status=200)=>new Response(JSON.stringify({schema_version:'1',...(value as object)}),{status});
function fakeApi({failing}:{failing?:string}={}) {
  const calls={list:0,views:[] as string[],copies:[demo] as typeof demo[]};
  const api=new ApiClient(async input=>{
    const url=String(input);
    if(url.endsWith('/health'))return reply({ready:true,agent_mode:'STUB'});
    if(url.endsWith('/catalogue'))return reply({catalogue_version:'release-0.1',variant_ids:[]});
    if(url.endsWith('/demonstrations'))return reply({demonstrations:calls.copies});
    if(url.endsWith('/cases')){calls.list++;return reply({demonstration_id:did,clock_mode:'REFERENCE',evaluation_at:caseView.evaluation_at,cases:ids.map(summary)});}
    const match=/\/cases\/([^/?]+)\?/.exec(url);
    if(match){
      calls.views.push(match[1]);
      if(match[1]===failing)return reply({error:{code:'STORAGE_UNAVAILABLE',message:'Case unavailable'}},503);
      return reply({...caseView,id:match[1],client:`Client ${match[1]}`});
    }
    return reply({});
  });
  return {api,calls};
}

it('loads the case list and then every saved case view for the selected workspace',async()=>{
  const {api,calls}=fakeApi();
  const {result}=renderHook(()=>useWorkspace(api));
  await waitFor(()=>expect(result.current.cases.length===3&&result.current.cases.every(entry=>entry.view)).toBe(true));
  expect(result.current.selected).toBe(did);
  expect(result.current.list?.cases.map(item=>item.id)).toEqual(ids);
  expect(result.current.cases.map(entry=>entry.view?.client)).toEqual(['Client case-a','Client case-b','Client case-c']);
  expect(result.current.detailsLoading).toBe(false);
  expect(result.current.health?.agent_mode).toBe('STUB');
  expect(result.current.imported).toBe(false);
  expect(result.current.evaluationAt).toBe(caseView.evaluation_at);
  expect(calls.views.sort()).toEqual([...ids].sort());
});

it('keeps a failing case visible with its error while the other cases still load',async()=>{
  const {api}=fakeApi({failing:'case-b'});
  const {result}=renderHook(()=>useWorkspace(api));
  await waitFor(()=>expect(result.current.detailsLoading).toBe(false));
  await waitFor(()=>expect(result.current.cases).toHaveLength(3));
  const [a,b,c]=result.current.cases;
  expect(a.view?.id).toBe('case-a');expect(a.error).toBeNull();
  expect(b.view).toBeNull();expect(b.error).toBe('Case unavailable');expect(b.summary.id).toBe('case-b');
  expect(c.view?.id).toBe('case-c');expect(c.error).toBeNull();
});

it('refetches the list and every case view on refresh',async()=>{
  const {api,calls}=fakeApi();
  const {result}=renderHook(()=>useWorkspace(api));
  await waitFor(()=>expect(result.current.cases.length===3&&result.current.cases.every(entry=>entry.view)).toBe(true));
  expect(calls.list).toBe(1);expect(calls.views).toHaveLength(3);
  const tick=result.current.refreshTick;
  act(()=>result.current.refresh());
  expect(result.current.refreshTick).toBe(tick+1);
  await waitFor(()=>expect(calls.views).toHaveLength(6));
  expect(calls.list).toBe(2);
  await waitFor(()=>expect(result.current.detailsLoading).toBe(false));
});

it('clears the selection when a deletion of the selected workspace commits',async()=>{
  localStorage.setItem('selected_demonstration_id',did);
  const {api,calls}=fakeApi();
  const {result}=renderHook(()=>useWorkspace(api));
  await waitFor(()=>expect(result.current.list).not.toBeNull());
  const remaining={...demo,id:'remaining-copy'};calls.copies=[remaining];
  act(()=>completePending(did,'case-a',{kind:'deletion',path:`/demonstrations/${did}/deletion`,operation:{schema_version:'1',operation_id:'delete-one'}},{schema_version:'1',receipt:{operation_id:'delete-one',operation_type:'DELETE_DEMONSTRATION',target_id:did,committed_at:caseView.evaluation_at,outcome:'DELETED',case_revision:null}}));
  expect(result.current.selected).toBeNull();
  expect(result.current.list).toBeNull();
  expect(result.current.cases).toEqual([]);
  expect(localStorage.getItem('selected_demonstration_id')).toBeNull();
  // Rediscovery then applies the usual rule: the sole remaining copy is selected and remembered.
  await waitFor(()=>expect(result.current.discovering).toBe(false));
  await waitFor(()=>expect(result.current.selected).toBe('remaining-copy'));
  expect(result.current.copies.map(copy=>copy.id)).toEqual(['remaining-copy']);
  expect(localStorage.getItem('selected_demonstration_id')).toBe('remaining-copy');
});

it('selecting another workspace stores it and drops the previous list',async()=>{
  const {api}=fakeApi();
  const {result}=renderHook(()=>useWorkspace(api));
  await waitFor(()=>expect(result.current.list).not.toBeNull());
  act(()=>result.current.select('other-copy'));
  expect(result.current.selected).toBe('other-copy');
  expect(localStorage.getItem('selected_demonstration_id')).toBe('other-copy');
  expect(result.current.list).toBeNull();
  expect(result.current.cases).toEqual([]);
});
