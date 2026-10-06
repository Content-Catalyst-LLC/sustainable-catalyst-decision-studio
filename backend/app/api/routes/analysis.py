from fastapi import APIRouter
from app.services import decision_service as svc

router = APIRouter(tags=["analysis"])

router.add_api_route('/audit/template', svc.audit_template_endpoint, methods=['GET'], name='audit_template_endpoint')
router.add_api_route('/audit/generate', svc.audit_generate_endpoint, methods=['POST'], name='audit_generate_endpoint')
router.add_api_route('/scenario-comparison/template', svc.scenario_comparison_template_endpoint, methods=['GET'], name='scenario_comparison_template_endpoint')
router.add_api_route('/scenario-comparison', svc.scenario_comparison_endpoint, methods=['POST'], name='scenario_comparison_endpoint')
router.add_api_route('/decision-packet/scenario-comparison', svc.decision_packet_scenario_comparison_endpoint, methods=['POST'], name='decision_packet_scenario_comparison_endpoint')
router.add_api_route('/scenario-studio/template', svc.scenario_studio_template_endpoint, methods=['GET'], name='scenario_studio_template_endpoint')
router.add_api_route('/scenario-studio/analyze', svc.scenario_studio_analyze_endpoint, methods=['POST'], name='scenario_studio_analyze_endpoint')
router.add_api_route('/scenario-studio/sensitivity', svc.scenario_studio_sensitivity_endpoint, methods=['POST'], name='scenario_studio_sensitivity_endpoint')
router.add_api_route('/scenario-studio/threshold', svc.scenario_studio_threshold_endpoint, methods=['POST'], name='scenario_studio_threshold_endpoint')
router.add_api_route('/decision-packet/scenario-studio', svc.decision_packet_scenario_studio_endpoint, methods=['POST'], name='decision_packet_scenario_studio_endpoint')
router.add_api_route('/workbench/handoffs', svc.workbench_handoffs_endpoint, methods=['GET'], name='workbench_handoffs_endpoint')
router.add_api_route('/workbench/handoff', svc.workbench_handoff_endpoint, methods=['POST'], name='workbench_handoff_endpoint')
router.add_api_route('/decision-packet/workbench-handoff', svc.decision_packet_workbench_handoff_endpoint, methods=['POST'], name='decision_packet_workbench_handoff_endpoint')
router.add_api_route('/decision-packet/storage-template', svc.decision_packet_storage_template_endpoint, methods=['GET'], name='decision_packet_storage_template_endpoint')
router.add_api_route('/decision-packet/save-template', svc.decision_packet_save_template_endpoint, methods=['POST'], name='decision_packet_save_template_endpoint')
router.add_api_route('/export-center/template', svc.export_center_template_endpoint, methods=['GET'], name='export_center_template_endpoint')
router.add_api_route('/export-center/bundle', svc.export_center_bundle_endpoint, methods=['POST'], name='export_center_bundle_endpoint')
router.add_api_route('/decision-packet/export-bundle', svc.decision_packet_export_bundle_endpoint, methods=['POST'], name='decision_packet_export_bundle_endpoint')
