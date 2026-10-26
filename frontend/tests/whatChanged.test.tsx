import {afterEach,expect,it,vi} from 'vitest';
import {act,cleanup,fireEvent,render,screen,within} from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import {ApiClient} from '../src/api/client';
import type {Attempt,CaseView,HistoryEvent} from '../src/api/types';
import {WhatChanged} from '../src/investigations/WhatChanged';
import {FindingsView} from '../src/investigations/FindingsView';
import {CaseHistory} from '../src/history/CaseHistory';
import {before,after,attempt,completed,comparisonView} from './comparisonFixtures';
import {cid,did} from './fixtures';

afterEach(()=>{cleanup();vi.restoreAllMocks();});
function harness(options:{pages?:{events:HistoryEvent[];next_cursor:number|null}[];record?:(id:string)=>Attempt;delay?:Promise<void>}={}){
  const calls:{url:string;method:string}[]=[];let page=0;
  const api=new ApiClient(async(url,init)=>{
    calls.push({url:String(url),method:init?.method??'GET'});
    if(options.delay)await options.delay;
    if(String(url).includes('/history'))return Response.json({schema_version:'1',...(options.pages?.[page++]??{events:[completed('before',1),completed('after',2)],next_cursor:null})});
    const id=String(url).includes('/before?')?'before':'after';
    return Response.json(options.record?.(id)??attempt(id==='before'?before:after));
  });return {api,calls};
}
function open(){fireEvent.click(screen.getByRole('button',{name:'Compare saved investigations'}));}

it('loads only on request, shows Cedar before/after certainty, sources and originals using GETs only',async()=>{
  const {api,calls}=harness();const onSource=vi.fn();
  render(<WhatChanged api={api} view={comparisonView} onSource={onSource}/>);
  expect(calls).toHaveLength(0);open();await screen.findByText('Recommendation changed');
  expect(screen.getByText('Latest two completed investigations')).toBeInTheDocument();
  expect(screen.getByText(/Recorded remainder/)).toBeInTheDocument();expect(screen.getByText(/Verified remainder/)).toBeInTheDocument();
  expect(screen.getByText('₹60,000.00')).toBeInTheDocument();expect(screen.getByText('₹0.00')).toBeInTheDocument();
  expect(screen.getByText(/recorded remainder is contested/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button',{name:'Inspect later source PK-003-L2 / saved reference 1'}));expect(onSource).toHaveBeenCalledWith('settlement');
  fireEvent.click(screen.getByRole('button',{name:'Open earlier investigation'}));
  const original=screen.getByRole('heading',{name:'Earlier saved investigation'}).closest('article')!;
  expect(within(original).getByText(`Result hash ${before.result_hash}`)).toBeInTheDocument();
  expect(screen.queryByRole('button',{name:'Accept recommendation'})).not.toBeInTheDocument();
  expect(calls.every(call=>call.method==='GET'&&call.url.includes(`demonstration_id=${did}`))).toBe(true);
});
it.each([0,1])('explains when history contains %i completed results without fetching a fabricated pair',async(count)=>{
  const {api,calls}=harness({pages:[{events:count?[completed('after',1)]:[],next_cursor:null}]});
  render(<WhatChanged api={api} view={comparisonView} onSource={()=>{}}/>);open();
  await screen.findByText(/Two completed investigations are needed/);expect(calls).toHaveLength(1);
});
it('stops at three history pages, labels partial history, and loads only another page on explicit request',async()=>{
  const pages=[{events:[completed('before',1)],next_cursor:50},{events:[completed('after',51)],next_cursor:100},{events:[],next_cursor:150},{events:[completed('last',151)],next_cursor:null}];
  const {api,calls}=harness({pages,record:id=>attempt(id==='before'?before:after)});
  render(<WhatChanged api={api} view={comparisonView} onSource={()=>{}}/>);open();
  await screen.findByText(/Partial history/);expect(calls.filter(call=>call.url.includes('/history'))).toHaveLength(3);
  expect(screen.queryByText('Latest two completed investigations')).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button',{name:'Load more comparison history'}));
  expect(await within(screen.getByLabelText('Earlier investigation')).findByRole('option',{name:/Saved result 3/})).toHaveValue('last');expect(calls.filter(call=>call.url.includes('/history'))).toHaveLength(4);
});
it('orders by sequence across pages, omits failed attempts, and marks a new completed head historical',async()=>{
  const {api}=harness({pages:[{events:[completed('before',3)],next_cursor:50},{events:[{...completed('failed',90),event_type:'INVESTIGATION_INCOMPLETE'},completed('after',52)],next_cursor:null}]});
  const {rerender}=render(<WhatChanged api={api} view={{...comparisonView,running_attempt:'running'}} onSource={()=>{}}/>);open();await screen.findByText('Recommendation changed');
  expect(screen.getByText(/Newer attempt is still running/)).toBeInTheDocument();expect(screen.queryByRole('option',{name:/failed/})).not.toBeInTheDocument();
  rerender(<WhatChanged api={api} view={{...comparisonView,latest_completed_result:{...after,investigation_id:'new-head'}}} onSource={()=>{}}/>);
  expect(screen.getByText(/Historical comparison/)).toBeInTheDocument();
});
it.each(['copy','case','result','status'])('rejects a historical record with mismatched %s',async(mismatch)=>{
  const {api}=harness({record:id=>({...attempt(id==='before'?before:after),...(mismatch==='copy'?{demonstration_id:'other'}:mismatch==='case'?{case_id:'other'}:mismatch==='result'?{result:{...before,investigation_id:'wrong'}}:{status:'INCOMPLETE',result:null})}) as Attempt});
  render(<WhatChanged api={api} view={comparisonView} onSource={()=>{}}/>);open();
  await screen.findByRole('alert');expect(screen.queryByText('Recommendation changed')).not.toBeInTheDocument();
});
it('discards delayed reads on copy/case navigation',async()=>{
  let release!:()=>void;const delay=new Promise<void>(resolve=>{release=resolve;});const {api}=harness({delay});
  const {rerender}=render(<WhatChanged api={api} view={comparisonView} onSource={()=>{}}/>);open();
  rerender(<WhatChanged api={api} view={{...comparisonView,demonstration_id:'other-copy',id:'other-case'}} onSource={()=>{}}/>);
  await act(async()=>{release();await delay;});expect(screen.queryByText('Recommendation changed')).not.toBeInTheDocument();
  expect(screen.getByRole('button',{name:'Compare saved investigations'})).toBeInTheDocument();
});
it('keeps current Findings readable when comparison reads fail',async()=>{
  const api=new ApiClient(async()=>{throw new Error('offline');});
  render(<><FindingsView result={after} view={comparisonView} onSource={()=>{}}/><WhatChanged api={api} view={comparisonView} onSource={()=>{}}/></>);open();
  await screen.findByRole('alert');expect(screen.getByRole('heading',{name:'Review case closure'})).toBeInTheDocument();
});
it('opens an explicitly requested historical side and requires distinct ordered choices',async()=>{
  const {api}=harness();render(<WhatChanged api={api} view={comparisonView} onSource={()=>{}} initialInvestigationId="before"/>);
  await screen.findByText('Recommendation changed');
  expect(screen.getByRole('heading',{name:'What changed'})).toHaveFocus();
  fireEvent.change(screen.getByLabelText('Earlier investigation'),{target:{value:'after'}});
  await screen.findByText(/Choose two distinct investigations in completion order/);
  expect(screen.queryByText('Recommendation changed')).not.toBeInTheDocument();
});
it('shows a later incomplete attempt separately and preserves null money as unknown',async()=>{
  const {api}=harness({pages:[{events:[completed('before',1),completed('after',2),{...completed('failed',3),event_type:'INVESTIGATION_INCOMPLETE'}],next_cursor:null}],record:id=>attempt(id==='before'?{...before,financial_facts:{...before.financial_facts,certainty:'UNKNOWN',balance:null}}:after)});
  render(<WhatChanged api={api} view={comparisonView} onSource={()=>{}}/>);open();await screen.findByText('Recommendation changed');
  expect(screen.getByText(/A later investigation was incomplete/)).toBeInTheDocument();expect(within(screen.getByLabelText('Earlier saved values')).getByText('Unknown')).toBeInTheDocument();
});
it('explains external verification for Cedar while retaining the exact saved next step',()=>{
  render(<FindingsView result={before} view={{...comparisonView,current_result:before,latest_completed_result:before}} onSource={()=>{}}/>);
  expect(screen.getByText(before.next_step)).toBeInTheDocument();expect(screen.getByText(/Check your bank statement or accounting records outside PromiseKeeper/)).toBeInTheDocument();
  expect(screen.queryByText(/fictional settlement update/i)).not.toBeInTheDocument();
});
it('links a completed History record to comparison without starting another investigation',()=>{
  const {api,calls}=harness();const compare=vi.fn();
  render(<CaseHistory api={api} view={comparisonView} events={[completed('before',1)]} cursor={null} onMore={()=>{}} onSource={()=>{}} onCompare={compare}/>);
  fireEvent.click(screen.getByRole('button',{name:'Compare this investigation'}));expect(compare).toHaveBeenCalledWith('before');expect(calls).toHaveLength(0);
});
it('reports an explicitly requested result absent from loaded history instead of silently claiming to compare it',async()=>{
  const {api}=harness();render(<WhatChanged api={api} view={comparisonView} onSource={()=>{}} initialInvestigationId="missing"/>);
  await screen.findByText(/Requested investigation is not among the loaded completed records/);
});
it('labels the current and historical result regions with their own recommendation',async()=>{
  const {api}=harness();render(<><FindingsView result={after} view={comparisonView} onSource={()=>{}}/><WhatChanged api={api} view={comparisonView} onSource={()=>{}}/></>);
  open();await screen.findByText('Recommendation changed');fireEvent.click(screen.getByRole('button',{name:'Open earlier investigation'}));
  expect(within(screen.getByRole('region',{name:'Verify the payment'})).getByText(before.next_step)).toBeInTheDocument();
  expect(within(screen.getByRole('region',{name:'Review case closure'})).getByText(after.next_step)).toBeInTheDocument();
});
it.each([0,1])('allows selecting the first earlier record after loading from %i completions to two',async(count)=>{
  const {api}=harness({pages:[{events:[],next_cursor:50},{events:[],next_cursor:100},{events:count?[completed('before',101)]:[],next_cursor:150},{events:count?[completed('after',151)]:[completed('before',151),completed('after',152)],next_cursor:null}]});
  render(<WhatChanged api={api} view={comparisonView} onSource={()=>{}}/>);open();await screen.findByText(/Partial history/);
  fireEvent.click(screen.getByRole('button',{name:'Load more comparison history'}));
  const earlier=await screen.findByLabelText('Earlier investigation');
  expect(within(earlier).getByRole('option',{name:'Choose investigation'})).toHaveProperty('selected',true);
  fireEvent.change(earlier,{target:{value:'before'}});fireEvent.change(screen.getByLabelText('Later investigation'),{target:{value:'after'}});
  await screen.findByText('Recommendation changed');
});
