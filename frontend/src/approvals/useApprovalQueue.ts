import type {CaseEntry, Workspace} from '../store/useWorkspace';
import {buildQueue, type ApprovalItem} from './queue';

/**
 * The approval queue from the shared case-detail store. `items` is null while the store is loading
 * (so a count is never shown as 0 too early); cases that failed to load are returned in `failed`.
 * The store's refresh() reloads every case view, so the queue recomputes after any decision.
 */
export function useApprovalQueue(ws:Workspace):{items:ApprovalItem[]|null; failed:CaseEntry[]} {
  const {cases,list,detailsLoading}=ws;
  const failed=cases.filter(entry=>!entry.view&&!!entry.error);
  // A case still without its view or an error has not loaded yet.
  const pending=!list||detailsLoading||cases.some(entry=>!entry.view&&!entry.error);
  return {items:pending?null:buildQueue(cases),failed};
}
