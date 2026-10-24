import { useState } from 'react';
import { ApiClient, clearOperation, pendingOperation, stableOperation } from '../api/client';
import type { Catalogue, ClockMode, Demonstration } from '../api/types';
import { instant } from '../components/format';
export function DemonstrationPicker({api,copies,selected,catalogue,onSelect,onCreated}:{api:ApiClient;copies:Demonstration[];selected:string|null;catalogue:Catalogue|null;onSelect:(id:string)=>void;onCreated:(id:string)=>void}) {
  const [variant,setVariant]=useState('');const [clock,setClock]=useState<ClockMode>('REFERENCE');const [busy,setBusy]=useState(false);const [error,setError]=useState('');
  const pending=pendingOperation('new','new','creation');
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
  return <section className="demonstration-picker" aria-label="Saved demonstration selection"><div className="copy-selection">{copies.length>0?<><label htmlFor="saved-copy">Demonstration copy</label><select id="saved-copy" value={selected??''} onChange={event=>onSelect(event.target.value)}><option value="" disabled>Choose a saved copy</option>{copies.map(copy=><option value={copy.id} key={copy.id}>{copy.selected_variant_id??'Baseline'} / {copy.clock_mode} / {instant(copy.created_at)} / {copy.id.slice(0,8)}</option>)}</select></>:<p>No saved demonstrations. Create a fictional copy to begin.</p>}</div><details className="create-copy" open={copies.length===0}><summary>Create another fictional copy</summary><div className="create-fields"><label>Registered fixture<select value={variant} disabled={!!pending||busy} onChange={event=>setVariant(event.target.value)}><option value="">Baseline</option>{catalogue?.variant_ids?.map(id=><option key={id}>{id}</option>)}</select></label><label>Business clock<select value={clock} disabled={!!pending||busy} onChange={event=>setClock(event.target.value as ClockMode)}><option value="REFERENCE">REFERENCE</option><option value="REAL">REAL</option></select></label><button disabled={!catalogue||busy} onClick={()=>void create()}>{busy?'Creating...':pending?'Retry original creation':'Create fictional demonstration'}</button></div><p className="subtle">A fresh isolated copy contains exactly three cases. Existing copies and history stay saved.</p>{error&&<p role="alert" className="notice">{error}</p>}</details></section>;
}
