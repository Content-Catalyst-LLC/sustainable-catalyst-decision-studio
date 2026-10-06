from fastapi import APIRouter
from app.services import decision_service as svc

router = APIRouter(tags=["platform"])

router.add_api_route('/connected-platform/template', svc.connected_platform_template_endpoint, methods=['GET'], name='connected_platform_template_endpoint')
router.add_api_route('/connected-platform/assess', svc.connected_platform_assess_endpoint, methods=['POST'], name='connected_platform_assess_endpoint')
router.add_api_route('/connected-platform/transition', svc.connected_platform_transition_endpoint, methods=['POST'], name='connected_platform_transition_endpoint')
router.add_api_route('/connected-platform/portfolio', svc.connected_platform_portfolio_endpoint, methods=['POST'], name='connected_platform_portfolio_endpoint')
router.add_api_route('/connected-platform/graph', svc.connected_platform_graph_endpoint, methods=['POST'], name='connected_platform_graph_endpoint')
router.add_api_route('/connected-platform/exchange', svc.connected_platform_exchange_endpoint, methods=['POST'], name='connected_platform_exchange_endpoint')
router.add_api_route('/decision-packet/connected-platform', svc.decision_packet_connected_platform_endpoint, methods=['POST'], name='decision_packet_connected_platform_endpoint')
router.add_api_route('/connected-platform/history/verify', svc.connected_platform_history_verify_endpoint, methods=['POST'], name='connected_platform_history_verify_endpoint')
