import type { Demonstration } from './types';
export const selectionKey = 'selected_demonstration_id';
export function resolveSelection(copies:Demonstration[], saved:string|null):string|null {
  if (saved && copies.some(copy => copy.id === saved)) return saved;
  return copies.length === 1 ? copies[0].id : null;
}
