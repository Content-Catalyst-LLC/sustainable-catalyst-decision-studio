from fastapi import APIRouter

from app import workspace_adapter as wa

router = APIRouter(tags=["workspace-execution-adapter"])
router.add_api_route('/v1/workspace/adapter', wa.adapter_status, methods=['GET'], name='workspace_adapter_status')
router.add_api_route('/v1/workspace/execute', wa.execute, methods=['POST'], name='workspace_adapter_execute')
