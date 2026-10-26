import {afterEach,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,screen,within} from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import {ApiClient} from '../src/api/client';
import {WorkspacePicker} from '../src/cases/WorkspacePicker';
import {CaseHistory} from '../src/history/CaseHistory';
import {WhatChanged} from '../src/investigations/WhatChanged';
import {before,after,attempt,completed,comparisonView} from './comparisonFixtures';
import {demo,source} from './fixtures';

afterEach(()=>{cleanup();localStorage.clear();vi.restoreAllMocks();});

it('distinguishes friendly copy choices with identical dates and preserves the selected exact identity without writes',()=>{
  const onSelect=vi.fn();const other={...demo,id:'11111111-1111-4111-8111-111111111112'};
  render(<WorkspacePicker workspaces={[demo,other]} selected={other.id} onSelect={onSelect}/>);
  const picker=screen.getByLabelText('Workspace');const options=within(picker).getAllByRole('option').slice(1);
  expect(picker).toHaveValue(other.id);
  expect(options[0]).toHaveTextContent('1. Saved workspace');expect(options[1]).toHaveTextContent('2. Saved workspace');
  fireEvent.change(picker,{target:{value:demo.id}});expect(onSelect).toHaveBeenCalledWith(demo.id);
  fireEvent.click(screen.getByText('Workspace details'));expect(screen.getByText(`Workspace ID: ${other.id}`)).toBeVisible();expect(onSelect).toHaveBeenCalledTimes(1);
});
it('loads ascending history through its human label while preserving the exact event code and payload on demand',()=>{
  const onMore=vi.fn(),fetcher=vi.fn();
  render(<CaseHistory api={new ApiClient(fetcher)} view={comparisonView} events={[completed('before',1)]} cursor={50} onMore={onMore} onSource={()=>{}}/>);
  expect(screen.getByText('Recommendation saved')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button',{name:'Load more history'}));expect(onMore).toHaveBeenCalledOnce();
  fireEvent.click(screen.getByText('Event details'));expect(screen.getByText('Recorded event: INVESTIGATION_COMPLETED')).toBeVisible();
  expect(screen.getByText(/"investigation_id": "before"/)).toBeVisible();expect(fetcher).not.toHaveBeenCalled();
});
it('uses readable completion labels and source versions without changing comparison identities or initiating writes',async()=>{
  const methods:string[]=[],onSource=vi.fn();
  const api=new ApiClient(async(url,init)=>{
    methods.push(init?.method??'GET');
    return Response.json(String(url).includes('/history')?{schema_version:'1',events:[completed('before',1),completed('after',2)],next_cursor:null}:attempt(String(url).includes('/before?')?before:after));
  });
  render(<WhatChanged api={api} view={{...comparisonView,evidence:[{...source,id:'settlement',stable_source_id:'PK-003-L2',version:2}] as typeof comparisonView.evidence}} onSource={onSource}/>);
  fireEvent.click(screen.getByRole('button',{name:'Compare saved investigations'}));await screen.findByText('Recommendation changed');
  const earlier=screen.getByLabelText('Earlier investigation');
  expect(within(earlier).getByRole('option',{name:/Saved result 1.*completed/i})).toHaveValue('before');
  expect(screen.getByLabelText('Later investigation')).toHaveValue('after');
  fireEvent.click(screen.getByRole('button',{name:'Inspect later source PK-003-L2 / v2'}));expect(onSource).toHaveBeenCalledWith('settlement');
  fireEvent.click(screen.getByText('Exact evidence version'));expect(screen.getByText('settlement',{exact:true})).toBeVisible();
  expect(methods.every(method=>method==='GET')).toBe(true);
});
it('shows rupees with the symbol and Indian grouping while other currencies keep their code',async()=>{
  const {money}=await import('../src/components/format');
  expect(money({currency:'INR',minor_units:'23500075'})).toBe('₹2,35,000.75');
  expect(money({currency:'INR',minor_units:'-5000'})).toBe('-₹50.00');
  expect(money({currency:'INR',minor_units:'0'})).toBe('₹0.00');
  expect(money({currency:'USD',minor_units:'123400'})).toBe('USD 1,234.00');
  expect(money(null)).toBe('Unknown');
});
