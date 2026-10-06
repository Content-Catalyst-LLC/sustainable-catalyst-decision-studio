from fastapi import FastAPI

from app.api.router import api_router
from app.services import decision_service as service

# Compatibility re-exports for callers that historically imported helpers from app.main.
from app.services.decision_service import *  # noqa: F401,F403

app = FastAPI(
    title="Sustainable Catalyst Decision Studio Backend",
    version=service.APP_VERSION,
)
app.middleware("http")(service.production_request_guard)
app.include_router(api_router)
