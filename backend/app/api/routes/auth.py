from fastapi import APIRouter
from app.services import decision_service as svc

router = APIRouter(tags=["global-auth"])
router.add_api_route('/auth/contract', svc.global_auth_contract_endpoint, methods=['GET'], name='global_auth_contract_endpoint')
router.add_api_route('/auth/configuration', svc.global_auth_configuration_endpoint, methods=['GET'], name='global_auth_configuration_endpoint')
router.add_api_route('/auth/whoami', svc.global_auth_whoami_endpoint, methods=['GET'], name='global_auth_whoami_endpoint')
router.add_api_route('/auth/authorize', svc.global_auth_authorize_endpoint, methods=['POST'], name='global_auth_authorize_endpoint')
router.add_api_route('/auth/scopes', svc.global_auth_scopes_endpoint, methods=['GET'], name='global_auth_scopes_endpoint')
router.add_api_route('/auth/decision-rooms/{room_id}/access', svc.global_auth_room_access_endpoint, methods=['GET'], name='global_auth_room_access_endpoint')
router.add_api_route('/auth/readiness', svc.global_auth_readiness_endpoint, methods=['GET'], name='global_auth_readiness_endpoint')
