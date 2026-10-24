import { afterEach, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import type { ApiClient } from '../src/api/client';
import type { AgentActivity, Attempt, Health } from '../src/api/types';
import { AgentTrace } from '../src/agents/AgentTrace';
import { AgentRoster } from '../src/agents/AgentRoster';
import { did } from './fixtures';

afterEach(cleanup);
const iid = '44444444-4444-4444-8444-444444444444';

function row(agent: AgentActivity['agent'], outcome: AgentActivity['outcome'], note: string | null = null, extra: Partial<AgentActivity> = {}): AgentActivity {
  return {agent, event: 'step', outcome, note, model: null, input_tokens: null, output_tokens: null, latency_ms: null, at: '2026-10-24T10:00:00Z',
    case_id: null, investigation_id: iid, morning_review_id: null, ...extra};
}

function api(activity: AgentActivity[], totals: Attempt['agent_totals'] = {input_tokens: 0, output_tokens: 0, latency_ms: 0, cost_usd: null}): ApiClient {
  return {attempt: async () => ({status: 'COMPLETE', draft_status: 'READY', agent_activity: activity, agent_totals: totals}) as unknown as Attempt} as unknown as ApiClient;
}

it('renders agent trace with revision note', async () => {
  render(<AgentTrace api={api([row('COMMUNICATOR', 'SUCCEEDED', 'Thanks.'), row('TONE_REVIEWER', 'REVISE', 'Too blunt'), row('OWNER', 'WAITING', 'Ready.')])} did={did} investigationId={iid}/>);
  expect(await screen.findByText('Tone reviewer')).toBeInTheDocument();
  expect(screen.getByText('asked for a revision')).toBeInTheDocument();
  expect(screen.getByText('Too blunt')).toBeInTheDocument();
  expect(screen.getByText('waiting for you')).toBeInTheDocument();
});

it('explains a fallback to the standard template', async () => {
  render(<AgentTrace api={api([row('COMMUNICATOR', 'FAILED', 'AGENT_UNAVAILABLE; the standard template is used.'), row('OWNER', 'WAITING')])} did={did} investigationId={iid}/>);
  expect(await screen.findByText('could not finish')).toBeInTheDocument();
  expect(screen.getByText(/standard template is used/)).toBeInTheDocument();
});

it('shows time and tokens and says cost is not configured', async () => {
  render(<AgentTrace api={api([row('EXTRACTOR', 'SUCCEEDED', null, {model: 'zai-org/GLM-5.3-Flash', input_tokens: 1200, output_tokens: 300, latency_ms: 6200}), row('OWNER', 'WAITING')],
    {input_tokens: 1200, output_tokens: 300, latency_ms: 6200, cost_usd: null})} did={did} investigationId={iid}/>);
  expect(await screen.findByText(/6\.2 s · 1,500 tokens · cost not configured/)).toBeInTheDocument();
  expect(screen.getByText(/zai-org\/GLM-5\.3-Flash · 6\.2 s · 1,500 tokens/)).toBeInTheDocument();
});

it('shows cost when rates are configured', async () => {
  render(<AgentTrace api={api([row('OWNER', 'WAITING')], {input_tokens: 10, output_tokens: 5, latency_ms: 100, cost_usd: 0.0012})} did={did} investigationId={iid}/>);
  expect(await screen.findByText(/≈ \$0\.0012/)).toBeInTheDocument();
});

it('limits the trace to the requested agents', async () => {
  render(<AgentTrace api={api([row('EXTRACTOR', 'SUCCEEDED'), row('COMMUNICATOR', 'SUCCEEDED', 'Thanks.'), row('OWNER', 'WAITING')])} did={did} investigationId={iid}
    agents={['COMMUNICATOR', 'SAFETY_CHECK', 'TONE_REVIEWER']} title="How this draft was written"/>);
  expect(await screen.findByText('How this draft was written')).toBeInTheDocument();
  expect(screen.getByText('Communicator')).toBeInTheDocument();
  expect(screen.queryByText('Promise extractor')).not.toBeInTheDocument();
});

it('roster shows roles and providers but never key-like text', () => {
  const health = {schema_version: '1', ready: true, agent_mode: 'LIVE', catalogue_version: 'release-0.1', configuration: {model: 'm', capability_available: true, agents: [
    {role: 'Extractor', provider: 'NEBIUS', model: 'zai-org/GLM-5.3-Flash', available: true, can_change: []},
    {role: 'Tone Reviewer', provider: 'FIREWORKS', model: 'accounts/fireworks/models/gpt-oss-120b', available: false, can_change: []},
    {role: 'Memory', provider: 'LOCAL', model: null, available: true, can_change: ['client payment notes']}]}} as Health;
  const {container} = render(<AgentRoster health={health}/>);
  expect(screen.getByText('Extractor')).toBeInTheDocument();
  expect(screen.getByText(/Fireworks/)).toBeInTheDocument();
  expect(screen.getByText(/not configured/)).toBeInTheDocument();
  expect(screen.getAllByText('read-only')).toHaveLength(2);
  expect(screen.getByText('can change: client payment notes')).toBeInTheDocument();
  expect(container.textContent).not.toMatch(/key|secret/i);
});

it('disclosure loads the drafting trace only when opened', async () => {
  const { AgentTraceDisclosure } = await import('../src/agents/AgentTrace');
  const { fireEvent } = await import('@testing-library/react');
  let calls = 0;
  const counting = {attempt: async () => { calls++; return {status: 'COMPLETE', draft_status: 'READY', agent_activity: [row('COMMUNICATOR', 'SUCCEEDED', 'Thanks.'), row('OWNER', 'WAITING')], agent_totals: null}; }} as unknown as ApiClient;
  const {container} = render(<AgentTraceDisclosure api={counting} did={did} investigationId={iid}/>);
  expect(screen.getByText('See how your AI team wrote this draft')).toBeInTheDocument();
  expect(calls).toBe(0);
  const details = container.querySelector('details')!;
  details.open = true;
  fireEvent(details, new Event('toggle'));
  expect(await screen.findByText('Communicator')).toBeInTheDocument();
  expect(calls).toBe(1);
});

it('shows who each agent handed its work to', async () => {
  render(<AgentTrace api={api([row('TONE_REVIEWER', 'REVISE', 'Warmer please', {recipient: 'COMMUNICATOR', message_kind: 'REVISION_REQUEST'}),
    row('TONE_REVIEWER', 'SUCCEEDED', 'ok', {recipient: 'OWNER', message_kind: 'DRAFT_FOR_APPROVAL'}), row('OWNER', 'WAITING')])} did={did} investigationId={iid}/>);
  expect(await screen.findByText('→ Communicator: revision request')).toBeInTheDocument();
  expect(screen.getByText('→ Your approval: draft for your approval')).toBeInTheDocument();
});
