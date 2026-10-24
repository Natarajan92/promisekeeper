import { execFile, spawn, type ChildProcess } from "node:child_process";
import { mkdirSync } from "node:fs";
import { createServer } from "node:net";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { randomUUID } from "node:crypto";

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../..");

export async function isolatedServer(preferredPort = 0, workflowMode?:'draft-fails-once'|'rerun-fails'|'closed-conflict') {
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
  let process: ChildProcess | null=null;
  const url=`http://127.0.0.1:${port}`;
  async function start() {
    process=spawn(path.join(repo,"backend/.venv/Scripts/python.exe"),
      workflowMode?[path.join(repo,"tests/e2e/support/workflow_server.py"),"--port",String(port),"--mode",workflowMode]:["-m","promisekeeper.cli","serve","--port",String(port),"--workers","1"],{
        cwd:repo,windowsHide:true,stdio:"ignore",env:{...globalThis.process.env,PK_AGENT_MODE:"STUB",
          PK_DB_PATH:databasePath,PYTHONPATH:path.join(repo,"backend/tests/support")},
      });
    const until=Date.now()+10_000;
    while(Date.now()<until) {
      try { if((await fetch(url+"/api/v1/health",{signal:AbortSignal.timeout(500)})).ok)return; }catch{}
      if(process.exitCode!==null)throw new Error("Isolated backend exited before readiness");
      await new Promise(resolve=>setTimeout(resolve,50));
    }
    throw new Error("Isolated backend readiness timed out");
  }
  async function stop() {
    if(!process||process.exitCode!==null||process.signalCode!==null) {process=null;return;}
    const done=new Promise<void>(resolve=>process!.once("exit",()=>resolve()));
    process.kill();
    await done;
    process=null;
  }
  // Fixture writes and byte inspections are restricted to this helper's stopped, fresh server.
  async function legacyFixture(mode:"seed"|"inspect", investigationIds:string[]) {
    if(process&&process.exitCode===null)throw new Error("Stop the isolated server before accessing its SQLite fixture");
    return new Promise<any>((resolve,reject)=>execFile(path.join(repo,"backend/.venv/Scripts/python.exe"),
      [path.join(repo,"tests/e2e/support/legacy_result.py"),databasePath,mode,...investigationIds],
      {cwd:repo,windowsHide:true,env:{...globalThis.process.env,PK_AGENT_MODE:"STUB",PYTHONPATH:path.join(repo,"backend/tests/support")}},
      (error,stdout,stderr)=>error?reject(new Error(stderr||error.message)):resolve(JSON.parse(stdout))));
  }
  return {url,start,stop,legacyFixture};
}
