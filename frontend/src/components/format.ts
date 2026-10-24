import type { Money } from '../api/types';
export function money(value:Money|null|undefined):string {
  if(!value) return 'Unknown';
  const raw=BigInt(value.minor_units); const magnitude=raw<0n?-raw:raw;
  return `${value.currency} ${raw<0n?'-':''}${(magnitude/100n).toLocaleString('en-IN')}.${(magnitude%100n).toString().padStart(2,'0')}`;
}
export function instant(value:string|null|undefined):string {
  if(!value) return 'Unknown date';
  return new Intl.DateTimeFormat('en-GB',{day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit',hourCycle:'h23',timeZone:'Asia/Kolkata'}).format(new Date(value))+' IST';
}
export function words(value:string) {return value.toLowerCase().replaceAll('_',' ');}
