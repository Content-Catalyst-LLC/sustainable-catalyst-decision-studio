from fastapi import APIRouter
from app.services import decision_service as svc

router = APIRouter(tags=["repository"])
router.add_api_route('/repository/authority', svc.repository_authority_endpoint, methods=['GET'], name='repository_authority_endpoint')
router.add_api_route('/repository/projects', svc.repository_create_project_endpoint, methods=['POST'], name='repository_create_project_endpoint')
router.add_api_route('/repository/projects/{project_id}', svc.repository_get_project_endpoint, methods=['GET'], name='repository_get_project_endpoint')
router.add_api_route('/repository/decisions', svc.repository_create_decision_endpoint, methods=['POST'], name='repository_create_decision_endpoint')
router.add_api_route('/repository/decisions', svc.repository_list_decisions_endpoint, methods=['GET'], name='repository_list_decisions_endpoint')
router.add_api_route('/repository/decisions/{decision_id}', svc.repository_get_decision_endpoint, methods=['GET'], name='repository_get_decision_endpoint')
router.add_api_route('/repository/decisions/{decision_id}', svc.repository_patch_decision_endpoint, methods=['PATCH'], name='repository_patch_decision_endpoint')
router.add_api_route('/repository/decisions/{decision_id}/object', svc.repository_put_object_endpoint, methods=['PUT'], name='repository_put_object_endpoint')
router.add_api_route('/repository/decisions/{decision_id}/object', svc.repository_get_object_endpoint, methods=['GET'], name='repository_get_object_endpoint')
router.add_api_route('/repository/decisions/{decision_id}/modules/{module_id}', svc.repository_bind_module_endpoint, methods=['PUT'], name='repository_bind_module_endpoint')
router.add_api_route('/repository/decisions/{decision_id}/snapshots', svc.repository_create_snapshot_endpoint, methods=['POST'], name='repository_create_snapshot_endpoint')
router.add_api_route('/repository/decisions/{decision_id}/snapshot', svc.repository_get_snapshot_endpoint, methods=['GET'], name='repository_get_snapshot_endpoint')
router.add_api_route('/repository/import/decision-object', svc.repository_import_decision_object_endpoint, methods=['POST'], name='repository_import_decision_object_endpoint')
