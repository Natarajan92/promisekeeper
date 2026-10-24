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

it('shows the latest briefing and case chips that open a case', async () => {
  const opened: string[] = [];
  render(<MorningReview api={fake({latestMorningReview: async () => ({schema_version: '1', morning_review: complete})})} did={did} onOpenCase={id => opened.push(id)} onDone={() => {}}/>);
  expect(await screen.findByText(/Northstar Analytics needs a follow-up today/)).toBeInTheDocument();
  expect(screen.getByText(/Every number was checked against your case facts/)).toBeInTheDocument();
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
