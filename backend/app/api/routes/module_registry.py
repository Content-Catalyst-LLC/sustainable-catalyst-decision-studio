from fastapi import APIRouter
from app.services import decision_service as svc

router = APIRouter(tags=["decision-module-registry"])

router.add_api_route('/decision-module-registry', svc.unified_module_registry_endpoint, methods=['GET'], name='unified_module_registry_endpoint')
router.add_api_route('/decision-module-registry/modules', svc.unified_module_registry_modules_endpoint, methods=['GET'], name='unified_module_registry_modules_endpoint')
router.add_api_route('/decision-module-registry/modules/{module_id}', svc.unified_module_registry_module_endpoint, methods=['GET'], name='unified_module_registry_module_endpoint')
router.add_api_route('/decision-module-registry/capabilities', svc.unified_module_registry_capabilities_endpoint, methods=['GET'], name='unified_module_registry_capabilities_endpoint')
router.add_api_route('/decision-module-registry/providers', svc.unified_module_registry_providers_endpoint, methods=['GET'], name='unified_module_registry_providers_endpoint')
router.add_api_route('/decision-module-registry/readiness', svc.unified_module_registry_readiness_endpoint, methods=['GET'], name='unified_module_registry_readiness_endpoint')
router.add_api_route('/decision-module-registry/validate', svc.unified_module_registry_validate_endpoint, methods=['POST'], name='unified_module_registry_validate_endpoint')
