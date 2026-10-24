import type { ClockMode, Health } from '../api/types';
export function StatusBanner({health,clock}:{health:Health|null;clock?:ClockMode}) {
  return <div className="status-banner"><span className="mode">{health?.agent_mode==='STUB'?'Scripted sample (STUB)':health?.agent_mode==='LIVE'?'Live model (LIVE)':'Mode unavailable'}</span><span>{clock==='REFERENCE'?'Fixed sample date (REFERENCE)':clock==='REAL'?'Current date and time (REAL)':'No demo time selected'}</span><span>Fictional cases only. No authentication. Do not enter real customer or banking details.</span></div>;
}
