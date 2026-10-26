"""New safety/language variations independent of the original eval strings."""
from datetime import datetime, timezone
import pytest
from promisekeeper.application.document_extraction import extract_document
from promisekeeper.domain.dates import deadline


def message(text):
    return 'Sender: Accounts team\nSent: 2026-10-20T10:00:00+05:30\n'+text+'\n'


@pytest.mark.parametrize('text',[
    'We will pay INR 5000 by 30 October 2026 after management approval.',
    'We will pay INR 5000 by 30 October 2026 once the goods arrive.',
    'We will pay INR 5000 by 30 October 2026 upon approval.',
    'We will pay INR 5000 by 30 October 2026 assuming finance agrees.',
    'She said: "We will pay INR 5000 by 30 October 2026."',
    'According to the customer, we will pay INR 5000 by 30 October 2026.',
    'This is a forwarded message: We will pay INR 5000 by 30 October 2026.',
    'Hum INR 5000 2026-10-30 ko pay kar denge agar approval mil gaya.',
    'Hum INR 5000 2026-10-30 ko pay nahi kar denge.',
    'We will pay INR 5000 by 30 October 2026 when the goods arrive.',
    'We will pay INR 5000 depending on cash flow by 30 October 2026.',
    'Customer promised: We will pay INR 5000 by 30 October 2026.',
    "'We will pay INR 5000 by 30 October 2026.'",
    'Hum INR 5000 2026-10-30 ko pay kar denge basharte stock mile.',
    'We will pay INR 5000 by 30 October 2026.\nCash flow permitting.',
    'We will pay INR 5000 by 30 October 2026.\nThis depends on receipt of funds.',
    'We will pay INR 5000 by 30 October 2026.\nYeh cash milne par hi hoga.',
    'We will pay INR 5000 by 30 October 2026.\nSubject: This is conditional on funding.',
    'We will pay INR 5000 by 30 October 2026.\nFrom: Only when cash arrives.',
])
def test_unqualified_substring_cannot_override_conditions_or_attribution(text):
    with pytest.raises(ValueError):extract_document(message(text),'whatsapp')


@pytest.mark.parametrize('role',['OWNER','THIRD_PARTY','UNVERIFIED'])
def test_other_roles_must_not_supply_active_customer_promises(role):
    text=message('We will pay INR 5000 by 30 October 2026.')
    with pytest.raises(ValueError):extract_document(text,'whatsapp',sender_role=role)
    context=extract_document(text,'whatsapp',sender_role=role,context_only=True)
    assert context['candidates']==[] and context['context_only']


@pytest.mark.parametrize('text',[
    'Hum INR 5000 2026-10-30 ko pay kar denge.',
    'Main INR 5000 2026-10-30 ko payment kar dunga.',
    'Ham INR 5000 2026-10-30 ko pay karenge.',
    'Payment of INR 5000 will be made by 30 October 2026.',
    'The payment of INR 5000 will be transferred by 30 October 2026.',
])
def test_supported_first_person_and_passive_future_promises(text):
    result=extract_document(message(text),'whatsapp')
    candidate=result['candidates'][0]
    assert candidate['kind']=='COMMITMENT'
    assert candidate['amount_text']=='5000' and candidate['date_text'] in {'2026-10-30','30 October 2026'}
    assert candidate['clause'] in text


def test_reviewed_weekday_policy_preserves_source_expression_and_shows_interpretation():
    result=extract_document(message('We will pay INR 5000 by next Friday.'),'whatsapp')
    item=result['candidates'][0]
    assert item['date_text']=='next Friday'
    assert item['interpreted_date']=='2026-10-23'
    assert item['interpreted_currency']=='INR'
    assert any('2026-10-23' in w for w in result['warnings'])
    source=datetime.fromisoformat('2026-10-20T10:00:00+05:30')
    assert deadline('next Friday',original_at=source).error=='UNRESOLVED_DATE'
    assert deadline('next Friday',original_at=source,allow_weekday=True).expires_at==datetime(2026,10,23,18,30,tzinfo=timezone.utc)


def test_same_weekday_means_seven_days_later_and_source_day_is_not_run_day():
    source=datetime.fromisoformat('2026-10-23T00:30:00+05:30')
    assert deadline('next Friday',original_at=source,allow_weekday=True).expires_at==datetime(2026,10,30,18,30,tzinfo=timezone.utc)


@pytest.mark.parametrize('subject',['Payment when cash arrives','This is conditional on funding','Customer said we will pay'])
def test_email_subject_cannot_silently_qualify_a_body_promise(subject):
    text=f'From: accounts@econ.example\nDate: Tue, 20 Oct 2026 10:00:00 +0530\nSubject: {subject}\nContent-Type: text/plain\n\nWe will pay INR 5000 by 30 October 2026.\n'
    with pytest.raises(ValueError):extract_document(text,'customer_email')


def test_email_body_header_lookalikes_are_body_and_plain_invoice_subject_is_supported():
    base='From: accounts@econ.example\nDate: Tue, 20 Oct 2026 10:00:00 +0530\nSubject: Invoice EC-101\nContent-Type: text/plain\n\nWe will pay INR 5000 by 30 October 2026.\n'
    assert extract_document(base,'customer_email')['candidates'][0]['kind']=='COMMITMENT'
    with pytest.raises(ValueError):extract_document(base+'Subject: Funding required.\n','customer_email')
