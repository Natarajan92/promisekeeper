import type { Evidence } from '../api/types';
import { instant, words } from '../components/format';
export function Timeline({evidence,onSource}:{evidence:Evidence[];onSource:(id:string)=>void}) {
  const dated=evidence.filter(record=>record.event_at).sort((a,b)=>Date.parse(a.event_at!)-Date.parse(b.event_at!) || a.stable_source_id.localeCompare(b.stable_source_id));
  const undated=evidence.filter(record=>!record.event_at).sort((a,b)=>a.stable_source_id.localeCompare(b.stable_source_id));
  const records=(items:Evidence[])=><ol className="timeline">{items.map(record=><li key={record.id}><time dateTime={record.event_at ?? undefined}>{record.event_at?instant(record.event_at):'Event time unknown'}</time><div><button className="text-button" onClick={()=>onSource(record.id)}>{record.stable_source_id} · version {record.version}</button><p>{words(record.kind)} · {record.availability}</p><p className="subtle">Arrived {instant(record.arrived_at)}</p></div></li>)}</ol>;
  return <section aria-labelledby="timeline-heading"><h2 id="timeline-heading">Evidence timeline</h2><p className="subtle">Ordered by source event time. Arrival time records when evidence reached this copy.</p>{dated.length?records(dated):<p>No dated evidence.</p>}{undated.length>0&&<><h3>Undated evidence</h3>{records(undated)}</>}</section>;
}
