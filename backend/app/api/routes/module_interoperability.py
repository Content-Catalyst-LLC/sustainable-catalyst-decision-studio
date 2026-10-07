from fastapi import APIRouter
from app.services import decision_service as svc

router = APIRouter(tags=["module-interoperability"])
router.add_api_route('/module-interoperability/contract', svc.module_interoperability_contract_endpoint, methods=['GET'], name='module_interoperability_contract_endpoint')
router.add_api_route('/module-interoperability/template', svc.module_interoperability_template_endpoint, methods=['GET'], name='module_interoperability_template_endpoint')
router.add_api_route('/module-interoperability/validate', svc.module_interoperability_validate_endpoint, methods=['POST'], name='module_interoperability_validate_endpoint')
router.add_api_route('/module-interoperability/decisions/{decision_id}', svc.module_interoperability_get_endpoint, methods=['GET'], name='module_interoperability_get_endpoint')
router.add_api_route('/module-interoperability/decisions/{decision_id}', svc.module_interoperability_upsert_endpoint, methods=['PUT'], name='module_interoperability_upsert_endpoint')
router.add_api_route('/module-interoperability/decisions/{decision_id}/share', svc.module_interoperability_share_endpoint, methods=['POST'], name='module_interoperability_share_endpoint')
router.add_api_route('/module-interoperability/decisions/{decision_id}/evidence/{evidence_ref:path}', svc.module_interoperability_evidence_endpoint, methods=['GET'], name='module_interoperability_evidence_endpoint')
router.add_api_route('/module-interoperability/decisions/{decision_id}/diagnostics', svc.module_interoperability_diagnostics_endpoint, methods=['GET'], name='module_interoperability_diagnostics_endpoint')
