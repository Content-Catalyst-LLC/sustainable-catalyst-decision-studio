from fastapi import APIRouter
from app.services import decision_service as svc

router = APIRouter(tags=["decision-lifecycle"])

router.add_api_route('/decision-packet/template', svc.decision_packet_template_endpoint, methods=['GET'], name='decision_packet_template_endpoint')
router.add_api_route('/decision-packet/analyze', svc.decision_packet_analyze_endpoint, methods=['POST'], name='decision_packet_analyze_endpoint')
router.add_api_route('/review/status-template', svc.review_status_template_endpoint, methods=['GET'], name='review_status_template_endpoint')
router.add_api_route('/brief-readiness', svc.brief_readiness_endpoint, methods=['POST'], name='brief_readiness_endpoint')
router.add_api_route('/decision-packet/readiness', svc.decision_packet_readiness_endpoint, methods=['POST'], name='decision_packet_readiness_endpoint')
router.add_api_route('/review/status', svc.review_status_endpoint, methods=['POST'], name='review_status_endpoint')
router.add_api_route('/governance/states', svc.governance_states_endpoint, methods=['GET'], name='governance_states_endpoint')
router.add_api_route('/governance/template', svc.governance_template_endpoint, methods=['GET'], name='governance_template_endpoint')
router.add_api_route('/governance/evaluate', svc.governance_evaluate_endpoint, methods=['POST'], name='governance_evaluate_endpoint')
router.add_api_route('/governance/transition', svc.governance_transition_endpoint, methods=['POST'], name='governance_transition_endpoint')
router.add_api_route('/decision-packet/governance', svc.decision_packet_governance_endpoint, methods=['POST'], name='decision_packet_governance_endpoint')
router.add_api_route('/governance/history/verify', svc.governance_history_verify_endpoint, methods=['POST'], name='governance_history_verify_endpoint')
router.add_api_route('/decision-packs/catalog', svc.decision_packs_catalog_endpoint, methods=['GET'], name='decision_packs_catalog_endpoint')
router.add_api_route('/decision-packs/{pack_id}', svc.decision_pack_endpoint, methods=['GET'], name='decision_pack_endpoint')
router.add_api_route('/decision-packs/validate', svc.decision_pack_validate_endpoint, methods=['POST'], name='decision_pack_validate_endpoint')
router.add_api_route('/decision-packs/apply', svc.decision_pack_apply_endpoint, methods=['POST'], name='decision_pack_apply_endpoint')
router.add_api_route('/decision-packet/domain-pack', svc.decision_packet_domain_pack_endpoint, methods=['POST'], name='decision_packet_domain_pack_endpoint')
