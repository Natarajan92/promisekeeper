"""Offline extraction must retain quoted tokens rather than invent money facts."""
import pytest
from promisekeeper.application.document_extraction import extract_document


def message(body):
    return 'Sender: Econ accounts\nSent: 2026-10-20T10:00:00+05:30\n'+body+'\n'


@pytest.mark.parametrize('currency', ['INR', 'inr', 'Rs.', '₹'])
def test_currency_is_a_verbatim_source_token(currency):
    result=extract_document(message(f'We will pay {currency} 60000 by 30 October 2026.'),'whatsapp')
    item=result['candidates'][0]
    assert item['currency_text']==currency
    assert item['amount_text']=='60000'
    assert item['currency_text'] in item['clause']


@pytest.mark.parametrize('amount', ['1.234', '1.2.3', '-100', '+100'])
def test_malformed_amounts_are_not_partially_extracted(amount):
    with pytest.raises(ValueError):
        extract_document(message(f'We paid INR {amount} on 20 October 2026.'),'whatsapp')


def test_parser_uses_text_and_retains_relative_date_without_guessing():
    result=extract_document(message("We'll pay INR 12345 by next Friday."),'whatsapp')
    assert result['candidates'][0]['date_text']=='next Friday'
    assert result['warnings']
    assert result['event_at'].endswith('+05:30')


def test_repeated_quote_and_context_override_are_rejected():
    line='We paid INR 60000 on 20 October 2026.'
    for content,context in [(message(line+'\n'+line),False),(message(line),True)]:
        with pytest.raises(ValueError):extract_document(content,'whatsapp',context_only=context)


@pytest.mark.parametrize('body',[
    'We cannot pay INR 40000 by 30 October 2026.',
    'We will not pay INR 40000 by 30 October 2026.',
    'We have not paid INR 40000 on 20 October 2026.',
    'If the project finishes we will pay INR 40000 by 30 October 2026.',
    'We may pay INR 40000 by 30 October 2026.',
    'Can you pay INR 40000 by 30 October 2026?',
    'The invoice says pay INR 40000 by 30 October 2026.',
    'We need to pay INR 40000 by 30 October 2026.',
])
def test_qualified_or_negative_wording_cannot_become_positive_financial_evidence(body):
    with pytest.raises(ValueError):extract_document(message(body),'whatsapp')


def test_downstream_candidate_limit_is_rejected_before_confirmation():
    body='\n'.join(f'We will pay INR {i} by 30 October 2026.' for i in range(1,32))
    with pytest.raises(ValueError,match='30'):
        extract_document(message(body),'whatsapp')


@pytest.mark.parametrize('reference',['NOVA-401','NO-101','NUMBER-101'])
def test_invoice_number_prefix_does_not_consume_identifier_letters(reference):
    for prefix in ['invoice ','invoice No. ','invoice number ']:
        result=extract_document(message(f'For {prefix}{reference}, we will pay INR 40000 by 30 October 2026.'),'whatsapp')
        assert result['invoice_references']==[reference]


@pytest.mark.parametrize('body',[
    'We will pay INR 40000 of INR 90000 by 30 October 2026.',
    'We will pay INR 40000 by 28 October 2026 or by 30 October 2026.',
    'We paid INR 40000 on 20 October 2026. UTR: EC-T1 or reference: EC-T2.',
    'We paid INR 40000 and we will pay again by 30 October 2026.',
    'We will pay INR 40000 or 20000 by 30 October 2026.',
    'We will pay INR 40000 by 30 October 2026 or 2 November 2026.',
    'We paid INR 40000 on 20 October 2026. UTR: EC-T1 or EC-T2.',
    'We will pay INR 40000 and 20000 by 30 October 2026.',
    'We paid INR 40000 on 20 October 2026. UTR: EC-T1 and EC-T2.',
    'We paid INR 10000 less 500 withholding on 20 October 2026.',
])
def test_competing_fields_or_intents_are_not_silently_reduced_to_first_match(body):
    with pytest.raises(ValueError):extract_document(message(body),'whatsapp')


def _eml(body):
    return ('From: accounts@econ.example\nTo: owner@agency.example\nDate: Tue, 20 Oct 2026 10:00:00 +0530\n'
            'Subject: Promise for invoice EC-102\nContent-Type: text/plain; charset=utf-8\n\n'+body+'\n')


PROMISE='For invoice EC-102, we will pay INR 40000 by 30 October 2026.'


@pytest.mark.parametrize('body', [
    PROMISE+'\nThank you for your patience.\n\nEcon accounts',
    PROMISE+'\nWarm regards,\nMeera Shah\nMeera Textiles',
    'Namaste,\n'+PROMISE,
    'Dear Ravi,\n'+PROMISE+'\nThank you for your patience.\n\nEcon accounts\nFictional demonstration only.',
])
def test_courtesy_and_signature_lines_do_not_block_a_direct_promise(body):
    result=extract_document(_eml(body),'customer_email')
    commitments=[c for c in result['candidates'] if c['kind']=='COMMITMENT']
    assert len(result['candidates'])==1 and len(commitments)==1
    assert commitments[0]['amount_text']=='40000'


@pytest.mark.parametrize('body', [
    PROMISE+'\nThanks, subject to approval.',
    PROMISE+'\nRegards, will confirm later',
    PROMISE+'\nThank you\nMaybe next week',
    PROMISE+'\nOne two three four five six',
    PROMISE+'\nThank you\nRef 2',
    'Thank you, if possible\n'+PROMISE,
    'Econ accounts\n'+PROMISE,
])
def test_hedged_closings_are_still_refused(body):
    with pytest.raises(ValueError):
        extract_document(_eml(body),'customer_email')


@pytest.mark.parametrize('closing', [
    'Tentatively.', 'Provisionally.', 'This is an estimate.',
    'Indicative date.', 'Best efforts.', 'Awaiting funds.',
    'Probably.', 'Likely.', 'Presumably.', 'Proposed.',
])
@pytest.mark.parametrize('casing', ['lower', 'upper', 'title'])
@pytest.mark.parametrize('punctuation', ['.', ''])
@pytest.mark.parametrize('kind', ['customer_email', 'whatsapp'])
def test_trailing_qualifiers_cannot_be_discarded_as_customer_signatures(closing, casing, punctuation, kind):
    # A bounded direct promise followed by a qualifier is not unconditional,
    # including when the qualifier looks like a short capitalized signature.
    body=PROMISE+'\n'+getattr(closing.rstrip('.'),casing)()+punctuation+'\nMeera Shah\nMeera Textiles'
    content=_eml(body) if kind=='customer_email' else message(body)
    with pytest.raises(ValueError):
        extract_document(content,kind)


@pytest.mark.parametrize('closing', [
    'For your attention.', 'Details below.', 'This is final.',
    'Please keep this confidential.', 'All Clear', 'It Is Settled',
])
@pytest.mark.parametrize('kind', ['customer_email', 'whatsapp'])
def test_unknown_short_prose_cannot_be_discarded_as_customer_signatures(closing, kind):
    body=PROMISE+'\n'+closing
    content=_eml(body) if kind=='customer_email' else message(body)
    with pytest.raises(ValueError):
        extract_document(content,kind)


@pytest.mark.parametrize('signature', [
    'Econ accounts', 'Meera Shah\nMeera Textiles',
    'Ravi Kumar\nEconcity Accounts', 'Ravi',
    'Meera Shah\nAccounts Head\nMeera Textiles',
    'Lakshmi Rao\nKaveri Packaging', 'Suresh Mehta\nMeera Textiles',
])
def test_bounded_customer_names_and_account_signatures_preserve_the_exact_promise(signature):
    result=extract_document(_eml('Namaste,\n'+PROMISE+'\nWarm regards,\n'+signature),'customer_email')
    assert len(result['candidates'])==1
    assert result['candidates'][0]['kind']=='COMMITMENT'
    assert result['candidates'][0]['clause']==PROMISE
    assert result['candidates'][0]['amount_text']=='40000'


@pytest.mark.parametrize('greeting', ['Hi maybe next week', 'Dear sir only partial', 'Hello if possible', 'Hi Maybe next week', 'Dear Ravi, will confirm later'])
@pytest.mark.parametrize('where', ['before', 'after'])
def test_hedged_greetings_are_refused_before_and_after_the_promise(greeting, where):
    body=greeting+'\n'+PROMISE if where=='before' else PROMISE+'\n'+greeting
    with pytest.raises(ValueError):
        extract_document(_eml(body),'customer_email')


def test_four_line_trailing_block_is_refused():
    with pytest.raises(ValueError):
        extract_document(_eml(PROMISE+'\nMeera Shah\nAccounts Head\nMeera Textiles\nMumbai Office'),'customer_email')


def test_no_promise_line_in_the_document_cannot_crash_the_prose_check():
    # Defensive: the prose check must not raise an empty-sequence error.
    with pytest.raises(ValueError) as error:
        extract_document(_eml('Thank you for your patience.'),'customer_email')
    assert 'max()' not in str(error.value) and 'empty' not in str(error.value)


@pytest.mark.parametrize('label', ['Invoice: EC-102', 'Invoice #EC-102', 'Invoice No. EC-102'])
@pytest.mark.parametrize('thanks', ['Thanks for checking with us.', 'Thank you for following up.', 'Thanks for the reminder', 'Thank you for reaching out!', 'Thanks for your message.'])
def test_invoice_label_and_reminder_courtesy_lines_are_harmless(label, thanks):
    result=extract_document('Sender: Acme accounts\nSent: 2026-10-13T11:00:00+05:30\n'+label+'\n\nWe will pay INR 80000 by 20 October 2026.\n'+thanks+'\n','whatsapp')
    assert [c['kind'] for c in result['candidates']]==['COMMITMENT']


@pytest.mark.parametrize('extra', ['Invoice: AD-201 partly', 'Thanks for checking, will see', 'Invoice: AD-201 AD-202'])
def test_hedged_label_and_courtesy_variants_are_refused(extra):
    for body in ('Sender: Acme\nSent: 2026-10-13T11:00:00+05:30\n'+extra+'\nWe will pay INR 80000 by 20 October 2026.\n',
                 'Sender: Acme\nSent: 2026-10-13T11:00:00+05:30\nWe will pay INR 80000 by 20 October 2026.\n'+extra+'\n'):
        with pytest.raises(ValueError):
            extract_document(body,'whatsapp')


@pytest.mark.parametrize('body', [
    'Dear Sir,\n\nHope you are doing well.\n\n'+PROMISE+'\n\nThank you for your patience.\n\nWarm regards,\nLakshmi Rao\nKaveri Packaging',
    'Hope you are well!\n'+PROMISE,
])
def test_hope_you_are_well_courtesy_does_not_block_a_direct_promise(body):
    # Regression (course-demo pack): SAFE_PROSE accepts this courtesy line, but the
    # whole-document qualifier screen refused it for the word "hope".
    result=extract_document(_eml(body),'customer_email')
    assert [c['amount_text'] for c in result['candidates'] if c['kind']=='COMMITMENT']==['40000']


@pytest.mark.parametrize('body', [
    'Hope you are doing well, we will pay INR 40000 by 30 October 2026.',
    'We hope to pay INR 40000 by 30 October 2026.',
    'Hope you are doing well.\nWe hope to pay INR 40000 by 30 October 2026.',
    PROMISE+'\nHope this works.',
    PROMISE+'\nHope you are doing well if possible.',
])
def test_hope_wording_outside_the_exact_courtesy_line_is_still_refused(body):
    with pytest.raises(ValueError):
        extract_document(_eml(body),'customer_email')


# --- Task 8 upload robustness regressions -------------------------------------------

LABEL_WORDS=['Invoice unless','Invoice: unpaid','Invoice conditional','Invoice partly','Invoice unpaid','Invoice nothing',
             'Invoice cancelled','Invoice disputed','Invoice:unpaid','Invoice #pending','Invoice No. later','Invoice until.']


@pytest.mark.parametrize('label',LABEL_WORDS)
@pytest.mark.parametrize('where',['before','after'])
def test_invoice_label_with_a_word_instead_of_an_id_cannot_sit_beside_a_promise(label,where):
    # Regression: SAFE_PROSE accepted "Invoice <any word>" as a harmless label, and
    # the qualifier screen skipped every SAFE_PROSE line, so qualifier words passed.
    promise='We will pay INR 40000 by 30 October 2026.'
    body=label+'\n'+promise if where=='before' else promise+'\n'+label
    with pytest.raises(ValueError):
        extract_document(message(body),'whatsapp')
    with pytest.raises(ValueError):
        extract_document(_eml(body),'customer_email')


@pytest.mark.parametrize('label',['Invoice EC-102.','Invoice: EC-102','Invoice #EC-102','Invoice No. EC-102','Hope you are doing well.'])
def test_real_invoice_labels_and_the_exact_courtesy_line_stay_harmless(label):
    result=extract_document(message(label+'\nWe will pay INR 40000 by 30 October 2026.'),'whatsapp')
    assert [c['kind'] for c in result['candidates']]==['COMMITMENT']


def test_qualifier_screen_exemption_is_only_the_exact_hope_courtesy():
    from promisekeeper.domain.document_rules import HOPE_COURTESY
    assert HOPE_COURTESY.fullmatch('Hope you are doing well.') and HOPE_COURTESY.fullmatch('hope you are well!')
    assert HOPE_COURTESY.fullmatch('Invoice unless') is None and HOPE_COURTESY.fullmatch('Thanks') is None


@pytest.mark.parametrize('amount,want',[('₹40000','40000'),('₹40,000','40,000'),('₹1,20,000','1,20,000'),('Rs. 1,20,000.50','1,20,000.50')])
def test_non_ascii_and_indian_grouped_email_amounts_are_quoted_exactly(amount,want):
    # Regression: a str email body with non-ASCII text was decoded through
    # raw-unicode-escape, turning "₹" into the literal text "₹".
    text=_eml(f'For invoice EC-102, we will pay {amount} by 30 October 2026.\n\nRegards,\nRavi')
    result=extract_document(text,'customer_email')
    [candidate]=result['candidates']
    assert candidate['amount_text']==want and candidate['clause'] in text and text.count(candidate['clause'])==1


def test_non_utf8_declared_email_with_non_ascii_text_is_refused_plainly():
    text=_eml('For invoice EC-102, we will pay ₹40000 by 30 October 2026.').replace('charset=utf-8','charset=iso-8859-1')
    with pytest.raises(ValueError,match='UTF-8'):
        extract_document(text,'customer_email')


@pytest.mark.parametrize('encoding,body',[
    ('base64','Rm9yIGludm9pY2UgRUMtMTAyLCB3ZSB3aWxsIHBheSBJTlIgNDAwMDAgYnkgMzAgT2N0b2JlciAyMDI2Lgo='),
    ('quoted-printable','For invoice EC-102, we will pay =E2=82=B940000 by 30 October 2026.'),
])
def test_encoded_email_bodies_are_refused_with_a_plain_reason(encoding,body):
    text=_eml(body).replace('charset=utf-8\n',f'charset=utf-8\nContent-Transfer-Encoding: {encoding}\n')
    with pytest.raises(ValueError,match='encoded'):
        extract_document(text,'customer_email')


def test_ascii_quoted_printable_body_that_is_verbatim_still_works():
    text=_eml(PROMISE).replace('charset=utf-8\n','charset=utf-8\nContent-Transfer-Encoding: quoted-printable\n')
    assert [c['kind'] for c in extract_document(text,'customer_email')['candidates']]==['COMMITMENT']


def test_plain_and_html_alternative_with_the_same_sentence_is_refused_plainly():
    text=('From: accounts@econ.example\nDate: Tue, 20 Oct 2026 10:00:00 +0530\nSubject: Promise for invoice EC-102\n'
          'MIME-Version: 1.0\nContent-Type: multipart/alternative; boundary="b1"\n\n--b1\nContent-Type: text/plain; charset=utf-8\n\n'
          +PROMISE+'\n--b1\nContent-Type: text/html; charset=utf-8\n\n<p>'+PROMISE+'</p>\n--b1--\n')
    with pytest.raises(ValueError,match='HTML'):
        extract_document(text,'customer_email')


@pytest.mark.parametrize('greeting',['Namaste ji','Namaste ji,','Hello ji!','Dear Ravi ji,'])
def test_ji_honorific_greeting_is_harmless(greeting):
    result=extract_document(message(greeting+'\nHum ₹48000 2026-11-04 ko payment kar denge.\nThank you'),'whatsapp')
    assert [c['amount_text'] for c in result['candidates']]==['48000']


@pytest.mark.parametrize('greeting',['Namaste ji, if possible','Namaste ji maybe later','Ji'])
def test_ji_greeting_still_screens_qualifiers(greeting):
    with pytest.raises(ValueError):
        extract_document(message(greeting+'\nHum ₹48000 2026-11-04 ko payment kar denge.'),'whatsapp')


@pytest.mark.parametrize('label',['Invoice unless1','Invoice 2pay','Invoice: unpaid9','Invoice #later2','Invoice No. 7pending',
                                  'Invoice EC-unless1','Invoice X1_maybe','Invoice 12paid'])
@pytest.mark.parametrize('where',['before','after'])
def test_invoice_ids_with_glued_qualifier_words_are_not_harmless_labels(label,where):
    # Review fix: word-boundary screening missed words glued to digits/underscores.
    promise='We will pay INR 40000 by 30 October 2026.'
    body=label+'\n'+promise if where=='before' else promise+'\n'+label
    with pytest.raises(ValueError):
        extract_document(message(body),'whatsapp')


@pytest.mark.parametrize('label',['Invoice KP-1004','Invoice: MT-1001','Invoice #INV-2026-001','Invoice No. LE-1005','Invoice SF-1003.'])
def test_ordinary_invoice_ids_remain_harmless_labels(label):
    result=extract_document(message(label+'\nWe will pay INR 40000 by 30 October 2026.'),'whatsapp')
    assert [c['kind'] for c in result['candidates']]==['COMMITMENT']


GROUPING='A quoted INR amount is not a plain number. Use digits with standard grouping, for example 48000, 48,000.50 or 1,20,000; no amount was guessed.'
PRECISION='A quoted INR amount has more than two decimal places; paise cannot be rounded and no amount was selected.'


@pytest.mark.parametrize('amount,want',[('₹1,20,00',GROUPING),('₹12,00',GROUPING),('INR 48,00,0',GROUPING),('Rs. 1,2,3',GROUPING),
                                        ('₹48000.505',PRECISION),('INR 1,20,000.123',PRECISION)])
def test_badly_formed_quoted_amounts_get_the_matching_plain_reason(amount,want):
    with pytest.raises(ValueError) as error:
        extract_document(message(f'We will pay {amount} by 30 October 2026.'),'whatsapp')
    assert str(error.value)==want
