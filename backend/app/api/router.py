from fastapi import APIRouter
from app.energy_runtime_consumer import router as energy_runtime_consumer_router
from app.api.routes.system import router as system_router
from app.api.routes.integrations import router as integrations_router
from app.api.routes.decision_lifecycle import router as decision_lifecycle_router
from app.api.routes.collaboration import router as collaboration_router
from app.api.routes.institutional import router as institutional_router
from app.api.routes.platform import router as platform_router
from app.api.routes.analysis import router as analysis_router
from app.api.routes.objects import router as objects_router
from app.api.routes.evidence_analysis import router as evidence_analysis_router
from app.api.routes.context_handoffs import router as context_handoffs_router
from app.api.routes.recommendations import router as recommendations_router
from app.api.routes.decision_kernel import router as decision_kernel_router
from app.api.routes.persistence import router as persistence_router
from app.api.routes.repository import router as repository_router
from app.api.routes.canvas import router as canvas_router
from app.api.routes.finance import router as finance_router
from app.api.routes.narrative_risk import router as narrative_risk_router
from app.api.routes.global_impact import router as global_impact_router
from app.api.routes.module_registry import router as module_registry_router
from app.api.routes.composition import router as composition_router
from app.api.routes.module_artifacts import router as module_artifacts_router
from app.api.routes.module_interoperability import router as module_interoperability_router
from app.api.routes.decision_rooms import router as decision_rooms_router
from app.api.routes.auth import router as auth_router
from app.api.routes.audit_ledger import router as audit_ledger_router

api_router = APIRouter()
api_router.include_router(energy_runtime_consumer_router)

api_router.include_router(system_router)
api_router.include_router(integrations_router)
api_router.include_router(decision_lifecycle_router)
api_router.include_router(collaboration_router)
api_router.include_router(institutional_router)
api_router.include_router(platform_router)
api_router.include_router(analysis_router)
api_router.include_router(objects_router)
api_router.include_router(evidence_analysis_router)
api_router.include_router(context_handoffs_router)
api_router.include_router(recommendations_router)
api_router.include_router(decision_kernel_router)
api_router.include_router(persistence_router)
api_router.include_router(repository_router)
api_router.include_router(canvas_router)
api_router.include_router(finance_router)
api_router.include_router(narrative_risk_router)
api_router.include_router(global_impact_router)
api_router.include_router(module_registry_router)
api_router.include_router(composition_router)
api_router.include_router(module_artifacts_router)
api_router.include_router(module_interoperability_router)
api_router.include_router(decision_rooms_router)
api_router.include_router(auth_router)
api_router.include_router(audit_ledger_router)
