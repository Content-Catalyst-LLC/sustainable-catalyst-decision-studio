from fastapi import APIRouter
from app.services import decision_service as svc

router = APIRouter(tags=["institutional"])

router.add_api_route('/api/v1/capabilities', svc.public_api_capabilities_endpoint, methods=['GET'], name='public_api_capabilities_endpoint')
router.add_api_route('/api/v1/sdk/contracts', svc.public_api_sdk_contracts_endpoint, methods=['GET'], name='public_api_sdk_contracts_endpoint')
router.add_api_route('/api/v1/public-dossier', svc.public_api_dossier_endpoint, methods=['POST'], name='public_api_dossier_endpoint')
router.add_api_route('/api/v1/embeds/readiness', svc.public_api_readiness_embed_endpoint, methods=['POST'], name='public_api_readiness_embed_endpoint')
router.add_api_route('/api/v1/embeds/scenario', svc.public_api_scenario_embed_endpoint, methods=['POST'], name='public_api_scenario_embed_endpoint')
router.add_api_route('/api/v1/packets/export', svc.institutional_bulk_export_endpoint, methods=['POST'], name='institutional_bulk_export_endpoint')
router.add_api_route('/api/v1/packets/import', svc.institutional_bulk_import_endpoint, methods=['POST'], name='institutional_bulk_import_endpoint')
router.add_api_route('/api/v1/archive', svc.institutional_archive_endpoint, methods=['POST'], name='institutional_archive_endpoint')
router.add_api_route('/api/v1/platform-core/gateway', svc.platform_core_gateway_endpoint, methods=['POST'], name='platform_core_gateway_endpoint')
router.add_api_route('/api/v1/events', svc.institutional_event_endpoint, methods=['POST'], name='institutional_event_endpoint')
router.add_api_route('/decision-packet/institutional-integration', svc.decision_packet_institutional_integration_endpoint, methods=['POST'], name='decision_packet_institutional_integration_endpoint')
router.add_api_route('/release-hardening/template', svc.release_hardening_template_endpoint, methods=['GET'], name='release_hardening_template_endpoint')
router.add_api_route('/release-hardening/accessibility-audit', svc.release_hardening_accessibility_endpoint, methods=['POST'], name='release_hardening_accessibility_endpoint')
router.add_api_route('/release-hardening/offline-manifest', svc.release_hardening_offline_endpoint, methods=['POST'], name='release_hardening_offline_endpoint')
router.add_api_route('/release-hardening/recovery-snapshot', svc.release_hardening_snapshot_endpoint, methods=['POST'], name='release_hardening_snapshot_endpoint')
router.add_api_route('/release-hardening/migration-assessment', svc.release_hardening_migration_endpoint, methods=['POST'], name='release_hardening_migration_endpoint')
router.add_api_route('/release-hardening/readiness', svc.release_hardening_readiness_endpoint, methods=['POST'], name='release_hardening_readiness_endpoint')
router.add_api_route('/decision-packet/release-hardening', svc.decision_packet_release_hardening_endpoint, methods=['POST'], name='decision_packet_release_hardening_endpoint')
