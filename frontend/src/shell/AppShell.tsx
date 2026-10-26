import type {ReactNode} from 'react';
import {StatusBanner} from '../components/StatusBanner';
import {routeLink, type Route} from '../routing';
import type {PageProps} from '../store/useWorkspace';
import {useWorkspaceDeletion, WorkspaceDeletionNotice, WorkspaceSwitcher} from './WorkspaceSwitcher';

type TabPage='dashboard'|'upload'|'cases'|'assistant'|'approvals';
const TABS:{page:TabPage;label:string}[]=[{page:'dashboard',label:'Dashboard'},{page:'upload',label:'Upload'},{page:'cases',label:'Cases'},{page:'assistant',label:'Assistant'},{page:'approvals',label:'Approvals'}];

function activeTab(route:Route):TabPage {return route.page==='case'?'cases':route.page;}

// approvals: the Approvals badge count, or null while it is unknown (never shown as 0 while loading).
export function AppShell({ws,route,navigate,approvals=null,children}:PageProps&{approvals?:number|null;children:ReactNode}) {
  const open=ws.list?ws.list.cases.filter(item=>item.lifecycle==='OPEN').length:null;
  const badges:Partial<Record<TabPage,number|null>>={cases:open,approvals};
  const active=activeTab(route);
  const deletion=useWorkspaceDeletion(ws);
  return <>
    <a className="skip-link" href="#main" onClick={event=>{
      // The skip link must not change the route hash; it moves focus to the page content instead.
      event.preventDefault();const main=document.getElementById('main');main?.focus();main?.scrollIntoView?.({block:'start'});
    }}>Skip to case workspace</a>
    <header className="app-header top-bar">
      <a className="wordmark" {...routeLink({page:'dashboard'},navigate)}><span className="brand-mark" aria-hidden="true">p</span><span className="brand-name">PromiseKeeper<small>Evidence before action.</small></span></a>
      <nav className="page-tabs" aria-label="Pages"><ul>{TABS.map(tab=>{const badge=badges[tab.page];return <li key={tab.page}>
        <a {...routeLink({page:tab.page},navigate)} aria-current={active===tab.page?'page':undefined}>{tab.label}{badge!=null&&<> <span className="tab-badge">{badge}</span></>}</a>
      </li>;})}</ul></nav>
      <WorkspaceSwitcher ws={ws} route={route} navigate={navigate} deletion={deletion}/>
    </header>
    <StatusBanner imported={ws.imported} health={ws.health} clock={ws.list?.clock_mode}/>
    <main id="main" tabIndex={-1}>
      {ws.discovering&&<p role="status">Loading saved workspaces…</p>}
      {ws.discoveryError&&<div className="notice" role="alert"><p>{ws.discoveryError}</p><button onClick={()=>void ws.discover()}>Retry loading workspaces</button></div>}
      {ws.copies.length>1&&!ws.selected&&!ws.discoveryError&&<p className="empty-state">Choose a workspace to inspect its cases.</p>}
      <WorkspaceDeletionNotice deletion={deletion}/>
      {children}
    </main>
    <footer>No customer messages are sent. Copy approved messages to your own communication tool.</footer>
  </>;
}
