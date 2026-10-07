from fastapi import APIRouter
from app.services import decision_service as svc

router = APIRouter(tags=["canvas"])
router.add_api_route('/canvas/contract', svc.canvas_contract_endpoint, methods=['GET'], name='canvas_contract_endpoint')
router.add_api_route('/canvas/template', svc.canvas_template_endpoint, methods=['GET'], name='canvas_template_endpoint')
router.add_api_route('/canvas/decisions/{decision_id}', svc.canvas_get_endpoint, methods=['GET'], name='canvas_get_endpoint')
router.add_api_route('/canvas/decisions/{decision_id}', svc.canvas_put_endpoint, methods=['PUT'], name='canvas_put_endpoint')
router.add_api_route('/canvas/decisions/{decision_id}/alternatives', svc.canvas_alternatives_get_endpoint, methods=['GET'], name='canvas_alternatives_get_endpoint')
router.add_api_route('/canvas/decisions/{decision_id}/alternatives', svc.canvas_alternatives_put_endpoint, methods=['PUT'], name='canvas_alternatives_put_endpoint')
router.add_api_route('/canvas/decisions/{decision_id}/criteria', svc.canvas_criteria_get_endpoint, methods=['GET'], name='canvas_criteria_get_endpoint')
router.add_api_route('/canvas/decisions/{decision_id}/criteria', svc.canvas_criteria_put_endpoint, methods=['PUT'], name='canvas_criteria_put_endpoint')
router.add_api_route('/canvas/decisions/{decision_id}/assumptions', svc.canvas_assumptions_get_endpoint, methods=['GET'], name='canvas_assumptions_get_endpoint')
router.add_api_route('/canvas/decisions/{decision_id}/assumptions', svc.canvas_assumptions_put_endpoint, methods=['PUT'], name='canvas_assumptions_put_endpoint')
router.add_api_route('/canvas/import/legacy', svc.canvas_legacy_import_endpoint, methods=['POST'], name='canvas_legacy_import_endpoint')
