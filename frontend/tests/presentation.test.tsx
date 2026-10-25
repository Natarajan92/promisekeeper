import {afterEach,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,screen,within} from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import {ApiClient} from '../src/api/client';
import {DemonstrationPicker} from '../src/cases/DemonstrationPicker';
import {CaseHistory} from '../src/history/CaseHistory';
import {WhatChanged} from '../src/investigations/WhatChanged';
import {before,after,attempt,completed,comparisonView} from './comparisonFixtures';
import {demo,source} from './fixtures';

afterEach(()=>{cleanup();localStorage.clear();vi.restoreAllMocks();});

it('distinguishes friendly copy choices with identical dates and preserves the selected exact identity without writes',()=>{
  const onSelect=vi.fn(),fetcher=vi.fn();const other={...demo,id:'11111111-1111-4111-8111-111111111112'};
  render(<DemonstrationPicker api={new ApiClient(fetcher)} copies={[demo,other]} selected={other.id} catalogue={null} onSelect={onSelect} onCreated={()=>{}}/>);
  const picker=screen.getByLabelText('Demonstration copy');const options=within(picker).getAllByRole('option').slice(1);
  expect(options[0]).toHaveTextContent('1. Standard payment examples');expect(options[1]).toHaveTextContent('2. Standard payment examples');
  expect(options[1]).toHaveTextContent('Fixed sample date');fireEvent.change(picker,{target:{value:demo.id}});expect(onSelect).toHaveBeenCalledWith(demo.id);
  fireEvent.click(screen.getByText('Saved copy details'));expect(screen.getByText(other.id)).toBeVisible();expect(fetcher).not.toHaveBeenCalled();
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
