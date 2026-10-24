import type { Health } from '../api/types';
import { PROVIDER_LABEL } from './agentLabels';

export function AgentRoster({health}: {health: Health | null}) {
  const agents = health?.configuration?.agents;
  if (!agents?.length) return null;
  return <details className="agent-roster">
    <summary>Your AI team ({agents.filter(agent => agent.available).length} of {agents.length} ready)</summary>
    <ul>{agents.map(agent => <li key={agent.role}>
      <strong>{agent.role}</strong>
      <span>{PROVIDER_LABEL[agent.provider] ?? agent.provider}{agent.model ? ` · ${agent.model}` : ''}</span>
      {!agent.available && <span className="agent-unavailable">not configured; safe fallback used</span>}
      {agent.can_change && <span className="agent-permission">{agent.can_change.length ? `can change: ${agent.can_change.join(', ')}` : 'read-only'}</span>}
    </li>)}</ul>
    <p className="subtle">AI agents read and write drafts. Code decides money and next steps. You approve everything; nothing is sent.</p>
  </details>;
}
