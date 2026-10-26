from promisekeeper.application.payment_matching import suggest_invoices


def test_generic_company_suffix_and_shared_city_do_not_suggest_unrelated_customer():
    payment=dict(payer_name='Econ Private Limited',payer_alias='ECONC',address='12 1st Gandhinagar KR PURAM Bangalore 560012')
    invoices=[dict(case_id='econ',invoice_id='EC-101',customer_name='Econcity Private Limited',customer_alias='econ',address='12 1st Gandhinagar KR Bangalore 560012'),
              dict(case_id='acme',invoice_id='AD-201',customer_name='Acme Design Studio',customer_alias='Acme',address='33 Church Street Bangalore 560001')]
    matches=suggest_invoices(payment,invoices)
    assert [m['case_id'] for m in matches]==['econ']
    assert all('identity' in ' '.join(m['reasons']) for m in matches)
