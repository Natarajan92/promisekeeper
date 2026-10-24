import { createServer } from 'node:http';
import { test, expect } from './support/test';
import { waitForInvestigation } from './support/scenarioEvents';

const unavailable = {schema_version:'1',error:{code:'STORAGE_UNAVAILABLE',message:'Storage unavailable',operation_id:null,retryable:true,blocking_reasons:[]}};

async function readServer(responses:{status:number;body:unknown}[]) {
  let reads=0;
  const server=createServer((request,response)=>{
    if(request.method!=='GET'||request.url!=='/status') {response.writeHead(405).end();return;}
    const next=responses[Math.min(reads++,responses.length-1)];
    response.writeHead(next.status,{'Content-Type':'application/json'}).end(JSON.stringify(next.body));
  });
  await new Promise<void>(resolve=>server.listen(0,'127.0.0.1',resolve));
  const address=server.address();
  if(!address||typeof address==='string')throw new Error('Missing loopback listener');
  return {url:`http://127.0.0.1:${address.port}/status`,reads:()=>reads,
    close:()=>new Promise<void>((resolve,reject)=>server.close(error=>error?reject(error):resolve()))};
}

test('investigation status waits through typed retryable GET failures and RUNNING before observing COMPLETE',async({request})=>{
  const server=await readServer([{status:503,body:unavailable},{status:503,body:unavailable},
    {status:200,body:{status:'RUNNING'}},{status:200,body:{status:'COMPLETE',result:{result_hash:'saved-result'}}}]);
  const errors:any[]=[];
  try {
    const observed=await waitForInvestigation(request,server.url,errors);
    expect(observed).toEqual({status:'COMPLETE',result:{result_hash:'saved-result'}});
    expect(server.reads()).toBe(4);
    expect(errors).toMatchObject([{http_status:503,code:'STORAGE_UNAVAILABLE'},{http_status:503,code:'STORAGE_UNAVAILABLE'}]);
  } finally {await server.close();}
});

for(const status of ['LIMITED','INCOMPLETE'])test(`investigation polling observes actual ${status} as terminal`,async({request})=>{
  const server=await readServer([{status:200,body:{status}}]);
  try {expect(await waitForInvestigation(request,server.url,[])).toEqual({status});}
  finally {await server.close();}
});

test('only unavailable status reads exhaust the original deadline without fabricating a terminal result',async({request})=>{
  const server=await readServer([{status:503,body:unavailable}]);const errors:any[]=[];
  try {
    await expect(waitForInvestigation(request,server.url,errors)).rejects.toThrow(/Timeout 10000ms/);
    expect(server.reads()).toBeGreaterThan(1);
    expect(errors).toHaveLength(server.reads());
  } finally {await server.close();}
});

for(const sample of [
  {name:'unknown status',status:200,body:{status:'UNOBSERVED'}},
  {name:'missing status',status:200,body:{}},
  {name:'unknown 503 code',status:503,body:{...unavailable,error:{...unavailable.error,code:'UNKNOWN'}}},
  {name:'nonretryable 503',status:503,body:{...unavailable,error:{...unavailable.error,retryable:false}}},
  {name:'unexpected HTTP error',status:400,body:unavailable},
])test(`investigation polling rejects ${sample.name} without treating it as terminal`,async({request})=>{
  const server=await readServer([sample]);
  try {await expect(waitForInvestigation(request,server.url,[])).rejects.toThrow();expect(server.reads()).toBe(1);}
  finally {await server.close();}
});
