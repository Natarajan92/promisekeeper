import { execFile, spawn, type ChildProcess } from "node:child_process";
import { mkdirSync, readFileSync, appendFileSync } from "node:fs";
import type { FaultPreset } from './fixtures';
import { createServer } from "node:net";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { randomUUID } from "node:crypto";

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../..");

export async function isolatedServer(preferredPort = 0, workflowMode?:'draft-fails-once'|'rerun-fails'|'closed-conflict'|FaultPreset) {
  const port = await new Promise<number>(resolve => {
    const probe = createServer();
    probe.listen(preferredPort,"127.0.0.1",()=> {
      const address=probe.address();
      const selected=typeof address==="object"&&address ? address.port : 0;
      probe.close(()=>resolve(selected));
    });
    probe.on("error",error=>{throw error;});
  });
  const folder=path.join(repo,".runtime/e2e",randomUUID());
  mkdirSync(folder,{recursive:true});
  const databasePath=path.join(folder,"fresh.sqlite");
  const lifecycle=(event:string)=>appendFileSync(path.join(folder,'process.jsonl'),JSON.stringify({at:new Date().toISOString(),event,pid:process?.pid??null})+'\n');
  let process: ChildProcess | null=null;
  const url=`http://127.0.0.1:${port}`;
  async function start(mode:typeof workflowMode=workflowMode) {
    lifecycle(`start:${mode??'normal'}`);
    if(process&&process.exitCode===null&&process.signalCode===null)throw new Error('Isolated server already running');
    process=spawn(path.join(repo,"backend/.venv/Scripts/python.exe"),
      [path.join(repo,"tests/e2e/support/workflow_server.py"),"--port",String(port),"--mode",mode??'normal'],{
        cwd:repo,windowsHide:true,stdio:["pipe","ignore","ignore"],env:{...globalThis.process.env,PK_AGENT_MODE:"STUB",
          PK_DB_PATH:databasePath,PYTHONPATH:path.join(repo,"backend/tests/support")},
      });
    const until=Date.now()+10_000;
    while(Date.now()<until) {
      try { if((await fetch(url+"/api/v1/health",{signal:AbortSignal.timeout(500)})).ok){lifecycle('ready');return;} }catch{}
      if(process.exitCode!==null)throw new Error("Isolated backend exited before readiness");
      await new Promise(resolve=>setTimeout(resolve,50));
    }
    throw new Error("Isolated backend readiness timed out");
  }
  async function waitForExit(timeout=10_000) {
    const child=process;
    if(!child)throw new Error('No isolated process was started');
    const until=Date.now()+timeout;
    while(child.exitCode===null&&child.signalCode===null&&Date.now()<until)await new Promise(resolve=>setTimeout(resolve,20));
    if(child.exitCode===null&&child.signalCode===null)throw new Error('Isolated process did not exit at the selected fault boundary');
    return child.exitCode;
  }
  async function kill() {
    lifecycle('kill-requested');
    if(process&&process.exitCode===null&&process.signalCode===null) {
      if(!process.stdin)throw new Error('Owned backend control pipe is unavailable');
      process.stdin.write('KILL\n');
      await waitForExit();
      lifecycle('process-exited');
    }
    process=null;
    lifecycle('checking-unreachable');
    try {if((await fetch(url+'/api/v1/health',{signal:AbortSignal.timeout(500)})).ok)throw new Error('Killed isolated backend still answers health');}
    catch(error) {if(error instanceof Error&&error.message==='Killed isolated backend still answers health')throw error;}
    lifecycle('unreachable');
  }
  async function faultMetadata() {
    try {return JSON.parse(readFileSync(path.join(folder,'fault.json'),'utf8'));}
    catch(error:any) {if(error.code==='ENOENT')return {provider_calls:0,provider_returns:0};throw error;}
  }
  async function stop() {
    if(process&&process.exitCode===null&&process.signalCode===null) {
      lifecycle('stop-requested');process.stdin?.write('STOP\n');
      try {await waitForExit(3_000);}catch {await kill();return;}
    }
    await kill(); // Also confirms the listener disappeared after graceful exit.
  }
  // Fixture writes and byte inspections are restricted to this helper's stopped, fresh server.
  async function legacyFixture(mode:"seed"|"inspect", investigationIds:string[]) {
    if(process&&process.exitCode===null)throw new Error("Stop the isolated server before accessing its SQLite fixture");
    return new Promise<any>((resolve,reject)=>execFile(path.join(repo,"backend/.venv/Scripts/python.exe"),
      [path.join(repo,"tests/e2e/support/legacy_result.py"),databasePath,mode,...investigationIds],
      {cwd:repo,windowsHide:true,env:{...globalThis.process.env,PK_AGENT_MODE:"STUB",PYTHONPATH:path.join(repo,"backend/tests/support")}},
      (error,stdout,stderr)=>error?reject(new Error(stderr||error.message)):resolve(JSON.parse(stdout))));
  }
  return {url,start,stop,kill,waitForExit,faultMetadata,legacyFixture};
}
