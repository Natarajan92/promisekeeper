import { useState } from 'react';
import { ApiClient, clearOperation, pendingOperation, stableOperation } from '../api/client';
import type { Catalogue, ClockMode, Demonstration } from '../api/types';
import { instant } from '../components/format';
export function DemonstrationPicker({api,copies,selected,catalogue,onSelect,onCreated}:{api:ApiClient;copies:Demonstration[];selected:string|null;catalogue:Catalogue|null;onSelect:(id:string)=>void;onCreated:(id:string)=>void}) {
  const [variant,setVariant]=useState('');const [clock,setClock]=useState<ClockMode>('REFERENCE');const [busy,setBusy]=useState(false);const [error,setError]=useState('');
  const pending=pendingOperation('new','new','creation');
  const selectedCopy=copies.find(copy=>copy.id===selected);
  async function create() {
    if(!catalogue)return;setBusy(true);setError('');
    try {
      const saved=pendingOperation('new','new','creation');
      // Creation cannot be scoped to a copy until a receipt returns its ID. Replay its exact idempotent command.
      const operation=saved ?? stableOperation('new','new','creation',{catalogue_version:catalogue.catalogue_version,variant_id:variant||null,clock_mode:clock});
      const response=await api.create(operation);
      if(!response.demonstration_id)throw new Error('Creation outcome needs reconciliation. Retry the original creation.');
      clearOperation('new','new','creation');onCreated(response.demonstration_id);
    }catch(reason){setError(reason instanceof Error?reason.message:'Creation outcome unknown. Retry the same operation.');}finally{setBusy(false);}
  }
  return <section className="demonstration-picker" aria-label="Saved demonstration selection"><div className="copy-selection">{copies.length>0?<><label htmlFor="saved-copy">Demonstration copy</label><select id="saved-copy" value={selected??''} onChange={event=>onSelect(event.target.value)}><option value="" disabled>Choose a saved copy</option>{copies.map((copy,index)=><option value={copy.id} key={copy.id}>{index+1}. {copy.selected_variant_id??'Standard payment examples'} · {copy.clock_mode==='REFERENCE'?'Fixed sample date':'Current date and time'} · saved {instant(copy.created_at)}</option>)}</select>{selectedCopy&&<details className="copy-reference"><summary>Saved copy details</summary><p>{selectedCopy.id}</p><p>Catalogue {selectedCopy.catalogue_version} · clock {selectedCopy.clock_mode}</p></details>}</>:<p>No saved demonstrations. Create a fictional copy to begin.</p>}</div><details className="create-copy" open={copies.length===0}><summary>Create another fictional copy</summary><div className="create-fields"><label>Sample scenario<select value={variant} disabled={!!pending||busy} onChange={event=>setVariant(event.target.value)}><option value="">Standard payment examples</option>{catalogue?.variant_ids?.map(id=><option key={id}>{id}</option>)}</select></label><label>Demo time<select value={clock} disabled={!!pending||busy} onChange={event=>setClock(event.target.value as ClockMode)}><option value="REFERENCE">Fixed sample date</option><option value="REAL">Current date and time</option></select></label><button disabled={!catalogue||busy} onClick={()=>void create()}>{busy?'Creating...':pending?'Retry original creation':'Create fictional demonstration'}</button></div><p className="subtle">Start with Standard payment examples and Fixed sample date for a repeatable walkthrough. A fresh copy contains three fictional cases. Existing copies and history stay saved.</p>{error&&<p role="alert" className="notice">{error}</p>}</details></section>;
}
