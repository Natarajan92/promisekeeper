import { afterEach, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { ApiClient } from '../src/api/client';
import { words } from '../src/components/format';
import { FinancialSummary } from '../src/cases/CaseEvidence';
import { InvestigationControls } from '../src/investigations/InvestigationControls';
import { caseView, facts } from './fixtures';

afterEach(cleanup);

it('explains draft safety reasons in plain language', () => {
  expect(words('NOTE_HAS_DIGITS')).toBe('The personal note contains a number. Amounts and dates belong only in the fact lines.');
  for (const code of ['NOTE_PAYMENT_TOPIC', 'NOTE_INSTRUCTION_LIKE', 'NOTE_TOO_LONG', 'NOTE_MULTI_PARAGRAPH', 'UNSUPPORTED_CLAUSE', 'UNSUPPORTED_FEE_OR_THREAT',
    'UNSUPPORTED_PAYMENT_INSTRUCTION', 'UNSUPPORTED_PAYMENT_ASSERTION', 'UNSUPPORTED_CURRENCY', 'UNSUPPORTED_AMOUNT', 'UNRESOLVED_PLACEHOLDER',
    'MISSING_REQUIRED_CLAUSE', 'PROVIDER_CIRCUIT_OPEN']) {
    expect(words(code)).not.toBe(code.toLowerCase().replaceAll('_', ' '));
    expect(words(code)).toMatch(/^[A-Z].*\.$/);
  }
});

it('describes balance certainty without system codes', () => {
  render(<FinancialSummary facts={facts as any}/>);
  expect(screen.getByText(/Balance confirmed by verified records\./)).toBeInTheDocument();
  expect(screen.queryByText(/certainty: KNOWN/)).toBeNull();
});

it('keeps an existing recommendation in front of a re-run', () => {
  render(<InvestigationControls api={new ApiClient()} view={{...caseView, current_result: {action: 'FOLLOW_UP'}} as any} onRefresh={() => {}}/>);
  expect(screen.getByRole('button', {name: 'Investigate case'})).not.toHaveClass('primary');
  expect(screen.getByText(/A current recommendation is saved/)).toBeInTheDocument();
});
