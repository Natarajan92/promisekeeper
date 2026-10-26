import type { ClockMode, Health } from '../api/types';
// Provider availability and verification privacy stay visible on every page.
export function StatusBanner({health,clock,imported=false}:{health:Health|null;clock?:ClockMode;imported?:boolean}) {
  const mode=health?.agent_mode==='STUB'?'stub':health?.agent_mode==='LIVE'?'live':'unknown';
  return <div className="status-banner"><span className={`mode mode-${mode}`}>{health?.agent_mode==='STUB'?'AI providers disabled':health?.agent_mode==='LIVE'?'AI providers enabled':'AI status unavailable'}</span><span className="status-clock">{clock==='REFERENCE'?(imported?'Imported data cutoff':'Saved review date'):clock==='REAL'?'Current date and time':'No workspace selected'}</span><span className="status-note">Internal verification environment. Do not enter real customer or banking details.</span></div>;
}
