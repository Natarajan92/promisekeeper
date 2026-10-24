import type { ClockMode, Health } from '../api/types';
export function StatusBanner({health,clock}:{health:Health|null;clock?:ClockMode}) {
  return <div className="status-banner"><span className="mode">{health?.agent_mode ?? 'Mode unavailable'}</span><span>{clock ?? 'No clock selected'}</span><span>Fictional cases only. No authentication. Do not enter real customer or banking details.</span></div>;
}
