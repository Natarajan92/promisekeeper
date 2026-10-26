import {afterEach,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,screen,waitFor,within} from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import type {ApiClient} from '../src/api/client';
import type {AgentActivity,Health,MorningReviewView} from '../src/api/types';
import {AGENT_KIND,AGENT_LABEL,AGENT_ORDER,KIND_LABEL} from '../src/agents/agentLabels';
import {AssistantPage} from '../src/pages/AssistantPage';
import type {Workspace} from '../src/store/useWorkspace';
import {caseView,did} from './fixtures';

afterEach(()=>{cleanup();vi.restoreAllMocks();});

const health={schema_version:'1',ready:true,agent_mode:'LIVE',catalogue_version:'release-0.1',configuration:{model:'m',capability_available:true,agents:[
  {role:'Supervisor',provider:'NEBIUS',model:'example/planner-small',available:true,can_change:['which case is investigated next']},
  {role:'Extractor',provider:'NEBIUS',model:'example/extractor-large',available:true,can_change:[]},
  {role:'Memory',provider:'LOCAL',model:null,available:true,can_change:['client payment notes']}]}} as Health;
const row=(agent:AgentActivity['agent'],outcome:AgentActivity['outcome'],extra:Partial<AgentActivity>={}):AgentActivity=>({agent,event:'step',outcome,note:null,model:null,input_tokens:null,output_tokens:null,latency_ms:null,at:'2026-10-24T10:00:01Z',case_id:'c1',investigation_id:'inv-1',morning_review_id:null,...extra});
const review:MorningReviewView={schema_version:'1',id:'m1',demonstration_id:did,status:'COMPLETE',started_at:'2026-10-24T10:00:00Z',terminal_at:'2026-10-24T10:00:05Z',
  briefing:'Northstar needs a follow-up today.',briefing_source:'AGENT',failure_code:null,started_by:'OWNER',
  outcomes:[
    {case_id:'c2',client:'Meridian Studio',invoice_id:'MS-221',outcome:'SKIPPED',action:'WAIT',reason:'The saved recommendation is still current.',balance_text:null,review_at_text:null,draft_ready:false,priority:2,supervisor_reason:'Nothing changed since the last check.'},
    {case_id:'c1',client:'Northstar Analytics',invoice_id:'NS-104',outcome:'INVESTIGATED',action:'FOLLOW_UP',reason:null,balance_text:'INR 80,000.00',review_at_text:null,draft_ready:true,priority:1,supervisor_reason:'The promised date passed without a verified payment.'}],
  agent_activity:[row('SUPERVISOR','SUCCEEDED',{event:'Choose which cases need work',note:'Northstar first.',case_id:null,investigation_id:null,morning_review_id:'m1'})]};
const result={investigation_id:'inv-1',action:'FOLLOW_UP'};
const entry=(id:string,client:string,withResult=true)=>({summary:{...caseView,id,client,invoice_id:`INV-${id}`,currency:'INR',due_at:null,has_previous_investigation:false,balance:null,balance_label:'UNKNOWN_REMAINDER',recommended_action:null,review_at:null},
  view:{...caseView,id,client,latest_completed_result:withResult?{...result,investigation_id:`inv-${id.slice(1)}`}:null,current_result:withResult?result:null},error:null});
function fakeApi(latest:MorningReviewView|null=review) {
  const attempt={status:'COMPLETE',draft_status:'READY',agent_totals:{input_tokens:200,output_tokens:100,latency_ms:1200,cost_usd:null},agent_activity:[
    row('INTAKE','SUCCEEDED',{note:'Read 3 saved sources.'}),
    row('EXTRACTOR','SUCCEEDED',{note:'Found one promise.',model:'example/extractor-large',input_tokens:200,output_tokens:100,latency_ms:1200,recipient:'RULES_ENGINE',message_kind:'PAYMENT_CANDIDATES'}),
    row('RULES_ENGINE','SUCCEEDED',{note:'Follow up.'}),
    row('OWNER','WAITING')]};
  const api={latestMorningReview:vi.fn(async()=>({schema_version:'1',morning_review:latest})),attempt:vi.fn(async()=>attempt),
    startMorningReview:vi.fn(async()=>({...review,status:'RUNNING',briefing:null})),morningReview:vi.fn(async()=>review)} as unknown as ApiClient;
  return api;
}
function workspace(api:ApiClient,changes:Partial<Workspace>={}):Workspace {
  const cases=[entry('c1','Northstar Analytics'),entry('c2','Meridian Studio')];
  return {api,health,catalogue:null,copies:[],selected:did,imported:false,discovering:false,discoveryError:'',
    list:{schema_version:'1',demonstration_id:did,clock_mode:'REFERENCE',evaluation_at:caseView.evaluation_at,cases:cases.map(item=>item.summary)},
    evaluationAt:caseView.evaluation_at,plan:{},cases,detailsLoading:false,refreshTick:0,listLoading:false,listError:'',
    select:()=>{},discover:async()=>{},refresh:vi.fn(),setPlan:()=>{},...changes} as unknown as Workspace;
}

it('shows one card per pipeline step with AI or Rules tags and provider/model only where health has it',async()=>{
  render(<AssistantPage ws={workspace(fakeApi())} route={{page:'assistant'}} navigate={()=>{}}/>);
  expect(screen.getByRole('heading',{level:1,name:'Assistant at work'})).toBeInTheDocument();
  const team=screen.getByRole('list',{name:'Your digital team'});
  const cards=within(team).getAllByRole('listitem');
  expect(cards).toHaveLength(AGENT_ORDER.length);
  AGENT_ORDER.forEach((agent,index)=>{
    expect(cards[index]).toHaveTextContent(AGENT_LABEL[agent]);
    expect(within(cards[index]).getByText(KIND_LABEL[AGENT_KIND[agent]],{exact:true})).toHaveClass('kind-tag');
  });
  const card=(agent:keyof typeof AGENT_LABEL)=>cards[AGENT_ORDER.indexOf(agent)];
  expect(card('SUPERVISOR')).toHaveTextContent('Nebius · example/planner-small');
  expect(card('EXTRACTOR')).toHaveTextContent('Nebius · example/extractor-large');
  expect(card('MEMORY')).toHaveTextContent('local store');
  // No health entry: never invent a provider or model.
  expect(card('COMMUNICATOR')).not.toHaveTextContent(/Nebius|offline stand-in|example\//);
  for(const agent of ['INTAKE','RULES_ENGINE','SAFETY_CHECK'] as const){expect(card(agent)).toHaveTextContent('Rules (code)');expect(card(agent)).not.toHaveTextContent(/Nebius|example\//);}
  expect(AGENT_KIND.OWNER).toBe('YOU');expect(KIND_LABEL).toEqual({AI:'AI',RULES:'Rules (code)',YOU:'You'});
  await screen.findByRole('list',{name:"Today's plan"});
});

it("lists today's plan in the supervisor's order with its reasons",async()=>{
  render(<AssistantPage ws={workspace(fakeApi())} route={{page:'assistant'}} navigate={()=>{}}/>);
  const plan=await screen.findByRole('list',{name:"Today's plan"});
  const rows=within(plan).getAllByRole('listitem');
  expect(rows).toHaveLength(2);
  expect(rows[0]).toHaveTextContent('Northstar Analytics');
  expect(rows[0]).toHaveTextContent('The promised date passed without a verified payment.');
  expect(rows[1]).toHaveTextContent('Meridian Studio');
  expect(rows[1]).toHaveTextContent('Nothing changed since the last check.');
  expect(screen.getByRole('button',{name:'Start morning review'})).toBeEnabled();
});

it('invites a first morning check when none has run',async()=>{
  render(<AssistantPage ws={workspace(fakeApi(null))} route={{page:'assistant'}} navigate={()=>{}}/>);
  expect(await screen.findByRole('button',{name:'Start morning review'})).toBeEnabled();
  expect(screen.getByText(/No morning review has run/)).toBeInTheDocument();
});

it('runs a morning check, follows it and refreshes the shared store when done',async()=>{
  const api=fakeApi(null);const ws=workspace(api);
  render(<AssistantPage ws={ws} route={{page:'assistant'}} navigate={()=>{}}/>);
  fireEvent.click(await screen.findByRole('button',{name:'Start morning review'}));
  await waitFor(()=>expect(api.startMorningReview).toHaveBeenCalledTimes(1),{timeout:3000});
  await waitFor(()=>expect(ws.refresh).toHaveBeenCalled(),{timeout:4000});
  expect(await screen.findByRole('list',{name:"Today's plan"})).toBeInTheDocument();
});

it('uses the morning review itself, so its start-failure wording is identical to the Dashboard',async()=>{
  const api=fakeApi(null);
  (api.startMorningReview as unknown as {mockRejectedValue:(e:Error)=>void}).mockRejectedValue(new Error('Server busy'));
  render(<AssistantPage ws={workspace(api)} route={{page:'assistant'}} navigate={()=>{}}/>);
  fireEvent.click(await screen.findByRole('button',{name:'Start morning review'}));
  expect(await screen.findByText('Morning review not started: Server busy')).toBeInTheDocument();
  expect(api.latestMorningReview).toHaveBeenCalledTimes(1);
});

it('shows the step-by-step feed for a case with tags, and technical details only on request',async()=>{
  const api=fakeApi();
  render(<AssistantPage ws={workspace(api)} route={{page:'assistant',caseId:'c1'}} navigate={()=>{}}/>);
  const feed=await screen.findByRole('list',{name:'Steps for Northstar Analytics'});
  await waitFor(()=>expect(within(feed).getAllByRole('listitem')).toHaveLength(4));
  const steps=within(feed).getAllByRole('listitem');
  expect(steps[0]).toHaveTextContent('Evidence intake');expect(within(steps[0]).getByText('Rules (code)',{exact:true})).toHaveClass('kind-tag');expect(steps[0]).toHaveTextContent('Read 3 saved sources.');
  expect(steps[1]).toHaveTextContent('Promise extractor');expect(within(steps[1]).getByText('AI',{exact:true})).toHaveClass('kind-tag');expect(steps[1]).toHaveTextContent('→ Payment rules: promises and payment claims');
  expect(steps[3]).toHaveTextContent('Your approval');expect(steps[3]).toHaveTextContent('waiting for you');
  expect(api.attempt).toHaveBeenCalledWith(did,'inv-1');
  expect(screen.queryByText(/300 tokens/)).not.toBeInTheDocument();
  const details=screen.getByText('Show technical details').closest('details')!;
  details.open=true;fireEvent(details,new Event('toggle'));
  expect(await screen.findByText(/example\/extractor-large · 1\.2 s · 300 tokens/)).toBeInTheDocument();
  expect(screen.getByText(/Total: 1\.2 s · 300 tokens · cost not configured/)).toBeInTheDocument();
});

it('chooses another case for the step-by-step feed through the route',async()=>{
  const navigate=vi.fn();
  render(<AssistantPage ws={workspace(fakeApi())} route={{page:'assistant',caseId:'c1'}} navigate={navigate}/>);
  fireEvent.change(await screen.findByLabelText('Case to follow'),{target:{value:'c2'}});
  expect(navigate).toHaveBeenCalledWith({page:'assistant',caseId:'c2'});
});
