from fastapi import APIRouter
from app.services import decision_service as svc

router = APIRouter(tags=["context-handoffs"])

router.add_api_route('/native-handoffs/contracts', svc.native_handoff_contracts_endpoint, methods=['GET'], name='native_handoff_contracts_endpoint')
router.add_api_route('/native-handoffs/template', svc.native_handoff_template_endpoint, methods=['GET'], name='native_handoff_template_endpoint')
router.add_api_route('/native-handoffs/receive', svc.native_handoff_receive_endpoint, methods=['POST'], name='native_handoff_receive_endpoint')
router.add_api_route('/native-handoffs/request', svc.native_handoff_request_endpoint, methods=['POST'], name='native_handoff_request_endpoint')
router.add_api_route('/native-handoffs/return', svc.native_handoff_return_endpoint, methods=['POST'], name='native_handoff_return_endpoint')
router.add_api_route('/decision-packet/native-handoff', svc.decision_packet_native_handoff_endpoint, methods=['POST'], name='decision_packet_native_handoff_endpoint')
router.add_api_route('/site-intelligence-context/contracts', svc.site_intelligence_context_contracts_endpoint, methods=['GET'], name='site_intelligence_context_contracts_endpoint')
router.add_api_route('/site-intelligence-context/template', svc.site_intelligence_context_template_endpoint, methods=['GET'], name='site_intelligence_context_template_endpoint')
router.add_api_route('/site-intelligence-context/build', svc.site_intelligence_context_build_endpoint, methods=['POST'], name='site_intelligence_context_build_endpoint')
router.add_api_route('/site-intelligence-context/validate', svc.site_intelligence_context_validate_endpoint, methods=['POST'], name='site_intelligence_context_validate_endpoint')
router.add_api_route('/decision-packet/site-intelligence-context', svc.decision_packet_site_intelligence_context_endpoint, methods=['POST'], name='decision_packet_site_intelligence_context_endpoint')
router.add_api_route('/decision-dependency-graph/template', svc.decision_dependency_graph_template_endpoint, methods=['GET'], name='decision_dependency_graph_template_endpoint')
router.add_api_route('/decision-dependency-graph/build', svc.decision_dependency_graph_build_endpoint, methods=['POST'], name='decision_dependency_graph_build_endpoint')
router.add_api_route('/decision-dependency-graph/validate', svc.decision_dependency_graph_validate_endpoint, methods=['POST'], name='decision_dependency_graph_validate_endpoint')
router.add_api_route('/decision-dependency-graph/impact', svc.decision_dependency_graph_impact_endpoint, methods=['POST'], name='decision_dependency_graph_impact_endpoint')
router.add_api_route('/decision-packet/dependency-graph', svc.decision_packet_dependency_graph_endpoint, methods=['POST'], name='decision_packet_dependency_graph_endpoint')
