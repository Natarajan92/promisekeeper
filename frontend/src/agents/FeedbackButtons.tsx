import { useState } from 'react';
import type { ApiClient } from '../api/client';

type Target = 'RECOMMENDATION' | 'DRAFT';

export function FeedbackButtons({api, did, cid, investigationId, target}: {api: ApiClient; did: string; cid: string; investigationId: string; target: Target}) {
  const [rating, setRating] = useState<'UP' | 'DOWN' | null>(null);
  const [comment, setComment] = useState('');
  const [state, setState] = useState<'idle' | 'saving' | 'saved'>('idle');
  const [message, setMessage] = useState('');
  const question = target === 'DRAFT' ? 'Was this draft useful?' : 'Was this recommendation useful?';
  async function send(choice: 'UP' | 'DOWN', text: string | null) {
    setState('saving'); setMessage('');
    try {
      const response = await api.feedback(did, cid, {schema_version: '1', operation_id: crypto.randomUUID(), investigation_id: investigationId,
        target, rating: choice, comment: text});
      setState('saved');
      setMessage(response.sent_to_langsmith ? 'Saved. Thanks, this helps improve the agents.' : 'Saved locally (LangSmith not configured).');
    } catch (error) {
      setState('idle');
      setMessage(`Feedback not saved: ${error instanceof Error ? error.message : 'try again.'}`);
    }
  }
  const id = `feedback-comment-${target.toLowerCase()}`;
  return <section className="feedback" aria-label={question}>
    <p className="feedback-question">{question}</p>
    {state !== 'saved' && <div className="feedback-actions">
      <button aria-pressed={rating === 'UP'} disabled={state === 'saving'} onClick={() => { setRating('UP'); void send('UP', null); }}>Helpful</button>
      <button aria-pressed={rating === 'DOWN'} disabled={state === 'saving'} onClick={() => setRating('DOWN')}>Needs work</button>
    </div>}
    {rating === 'DOWN' && state !== 'saved' && <div className="feedback-comment">
      <label htmlFor={id}>What should be better? (optional)</label>
      <textarea id={id} maxLength={500} rows={2} value={comment} onChange={event => setComment(event.target.value)}/>
      <button className="primary" disabled={state === 'saving'} onClick={() => void send('DOWN', comment.trim() || null)}>Send feedback</button>
    </div>}
    <p className="subtle" role="status" aria-live="polite">{message}</p>
  </section>;
}
