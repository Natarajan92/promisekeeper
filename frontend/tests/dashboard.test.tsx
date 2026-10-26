import {afterEach,expect,it} from 'vitest';
import {cleanup,render,screen,within} from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import App from '../src/App';
import {ApiClient} from '../src/api/client';
import type {CaseSummary} from '../src/api/types';
import {collectTotals} from '../src/dashboard/totals';
import {caseView,demo,did} from './fixtures';

afterEach(()=>{cleanup();localStorage.clear();window.location.hash='';});

const inr=(rupees:number)=>({currency:'INR' as const,minor_units:String(rupees*100)});
function summary(id:string,client:string,extra:Partial<CaseSummary>):CaseSummary {
  return {id,catalogue_case_id:id.toUpperCase(),client,invoice_id:`INV-${id}`,currency:'INR',due_text:'10 October 2026',due_at:'2026-10-10T18:30:00Z',lifecycle:'OPEN',case_revision:0,
    has_previous_investigation:false,review_required:false,balance:inr(0),balance_label:'VERIFIED_REMAINDER',recommended_action:null,review_at:null,...extra};
}
const verified=summary('a','Northstar Analytics',{balance:inr(80_000),balance_label:'VERIFIED_REMAINDER',recommended_action:'FOLLOW_UP'});
const recorded=summary('b','Cedar Retail Labs',{balance:inr(12_000),balance_label:'RECORDED_REMAINDER',recommended_action:'VERIFY_PAYMENT'});
const unknown=summary('c','Lotus Interiors',{balance:null,balance_label:'UNKNOWN_REMAINDER',recommended_action:'WAIT'});
const dollars=summary('d','Overseas Client',{currency:'USD',balance:{currency:'USD',minor_units:'50000'} as never,balance_label:'VERIFIED_REMAINDER',recommended_action:'WAIT'});
const closed=summary('e','Banyan Logistics',{lifecycle:'CLOSED',balance:inr(99_999),balance_label:'VERIFIED_REMAINDER',recommended_action:'CLOSE'});

it('sums only known INR open balances and counts unknown and other currencies separately',()=>{
  expect(collectTotals([verified,recorded])).toEqual({inrMinor:9_200_000n,recordedMinor:1_200_000n,unknownCount:0,otherCurrencyCount:0});
  expect(collectTotals([verified,unknown]).unknownCount).toBe(1);
  expect(collectTotals([verified,unknown]).inrMinor).toBe(8_000_000n);
  expect(collectTotals([verified,dollars]).otherCurrencyCount).toBe(1);
  expect(collectTotals([verified,dollars]).inrMinor).toBe(8_000_000n);
  expect(collectTotals([verified,closed])).toEqual({inrMinor:8_000_000n,recordedMinor:0n,unknownCount:0,otherCurrencyCount:0});
  expect(collectTotals([])).toEqual({inrMinor:0n,recordedMinor:0n,unknownCount:0,otherCurrencyCount:0});
});

function dashboardApi(cases:CaseSummary[]) {
  return new ApiClient(async input=>{
    const url=String(input);
    const view=(id:string)=>{const item=cases.find(entry=>url.includes(`/cases/${entry.id}`))??cases[0];return {...caseView,id:item?.id??id,client:item?.client,lifecycle:item?.lifecycle??'OPEN'};};
    const body=url.endsWith('/health')?{ready:true,agent_mode:'STUB'}:url.endsWith('/catalogue')?{catalogue_version:'release-0.1',variant_ids:[]}:url.endsWith('/demonstrations')?{demonstrations:[demo]}
      :url.endsWith('/cases')?{demonstration_id:did,clock_mode:'REFERENCE',evaluation_at:caseView.evaluation_at,cases}
      :url.includes('/morning-reviews/latest')?{morning_review:null}:view('x');
    return new Response(JSON.stringify({schema_version:'1',...body}));
  });
}

it('shows the still-to-collect total with its recorded, unknown and other-currency notes',async()=>{
  render(<App api={dashboardApi([verified,recorded,unknown,dollars,closed])}/>);
  const total=await screen.findByRole('region',{name:'Still to collect'});
  expect(within(total).getByText('₹92,000.00')).toBeInTheDocument();
  expect(within(total).getByText('₹12,000.00 of this is recorded but not yet verified')).toBeInTheDocument();
  expect(within(total).getByText('plus 1 with unknown balance')).toBeInTheDocument();
  expect(within(total).getByText('1 in other currencies')).toBeInTheDocument();
  expect(screen.getByRole('button',{name:'Start morning review'})).toBeInTheDocument();
  expect(screen.getAllByRole('heading',{level:1})).toHaveLength(1);
});

it('never shows an unknown-only workspace as zero rupees',async()=>{
  render(<App api={dashboardApi([unknown])}/>);
  const total=await screen.findByRole('region',{name:'Still to collect'});
  expect(within(total).queryByText('₹0.00')).not.toBeInTheDocument();
  expect(within(total).getByText('Unknown')).toBeInTheDocument();
  expect(within(total).getByText('plus 1 with unknown balance')).toBeInTheDocument();
});

it('links every Follow up today row to its case page, in attention order',async()=>{
  render(<App api={dashboardApi([unknown,verified,recorded,closed])}/>);
  const list=await screen.findByRole('list',{name:'Follow up today'});
  const links=within(list).getAllByRole('link');
  expect(links.map(link=>link.getAttribute('href'))).toEqual(['#/cases/a','#/cases/b']);
  expect(links[0]).toHaveTextContent('Northstar Analytics');
  expect(links[0]).toHaveTextContent('₹80,000.00');
  expect(within(list).queryByText('Banyan Logistics')).not.toBeInTheDocument();
});

it('counts follow-ups and payment checks from the case list',async()=>{
  render(<App api={dashboardApi([verified,recorded,unknown,closed])}/>);
  const tiles=await screen.findByRole('list',{name:'Today at a glance'});
  expect(within(tiles).getByText('Follow-ups due').closest('li')).toHaveTextContent('1');
  expect(within(tiles).getByText('Payments to verify').closest('li')).toHaveTextContent('1');
});

it('greets an empty workspace with the upload starting point',async()=>{
  render(<App api={dashboardApi([])}/>);
  expect(await screen.findByRole('heading',{name:'Start by uploading your records'})).toBeInTheDocument();
  expect(screen.getByRole('link',{name:'Upload your records'})).toHaveAttribute('href','#/upload');
  expect(screen.queryByRole('region',{name:'Still to collect'})).not.toBeInTheDocument();
});
