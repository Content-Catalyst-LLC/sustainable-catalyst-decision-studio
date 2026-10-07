from fastapi import APIRouter
from app.services import decision_service as svc

router = APIRouter(tags=["narrative-risk"])
router.add_api_route('/narrative-risk/contract', svc.narrative_risk_contract_endpoint, methods=['GET'], name='narrative_risk_contract_endpoint')
router.add_api_route('/narrative-risk/template', svc.narrative_risk_template_endpoint, methods=['GET'], name='narrative_risk_template_endpoint')
router.add_api_route('/narrative-risk/decisions/{decision_id}', svc.narrative_risk_get_endpoint, methods=['GET'], name='narrative_risk_get_endpoint')
router.add_api_route('/narrative-risk/decisions/{decision_id}', svc.narrative_risk_put_endpoint, methods=['PUT'], name='narrative_risk_put_endpoint')
router.add_api_route('/narrative-risk/decisions/{decision_id}/claims', svc.narrative_risk_claims_get_endpoint, methods=['GET'], name='narrative_risk_claims_get_endpoint')
router.add_api_route('/narrative-risk/decisions/{decision_id}/claims', svc.narrative_risk_claims_put_endpoint, methods=['PUT'], name='narrative_risk_claims_put_endpoint')
router.add_api_route('/narrative-risk/decisions/{decision_id}/signals', svc.narrative_risk_signals_get_endpoint, methods=['GET'], name='narrative_risk_signals_get_endpoint')
router.add_api_route('/narrative-risk/decisions/{decision_id}/signals', svc.narrative_risk_signals_put_endpoint, methods=['PUT'], name='narrative_risk_signals_put_endpoint')
router.add_api_route('/narrative-risk/decisions/{decision_id}/evidence-links', svc.narrative_risk_evidence_links_get_endpoint, methods=['GET'], name='narrative_risk_evidence_links_get_endpoint')
router.add_api_route('/narrative-risk/decisions/{decision_id}/evidence-links', svc.narrative_risk_evidence_links_put_endpoint, methods=['PUT'], name='narrative_risk_evidence_links_put_endpoint')
router.add_api_route('/narrative-risk/import/legacy', svc.narrative_risk_legacy_import_endpoint, methods=['POST'], name='narrative_risk_legacy_import_endpoint')
