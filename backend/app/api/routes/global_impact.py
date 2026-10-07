from fastapi import APIRouter
from app.services import decision_service as svc

router = APIRouter(tags=["global-impact"])
router.add_api_route('/global-impact/contract', svc.global_impact_contract_endpoint, methods=['GET'], name='global_impact_contract_endpoint')
router.add_api_route('/global-impact/template', svc.global_impact_template_endpoint, methods=['GET'], name='global_impact_template_endpoint')
router.add_api_route('/global-impact/decisions/{decision_id}', svc.global_impact_get_endpoint, methods=['GET'], name='global_impact_get_endpoint')
router.add_api_route('/global-impact/decisions/{decision_id}', svc.global_impact_put_endpoint, methods=['PUT'], name='global_impact_put_endpoint')
router.add_api_route('/global-impact/decisions/{decision_id}/impact-claims', svc.global_impact_claims_get_endpoint, methods=['GET'], name='global_impact_claims_get_endpoint')
router.add_api_route('/global-impact/decisions/{decision_id}/impact-claims', svc.global_impact_claims_put_endpoint, methods=['PUT'], name='global_impact_claims_put_endpoint')
router.add_api_route('/global-impact/decisions/{decision_id}/indicators', svc.global_impact_indicators_get_endpoint, methods=['GET'], name='global_impact_indicators_get_endpoint')
router.add_api_route('/global-impact/decisions/{decision_id}/indicators', svc.global_impact_indicators_put_endpoint, methods=['PUT'], name='global_impact_indicators_put_endpoint')
router.add_api_route('/global-impact/decisions/{decision_id}/evidence-links', svc.global_impact_evidence_links_get_endpoint, methods=['GET'], name='global_impact_evidence_links_get_endpoint')
router.add_api_route('/global-impact/decisions/{decision_id}/evidence-links', svc.global_impact_evidence_links_put_endpoint, methods=['PUT'], name='global_impact_evidence_links_put_endpoint')
router.add_api_route('/global-impact/import/legacy', svc.global_impact_legacy_import_endpoint, methods=['POST'], name='global_impact_legacy_import_endpoint')
