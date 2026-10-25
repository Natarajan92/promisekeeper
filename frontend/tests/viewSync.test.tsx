import { afterEach, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import type { ApiClient } from '../src/api/client';
import type { CaseOutcome, CaseSummary, MorningReviewView } from '../src/api/types';
import { MorningReview } from '../src/agents/MorningReview';
import { CaseList } from '../src/cases/CaseList';
import { did } from './fixtures';

afterEach(cleanup);

const at = '2026-10-23T04:30:00Z';
const base = {invoice_id: 'INV', currency: 'INR', due_at: '2026-10-10T18:30:00Z', due_text: '10 October 2026', lifecycle: 'OPEN', case_revision: 1,
  has_previous_investigation: true, review_required: false, balance: {currency: 'INR', minor_units: '100'}, balance_label: 'VERIFIED_REMAINDER', review_at: null};
const summary = (n: number, client: string, recommended_action: string, extra = {}) =>
  ({...base, id: `case-${n}`, catalogue_case_id: `PK-00${n}`, client, recommended_action, ...extra}) as unknown as CaseSummary;
const cases = [
  summary(1, 'Northstar Analytics', 'FOLLOW_UP'),
  summary(2, 'Meridian Software', 'WAIT', {review_at: '2026-10-26T00:00:00+05:30'}),
  summary(3, 'Cedar Retail Labs', 'VERIFY_PAYMENT'),
  summary(4, 'Saffron Foods', 'FOLLOW_UP'),
  summary(5, 'Lotus Interiors', 'VERIFY_PAYMENT'),
  summary(6, 'Banyan Logistics', 'CLOSE'),
];
// The live supervisor checked Banyan first; it still belongs after every case needing attention.
const checked = ['case-6', 'case-4', 'case-1', 'case-5', 'case-3', 'case-2'];
const outcome = (id: string, priority: number): CaseOutcome => {
  const item = cases.find(c => c.id === id)!;
  return {case_id: id, client: item.client, invoice_id: 'INV', outcome: 'INVESTIGATED', action: item.recommended_action, reason: null,
    balance_text: null, review_at_text: null, draft_ready: item.recommended_action === 'FOLLOW_UP', priority, supervisor_reason: `Reason for ${item.client}.`};
};
const review: MorningReviewView = {schema_version: '1', id: 'm1', demonstration_id: did, status: 'COMPLETE', started_at: at, terminal_at: at,
  briefing: 'Saved summary.', briefing_source: 'AGENT', failure_code: null, outcomes: checked.map((id, i) => outcome(id, i + 1)), agent_activity: []};
const plan = Object.fromEntries(checked.map((id, i) => [id, i + 1]));
const api = {latestMorningReview: async () => ({schema_version: '1', morning_review: review})} as unknown as ApiClient;

function stripClients() {
  return within(screen.getByRole('list', {name: 'Morning review cases'})).getAllByRole('button').map(b => b.querySelector('strong')!.textContent);
}
function overviewClients() {
  return within(screen.getByRole('navigation', {name: 'Fictional cases'})).getAllByRole('button').map(b => b.querySelector('strong')?.textContent).filter(Boolean);
}

it('lists cases in the same order with the same status in the morning strip and the case overview', async () => {
  let reported: Record<string, number> = {};
  render(<><MorningReview api={api} did={did} cases={cases} evaluationAt={at} onPlan={value => { reported = value; }} onOpenCase={() => {}} onDone={() => {}}/>
    <CaseList cases={cases} evaluationAt={at} plan={plan} selected={null} onSelect={() => {}}/></>);
  await screen.findByText('Checked #1 by your supervisor');
  expect(reported).toEqual(plan);
  const urgent = ['Saffron Foods', 'Northstar Analytics', 'Lotus Interiors', 'Cedar Retail Labs'];
  expect(stripClients()).toEqual([...urgent, 'Banyan Logistics', 'Meridian Software']);
  expect(overviewClients()).toEqual(urgent);
  fireEvent.click(screen.getByRole('button', {name: 'Show all 6 cases'}));
  expect(overviewClients()).toEqual(stripClients());
  const strip = screen.getByRole('list', {name: 'Morning review cases'});
  expect(within(strip).getAllByText('Needs attention')).toHaveLength(4);
  expect(within(strip).getAllByText('Can wait')).toHaveLength(2);
  const banyan = within(strip).getByRole('button', {name: /Banyan Logistics/});
  expect(banyan).toHaveTextContent('Review case closure');
  expect(banyan).toHaveTextContent('Checked #1 by your supervisor');
});

it('shows the current case status in the strip, not the snapshot saved at review time', async () => {
  const closed = cases.map(c => c.id === 'case-1' ? {...c, lifecycle: 'CLOSED' as const} : c);
  render(<MorningReview api={api} did={did} cases={closed} evaluationAt={at} onOpenCase={() => {}} onDone={() => {}}/>);
  await screen.findByText('Checked #1 by your supervisor');
  const northstar = within(screen.getByRole('list', {name: 'Morning review cases'})).getByRole('button', {name: /Northstar Analytics/});
  expect(northstar).toHaveTextContent('Case closed');
  expect(northstar).toHaveTextContent('Can wait');
  expect(northstar).not.toHaveTextContent('draft ready for review');
});
