import type { AgentName, AgentOutcome } from '../api/types';

export const AGENT_LABEL: Record<AgentName, string> = {
  INTAKE: 'Evidence intake', EXTRACTOR: 'Promise extractor', RULES_ENGINE: 'Payment rules', MEMORY: 'Client memory',
  COMMUNICATOR: 'Communicator', SAFETY_CHECK: 'Safety check', TONE_REVIEWER: 'Tone reviewer', OWNER: 'Your approval',
  SUPERVISOR: 'Morning supervisor', BRIEFING: 'Briefing writer',
};

export const AGENT_ROLE: Record<AgentName, string> = {
  INTAKE: 'Reads the saved evidence', EXTRACTOR: 'AI: finds promises and payment claims', RULES_ENGINE: 'Code: money, dates and the one next step',
  MEMORY: 'Recalls this client’s payment history', COMMUNICATOR: 'AI: writes one friendly note', SAFETY_CHECK: 'Code: blocks amounts, fees and instructions',
  TONE_REVIEWER: 'AI: checks the note is polite and fair', OWNER: 'You decide; nothing is sent', SUPERVISOR: 'Decides which cases need work',
  BRIEFING: 'AI: summarises your cases',
};

export const OUTCOME_LABEL: Record<AgentOutcome, string> = {
  STARTED: 'working', SUCCEEDED: 'done', REVISE: 'asked for a revision', FALLBACK: 'used the standard template',
  FAILED: 'could not finish', WAITING: 'waiting for you', SKIPPED: 'not used',
};

export const PROVIDER_LABEL: Record<string, string> = {
  SCRIPTED: 'offline stand-in', NEBIUS: 'Nebius', FIREWORKS: 'Fireworks', MEM0: 'mem0', LOCAL: 'local store',
};

export function usage(latencyMs: number | null, inputTokens: number | null, outputTokens: number | null) {
  const parts: string[] = [];
  if (latencyMs) parts.push(`${(latencyMs / 1000).toFixed(1)} s`);
  const tokens = (inputTokens ?? 0) + (outputTokens ?? 0);
  if (tokens) parts.push(`${tokens.toLocaleString('en-US')} tokens`);
  return parts;
}
