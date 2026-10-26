import {afterEach,expect,it} from 'vitest';
import {cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import App from '../src/App';
import {ApiClient} from '../src/api/client';
import {caseView,cid,demo,did} from './fixtures';

afterEach(()=>{cleanup();localStorage.clear();window.location.hash='';});
const forbidden=/\bdemo(?:nstration)?s?\b|\bfictional\b|\bsample\b|course-demo|START-HERE|docs\//i;
function setup(hash:string,empty=false) {
  window.location.hash=hash;
  const calls:string[]=[];
  const api=new ApiClient(async(input,init)=>{
    const url=String(input);calls.push(`${init?.method??'GET'} ${url}`);
    const data=url.endsWith('/health')?{ready:true,agent_mode:'STUB'}:
      url.endsWith('/catalogue')?{catalogue_version:'release-0.1',variant_ids:[],events:[]}:
      url.endsWith('/demonstrations')?{demonstrations:empty?[]:[demo]}:
      url.endsWith('/cases')?{demonstration_id:did,clock_mode:'REFERENCE',evaluation_at:caseView.evaluation_at,cases:[{...caseView,currency:'INR',has_previous_investigation:false}]}:
      url.endsWith('/morning-reviews/latest')?{morning_review:null}:
      url.includes('/history')?{events:[],next_cursor:null}:
      url.includes('/intake')?{customers:[],cases:[],payments:[],documents:[],files:[],as_of:caseView.evaluation_at}:{...caseView,evidence:caseView.evidence.map(source=>({...source,data:{speaker:'Studio North'}}))};
    return Response.json({schema_version:'1',...data});
  });
  render(<App api={api}/>);
  return calls;
}

it.each(['#/dashboard','#/cases','#/assistant','#/approvals',`#/cases/${cid}`,...[1,2,3,4,5,6].map(n=>`#/upload?step=${n}`)])('uses product wording across %s and its workspace controls',async hash=>{
  setup(hash);
  await waitFor(()=>expect(screen.queryByText(/Loading saved workspaces|Loading saved workspaces/)).not.toBeInTheDocument());
  await screen.findByRole('button',{name:/^Workspace/});
  fireEvent.click(screen.getByRole('button',{name:/^Workspace/}));
  await screen.findByRole('combobox',{name:'Workspace'});
  expect(document.body.textContent).not.toMatch(forbidden);
  expect(screen.queryByRole('button',{name:/create.*demonstration/i})).not.toBeInTheDocument();
  expect(screen.getByText(/Internal verification environment/)).toBeInTheDocument();
  if(hash===`#/cases/${cid}`){
    fireEvent.click(await screen.findByRole('button',{name:'History'}));
    expect(document.body.textContent).not.toMatch(forbidden);
    expect(screen.queryByRole('button',{name:/Preview selected.*update/})).not.toBeInTheDocument();
  }
});

it('onboards through uploads without fixture reads or implicit writes',async()=>{
  const calls=setup('#/dashboard',true);
  await screen.findByRole('link',{name:'Upload your records'});
  fireEvent.click(screen.getByRole('button',{name:/^Workspace/}));
  await screen.findByText('No saved workspaces. Upload records to get started.');
  fireEvent.click(screen.getByRole('link',{name:'New workspace'}));
  await screen.findByRole('heading',{name:'Bring in your records'});
  expect(calls.some(call=>call.includes('/catalogue'))).toBe(false);
  expect(calls.every(call=>call.startsWith('GET '))).toBe(true);
  expect(document.querySelector('a[href*="/samples/"]')).toBeNull();
  expect(document.body.textContent).not.toMatch(forbidden);
});
