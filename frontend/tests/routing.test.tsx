import {afterEach,expect,it} from 'vitest';
import {act,cleanup,renderHook} from '@testing-library/react';
import {parseRoute,routeHref,useRoute,type Route} from '../src/routing';

afterEach(()=>{cleanup();localStorage.clear();window.location.hash='';});

it('parses every page and falls back to the dashboard for unknown or empty hashes',()=>{
  expect(parseRoute('')).toEqual({page:'dashboard'});
  expect(parseRoute('#/')).toEqual({page:'dashboard'});
  expect(parseRoute('#/dashboard')).toEqual({page:'dashboard'});
  expect(parseRoute('#/nope')).toEqual({page:'dashboard'});
  expect(parseRoute('#main')).toEqual({page:'dashboard'});
  expect(parseRoute('#/cases')).toEqual({page:'cases'});
  expect(parseRoute('#/cases/x%2Fy')).toEqual({page:'case',caseId:'x/y'});
  expect(parseRoute('#/cases/abc?section=evidence')).toEqual({page:'case',caseId:'abc',section:'evidence'});
  expect(parseRoute('#/cases/abc?section=bogus')).toEqual({page:'case',caseId:'abc'});
  expect(parseRoute('#/cases/%E0%A4')).toEqual({page:'dashboard'});
  expect(parseRoute('#/upload')).toEqual({page:'upload'});
  expect(parseRoute('#/upload?step=3')).toEqual({page:'upload',step:3});
  expect(parseRoute('#/upload?step=9')).toEqual({page:'upload'});
  expect(parseRoute('#/assistant')).toEqual({page:'assistant'});
  expect(parseRoute('#/assistant?case=c1')).toEqual({page:'assistant',caseId:'c1'});
  expect(parseRoute('#/approvals')).toEqual({page:'approvals'});
  expect(parseRoute('#/approvals?item=reminder%3Ac1')).toEqual({page:'approvals',itemId:'reminder:c1'});
});

it('builds hrefs that round-trip through the parser',()=>{
  expect(routeHref({page:'case',caseId:'abc',section:'evidence'})).toBe('#/cases/abc?section=evidence');
  const hashes=['#/dashboard','#/upload','#/upload?step=3','#/cases','#/cases/x%2Fy','#/cases/abc?section=history','#/assistant','#/assistant?case=c1','#/approvals','#/approvals?item=reminder%3Ac1'];
  for(const hash of hashes)expect(routeHref(parseRoute(hash))).toBe(hash);
  const routes:Route[]=[{page:'dashboard'},{page:'cases'},{page:'case',caseId:'a b/c'},{page:'case',caseId:'z',section:'compare'},{page:'upload',step:6}];
  for(const route of routes)expect(parseRoute(routeHref(route))).toEqual(route);
});

it('follows hashchange and navigate pushes a new hash',async()=>{
  window.location.hash='#/cases';
  const {result}=renderHook(()=>useRoute());
  expect(result.current[0]).toEqual({page:'cases'});
  act(()=>result.current[1]({page:'case',caseId:'c1',section:'overview'}));
  expect(result.current[0]).toEqual({page:'case',caseId:'c1',section:'overview'});
  expect(window.location.hash).toBe('#/cases/c1?section=overview');
  await act(async()=>{window.location.hash='#/approvals';window.dispatchEvent(new HashChangeEvent('hashchange'));});
  expect(result.current[0]).toEqual({page:'approvals'});
});

it('treats a repeated navigation to the same route as a fresh request',()=>{
  window.location.hash='#/cases/c1';
  const {result}=renderHook(()=>useRoute());
  const first=result.current[0];
  act(()=>result.current[1]({page:'case',caseId:'c1'}));
  expect(result.current[0]).toEqual(first);
  expect(result.current[0]).not.toBe(first);
});

// App-level routing behaviour: deep links, the shell tabs and the skip link.
import {fireEvent,render,screen,waitFor,within} from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import App from '../src/App';
import {ApiClient} from '../src/api/client';
import {caseView,cid,demo,did} from './fixtures';

const second='77777777-7777-4777-8777-777777777777';
function appApi(copies=[demo]) {
  return new ApiClient(async input=>{
    const url=String(input);
    const body=url.endsWith('/health')?{ready:true,agent_mode:'STUB'}:url.endsWith('/catalogue')?{catalogue_version:'release-0.1',variant_ids:[]}:url.endsWith('/demonstrations')?{demonstrations:copies}
      :url.endsWith('/cases')?{demonstration_id:url.includes(second)?second:did,clock_mode:'REFERENCE',evaluation_at:caseView.evaluation_at,cases:[{...caseView,demonstration_id:url.includes(second)?second:did,currency:'INR',due_at:null,has_previous_investigation:false,balance:null,balance_label:'UNKNOWN_REMAINDER',recommended_action:null,review_at:null},{...caseView,id:'closed-case',client:'Closed client',lifecycle:'CLOSED',currency:'INR',due_at:null,has_previous_investigation:false,balance:null,balance_label:'UNKNOWN_REMAINDER',recommended_action:null,review_at:null}]}
      :url.includes('/morning-reviews/latest')?{morning_review:null}:url.includes('/history')?{events:[],next_cursor:null}:{...caseView,demonstration_id:url.includes(second)?second:did};
    return new Response(JSON.stringify({schema_version:'1',...body}));
  });
}

it('explains a deep link to a case outside the current workspace instead of showing a blank page',async()=>{
  window.location.hash='#/cases/deleted-case';
  render(<App api={appApi()}/>);
  expect(await screen.findByRole('heading',{level:1,name:"This case isn't in the current workspace"})).toBeInTheDocument();
  const back=screen.getByRole('link',{name:'Back to Cases'});
  expect(back).toHaveAttribute('href','#/cases');
  fireEvent.click(back);
  expect(await screen.findByRole('heading',{level:1,name:'Cases'})).toBeInTheDocument();
  expect(window.location.hash).toBe('#/cases');
});

it('restores a refreshed case deep link without moving focus and marks the Cases tab current',async()=>{
  window.location.hash=`#/cases/${cid}`;
  render(<App api={appApi()}/>);
  const heading=await screen.findByRole('heading',{level:1,name:'Studio North'});
  expect(heading).not.toHaveFocus();
  expect(screen.getAllByRole('heading',{level:1})).toHaveLength(1);
  const tabs=within(screen.getByRole('navigation',{name:'Pages'}));
  await waitFor(()=>expect(tabs.getByRole('link',{name:'Cases 1'})).toHaveAttribute('aria-current','page'));
  expect(tabs.getByRole('link',{name:'Dashboard'})).not.toHaveAttribute('aria-current');
  expect(tabs.getByRole('link',{name:'Approvals'})).toHaveTextContent(/^Approvals$/);
});

it('opens a routed section and keeps the route when the skip link moves focus',async()=>{
  window.location.hash=`#/cases/${cid}?section=history`;
  render(<App api={appApi()}/>);
  await screen.findByRole('heading',{level:1,name:'Studio North'});
  expect(screen.getByRole('button',{name:'History'})).toHaveAttribute('aria-current','page');
  fireEvent.click(screen.getByRole('link',{name:'Skip to case workspace'}));
  expect(document.getElementById('main')).toHaveFocus();
  expect(window.location.hash).toBe(`#/cases/${cid}?section=history`);
  expect(screen.getByRole('heading',{level:1,name:'Studio North'})).toBeInTheDocument();
});

it('switching workspace from a case page returns to the Cases list of the new workspace',async()=>{
  localStorage.setItem('selected_demonstration_id',did);
  window.location.hash=`#/cases/${cid}`;
  render(<App api={appApi([demo,{...demo,id:second}])}/>);
  await screen.findByRole('heading',{level:1,name:'Studio North'});
  const toggle=screen.getByRole('button',{name:/^Workspace/});
  expect(toggle).toHaveAttribute('aria-expanded','false');
  expect(screen.queryByLabelText('Demonstration copy')).not.toBeInTheDocument();
  fireEvent.click(toggle);
  expect(toggle).toHaveAttribute('aria-expanded','true');
  expect(screen.getByRole('link',{name:'New upload workspace'})).toHaveAttribute('href','#/upload?step=1');
  expect(screen.getByText('Delete selected demonstration')).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('Demonstration copy'),{target:{value:second}});
  expect(await screen.findByRole('heading',{level:1,name:'Cases'})).toBeInTheDocument();
  expect(window.location.hash).toBe('#/cases');
  expect(localStorage.getItem('selected_demonstration_id')).toBe(second);
  expect(toggle).toHaveAttribute('aria-expanded','false');
});

// Controller ruling (Task 5 follow-up): the chooser never opens by itself; it stays one click away.
it('keeps the workspace chooser reachable, but closed, while no workspace is selected',async()=>{
  render(<App api={appApi([demo,{...demo,id:second}])}/>);
  expect(await screen.findByText('Choose a saved demonstration to inspect its cases.')).toBeInTheDocument();
  const toggle=screen.getByRole('button',{name:/^Workspace/});
  expect(toggle).toHaveAttribute('aria-expanded','false');expect(toggle).toBeEnabled();
  expect(screen.queryByLabelText('Demonstration copy')).not.toBeInTheDocument();
  fireEvent.click(toggle);
  expect(await screen.findByLabelText('Demonstration copy')).toBeInTheDocument();
  expect(toggle).toHaveAttribute('aria-expanded','true');
});
