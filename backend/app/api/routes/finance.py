from fastapi import APIRouter
from app.services import decision_service as svc

router = APIRouter(tags=["finance"])
router.add_api_route('/finance/contract', svc.finance_contract_endpoint, methods=['GET'], name='finance_contract_endpoint')
router.add_api_route('/finance/template', svc.finance_template_endpoint, methods=['GET'], name='finance_template_endpoint')
router.add_api_route('/finance/decisions/{decision_id}', svc.finance_get_endpoint, methods=['GET'], name='finance_get_endpoint')
router.add_api_route('/finance/decisions/{decision_id}', svc.finance_put_endpoint, methods=['PUT'], name='finance_put_endpoint')
router.add_api_route('/finance/decisions/{decision_id}/assumptions', svc.finance_assumptions_get_endpoint, methods=['GET'], name='finance_assumptions_get_endpoint')
router.add_api_route('/finance/decisions/{decision_id}/assumptions', svc.finance_assumptions_put_endpoint, methods=['PUT'], name='finance_assumptions_put_endpoint')
router.add_api_route('/finance/decisions/{decision_id}/scenarios', svc.finance_scenarios_get_endpoint, methods=['GET'], name='finance_scenarios_get_endpoint')
router.add_api_route('/finance/decisions/{decision_id}/scenarios', svc.finance_scenarios_put_endpoint, methods=['PUT'], name='finance_scenarios_put_endpoint')
router.add_api_route('/finance/decisions/{decision_id}/workbench-receipts', svc.finance_workbench_receipts_get_endpoint, methods=['GET'], name='finance_workbench_receipts_get_endpoint')
router.add_api_route('/finance/decisions/{decision_id}/workbench-receipts', svc.finance_workbench_receipts_put_endpoint, methods=['PUT'], name='finance_workbench_receipts_put_endpoint')
router.add_api_route('/finance/import/legacy', svc.finance_legacy_import_endpoint, methods=['POST'], name='finance_legacy_import_endpoint')
