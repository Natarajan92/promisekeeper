import {afterEach,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,screen,waitFor,within} from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import App from '../src/App';
import {ApiClient} from '../src/api/client';
import {caseView,cid,demo,did} from './fixtures';

// Selected-copy deletion lives only in the shell's Workspace switcher; its pending record uses the workspace scope.
afterEach(()=>{cleanup();localStorage.clear();vi.restoreAllMocks();window.location.hash='';});
const workspaceKey=`promisekeeper.pending.${did}.workspace`;
const reply=(value:unknown,status=200)=>new Response(JSON.stringify({schema_version:'1',...(value as object)}),{status});
const deletedReceipt=(operationId:string)=>({receipt:{operation_id:operationId,operation_type:'DELETE_DEMONSTRATION',target_id:did,committed_at:caseView.evaluation_at,outcome:'DELETED',case_revision:null}});
function deletionApp({post='commit',lookup='absent'}:{post?:'commit'|'lost'|'lost-then-commit';lookup?:'absent'|'committed'}={}) {
  let copies=[demo];const posts:Record<string,any>[]=[];let committed:string|null=null;
  const api=new ApiClient(async(input,init)=>{
    const url=String(input);
    if(init?.body){
      const body=JSON.parse(init.body as string);posts.push(body);
      if(post==='lost'||(post==='lost-then-commit'&&posts.length===1)){if(lookup==='committed'){committed=body.operation_id;copies=[];}throw new Error('Lost response');}
      committed=body.operation_id;copies=[];return reply(deletedReceipt(body.operation_id));
    }
    if(url.includes('/operations/'))return committed&&url.includes(committed)?reply(deletedReceipt(committed)):reply({error:{code:'NOT_RECORDED',message:'Not recorded'}},404);
    if(url.endsWith('/health'))return reply({ready:true,agent_mode:'STUB'});
    if(url.endsWith('/catalogue'))return reply({catalogue_version:'release-0.1',variant_ids:[],events:[{id:'U1',kind:'CLOCK',eligible_variant_ids:[null],case_id:'PK-001',evaluation_at:caseView.evaluation_at}]});
    if(url.endsWith('/demonstrations'))return reply({demonstrations:copies});
    if(url.endsWith('/cases'))return reply({demonstration_id:did,clock_mode:'REFERENCE',evaluation_at:caseView.evaluation_at,cases:[{...caseView,currency:'INR',due_at:null,has_previous_investigation:false,balance:null,balance_label:'UNKNOWN_REMAINDER',recommended_action:null,review_at:null}]});
    if(url.includes('/history'))return reply({events:[],next_cursor:null});
    if(url.includes('/morning-reviews/latest'))return reply({morning_review:null});
    return reply(caseView);
  });
  return {api,posts};
}
const openSwitcher=()=>fireEvent.click(screen.getByRole('button',{name:/^Workspace/}));
function confirmDeletion() {
  fireEvent.click(screen.getByRole('button',{name:'Review selected-copy deletion'}));
  expect(screen.getByRole('button',{name:'Delete this demonstration'})).toBeDisabled();
  fireEvent.click(screen.getByLabelText('Confirm deletion of this selected demonstration'));
}

it('requires explicit confirmation before selected-copy deletion and reports only committed deletion',async()=>{
  const app=deletionApp();render(<App api={app.api}/>);
  await screen.findByRole('heading',{level:1,name:'Your payment casebook'});
  await waitFor(()=>expect(screen.getByRole('button',{name:/^Workspace/})).toBeEnabled());
  openSwitcher();confirmDeletion();
  expect(app.posts).toHaveLength(0);
  fireEvent.click(screen.getByRole('button',{name:'Delete this demonstration'}));
  await screen.findByText('Selected demonstration deleted.');
  expect(localStorage.getItem(workspaceKey)).toBeNull();
  expect(app.posts).toHaveLength(1);expect(app.posts[0]).toMatchObject({confirmed_demonstration_id:did,confirm:true});
  // The committed deletion clears the selection and rediscovers without creating a replacement.
  expect(await screen.findByText(/No saved demonstrations/)).toBeInTheDocument();
  expect(localStorage.getItem('selected_demonstration_id')).toBeNull();
  expect(app.posts).toHaveLength(1);
});

it('keeps the switcher deletion locked while a case request is pending, at render and at click time',async()=>{
  localStorage.setItem(`promisekeeper.pending.${did}.${cid}`,JSON.stringify({kind:'closure',path:'/closure',operation:{schema_version:'1',operation_id:'case-operation'}}));
  const app=deletionApp();const {unmount}=render(<App api={app.api}/>);
  await waitFor(()=>expect(screen.getByRole('button',{name:/^Workspace/})).toBeEnabled());
  await screen.findByRole('region',{name:'Still to collect'});
  openSwitcher();
  expect(screen.getByRole('button',{name:'Review selected-copy deletion'})).toBeDisabled();
  unmount();localStorage.clear();
  localStorage.setItem(`promisekeeper.operation.${did}.${cid}.investigation`,JSON.stringify({schema_version:'1',operation_id:'start-operation'}));
  render(<App api={app.api}/>);
  await waitFor(()=>expect(screen.getByRole('button',{name:/^Workspace/})).toBeEnabled());
  await screen.findByRole('region',{name:'Still to collect'});
  openSwitcher();
  expect(screen.getByRole('button',{name:'Review selected-copy deletion'})).toBeDisabled();
  cleanup();localStorage.clear();
  render(<App api={app.api}/>);
  await waitFor(()=>expect(screen.getByRole('button',{name:/^Workspace/})).toBeEnabled());
  await screen.findByRole('region',{name:'Still to collect'});
  openSwitcher();confirmDeletion();
  // Retained by another tab after this control rendered: no notification reaches it, so the click re-checks.
  localStorage.setItem(`promisekeeper.pending.${did}.${cid}`,JSON.stringify({kind:'closure',path:'/closure',operation:{schema_version:'1',operation_id:'late-operation'}}));
  fireEvent.click(screen.getByRole('button',{name:'Delete this demonstration'}));
  expect(screen.getByRole('alert')).toHaveTextContent('Reconcile the pending case request before deleting this copy.');
  expect(app.posts).toHaveLength(0);expect(localStorage.getItem(workspaceKey)).toBeNull();
});

it('keeps an uncertain deletion pending until its committed receipt is found',async()=>{
  const app=deletionApp({post:'lost',lookup:'committed'});render(<App api={app.api}/>);
  await waitFor(()=>expect(screen.getByRole('button',{name:/^Workspace/})).toBeEnabled());
  await screen.findByRole('region',{name:'Still to collect'});
  openSwitcher();confirmDeletion();fireEvent.click(screen.getByRole('button',{name:'Delete this demonstration'}));
  await screen.findByText(/Connection unavailable/);
  expect(screen.queryByText('Selected demonstration deleted.')).not.toBeInTheDocument();
  expect(localStorage.getItem(workspaceKey)).toContain(app.posts[0].operation_id);
  const notice=screen.getByRole('region',{name:'Pending demonstration deletion'});
  fireEvent.click(within(notice).getByRole('button',{name:'Check saved request outcome'}));
  await screen.findByText('Selected demonstration deleted.');
  expect(localStorage.getItem(workspaceKey)).toBeNull();
  expect(app.posts).toHaveLength(1);
});

it('an uncertain deletion stays visible outside the switcher, locks case commands, and its exact retry completes',async()=>{
  window.location.hash=`#/cases/${cid}?section=history`;
  const app=deletionApp({post:'lost-then-commit'});render(<App api={app.api}/>);
  await screen.findByRole('heading',{level:1,name:'Studio North'});
  expect(screen.getByRole('button',{name:'Investigate case'})).toBeEnabled();
  await waitFor(()=>expect(screen.getByRole('button',{name:'Preview selected fictional update'})).toBeEnabled());
  openSwitcher();confirmDeletion();fireEvent.click(screen.getByRole('button',{name:'Delete this demonstration'}));
  await screen.findByText(/Connection unavailable/);
  openSwitcher();
  expect(screen.queryByRole('button',{name:'Delete this demonstration'})).not.toBeInTheDocument();
  const notice=screen.getByRole('region',{name:'Pending demonstration deletion'});
  expect(notice).toHaveTextContent('case actions stay locked');
  // Every case command in this copy is fenced while the deletion outcome is unknown.
  expect(screen.getByRole('button',{name:'Investigate case'})).toBeDisabled();
  expect(screen.getByRole('button',{name:'Preview selected fictional update'})).toBeDisabled();
  expect(screen.getAllByText('A request is pending for this copy and case. Its exact payload is retained.').length).toBeGreaterThan(0);
  fireEvent.click(within(notice).getByRole('button',{name:'Retry original request'}));
  await screen.findByText('Selected demonstration deleted.');
  expect(app.posts).toHaveLength(2);expect(app.posts[1]).toEqual(app.posts[0]);
  expect(localStorage.getItem(workspaceKey)).toBeNull();
  await waitFor(()=>expect(localStorage.getItem('selected_demonstration_id')).toBeNull());
  expect(await screen.findByRole('heading',{level:1,name:"This case isn't in the current workspace"})).toBeInTheDocument();
});
