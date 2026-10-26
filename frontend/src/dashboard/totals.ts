import type {CaseSummary} from '../api/types';

export interface Totals {inrMinor:bigint; recordedMinor:bigint; unknownCount:number; otherCurrencyCount:number}

/**
 * "Still to collect" for the Dashboard, from open cases only (spec: Decisions, "Still to collect").
 * Verified and recorded INR remainders are summed; recorded ones are also totalled separately so the
 * page can say how much is not yet verified. Unknown balances and other currencies are never summed,
 * only counted, so an unknown is never shown as zero.
 */
export function collectTotals(cases:CaseSummary[]):Totals {
  const totals:Totals={inrMinor:0n,recordedMinor:0n,unknownCount:0,otherCurrencyCount:0};
  for(const item of cases) {
    if(item.lifecycle!=='OPEN')continue;
    if(item.balance_label==='UNKNOWN_REMAINDER'||!item.balance){totals.unknownCount++;continue;}
    if(item.currency!=='INR'||item.balance.currency!=='INR'){totals.otherCurrencyCount++;continue;}
    const amount=BigInt(item.balance.minor_units);
    totals.inrMinor+=amount;
    if(item.balance_label==='RECORDED_REMAINDER')totals.recordedMinor+=amount;
  }
  return totals;
}

/** How many open cases were summed into the INR total. */
export function summedCount(cases:CaseSummary[],totals:Totals) {
  return cases.filter(item=>item.lifecycle==='OPEN').length-totals.unknownCount-totals.otherCurrencyCount;
}
