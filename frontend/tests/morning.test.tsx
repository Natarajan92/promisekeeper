import { afterEach, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { ApiError, type ApiClient } from '../src/api/client';
import type { MorningReviewView } from '../src/api/types';
import { MorningReview } from '../src/agents/MorningReview';
import { did } from './fixtures';

afterEach(cleanup);

const complete: MorningReviewView = {schema_version: '1', id: 'm1', demonstration_id: did, status: 'COMPLETE', started_at: '2026-10-24T10:00:00Z',
  terminal_at: '2026-10-24T10:00:05Z', briefing: 'Northstar Analytics needs a follow-up today. Meridian Studio can wait.', briefing_source: 'AGENT', failure_code: null,
  outcomes: [
    {case_id: 'c1', client: 'Northstar Analytics', invoice_id: 'NS-104', outcome: 'INVESTIGATED', action: 'FOLLOW_UP', reason: null, balance_text: 'INR 80,000.00', review_at_text: null, draft_ready: true},
    {case_id: 'c2', client: 'Meridian Studio', invoice_id: 'MS-221', outcome: 'SKIPPED', action: 'WAIT', reason: 'The saved recommendation is still current.', balance_text: null, review_at_text: '26 Oct 2026, 00:00 IST', draft_ready: false}],
  agent_activity: [{agent: 'SUPERVISOR', event: 'Choose which cases need work', outcome: 'SUCCEEDED', note: '1 of 2 cases need a fresh investigation.', model: null,
    input_tokens: null, output_tokens: null, latency_ms: 12, at: '2026-10-24T10:00:01Z', case_id: null, investigation_id: null, morning_review_id: 'm1'}]};

function fake(overrides: Partial<Record<'latestMorningReview' | 'startMorningReview' | 'morningReview', unknown>> = {}) {
  return {latestMorningReview: async () => ({schema_version: '1', morning_review: null}), startMorningReview: async () => ({...complete, status: 'RUNNING', briefing: null}),
    morningReview: async () => complete, ...overrides} as unknown as ApiClient;
}

it('keeps completed case choices visible and opens the full briefing only on request', async () => {
  const opened: string[] = [];
  render(<MorningReview api={fake({latestMorningReview: async () => ({schema_version: '1', morning_review: complete})})} did={did} onOpenCase={id => opened.push(id)} onDone={() => {}}/>);
  expect(await screen.findByText('Review complete. Choose a case to see its recommendation.')).toBeVisible();
  expect(screen.getByText(/Northstar Analytics needs a follow-up today/)).not.toBeVisible();
  fireEvent.click(screen.getByText('Read saved briefing'));
  expect(screen.getByText(/Northstar Analytics needs a follow-up today/)).toBeVisible();
  expect(screen.getByText(/Each amount and date was checked against that case's facts/)).toBeVisible();
  fireEvent.click(screen.getByRole('button', {name: /Northstar Analytics.*Follow up.*draft ready/}));
  expect(opened).toEqual(['c1']);
  expect(screen.getByRole('button', {name: /Meridian Studio.*no change needed/})).toBeInTheDocument();
});

it('starts a review, shows the supervisor working and refreshes cases when done', async () => {
  let done = 0;
  render(<MorningReview api={fake()} did={did} onOpenCase={() => {}} onDone={() => { done++; }}/>);
  fireEvent.click(await screen.findByRole('button', {name: 'Start morning review'}));
  expect(await screen.findByText(/Northstar Analytics needs a follow-up today/, {}, {timeout: 4000})).toBeInTheDocument();
  expect(screen.getByText(/1 of 2 cases need a fresh investigation\./)).toBeInTheDocument();
  expect(done).toBe(1);
});

it('explains why a review could not start', async () => {
  const busy = fake({startMorningReview: async () => { throw new ApiError('MORNING_REVIEW_RUNNING', 'A morning review is already running.', 409); }});
  render(<MorningReview api={busy} did={did} onOpenCase={() => {}} onDone={() => {}}/>);
  fireEvent.click(await screen.findByRole('button', {name: 'Start morning review'}));
  expect(await screen.findByText(/Morning review not started: A morning review is already running\./)).toBeInTheDocument();
});

it('says when the supervisor started the review on its own', async () => {
  render(<MorningReview api={fake({latestMorningReview: async () => ({schema_version: '1', morning_review: {...complete, started_by: 'AUTONOMOUS'}})})} did={did} onOpenCase={() => {}} onDone={() => {}}/>);
  expect(await screen.findByText(/Started automatically by your AI supervisor/)).toBeInTheDocument();
});

it('keeps following a review that is already running when the page opens', async () => {
  let done = 0;
  render(<MorningReview api={fake({latestMorningReview: async () => ({schema_version: '1', morning_review: {...complete, status: 'RUNNING', briefing: null}})})}
    did={did} onOpenCase={() => {}} onDone={() => { done++; }}/>);
  expect(await screen.findByText(/Northstar Analytics needs a follow-up today/, {}, {timeout: 4000})).toBeInTheDocument();
  expect(done).toBe(1);
});

it('offers to check again instead of staying disabled when a review runs long', async () => {
  const running = {...complete, status: 'RUNNING' as const, briefing: null};
  render(<MorningReview api={fake({latestMorningReview: async () => ({schema_version: '1', morning_review: running}), morningReview: async () => running})}
    did={did} onOpenCase={() => {}} onDone={() => {}} maxWaitMs={50}/>);
  const again = await screen.findByRole('button', {name: 'Check again'}, {timeout: 4000});
  expect(again).toBeEnabled();
});

it('shows the supervisor plan order, its reasons and a sideways strip with controls', async () => {
  const planned: MorningReviewView = {...complete,
    outcomes: [
      {...complete.outcomes[0], priority: 1, supervisor_reason: 'Largest open balance still waiting (INR 80,000.00), overdue 12 days.'},
      {case_id: 'c3', client: 'Saffron Foods', invoice_id: 'SF-221', outcome: 'INVESTIGATED', action: 'FOLLOW_UP', reason: null, balance_text: 'INR 60,000.00', review_at_text: null, draft_ready: true,
        priority: 2, supervisor_reason: 'Saffron Foods next: overdue 17 days.'},
      complete.outcomes[1]],
    agent_activity: [...complete.agent_activity,
      {agent: 'SUPERVISOR', event: 'Investigate Saffron Foods next', outcome: 'FALLBACK', note: 'Planner choice not used because it named a case that is not waiting in this review. Taken in rule order.',
        model: null, input_tokens: null, output_tokens: null, latency_ms: 5, at: '2026-10-24T10:00:02Z', case_id: 'c3', investigation_id: null, morning_review_id: 'm1'}]};
  render(<MorningReview api={fake({latestMorningReview: async () => ({schema_version: '1', morning_review: planned})})} did={did} onOpenCase={() => {}} onDone={() => {}}/>);
  expect(await screen.findByText('Checked #1 by your supervisor')).toBeVisible();
  expect(screen.getByText('Checked #2 by your supervisor')).toBeVisible();
  expect(screen.getAllByText(/^Checked #\d by your supervisor$/)).toHaveLength(2);
  expect(screen.getByText(/Saffron Foods next: overdue 17 days/)).toBeVisible();
  expect(screen.getByRole('list', {name: 'Morning review cases'}).children).toHaveLength(3);
  expect(screen.getByRole('button', {name: 'Next cases'})).toBeVisible();
  expect(screen.getByRole('button', {name: 'Previous cases'})).toBeVisible();
  fireEvent.click(screen.getByText('See what the supervisor did'));
  expect(screen.getByText(/Investigate Saffron Foods next \(rule order\)/)).toBeVisible();
  expect(screen.queryByText(/used the standard template/)).not.toBeInTheDocument();
});
