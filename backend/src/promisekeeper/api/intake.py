from pathlib import Path
from fastapi import APIRouter,Request
from fastapi.responses import FileResponse
from promisekeeper.application.intake import preview_import,commit_import,intake_overview,confirm_allocation,confirm_ledger_review,original_import
from promisekeeper.application.operations import CommandError
from promisekeeper.contracts.common import Id
from promisekeeper.contracts.intake import IntakePreview,IntakeCommit,AllocationCommand,LedgerReviewCommand

router=APIRouter()
SAMPLES={'customers.csv','invoices.csv','payments-initial.csv','payments-later.csv','allocations.csv','bank-statement.csv',
         'remittance-email.eml','customer-promise.eml','customer-payment-claim.eml','whatsapp-promise.txt','whatsapp-paid.txt'}


@router.post('/intake/previews')
def preview(command:IntakePreview,request:Request):return preview_import(request.app.state.db,command.model_dump())


@router.post('/intake/commits')
def commit(command:IntakeCommit,request:Request):return commit_import(request.app.state.db,command.model_dump())


@router.get('/demonstrations/{did}/intake')
def overview(did:Id,request:Request):return intake_overview(request.app.state.db,did)


@router.post('/demonstrations/{did}/intake/allocations')
def allocate(did:Id,command:AllocationCommand,request:Request):return confirm_allocation(request.app.state.db,did,command.model_dump())


@router.post('/demonstrations/{did}/intake/ledger-reviews')
def review(did:Id,command:LedgerReviewCommand,request:Request):return confirm_ledger_review(request.app.state.db,did,command.model_dump())


@router.get('/demonstrations/{did}/intake/files/{bid}')
def original(did:Id,bid:Id,request:Request):return original_import(request.app.state.db,did,bid)


@router.get('/intake/samples/{filename}')
def sample(filename:str):
    if filename not in SAMPLES:raise CommandError('NOT_FOUND',404)
    path=Path(__file__).resolve().parents[4]/'docs'/'demo-import'/filename
    if not path.is_file():raise CommandError('NOT_FOUND',404)
    return FileResponse(path,filename=filename,media_type='text/plain; charset=utf-8')
