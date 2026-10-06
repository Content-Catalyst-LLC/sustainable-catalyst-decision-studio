from fastapi import APIRouter
from app.services import decision_service as svc

router = APIRouter(tags=["system"])

router.add_api_route('/health', svc.health, methods=['GET'], name='health')
router.add_api_route('/release', svc.release_endpoint, methods=['GET'], name='release_endpoint')
router.add_api_route('/ai/status', svc.ai_status, methods=['GET'], name='ai_status')
router.add_api_route('/analyze', svc.analyze_endpoint, methods=['POST'], name='analyze_endpoint')
router.add_api_route('/brief', svc.brief_endpoint, methods=['POST'], name='brief_endpoint')
router.add_api_route('/report', svc.report_endpoint, methods=['POST'], name='report_endpoint')
router.add_api_route('/integrated-brief', svc.integrated_brief_endpoint, methods=['POST'], name='integrated_brief_endpoint')
router.add_api_route('/decision-packet/brief', svc.decision_packet_brief_endpoint, methods=['POST'], name='decision_packet_brief_endpoint')
router.add_api_route('/public/landing-template', svc.public_landing_template_endpoint, methods=['GET'], name='public_landing_template_endpoint')
router.add_api_route('/public/demo-template', svc.public_demo_template_endpoint, methods=['GET'], name='public_demo_template_endpoint')
router.add_api_route('/templates', svc.templates, methods=['GET'], name='templates')
