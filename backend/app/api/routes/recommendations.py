from fastapi import APIRouter
from app.services import decision_service as svc

router = APIRouter(tags=["recommendations"])

router.add_api_route('/recommendation-review/template', svc.recommendation_review_template_endpoint, methods=['GET'], name='recommendation_review_template_endpoint')
router.add_api_route('/recommendation-review/candidate', svc.recommendation_review_candidate_endpoint, methods=['POST'], name='recommendation_review_candidate_endpoint')
router.add_api_route('/recommendation-review/challenge', svc.recommendation_review_challenge_endpoint, methods=['POST'], name='recommendation_review_challenge_endpoint')
router.add_api_route('/recommendation-review/evaluate', svc.recommendation_review_evaluate_endpoint, methods=['POST'], name='recommendation_review_evaluate_endpoint')
router.add_api_route('/recommendation-review/disposition', svc.recommendation_review_disposition_endpoint, methods=['POST'], name='recommendation_review_disposition_endpoint')
router.add_api_route('/decision-packet/recommendation-review', svc.decision_packet_recommendation_review_endpoint, methods=['POST'], name='decision_packet_recommendation_review_endpoint')
router.add_api_route('/connected-intelligence/template', svc.connected_intelligence_template_v300_endpoint, methods=['GET'], name='connected_intelligence_template_v300_endpoint')
router.add_api_route('/connected-intelligence/build', svc.connected_intelligence_build_v300_endpoint, methods=['POST'], name='connected_intelligence_build_v300_endpoint')
router.add_api_route('/connected-intelligence/validate', svc.connected_intelligence_validate_v300_endpoint, methods=['POST'], name='connected_intelligence_validate_v300_endpoint')
router.add_api_route('/decision-packet/connected-intelligence', svc.decision_packet_connected_intelligence_v300_endpoint, methods=['POST'], name='decision_packet_connected_intelligence_v300_endpoint')
