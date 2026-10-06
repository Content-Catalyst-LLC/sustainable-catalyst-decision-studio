from fastapi import APIRouter
from app.services import decision_service as svc

router = APIRouter(tags=["persistence"])
router.add_api_route('/persistence/status', svc.persistence_status_endpoint, methods=['GET'], name='persistence_status_endpoint')
router.add_api_route('/persistence/schema', svc.persistence_schema_endpoint, methods=['GET'], name='persistence_schema_endpoint')
router.add_api_route('/persistence/contract', svc.persistence_contract_endpoint, methods=['GET'], name='persistence_contract_endpoint')
