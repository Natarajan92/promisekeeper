import {useCallback, useEffect, useState} from 'react';

// Hash routes survive a refresh because the backend serves only the built index for "/".
export type CaseSection='overview'|'evidence'|'history'|'compare';
export type Route={page:'dashboard'}|{page:'upload';step?:number}|{page:'cases'}|{page:'case';caseId:string;section?:CaseSection}|{page:'assistant';caseId?:string}|{page:'approvals';itemId?:string};

const SECTIONS:readonly CaseSection[]=['overview','evidence','history','compare'];
const STEPS=6;
const dashboard:Route={page:'dashboard'};

export function parseRoute(hash:string):Route {
  const raw=hash.startsWith('#')?hash.slice(1):hash;
  const split=raw.indexOf('?');
  const path=split<0?raw:raw.slice(0,split);
  const params=new URLSearchParams(split<0?'':raw.slice(split+1));
  if(!path.startsWith('/')&&path!=='')return {...dashboard};
  let parts:string[];
  try {parts=path.split('/').filter(Boolean).map(part=>decodeURIComponent(part));}
  catch {return {...dashboard};}
  const [page,id,...rest]=parts;
  if(rest.length)return {...dashboard};
  if(page===undefined||(page==='dashboard'&&id===undefined))return {...dashboard};
  if(page==='upload'&&id===undefined) {
    const step=Number(params.get('step'));
    return Number.isInteger(step)&&step>=1&&step<=STEPS?{page:'upload',step}:{page:'upload'};
  }
  if(page==='cases') {
    if(id===undefined)return {page:'cases'};
    const section=params.get('section') as CaseSection|null;
    return section&&SECTIONS.includes(section)?{page:'case',caseId:id,section}:{page:'case',caseId:id};
  }
  if(page==='assistant'&&id===undefined) {
    const caseId=params.get('case');
    return caseId?{page:'assistant',caseId}:{page:'assistant'};
  }
  if(page==='approvals'&&id===undefined) {
    const itemId=params.get('item');
    return itemId?{page:'approvals',itemId}:{page:'approvals'};
  }
  return {...dashboard};
}

const query=(name:string,value:string|number|undefined)=>value===undefined||value===''?'':`?${name}=${encodeURIComponent(String(value))}`;
export function routeHref(route:Route):string {
  switch(route.page) {
    case 'dashboard':return '#/dashboard';
    case 'upload':return `#/upload${query('step',route.step)}`;
    case 'cases':return '#/cases';
    case 'case':return `#/cases/${encodeURIComponent(route.caseId)}${query('section',route.section)}`;
    case 'assistant':return `#/assistant${query('case',route.caseId)}`;
    case 'approvals':return `#/approvals${query('item',route.itemId)}`;
  }
}

// The route parsed when the page loads is not an in-app navigation, so it never moves focus.
const loadedRoutes=new WeakSet<Route>();
export function isPageLoadRoute(route:Route):boolean {return loadedRoutes.has(route);}

export function useRoute():[Route,(route:Route)=>void] {
  const [route,setRoute]=useState<Route>(()=>{const initial=parseRoute(window.location.hash);loadedRoutes.add(initial);return initial;});
  useEffect(()=>{
    // Back/forward and typed hashes arrive here; an unchanged href keeps the current request object.
    function changed() {
      const next=parseRoute(window.location.hash);
      setRoute(old=>routeHref(old)===routeHref(next)?old:next);
    }
    window.addEventListener('hashchange',changed);
    return ()=>window.removeEventListener('hashchange',changed);
  },[]);
  // Each navigation is a fresh request, even to the current route, so pages can reset and refocus.
  const navigate=useCallback((next:Route)=>{
    const href=routeHref(next);
    if(window.location.hash!==href)window.location.hash=href;
    setRoute({...next});
  },[]);
  return [route,navigate];
}

// Anchor props for an in-app link: a plain click navigates in place; modified clicks keep browser behaviour.
export function routeLink(route:Route,navigate:(route:Route)=>void,after?:()=>void) {
  return {href:routeHref(route),onClick:(event:{button:number;metaKey:boolean;ctrlKey:boolean;shiftKey:boolean;altKey:boolean;preventDefault:()=>void})=>{
    if(event.button!==0||event.metaKey||event.ctrlKey||event.shiftKey||event.altKey)return;
    event.preventDefault();navigate(route);after?.();
  }};
}
