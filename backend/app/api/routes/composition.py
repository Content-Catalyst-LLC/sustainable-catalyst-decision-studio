from fastapi import APIRouter
from app.services import decision_service as svc

router = APIRouter(tags=["cross-module-composition"])
router.add_api_route('/decision-composition/contract', svc.composition_contract_endpoint, methods=['GET'], name='composition_contract_endpoint')
router.add_api_route('/decision-composition/template', svc.composition_template_endpoint, methods=['GET'], name='composition_template_endpoint')
router.add_api_route('/decision-composition/validate', svc.composition_validate_endpoint, methods=['POST'], name='composition_validate_endpoint')
router.add_api_route('/decision-composition/decisions/{decision_id}', svc.composition_get_endpoint, methods=['GET'], name='composition_get_endpoint')
router.add_api_route('/decision-composition/decisions/{decision_id}', svc.composition_put_endpoint, methods=['PUT'], name='composition_put_endpoint')
router.add_api_route('/decision-composition/decisions/{decision_id}/refresh', svc.composition_refresh_endpoint, methods=['POST'], name='composition_refresh_endpoint')
router.add_api_route('/decision-composition/decisions/{decision_id}/diagnostics', svc.composition_diagnostics_endpoint, methods=['GET'], name='composition_diagnostics_endpoint')
