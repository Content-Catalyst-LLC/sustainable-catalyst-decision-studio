from fastapi import APIRouter
from app.services import decision_service as svc

router = APIRouter(tags=["integrations"])

router.add_api_route('/integrations/modules', svc.integrations_modules_endpoint, methods=['GET'], name='integrations_modules_endpoint')
router.add_api_route('/integrations/module-navigation', svc.integrations_module_navigation_endpoint, methods=['GET'], name='integrations_module_navigation_endpoint')
router.add_api_route('/integrations/adapters', svc.integrations_adapters_endpoint, methods=['GET'], name='integrations_adapters_endpoint')
router.add_api_route('/integrations/platform', svc.integrations_platform_endpoint, methods=['GET'], name='integrations_platform_endpoint')
router.add_api_route('/integrations/contracts', svc.integrations_contracts_endpoint, methods=['GET'], name='integrations_contracts_endpoint')
router.add_api_route('/integrations/contracts/{product_id}', svc.integrations_contract_endpoint, methods=['GET'], name='integrations_contract_endpoint')
router.add_api_route('/integrations/validate', svc.integrations_validate_endpoint, methods=['POST'], name='integrations_validate_endpoint')
router.add_api_route('/integrations/import-batch', svc.integrations_import_batch_endpoint, methods=['POST'], name='integrations_import_batch_endpoint')
router.add_api_route('/decision-packet/platform-handoffs', svc.decision_packet_platform_handoffs_endpoint, methods=['GET'], name='decision_packet_platform_handoffs_endpoint')
router.add_api_route('/integrations/import', svc.integrations_import_endpoint, methods=['POST'], name='integrations_import_endpoint')
router.add_api_route('/decision-packet/import', svc.decision_packet_import_endpoint, methods=['POST'], name='decision_packet_import_endpoint')
