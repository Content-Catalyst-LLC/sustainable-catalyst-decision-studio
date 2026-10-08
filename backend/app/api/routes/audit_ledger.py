from fastapi import APIRouter
from app.services import decision_service as svc

router = APIRouter(tags=["decision-audit-ledger"])
router.add_api_route('/audit-ledger/contract', svc.audit_ledger_contract_endpoint, methods=['GET'], name='audit_ledger_contract_endpoint')
router.add_api_route('/audit-ledger/readiness', svc.audit_ledger_readiness_endpoint, methods=['GET'], name='audit_ledger_readiness_endpoint')
router.add_api_route('/audit-ledger/validate', svc.audit_ledger_validate_endpoint, methods=['POST'], name='audit_ledger_validate_endpoint')
router.add_api_route('/audit-ledger/decisions/{decision_id}', svc.audit_ledger_list_endpoint, methods=['GET'], name='audit_ledger_list_endpoint')
router.add_api_route('/audit-ledger/decisions/{decision_id}/events/{event_id}', svc.audit_ledger_event_endpoint, methods=['GET'], name='audit_ledger_event_endpoint')
router.add_api_route('/audit-ledger/decisions/{decision_id}/verify', svc.audit_ledger_verify_endpoint, methods=['GET'], name='audit_ledger_verify_endpoint')
router.add_api_route('/audit-ledger/decisions/{decision_id}/replay', svc.audit_ledger_replay_endpoint, methods=['GET'], name='audit_ledger_replay_endpoint')
router.add_api_route('/audit-ledger/decisions/{decision_id}/events', svc.audit_ledger_append_endpoint, methods=['POST'], name='audit_ledger_append_endpoint')
