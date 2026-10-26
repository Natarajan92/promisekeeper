import type { ClockMode, Health } from '../api/types';
// A slim strip under the top bar; LIVE versus STUB stays visible on every page.
export function StatusBanner({health,clock,imported=false}:{health:Health|null;clock?:ClockMode;imported?:boolean}) {
  const mode=health?.agent_mode==='STUB'?'stub':health?.agent_mode==='LIVE'?'live':'unknown';
  return <div className="status-banner"><span className={`mode mode-${mode}`}>{health?.agent_mode==='STUB'?'Scripted sample (STUB)':health?.agent_mode==='LIVE'?'Live model (LIVE)':'Mode unavailable'}</span><span className="status-clock">{clock==='REFERENCE'?(imported?'Imported data cutoff (REFERENCE)':'Fixed sample date (REFERENCE)'):clock==='REAL'?'Current date and time (REAL)':'No demo time selected'}</span><span className="status-note">Fictional cases only. No authentication. Do not enter real customer or banking details.</span></div>;
}
