import type { AgentName, AgentOutcome } from '../api/types';

export const AGENT_LABEL: Record<AgentName, string> = {
  INTAKE: 'Evidence intake', EXTRACTOR: 'Promise extractor', RULES_ENGINE: 'Payment rules', MEMORY: 'Client memory',
  COMMUNICATOR: 'Communicator', SAFETY_CHECK: 'Safety check', TONE_REVIEWER: 'Tone reviewer', OWNER: 'Your approval',
  SUPERVISOR: 'Morning supervisor', BRIEFING: 'Briefing writer',
};

export const AGENT_ROLE: Record<AgentName, string> = {
  INTAKE: 'Reads the saved evidence', EXTRACTOR: 'AI: finds promises and payment claims', RULES_ENGINE: 'Code: money, dates and the one next step',
  MEMORY: 'Recalls this client’s payment history', COMMUNICATOR: 'AI: writes one friendly note', SAFETY_CHECK: 'Code: blocks amounts, fees and instructions',
  TONE_REVIEWER: 'AI: checks the note is polite and fair', OWNER: 'You decide; nothing is sent', SUPERVISOR: 'AI: plans which case to work on next',
  BRIEFING: 'AI: summarises your cases',
};

export const OUTCOME_LABEL: Record<AgentOutcome, string> = {
  STARTED: 'working', SUCCEEDED: 'done', REVISE: 'asked for a revision', FALLBACK: 'used the standard template',
  FAILED: 'could not finish', WAITING: 'waiting for you', SKIPPED: 'not used',
};

export const MESSAGE_LABEL: Record<string, string> = {
  EVIDENCE_PACKET: 'evidence packet', PAYMENT_CANDIDATES: 'promises and payment claims', DECISION: 'recommended action',
  CLIENT_HISTORY: 'client payment history', NOTE_DRAFT: 'personal note', REVISION_REQUEST: 'revision request',
  DRAFT_FOR_APPROVAL: 'draft for your approval', CASE_SELECTION: 'case to investigate', CASE_OUTCOME: 'case outcome', BRIEFING: 'briefing',
};

export const PROVIDER_LABEL: Record<string, string> = {
  SCRIPTED: 'predefined responses', NEBIUS: 'Nebius', FIREWORKS: 'Fireworks', MEM0: 'mem0', LOCAL: 'local store',
};

export function usage(latencyMs: number | null, inputTokens: number | null, outputTokens: number | null) {
  const parts: string[] = [];
  if (latencyMs) parts.push(`${(latencyMs / 1000).toFixed(1)} s`);
  const tokens = (inputTokens ?? 0) + (outputTokens ?? 0);
  if (tokens) parts.push(`${tokens.toLocaleString('en-US')} tokens`);
  return parts;
}

/** Whether a step is an AI model, rule-based code, or the business owner. */
export const AGENT_KIND: Record<AgentName, 'AI' | 'RULES' | 'YOU'> = {
  SUPERVISOR: 'AI', INTAKE: 'RULES', EXTRACTOR: 'AI', RULES_ENGINE: 'RULES', MEMORY: 'RULES',
  COMMUNICATOR: 'AI', SAFETY_CHECK: 'RULES', TONE_REVIEWER: 'AI', BRIEFING: 'AI', OWNER: 'YOU',
};

export const KIND_LABEL: Record<'AI' | 'RULES' | 'YOU', string> = {AI: 'AI', RULES: 'Rules (code)', YOU: 'You'};

/** Pipeline order: the supervisor plans, each case runs intake to tone review, the briefing reports, you decide. */
export const AGENT_ORDER: readonly AgentName[] = [
  'SUPERVISOR', 'INTAKE', 'EXTRACTOR', 'RULES_ENGINE', 'MEMORY', 'COMMUNICATOR', 'SAFETY_CHECK', 'TONE_REVIEWER', 'BRIEFING', 'OWNER',
];

/** The health-configuration role behind each agent; steps without one have no provider or model to show. */
export const HEALTH_ROLE: Partial<Record<AgentName, string>> = {
  SUPERVISOR: 'Supervisor', EXTRACTOR: 'Extractor', COMMUNICATOR: 'Communicator', TONE_REVIEWER: 'Tone Reviewer', BRIEFING: 'Briefing', MEMORY: 'Memory',
};
