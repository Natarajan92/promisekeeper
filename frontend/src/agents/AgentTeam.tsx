import type { AgentActivity, AgentName, Health } from '../api/types';
import { AgentRoster, providerLine } from './AgentRoster';
import { AGENT_KIND, AGENT_LABEL, AGENT_ORDER, AGENT_ROLE, HEALTH_ROLE, KIND_LABEL, OUTCOME_LABEL } from './agentLabels';

export const AGENT_ICON: Record<AgentName, string> = {
  SUPERVISOR: '🧭', INTAKE: '📥', EXTRACTOR: '🔎', RULES_ENGINE: '⚖️', MEMORY: '🗂️',
  COMMUNICATOR: '✍️', SAFETY_CHECK: '🛡️', TONE_REVIEWER: '🤝', BRIEFING: '📋', OWNER: '🙋',
};

/** The role line without its "AI:"/"Code:" prefix, because the card's tag already says which it is. */
export function plainRole(agent: AgentName) {
  const text = AGENT_ROLE[agent].replace(/^(AI|Code): /, '');
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function KindTag({agent}: {agent: AgentName}) {
  const kind = AGENT_KIND[agent];
  return <span className={`kind-tag kind-${kind.toLowerCase()}`}>{KIND_LABEL[kind]}</span>;
}

/** One card per pipeline step: what it does, whether it is AI or code, its latest status and its configured provider. */
export function AgentTeam({health, latest, scope}: {health: Health | null; latest: Partial<Record<AgentName, AgentActivity>>; scope: (row: AgentActivity) => string}) {
  const configured = health?.configuration?.agents ?? [];
  return <section className="agent-team-section" aria-labelledby="agent-team-heading">
    <div className="assistant-section-head">
      <h2 id="agent-team-heading">Your digital team</h2>
      <p className="subtle">AI agents read and write drafts. Rules written in code decide money and the one next step. You approve everything, and nothing is sent.</p>
    </div>
    <ol className="agent-team" aria-labelledby="agent-team-heading">{AGENT_ORDER.map((agent, index) => {
      const role = HEALTH_ROLE[agent];
      const config = role ? configured.find(item => item.role === role) : undefined;
      const row = latest[agent];
      return <li key={agent} className={`agent-card kind-${AGENT_KIND[agent].toLowerCase()}`}>
        <div className="agent-card-top">
          <span className="agent-icon" aria-hidden="true">{AGENT_ICON[agent]}</span>
          <span className="agent-card-step">Step {index + 1}</span>
          <KindTag agent={agent}/>
        </div>
        <h3>{AGENT_LABEL[agent]}</h3>
        <p className="agent-card-role">{plainRole(agent)}</p>
        <p className={`agent-card-status${row ? ` outcome-${row.outcome.toLowerCase()}` : ''}`}>{row ? `Latest: ${OUTCOME_LABEL[row.outcome]} ${scope(row)}` : 'No recent activity'}</p>
        {config && <p className="agent-card-model">{providerLine(config)}{!config.available ? ' · not configured; safe fallback used' : ''}</p>}
      </li>;
    })}</ol>
    <AgentRoster health={health}/>
  </section>;
}
