import { afterEach, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import type { CaseSummary } from '../src/api/types';
import { CaseList, needsAttention } from '../src/cases/CaseList';
import { did } from './fixtures';

afterEach(cleanup);

const base = {catalogue_case_id: 'PK-001', invoice_id: 'INV', currency: 'INR', due_at: '2026-10-10T18:30:00Z', due_text: '10 October 2026',
  lifecycle: 'OPEN', case_revision: 1, has_previous_investigation: true, review_required: false, balance: {currency: 'INR', minor_units: '100'},
  balance_label: 'VERIFIED_REMAINDER', recommended_action: 'FOLLOW_UP', review_at: null} as const;
const at = '2026-10-23T04:30:00Z';
function item(id: string, client: string, extra: Partial<CaseSummary> = {}) {
  return {...base, id: `${did.slice(0, 30)}${id}`, client, ...extra} as unknown as CaseSummary;
}
const cases = [
  item('000001', 'Follow up client'),
  item('000002', 'Waiting client', {recommended_action: 'WAIT', review_at: '2026-10-26T00:00:00+05:30'}),
  item('000003', 'Claim client', {recommended_action: 'VERIFY_PAYMENT'}),
  item('000004', 'New client', {recommended_action: null, has_previous_investigation: false}),
  item('000005', 'Settled client', {recommended_action: 'CLOSE'}),
  item('000006', 'Closed client', {lifecycle: 'CLOSED', recommended_action: null}),
];

it('classifies which cases need attention now', () => {
  expect(cases.map(c => needsAttention(c, at))).toEqual([true, false, true, true, false, false]);
  const due = item('000007', 'Due wait', {recommended_action: 'WAIT', review_at: '2026-10-22T00:00:00Z'});
  expect(needsAttention(due, at)).toBe(true);
  expect(needsAttention(item('000008', 'Changed', {recommended_action: 'WAIT', review_required: true}), at)).toBe(true);
});

it('shows only urgent cases by default, keeps the open case visible and toggles to all', () => {
  render(<CaseList cases={cases} selected={cases[1].id} onSelect={() => {}} evaluationAt={at}/>);
  expect(screen.getByRole('heading', {name: /Case overview 3 need attention/})).toBeVisible();
  expect(screen.getByRole('button', {name: /Waiting client/})).toBeVisible();
  expect(screen.queryByRole('button', {name: /Settled client/})).not.toBeInTheDocument();
  expect(screen.queryByRole('button', {name: /Closed client/})).not.toBeInTheDocument();
  expect(screen.getByText(/2 more can wait/)).toBeVisible();
  const toggle = screen.getByRole('button', {name: 'Show all 6 cases'});
  expect(toggle).toHaveAttribute('aria-pressed', 'false');
  fireEvent.click(toggle);
  expect(screen.getByRole('button', {name: /Settled client/})).toBeVisible();
  expect(screen.getByRole('button', {name: /Closed client/})).toBeVisible();
  expect(screen.getByRole('button', {name: 'Show only cases needing attention'})).toHaveAttribute('aria-pressed', 'true');
});

it('says so when nothing needs attention', () => {
  render(<CaseList cases={[cases[4], cases[5]]} selected={null} onSelect={() => {}} evaluationAt={at}/>);
  expect(screen.getByText('Nothing needs your attention right now.')).toBeVisible();
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});
