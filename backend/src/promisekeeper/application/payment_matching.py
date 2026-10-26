"""Read-only explanations, never an automatic customer identity or settlement decision."""
from difflib import SequenceMatcher
import re


def tokens(value):
    return set(re.findall(r'[a-z0-9]+',value.casefold()))-{'private','limited','pvt','ltd'}


def suggest_invoices(payment,invoices):
    suggestions=[]
    for invoice in invoices:
        reasons=[];score=0
        if payment.get('invoice_reference') and payment['invoice_reference']==invoice['invoice_id']:
            score+=100;reasons.append('Exact supplied invoice reference; confirmation still required.')
        payer=' '.join([payment.get('payer_name',''),payment.get('payer_alias','')])
        customer=' '.join([invoice.get('customer_name',''),invoice.get('customer_alias','')])
        common=tokens(payer)&tokens(customer)
        if common:
            score+=30;reasons.append('Name/alias tokens overlap: '+', '.join(sorted(common))+'. This does not establish identity.')
        elif tokens(payer) and tokens(customer) and SequenceMatcher(None,' '.join(sorted(tokens(payer))),' '.join(sorted(tokens(customer)))).ratio()>=0.65:
            score+=10;reasons.append('Names look similar but contain different words; review the original names.')
        address=tokens(payment.get('address',''))&tokens(invoice.get('address',''))
        # A shared city or generic company suffix alone is too weak to suggest
        # a customer. Preserve address evidence alongside a stronger signal.
        if address and (score or len(address)>=3):
            score+=min(len(address),10);reasons.append('Address tokens overlap: '+', '.join(sorted(address))+'. Abbreviations are not assumed equivalent.')
        if score:
            suggestions.append(dict(case_id=invoice['case_id'],invoice_id=invoice['invoice_id'],
                                    customer_name=invoice['customer_name'],reasons=reasons,_rank=score))
    suggestions.sort(key=lambda row:(-row['_rank'],row['invoice_id']))
    return [{k:v for k,v in row.items() if k!='_rank'} for row in suggestions]
