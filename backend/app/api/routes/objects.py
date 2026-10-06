from fastapi import APIRouter
from app.services import decision_service as svc

router = APIRouter(tags=["objects"])

router.add_api_route('/decision-object/template', svc.decision_object_template_endpoint, methods=['GET'], name='decision_object_template_endpoint')
router.add_api_route('/platform-context/template', svc.platform_context_template_endpoint, methods=['GET'], name='platform_context_template_endpoint')
router.add_api_route('/decision-object/from-packet', svc.decision_object_from_packet_endpoint, methods=['POST'], name='decision_object_from_packet_endpoint')
router.add_api_route('/decision-object/normalize', svc.decision_object_normalize_endpoint, methods=['POST'], name='decision_object_normalize_endpoint')
router.add_api_route('/decision-object/context', svc.decision_object_context_endpoint, methods=['POST'], name='decision_object_context_endpoint')
router.add_api_route('/decision-object/to-packet', svc.decision_object_to_packet_endpoint, methods=['POST'], name='decision_object_to_packet_endpoint')
router.add_api_route('/decision-packet/decision-object', svc.decision_packet_decision_object_endpoint, methods=['POST'], name='decision_packet_decision_object_endpoint')
router.add_api_route('/decision-object/evidence', svc.decision_object_evidence_endpoint, methods=['POST'], name='decision_object_evidence_endpoint')
router.add_api_route('/decision-object/tradeoffs', svc.decision_object_tradeoffs_endpoint, methods=['POST'], name='decision_object_tradeoffs_endpoint')
router.add_api_route('/decision-object/uncertainty-confidence', svc.decision_object_uncertainty_confidence_endpoint, methods=['POST'], name='decision_object_uncertainty_confidence_endpoint')
router.add_api_route('/decision-object/scenario-stress', svc.decision_object_scenario_stress_v250_endpoint, methods=['POST'], name='decision_object_scenario_stress_v250_endpoint')
router.add_api_route('/decision-object/native-handoff', svc.decision_object_native_handoff_endpoint, methods=['POST'], name='decision_object_native_handoff_endpoint')
router.add_api_route('/decision-object/site-intelligence-context', svc.decision_object_site_intelligence_context_endpoint, methods=['POST'], name='decision_object_site_intelligence_context_endpoint')
router.add_api_route('/decision-object/dependency-graph', svc.decision_object_dependency_graph_endpoint, methods=['POST'], name='decision_object_dependency_graph_endpoint')
router.add_api_route('/decision-object/recommendation-review', svc.decision_object_recommendation_review_endpoint, methods=['POST'], name='decision_object_recommendation_review_endpoint')
router.add_api_route('/decision-object/connected-intelligence', svc.decision_object_connected_intelligence_v300_endpoint, methods=['POST'], name='decision_object_connected_intelligence_v300_endpoint')
