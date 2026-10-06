from fastapi import APIRouter
from app.services import decision_service as svc

router = APIRouter(tags=["decision-kernel"])

router.add_api_route('/decision-kernel/contracts', svc.decision_kernel_contracts_endpoint, methods=['GET'], name='decision_kernel_contracts_endpoint')
router.add_api_route('/decision-kernel/template', svc.decision_kernel_template_endpoint, methods=['GET'], name='decision_kernel_template_endpoint')
router.add_api_route('/decision-kernel/validate', svc.decision_kernel_validate_endpoint, methods=['POST'], name='decision_kernel_validate_endpoint')
router.add_api_route('/decision-modules', svc.decision_modules_endpoint, methods=['GET'], name='decision_modules_endpoint')
router.add_api_route('/decision-modules/{module_id}', svc.decision_module_endpoint, methods=['GET'], name='decision_module_endpoint')
router.add_api_route('/decision-modules/{module_id}/validate', svc.decision_module_validate_endpoint, methods=['POST'], name='decision_module_validate_endpoint')
