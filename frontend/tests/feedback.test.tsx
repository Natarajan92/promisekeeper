import { afterEach, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { ApiClient } from '../src/api/client';
import { FeedbackButtons } from '../src/agents/FeedbackButtons';
import { cid, did } from './fixtures';

afterEach(cleanup);
const iid = '44444444-4444-4444-8444-444444444444';

function recording(sent = false) {
  const posts: {url: string; body: Record<string, unknown>}[] = [];
  const api = new ApiClient(async (url, init) => {
    const body = JSON.parse(String(init?.body));
    posts.push({url: String(url), body});
    return new Response(JSON.stringify({schema_version: '1', sent_to_langsmith: sent,
      feedback: {id: 'f', case_id: cid, investigation_id: iid, target: body.target, rating: body.rating, comment: body.comment, created_at: '2026-10-24T10:00:00Z'}}), {status: 201});
  });
  return {api, posts};
}

it('thumbs up saves immediately and thanks the owner', async () => {
  const {api, posts} = recording(true);
  render(<FeedbackButtons api={api} did={did} cid={cid} investigationId={iid} target="RECOMMENDATION"/>);
  fireEvent.click(screen.getByRole('button', {name: 'Helpful'}));
  expect(await screen.findByText('Feedback saved. Thank you.')).toBeInTheDocument();
  expect(screen.queryByText(/improve the agents/i)).not.toBeInTheDocument();
  expect(screen.getByText('Forwarded to LangSmith.')).not.toBeVisible();
  fireEvent.click(screen.getByText('Delivery details'));
  expect(screen.getByText('Forwarded to LangSmith.')).toBeVisible();
  expect(posts[0].url).toContain(`/cases/${cid}/feedback?demonstration_id=${did}`);
  expect(posts[0].body).toMatchObject({investigation_id: iid, target: 'RECOMMENDATION', rating: 'UP', comment: null});
});

it('confirms a local save without inferring the forwarding configuration', async () => {
  const {api, posts} = recording(false);
  render(<FeedbackButtons api={api} did={did} cid={cid} investigationId={iid} target="DRAFT"/>);
  fireEvent.click(screen.getByRole('button', {name: 'Needs work'}));
  fireEvent.change(screen.getByLabelText('What should be better? (optional)'), {target: {value: 'Too formal'}});
  fireEvent.click(screen.getByRole('button', {name: 'Send feedback'}));
  expect(await screen.findByText('Feedback saved locally.')).toBeInTheDocument();
  expect(screen.queryByText(/LangSmith|not configured|improve the agents/i)).not.toBeInTheDocument();
  expect(posts[0].body).toMatchObject({target: 'DRAFT', rating: 'DOWN', comment: 'Too formal'});
});

it('shows a readable error and keeps the choice when saving fails', async () => {
  const api = new ApiClient(async () => new Response(JSON.stringify({schema_version: '1', error: {code: 'NOT_FOUND', message: 'Investigation not found.'}}), {status: 404}));
  render(<FeedbackButtons api={api} did={did} cid={cid} investigationId={iid} target="RECOMMENDATION"/>);
  fireEvent.click(screen.getByRole('button', {name: 'Helpful'}));
  expect(await screen.findByText(/Feedback not saved: Investigation not found\./)).toBeInTheDocument();
  expect(screen.getByRole('button', {name: 'Helpful'})).toBeEnabled();
});
