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
