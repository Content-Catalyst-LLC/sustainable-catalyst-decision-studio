from fastapi import APIRouter
from app.services import decision_service as svc

router = APIRouter(tags=["module-artifacts"])
router.add_api_route('/module-artifacts/contract', svc.module_artifact_contract_endpoint, methods=['GET'], name='module_artifact_contract_endpoint')
router.add_api_route('/module-artifacts/template', svc.module_artifact_template_endpoint, methods=['GET'], name='module_artifact_template_endpoint')
router.add_api_route('/module-artifacts/validate', svc.module_artifact_validate_endpoint, methods=['POST'], name='module_artifact_validate_endpoint')
router.add_api_route('/module-artifacts/decisions/{decision_id}', svc.module_artifact_list_endpoint, methods=['GET'], name='module_artifact_list_endpoint')
router.add_api_route('/module-artifacts/decisions/{decision_id}', svc.module_artifact_create_endpoint, methods=['POST'], name='module_artifact_create_endpoint')
router.add_api_route('/module-artifacts/decisions/{decision_id}/{artifact_id}', svc.module_artifact_get_endpoint, methods=['GET'], name='module_artifact_get_endpoint')
router.add_api_route('/module-artifacts/decisions/{decision_id}/{artifact_id}/revisions', svc.module_artifact_revise_endpoint, methods=['POST'], name='module_artifact_revise_endpoint')
router.add_api_route('/module-artifacts/decisions/{decision_id}/{artifact_id}/lineage', svc.module_artifact_lineage_endpoint, methods=['GET'], name='module_artifact_lineage_endpoint')
