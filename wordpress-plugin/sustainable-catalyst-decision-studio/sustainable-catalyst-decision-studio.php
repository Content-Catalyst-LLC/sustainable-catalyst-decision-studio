<?php
/**
 * Plugin Name: Sustainable Catalyst Decision Studio
 * Description: Private collaborative decision rooms with role-based review, comments, revisions, snapshots, change requests, approved-version locks, and typed evidence handoffs from Knowledge Library, Research Librarian, Site Intelligence, Workbench, Research Lab, and Platform Core; legacy artifact adapters remain supported.
 * Version: 1.11.0
 * Author: Content Catalyst LLC
 * Text Domain: sustainable-catalyst-decision-studio
 */

if (!defined('ABSPATH')) {
    exit;
}

class Sustainable_Catalyst_Decision_Studio {
    const VERSION = '1.11.0';
    const BUILD_FINGERPRINT = 'scds-v1.11.0-collaborative-decision-rooms';
    const SOURCE_COMMIT = 'release-v1.11.0';
    const RELEASE_DATE = '2026-07-16';
    const DB_VERSION = '1.5.0';
    const DB_VERSION_OPTION = 'scds_db_version';
    const INSTALLED_VERSION_OPTION = 'scds_installed_version';
    const MAX_PUBLIC_REQUEST_BYTES = 1048576;
    const PUBLIC_RATE_LIMIT = 60;
    const OPTION_KEY = 'scds_settings';
    const NONCE_ACTION = 'wp_rest';
    const PROJECTS_TABLE = 'scds_projects';
    const REPORTS_TABLE = 'scds_reports';
    const VALIDATION_TABLE = 'scds_validation';
    const ROOMS_TABLE = 'scds_rooms';
    const ROOM_MEMBERS_TABLE = 'scds_room_members';
    const ROOM_EVENTS_TABLE = 'scds_room_events';
    const COLLABORATION_ROOM_SCHEMA = 'scds-collaborative-decision-room/1.0';
    const COLLABORATION_EVENT_SCHEMA = 'scds-collaboration-event/1.0';

    public function __construct() {
        add_action('init', [$this, 'register_assets']);
        add_shortcode('sc_decision_studio', [$this, 'render_decision_studio_shortcode']);
        add_shortcode('sustainable_catalyst_platform', [$this, 'render_legacy_shortcode']);
        add_shortcode('sustainable_catalyst_platform_cta', [$this, 'render_cta_shortcode']);
        add_action('admin_menu', [$this, 'register_admin_menu']);
        add_action('admin_init', [$this, 'maybe_save_settings']);
        add_action('rest_api_init', [$this, 'register_rest_routes']);
        add_action('plugins_loaded', [__CLASS__, 'maybe_upgrade']);
        add_filter('rest_pre_dispatch', [$this, 'protect_public_rest_request'], 10, 3);
    }

    public static function activate() {
        self::maybe_upgrade();
        $defaults = self::default_settings();
        $existing = get_option(self::OPTION_KEY, []);
        update_option(self::OPTION_KEY, wp_parse_args($existing, $defaults));
        self::seed_validation_rows();
        self::maybe_create_page();
    }

    public static function maybe_upgrade() {
        $installed_db = (string) get_option(self::DB_VERSION_OPTION, '0');
        $installed_release = (string) get_option(self::INSTALLED_VERSION_OPTION, '0');
        if (version_compare($installed_db, self::DB_VERSION, '<') || $installed_release !== self::VERSION) {
            self::create_tables();
            self::seed_validation_rows();
            update_option(self::DB_VERSION_OPTION, self::DB_VERSION, false);
            update_option(self::INSTALLED_VERSION_OPTION, self::VERSION, false);
        }
    }

    private static function maybe_create_page() {
        if (get_page_by_path('platform/decision-studio') || get_page_by_path('decision-studio')) {
            return;
        }
        wp_insert_post([
            'post_title'   => 'Decision Studio',
            'post_name'    => 'decision-studio',
            'post_status'  => 'draft',
            'post_type'    => 'page',
            'post_content' => '[sc_decision_studio mode="full" title="Sustainable Catalyst Decision Studio"]',
        ]);
    }

    private static function create_tables() {
        global $wpdb;
        require_once ABSPATH . 'wp-admin/includes/upgrade.php';
        $charset = $wpdb->get_charset_collate();
        $projects = $wpdb->prefix . self::PROJECTS_TABLE;
        $reports = $wpdb->prefix . self::REPORTS_TABLE;
        $validation = $wpdb->prefix . self::VALIDATION_TABLE;
        $rooms = $wpdb->prefix . self::ROOMS_TABLE;
        $room_members = $wpdb->prefix . self::ROOM_MEMBERS_TABLE;
        $room_events = $wpdb->prefix . self::ROOM_EVENTS_TABLE;

        dbDelta("CREATE TABLE $projects (
            id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            project_name VARCHAR(255) NOT NULL,
            sector VARCHAR(160) DEFAULT '',
            location VARCHAR(160) DEFAULT '',
            decision_question LONGTEXT,
            status VARCHAR(40) DEFAULT 'draft',
            inputs_json LONGTEXT,
            results_json LONGTEXT,
            packet_json LONGTEXT,
            audit_json LONGTEXT,
            readiness_json LONGTEXT,
            scenario_comparison_json LONGTEXT,
            scenario_studio_json LONGTEXT,
            workbench_handoff_json LONGTEXT,
            integrated_brief_json LONGTEXT,
            governance_json LONGTEXT,
            collaboration_json LONGTEXT,
            export_bundle_json LONGTEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            KEY status (status),
            KEY created_at (created_at)
        ) $charset;");

        dbDelta("CREATE TABLE $reports (
            id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            project_id BIGINT UNSIGNED DEFAULT 0,
            report_title VARCHAR(255) DEFAULT '',
            report_json LONGTEXT,
            report_markdown LONGTEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            KEY project_id (project_id)
        ) $charset;");

        dbDelta("CREATE TABLE $validation (
            id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            module_id VARCHAR(120) NOT NULL,
            module_name VARCHAR(255) NOT NULL,
            status VARCHAR(40) DEFAULT 'experimental',
            sample_inputs LONGTEXT,
            expected_outputs LONGTEXT,
            warnings LONGTEXT,
            last_validated DATETIME NULL,
            PRIMARY KEY (id),
            UNIQUE KEY module_id (module_id)
        ) $charset;");

        dbDelta("CREATE TABLE $rooms (
            id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            room_uuid VARCHAR(80) NOT NULL,
            project_id BIGINT UNSIGNED DEFAULT 0,
            title VARCHAR(255) NOT NULL,
            visibility VARCHAR(40) DEFAULT 'private',
            status VARCHAR(40) DEFAULT 'active',
            owner_user_id BIGINT UNSIGNED DEFAULT 0,
            room_json LONGTEXT,
            packet_json LONGTEXT,
            locked_version_hash VARCHAR(100) DEFAULT '',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            UNIQUE KEY room_uuid (room_uuid),
            KEY owner_user_id (owner_user_id),
            KEY project_id (project_id),
            KEY status (status)
        ) $charset;");

        dbDelta("CREATE TABLE $room_members (
            id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            room_id BIGINT UNSIGNED NOT NULL,
            user_id BIGINT UNSIGNED DEFAULT 0,
            email VARCHAR(190) DEFAULT '',
            display_name VARCHAR(255) DEFAULT '',
            role VARCHAR(40) DEFAULT 'observer',
            status VARCHAR(40) DEFAULT 'invited',
            invited_by BIGINT UNSIGNED DEFAULT 0,
            invited_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            accepted_at DATETIME NULL,
            last_seen_at DATETIME NULL,
            PRIMARY KEY (id),
            KEY room_id (room_id),
            KEY user_id (user_id),
            KEY email (email)
        ) $charset;");

        dbDelta("CREATE TABLE $room_events (
            id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            room_id BIGINT UNSIGNED NOT NULL,
            event_type VARCHAR(80) NOT NULL,
            actor_user_id BIGINT UNSIGNED DEFAULT 0,
            actor_name VARCHAR(255) DEFAULT '',
            target_type VARCHAR(80) DEFAULT 'room',
            target_id VARCHAR(120) DEFAULT '',
            event_json LONGTEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            KEY room_id (room_id),
            KEY event_type (event_type),
            KEY created_at (created_at)
        ) $charset;");
    }

    private static function seed_validation_rows() {
        global $wpdb;
        $table = $wpdb->prefix . self::VALIDATION_TABLE;
        $modules = [
            ['project-intake', 'Project Intake', 'validated'],
            ['four-pillar-scorecard', 'Four-Pillar Scorecard', 'validated'],
            ['emissions-calculator', 'Emissions Calculator', 'validated'],
            ['energy-cost-calculator', 'Energy and Cost Calculator', 'validated'],
            ['npv-roi-payback', 'NPV / ROI / Payback', 'validated'],
            ['risk-resilience-matrix', 'Risk and Resilience Matrix', 'needs_review'],
            ['scenario-comparison', 'Scenario Comparison', 'validated'],
            ['stakeholder-impact-matrix', 'Stakeholder Impact Matrix', 'experimental'],
            ['governance-readiness-review', 'Governance Readiness Review', 'needs_review'],
            ['sdg-planetary-boundary-map', 'SDG / Planetary Boundary Mapping', 'experimental'],
            ['materiality-tradeoff-analysis', 'Materiality and Tradeoff Analysis', 'experimental'],
            ['procurement-supplier-comparison', 'Procurement / Supplier Comparison', 'experimental'],
            ['uncertainty-sensitivity', 'Uncertainty and Sensitivity Analysis', 'needs_review'],
            ['decision-brief-generator', 'Decision Brief Generator', 'validated'],
            ['brief-readiness-review-status', 'Brief Readiness / Review Status', 'validated'],
            ['scenario-comparison-matrix', 'Scenario Comparison Matrix', 'validated'],
            ['advanced-scenario-studio', 'Advanced Scenario Studio', 'validated'],
            ['one-way-sensitivity', 'One-Way Sensitivity Analysis', 'validated'],
            ['multi-variable-sensitivity', 'Multi-Variable Sensitivity Grid', 'validated'],
            ['threshold-break-even', 'Threshold and Break-Even Analysis', 'validated'],
            ['uncertainty-envelopes', 'Uncertainty Envelopes', 'validated'],
            ['stakeholder-distribution', 'Stakeholder Distribution Analysis', 'validated'],
            ['time-horizon-option-value', 'Time Horizon and Option Value', 'validated'],
            ['workbench-handoff-router', 'Workbench Handoff Router', 'validated'],
            ['audit-trail-assumptions-log', 'Audit Trail / Assumptions Log', 'validated'],
            ['saved-decision-packets', 'Saved Decision Packets', 'validated'],
            ['export-center-bundle', 'Export Center Bundle', 'validated'],
            ['public-landing-page', 'Professional Public Landing Page', 'validated'],
            ['demo-refresh', 'Professional Demo Refresh', 'validated'],
            ['decision-governance-center', 'Decision Governance and Review Center', 'validated'],
            ['immutable-review-history', 'Immutable Review History', 'validated'],
            ['approval-export-gates', 'Approval and Export Gates', 'validated'],
            ['collaborative-decision-rooms', 'Collaborative Decision Rooms', 'validated'],
            ['room-comments-change-requests', 'Room Comments and Change Requests', 'validated'],
            ['packet-snapshots-comparison', 'Packet Snapshots and Version Comparison', 'validated'],
            ['private-room-sharing', 'Private Room Sharing', 'validated'],
            ['approved-version-locks', 'Approved Version Locks', 'validated'],
            ['contact-engagement-handoff', 'Contact and Engagement Handoff', 'validated'],
        ];
        foreach ($modules as $m) {
            $wpdb->replace($table, [
                'module_id' => $m[0],
                'module_name' => $m[1],
                'status' => $m[2],
                'sample_inputs' => wp_json_encode(['demo' => true, 'baseline_emissions' => 1200, 'capex' => 950000, 'annual_savings' => 185000]),
                'expected_outputs' => wp_json_encode(['score_range' => '0-100', 'exports' => ['json', 'csv', 'print_pdf']]),
                'warnings' => 'Educational decision support only. Not professional advice, certification, assurance, or regulated engineering analysis.',
                'last_validated' => current_time('mysql'),
            ]);
        }
    }

    public static function default_settings() {
        return [
            'brand_title' => 'Sustainable Catalyst Decision Studio',
            'brand_subtitle' => 'Connected decision intelligence for private collaboration, evidence review, scenario analysis, governed approval, revisions, and locked Decision Packet versions.',
            'methodology_note' => 'AI in the toolkit, never in control. Outputs are decision-support drafts and educational analyses, not legal, financial, engineering, medical, sustainability assurance, tax, compliance, or investment advice.',
            'backend_url' => '',
            'backend_api_key' => '',
            'backend_enabled' => '0',
            'ai_briefing_enabled' => '1',
            'workbench_integration' => '1',
            'default_display' => 'full',
            'allow_save_projects' => '1',
        ];
    }

    private function settings() {
        return wp_parse_args(get_option(self::OPTION_KEY, []), self::default_settings());
    }

    public function register_assets() {
        $base = plugin_dir_url(__FILE__);
        wp_register_style('scds-decision-studio', $base . 'assets/css/scds-decision-studio.css', [], self::VERSION);
        wp_register_script('scds-decision-studio', $base . 'assets/js/scds-decision-studio.js', [], self::VERSION, true);
    }

    public function render_legacy_shortcode($atts = []) {
        $atts = shortcode_atts(['mode' => 'full', 'title' => 'Sustainable Catalyst Decision Studio'], $atts, 'sustainable_catalyst_platform');
        return $this->render_decision_studio_shortcode($atts);
    }

    public function render_cta_shortcode($atts = []) {
        $atts = shortcode_atts(['href' => '#scds-decision-studio', 'label' => 'Open Decision Studio'], $atts, 'sustainable_catalyst_platform_cta');
        return '<a class="scds-button scds-button-primary" href="' . esc_url($atts['href']) . '">' . esc_html($atts['label']) . '</a>';
    }

    public function render_decision_studio_shortcode($atts = []) {
        $settings = $this->settings();
        $atts = shortcode_atts([
            'mode' => $settings['default_display'],
            'title' => $settings['brand_title'],
            'project_type' => '',
            'display' => '',
            'tool' => '',
        ], $atts, 'sc_decision_studio');

        $mode = sanitize_key($atts['mode']);
        if (!in_array($mode, ['full', 'landing', 'demo', 'workflow', 'readiness', 'governance', 'room', 'project-intake', 'scorecard', 'risk', 'scenario', 'handoff', 'packets', 'export', 'report', 'drawer', 'compact'], true)) {
            $mode = 'full';
        }
        $display = sanitize_key($atts['display'] ?: $mode);

        if ($mode === 'landing') {
            return $this->render_public_landing_shortcode($atts);
        }
        if ($mode === 'demo') {
            return $this->render_public_demo_shortcode($atts);
        }

        $start_tab = $mode === 'workflow' ? 'workflow' : ($mode === 'readiness' ? 'readiness' : ($mode === 'governance' ? 'governance' : ($mode === 'room' ? 'room' : ($mode === 'project-intake' ? 'intake' : (in_array($mode, ['scorecard', 'risk', 'scenario', 'handoff', 'packets', 'export', 'report'], true) ? $mode : 'intake')))));
        $uid = 'scds-' . wp_generate_uuid4();

        wp_enqueue_style('scds-decision-studio');
        wp_enqueue_script('scds-decision-studio');
        wp_localize_script('scds-decision-studio', 'SCDSDecisionStudio', [
            'restAnalyzeUrl' => esc_url_raw(rest_url('scds/v1/analyze')),
            'restSaveUrl' => esc_url_raw(rest_url('scds/v1/projects')),
            'restTemplatesUrl' => esc_url_raw(rest_url('scds/v1/templates')),
            'restBriefUrl' => esc_url_raw(rest_url('scds/v1/ai-brief')),
            'restBackendStatusUrl' => esc_url_raw(rest_url('scds/v1/backend-status')),
            'restIntegrationsUrl' => esc_url_raw(rest_url('scds/v1/integrations')),
            'restDecisionPacketTemplateUrl' => esc_url_raw(rest_url('scds/v1/decision-packet/template')),
            'restAdaptersUrl' => esc_url_raw(rest_url('scds/v1/integrations/adapters')),
            'restPlatformIntegrationsUrl' => esc_url_raw(rest_url('scds/v1/integrations/platform')),
            'restContractsUrl' => esc_url_raw(rest_url('scds/v1/integrations/contracts')),
            'restValidateArtifactUrl' => esc_url_raw(rest_url('scds/v1/integrations/validate')),
            'restImportBatchUrl' => esc_url_raw(rest_url('scds/v1/integrations/import-batch')),
            'restPlatformHandoffsUrl' => esc_url_raw(rest_url('scds/v1/decision-packet/platform-handoffs')),
            'restImportArtifactUrl' => esc_url_raw(rest_url('scds/v1/integrations/import')),
            'restDecisionPacketImportUrl' => esc_url_raw(rest_url('scds/v1/decision-packet/import')),
            'restGovernanceStatesUrl' => esc_url_raw(rest_url('scds/v1/governance/states')),
            'restGovernanceTemplateUrl' => esc_url_raw(rest_url('scds/v1/governance/template')),
            'restGovernanceEvaluateUrl' => esc_url_raw(rest_url('scds/v1/governance/evaluate')),
            'restGovernanceTransitionUrl' => esc_url_raw(rest_url('scds/v1/governance/transition')),
            'restDecisionPacketGovernanceUrl' => esc_url_raw(rest_url('scds/v1/decision-packet/governance')),
            'restGovernanceHistoryVerifyUrl' => esc_url_raw(rest_url('scds/v1/governance/history/verify')),
            'restAuditTemplateUrl' => esc_url_raw(rest_url('scds/v1/audit/template')),
            'restAuditGenerateUrl' => esc_url_raw(rest_url('scds/v1/audit/generate')),
            'restIntegratedBriefUrl' => esc_url_raw(rest_url('scds/v1/integrated-brief')),
            'restBriefReadinessUrl' => esc_url_raw(rest_url('scds/v1/brief-readiness')),
            'restDecisionPacketReadinessUrl' => esc_url_raw(rest_url('scds/v1/decision-packet/readiness')),
            'restReviewStatusTemplateUrl' => esc_url_raw(rest_url('scds/v1/review/status-template')),
            'restReviewStatusUrl' => esc_url_raw(rest_url('scds/v1/review/status')),
            'restScenarioComparisonUrl' => esc_url_raw(rest_url('scds/v1/scenario-comparison')),
            'restDecisionPacketScenarioComparisonUrl' => esc_url_raw(rest_url('scds/v1/decision-packet/scenario-comparison')),
            'restScenarioStudioTemplateUrl' => esc_url_raw(rest_url('scds/v1/scenario-studio/template')),
            'restScenarioStudioAnalyzeUrl' => esc_url_raw(rest_url('scds/v1/scenario-studio/analyze')),
            'restScenarioStudioSensitivityUrl' => esc_url_raw(rest_url('scds/v1/scenario-studio/sensitivity')),
            'restScenarioStudioThresholdUrl' => esc_url_raw(rest_url('scds/v1/scenario-studio/threshold')),
            'restDecisionPacketScenarioStudioUrl' => esc_url_raw(rest_url('scds/v1/decision-packet/scenario-studio')),
            'restWorkbenchHandoffCatalogUrl' => esc_url_raw(rest_url('scds/v1/workbench/handoffs')),
            'restWorkbenchHandoffUrl' => esc_url_raw(rest_url('scds/v1/workbench/handoff')),
            'restDecisionPacketWorkbenchHandoffUrl' => esc_url_raw(rest_url('scds/v1/decision-packet/workbench-handoff')),
            'restPacketStorageTemplateUrl' => esc_url_raw(rest_url('scds/v1/decision-packet/storage-template')),
            'restPacketSaveTemplateUrl' => esc_url_raw(rest_url('scds/v1/decision-packet/save-template')),
            'restPacketsUrl' => esc_url_raw(rest_url('scds/v1/packets')),
            'restExportCenterTemplateUrl' => esc_url_raw(rest_url('scds/v1/export-center/template')),
            'restExportBundleUrl' => esc_url_raw(rest_url('scds/v1/export-center/bundle')),
            'restDecisionPacketExportBundleUrl' => esc_url_raw(rest_url('scds/v1/decision-packet/export-bundle')),
            'restPublicLandingTemplateUrl' => esc_url_raw(rest_url('scds/v1/public/landing-template')),
            'restPublicDemoTemplateUrl' => esc_url_raw(rest_url('scds/v1/public/demo-template')),
            'restCollaborationTemplateUrl' => esc_url_raw(rest_url('scds/v1/collaboration/template')),
            'restCollaborationActionUrl' => esc_url_raw(rest_url('scds/v1/collaboration/action')),
            'restDecisionPacketCollaborationUrl' => esc_url_raw(rest_url('scds/v1/decision-packet/collaboration')),
            'restRoomsUrl' => esc_url_raw(rest_url('scds/v1/rooms')),
            'restCurrentUserRoomsUrl' => esc_url_raw(rest_url('scds/v1/rooms')),
            'isLoggedIn' => is_user_logged_in(),
            'currentUser' => ['id'=>get_current_user_id(),'name'=>is_user_logged_in()?wp_get_current_user()->display_name:'','role'=>current_user_can('manage_options')?'owner':(current_user_can('edit_posts')?'editor':'observer')],
            'storageKey' => 'scds_saved_decision_packets_v1_11_0',
            'nonce' => wp_create_nonce(self::NONCE_ACTION),
            'backendEnabled' => $settings['backend_enabled'] === '1' && !empty($settings['backend_url']),
            'aiBriefingEnabled' => $settings['ai_briefing_enabled'] === '1',
            'workbenchIntegration' => $settings['workbench_integration'] === '1',
            'methodologyNote' => sanitize_text_field($settings['methodology_note']),
        ]);

        ob_start();
        ?>
        <section id="<?php echo esc_attr($uid); ?>" class="scds-shell scds-mode-<?php echo esc_attr($mode); ?> scds-display-<?php echo esc_attr($display); ?>" data-scds-app data-scds-mode="<?php echo esc_attr($mode); ?>" data-scds-start-tab="<?php echo esc_attr($start_tab); ?>">
            <?php if ($mode === 'drawer') : ?>
                <button type="button" class="scds-drawer-toggle" data-scds-drawer-toggle><?php echo esc_html($atts['title']); ?> →</button>
                <div class="scds-drawer-panel" hidden>
            <?php endif; ?>

            <header class="scds-hero">
                <p class="scds-kicker">Sustainable Catalyst Platform · Decision Studio v<?php echo esc_html(self::VERSION); ?></p>
                <h2><?php echo esc_html($atts['title']); ?></h2>
                <p><?php echo esc_html($settings['brand_subtitle']); ?></p>
                <div class="scds-note"><strong>Boundary:</strong> <?php echo esc_html($settings['methodology_note']); ?></div>
            </header>

            <nav class="scds-tabs" aria-label="Decision Studio sections">
                <button type="button" class="scds-tab is-active" data-scds-tab="intake">Intake</button>
                <button type="button" class="scds-tab" data-scds-tab="workflow">Workflow</button>
                <button type="button" class="scds-tab" data-scds-tab="readiness">Readiness</button>
                <button type="button" class="scds-tab" data-scds-tab="governance">Governance</button>
                <button type="button" class="scds-tab" data-scds-tab="room">Decision Room</button>
                <button type="button" class="scds-tab" data-scds-tab="scorecard">Scorecard</button>
                <button type="button" class="scds-tab" data-scds-tab="risk">Risk</button>
                <button type="button" class="scds-tab" data-scds-tab="scenario">Scenarios</button>
                <button type="button" class="scds-tab" data-scds-tab="handoff">Workbench Handoff</button>
                <button type="button" class="scds-tab" data-scds-tab="export">Packets &amp; Export</button>
                <button type="button" class="scds-tab" data-scds-tab="report">Report</button>
                <button type="button" class="scds-tab" data-scds-tab="audit">Audit</button>
            </nav>

            <div class="scds-panels">
                <?php $this->render_panel_intake($mode); ?>
                <?php $this->render_panel_workflow($mode); ?>
                <?php $this->render_panel_readiness($mode); ?>
                <?php $this->render_panel_governance($mode); ?>
                <?php $this->render_panel_collaboration($mode); ?>
                <?php $this->render_panel_scorecard($mode); ?>
                <?php $this->render_panel_risk($mode); ?>
                <?php $this->render_panel_scenario($mode); ?>
                <?php $this->render_panel_handoff($mode); ?>
                <?php $this->render_panel_export_center($mode); ?>
                <?php $this->render_panel_report($mode); ?>
                <?php $this->render_panel_ai($mode); ?>
                <?php $this->render_panel_audit($mode); ?>
            </div>

            <div class="scds-output" data-scds-output aria-live="polite"></div>

            <?php if ($mode === 'drawer') : ?>
                </div>
            <?php endif; ?>
        </section>
        <?php
        return ob_get_clean();
    }


    private function public_landing_template() {
        return [
            'headline' => 'Decision Studio',
            'positioning' => 'The governance and synthesis layer of the Sustainable Catalyst platform. Decision Studio receives typed evidence, research routes, live indicators, calculations, experiments, entities, and provenance records, then assembles them into a reviewable Decision Packet.',
            'workflow' => [
                ['step'=>'Source','module'=>'Knowledge Library','description'=>'Import structured sources, quotations, Harvard-style citations, bibliographies, and collection context.'],
                ['step'=>'Route','module'=>'Research Librarian','description'=>'Carry research routes, recommended titles, evidence gaps, and follow-up questions into the packet.'],
                ['step'=>'Observe','module'=>'Site Intelligence','description'=>'Attach indicators, country dossiers, live observations, source health, freshness, and methodology.'],
                ['step'=>'Calculate','module'=>'Workbench','description'=>'Import formulas, models, graphs, assumptions, validation checks, and technical reports.'],
                ['step'=>'Test','module'=>'Research Lab','description'=>'Attach experiments, notebooks, datasets, instruments, validation results, and scientific limitations.'],
                ['step'=>'Connect','module'=>'Platform Core','description'=>'Resolve shared entities, Evidence Ledger records, provenance links, relationships, and signed manifests.'],
                ['step'=>'Decide','module'=>'Decision Studio','description'=>'Compare alternatives, expose uncertainty, generate briefs, apply readiness gates, and preserve audit history.'],
            ],
            'features' => [
                ['title'=>'Typed platform artifacts','description'=>'Validate the additive scds-platform-artifact/1.0 envelope across six current Sustainable Catalyst products.'],
                ['title'=>'Unified evidence registry','description'=>'Retain source identity, methodology, freshness, confidence, citations, evidence notes, and transformation history.'],
                ['title'=>'Integrity verification','description'=>'Calculate canonical payload hashes and flag supplied hashes that do not match the imported artifact.'],
                ['title'=>'Decision Packet workspace','description'=>'Use scds-decision-packet/1.4 to hold platform handoffs, evidence, assumptions, scenarios, experiments, calculations, entities, provenance, and audit records.'],
                ['title'=>'Batch and legacy import','description'=>'Import multiple typed artifacts while preserving compatibility with earlier Catalyst module exports.'],
                ['title'=>'Readiness and scenario review','description'=>'Evaluate evidence completeness, compare alternatives, surface unresolved issues, and route deeper modeling to Workbench.'],
                ['title'=>'Saved packets and export center','description'=>'Save working packets and export JSON, Markdown, HTML, audit, readiness, scenario, and handoff artifacts.'],
            ],
        ];
    }

    public function render_public_landing_shortcode($atts = []) {
        $settings = $this->settings();
        $atts = shortcode_atts(['title'=>$settings['brand_title']], $atts, 'sc_decision_studio');
        $t = $this->public_landing_template();
        wp_enqueue_style('scds-decision-studio');
        ob_start(); ?>
        <section class="scds-landing scds-public-shell">
            <header class="scds-public-hero">
                <p class="scds-kicker">Sustainable Catalyst Platform · Decision Studio v<?php echo esc_html(self::VERSION); ?></p>
                <h2><?php echo esc_html($atts['title']); ?></h2>
                <p><?php echo esc_html($t['positioning']); ?></p>
                <div class="scds-public-actions"><a class="scds-button scds-button-primary" href="#scds-live-demo">Open Live Studio →</a><a class="scds-button" href="#scds-workflow-map">View Workflow →</a><a class="scds-button" href="#scds-public-boundary">Boundaries →</a></div>
            </header>
            <section id="scds-workflow-map" class="scds-public-section"><p class="scds-section-kicker">Integrated workflow</p><h3>Source → Route → Observe → Calculate → Test → Connect → Decide</h3><div class="scds-public-workflow">
                <?php foreach ($t['workflow'] as $item): ?><article><p class="scds-card-label"><?php echo esc_html($item['step']); ?></p><h4><?php echo esc_html($item['module']); ?></h4><p><?php echo esc_html($item['description']); ?></p></article><?php endforeach; ?>
            </div></section>
            <section class="scds-public-section"><p class="scds-section-kicker">Platform capabilities</p><h3>What Decision Studio now supports</h3><div class="scds-public-grid">
                <?php foreach ($t['features'] as $item): ?><article><h4><?php echo esc_html($item['title']); ?></h4><p><?php echo esc_html($item['description']); ?></p></article><?php endforeach; ?>
            </div></section>
            <section id="scds-live-demo" class="scds-public-section"><p class="scds-section-kicker">Live module</p><h3>Open the integrated workspace</h3><?php echo $this->render_decision_studio_shortcode(['mode'=>'full','title'=>'Sustainable Catalyst Decision Studio']); ?></section>
            <section id="scds-public-boundary" class="scds-public-section scds-public-boundary"><p class="scds-section-kicker">Boundaries</p><h3>Educational decision support</h3><p><?php echo esc_html($settings['methodology_note']); ?></p></section>
        </section>
        <?php return ob_get_clean();
    }

    public function render_public_demo_shortcode($atts = []) {
        $settings = $this->settings();
        $atts = shortcode_atts(['title'=>'Decision Studio Demo'], $atts, 'sc_decision_studio');
        wp_enqueue_style('scds-decision-studio');
        ob_start(); ?>
        <section class="scds-demo scds-public-shell">
            <header class="scds-public-hero">
                <p class="scds-kicker">Sustainable Catalyst Platform Demo · v<?php echo esc_html(self::VERSION); ?></p>
                <h2><?php echo esc_html($atts['title']); ?></h2>
                <p>Use Canvas to frame. Use Data to anchor. Use Analytics R to model. Use Global Impact to measure. Use Narrative Risk to review. Use Finance to evaluate. Use Grit to sustain. Use Decision Studio to decide.</p>
            </header>
            <section class="scds-public-section"><p class="scds-section-kicker">Demo path</p><h3>A professional walkthrough</h3><ol class="scds-demo-steps"><li>Start with the default decision intake.</li><li>Run the scorecard and review four-pillar results.</li><li>Generate readiness and inspect unresolved issues.</li><li>Compare scenarios and rank options.</li><li>Create Workbench handoffs for deeper analysis.</li><li>Save the packet or export the bundle.</li></ol></section>
            <section class="scds-public-section" id="scds-demo-workspace"><?php echo $this->render_decision_studio_shortcode(['mode'=>'full','title'=>'Decision Studio Demo Workspace']); ?></section>
            <section class="scds-public-section scds-public-boundary"><p><strong>Boundary:</strong> <?php echo esc_html($settings['methodology_note']); ?></p></section>
        </section>
        <?php return ob_get_clean();
    }

    private function render_panel_intake($mode) { ?>
        <section class="scds-panel is-active" data-scds-panel="intake">
            <div class="scds-panel-head"><p class="scds-section-kicker">Project intake</p><h3>Define the decision question</h3><p>Capture the project, policy, procurement, retrofit, supplier, or strategy decision before scoring it.</p></div>
            <div class="scds-form-grid">
                <label>Project / decision name<input type="text" data-scds-field="projectName" value="Fleet electrification decision"></label>
                <label>Organization type<input type="text" data-scds-field="orgType" value="Mid-sized logistics company"></label>
                <label>Sector<select data-scds-field="sector"><option>Transportation and logistics</option><option>Manufacturing</option><option>Real estate and buildings</option><option>Food and agriculture</option><option>Energy and utilities</option><option>Higher education / nonprofit</option><option>Public sector / municipal</option><option>Other</option></select></label>
                <label>Location<input type="text" data-scds-field="location" value="United States / Midwest"></label>
                <label>Time horizon<select data-scds-field="horizon"><option>1 year</option><option>3 years</option><option selected>5 years</option><option>10 years</option><option>20 years</option></select></label>
                <label>Primary decision type<select data-scds-field="decisionType"><option>Capital project</option><option>Policy choice</option><option>Procurement / supplier comparison</option><option>Facility retrofit</option><option>Program intervention</option><option>Strategy portfolio</option></select></label>
            </div>
            <label class="scds-wide">Decision question<textarea rows="4" data-scds-field="decisionQuestion">Should the company electrify part of its delivery fleet over the next five years while maintaining service reliability and controlling total cost of ownership?</textarea></label>
            <label class="scds-wide">Constraints, tradeoffs, or data gaps<textarea rows="4" data-scds-field="constraints">Upfront vehicle and charging infrastructure cost; electricity source uncertainty; driver training; route variability; maintenance capacity; possible grant funding; customer pressure for lower-carbon delivery.</textarea></label>
            <div class="scds-actions"><button type="button" class="scds-button scds-button-primary" data-scds-run>Run Decision Analysis</button><button type="button" class="scds-button" data-scds-demo>Reset Demo Inputs</button><button type="button" class="scds-button" data-scds-copy-shortcode>Copy Shortcode</button></div>
        </section>
    <?php }


    private function render_panel_workflow($mode) { ?>
        <section class="scds-panel" data-scds-panel="workflow">
            <div class="scds-panel-head">
                <p class="scds-section-kicker">Unified evidence and platform handoffs</p>
                <h3>Source → Research → Observe → Model → Validate → Trace → Decide</h3>
                <p>Decision Studio now accepts a shared typed-artifact envelope from the current Sustainable Catalyst platform. Every import can retain its source product, version, artifact identifier, methodology, freshness, confidence, integrity hash, and transformation history.</p>
            </div>
            <div class="scds-workflow-strip" aria-label="Decision Studio connected platform workflow">
                <span>Knowledge Library</span><span>Research Librarian</span><span>Site Intelligence</span><span>Workbench</span><span>Research Lab</span><span>Platform Core</span><span>Decision Studio</span>
            </div>
            <div class="scds-integration-grid">
                <?php foreach ($this->module_integrations() as $module) : ?>
                    <article class="scds-integration-card" data-scds-module="<?php echo esc_attr($module['id']); ?>">
                        <p class="scds-card-label"><?php echo esc_html($module['label']); ?></p>
                        <h4><?php echo esc_html($module['name']); ?></h4>
                        <p><?php echo esc_html($module['summary']); ?></p>
                        <p class="scds-integration-use"><strong>Packet target:</strong> <?php echo esc_html($module['packet_section']); ?></p>
                        <div class="scds-card-actions">
                            <a class="scds-mini-button" href="<?php echo esc_url($module['url']); ?>">Open product →</a>
                            <button type="button" class="scds-mini-button" data-scds-mark-artifact="<?php echo esc_attr($module['artifact_key']); ?>">Mark for packet</button>
                        </div>
                    </article>
                <?php endforeach; ?>
            </div>
            <div class="scds-note"><strong>v1.11.0 contract:</strong> <code>scds-platform-artifact/1.0</code> is additive. Legacy Canvas, Data, Analytics R, Global Impact, Narrative Risk, Finance, and Grit JSON exports remain importable through compatibility adapters.</div>
            <div class="scds-import-box">
                <div class="scds-panel-head scds-panel-head-small">
                    <p class="scds-section-kicker">Typed artifact import</p>
                    <h4>Paste a product artifact or legacy JSON export</h4>
                    <p>Select a source product or use auto-detect. Typed envelopes are validated before they are normalized into evidence, research, model, experiment, entity, provenance, and audit sections.</p>
                </div>
                <div class="scds-form-grid">
                    <label>Source product
                        <select data-scds-import-module>
                            <option value="">Auto-detect</option>
                            <option value="knowledge-library">Knowledge Library</option>
                            <option value="research-librarian">Research Librarian</option>
                            <option value="site-intelligence">Site Intelligence</option>
                            <option value="workbench">Workbench</option>
                            <option value="research-lab">Research Lab</option>
                            <option value="platform-core">Platform Core</option>
                            <optgroup label="Legacy compatibility">
                                <option value="catalyst-canvas">Catalyst Canvas</option>
                                <option value="catalyst-data">Catalyst Data</option>
                                <option value="catalyst-analytics-r">Catalyst Analytics R</option>
                                <option value="global-impact-catalyst">Global Impact Catalyst</option>
                                <option value="catalyst-narrative-risk">Narrative Risk</option>
                                <option value="catalyst-finance">Catalyst Finance</option>
                                <option value="catalyst-grit">Catalyst Grit</option>
                            </optgroup>
                        </select>
                    </label>
                    <label>Import action
                        <select data-scds-import-action>
                            <option value="merge">Validate and merge into packet</option>
                            <option value="preview">Preview normalized patch only</option>
                        </select>
                    </label>
                </div>
                <label class="scds-wide">Artifact JSON<textarea rows="10" data-scds-artifact-json placeholder='Paste an scds-platform-artifact/1.0 envelope or a supported legacy export'></textarea></label>
                <div class="scds-actions"><button type="button" class="scds-button scds-button-primary" data-scds-import-artifact>Validate &amp; Import</button><button type="button" class="scds-button" data-scds-load-sample-artifact>Load Knowledge Library Sample</button><button type="button" class="scds-button" data-scds-download-packet>Download Decision Packet JSON</button></div>
                <div class="scds-import-result" data-scds-import-result></div>
            </div>
            <div class="scds-actions"><button type="button" class="scds-button scds-button-primary" data-scds-packet-template>Preview Decision Packet</button><button type="button" class="scds-button" data-scds-run>Run Current Decision Analysis</button></div>
            <div class="scds-packet-preview" data-scds-packet-preview></div>
        </section>
    <?php }


    private function render_panel_readiness($mode) { ?>
        <section class="scds-panel" data-scds-panel="readiness">
            <div class="scds-panel-head">
                <p class="scds-section-kicker">Brief readiness &amp; review status</p>
                <h3>Quality gates before export</h3>
                <p>Review whether the Decision Packet is ready for a draft brief, reviewed export, or further evidence work. The readiness gate checks framing, evidence, scenarios, impact, claims, finance, recovery, audit/provenance, and synthesis.</p>
            </div>
            <div class="scds-note"><strong>v1.11.0:</strong> readiness scoring now surfaces section status, unresolved issues, required reviews, and export gates. It is a workflow quality screen, not approval or professional signoff.</div>
            <div class="scds-actions">
                <button type="button" class="scds-button scds-button-primary" data-scds-readiness>Check Brief Readiness</button>
                <button type="button" class="scds-button" data-scds-generate-review-status>Generate Review Status</button>
                <button type="button" class="scds-button" data-scds-export-readiness-json>Download Readiness JSON</button>
                <button type="button" class="scds-button" data-scds-integrated-brief>Generate Integrated Brief</button>
            </div>
            <div class="scds-readiness-output" data-scds-readiness-output></div>
        </section>
    <?php }

    private function render_panel_governance($mode) { ?>
        <section class="scds-panel" data-scds-panel="governance">
            <div class="scds-panel-head">
                <p class="scds-section-kicker">Decision governance &amp; review center</p>
                <h3>Assign accountability, control review, and record human approval</h3>
                <p>Move the Decision Packet through a controlled lifecycle with a named owner, assigned reviewers, approval conditions, exceptions, conflict declarations, sign-offs, expiration dates, and a tamper-evident review history.</p>
            </div>
            <div class="scds-note"><strong>Human control:</strong> Decision Studio may flag missing evidence or contradictions, but it cannot approve, certify, assure, or professionally sign off a decision.</div>
            <div class="scds-form-grid">
                <label>Current state<select data-scds-governance-current><option value="draft">Draft</option><option value="evidence_gathering">Evidence gathering</option><option value="analysis">Analysis</option><option value="review" selected>Review</option><option value="revision_required">Revision required</option><option value="approved">Approved</option><option value="rejected">Rejected</option><option value="deferred">Deferred</option><option value="implemented">Implemented</option><option value="retired">Retired</option></select></label>
                <label>Requested state<select data-scds-governance-requested><option value="review">Review</option><option value="revision_required">Revision required</option><option value="approved" selected>Approved</option><option value="rejected">Rejected</option><option value="deferred">Deferred</option><option value="implemented">Implemented</option><option value="retired">Retired</option></select></label>
                <label>Decision owner<input type="text" data-scds-governance-owner value="" placeholder="Accountable human owner"></label>
                <label>Owner role<input type="text" data-scds-governance-owner-role value="" placeholder="Program Director"></label>
                <label>Review actor<input type="text" data-scds-governance-actor value="" placeholder="Review Chair"></label>
                <label>Actor role<input type="text" data-scds-governance-actor-role value="review_chair"></label>
                <label>Approval expires<input type="date" data-scds-governance-expires></label>
                <label>Reassessment due<input type="date" data-scds-governance-reassess></label>
            </div>
            <label class="scds-wide">Transition reason<textarea rows="3" data-scds-governance-reason placeholder="Explain the review outcome or requested state change"></textarea></label>
            <div class="scds-form-grid">
                <label>Reviewers JSON<textarea rows="7" data-scds-governance-reviewers placeholder='[{"name":"Independent Reviewer","role":"independent_reviewer","status":"approved"}]'></textarea></label>
                <label>Approval conditions JSON<textarea rows="7" data-scds-governance-conditions placeholder='[{"description":"Evidence review complete","required":true,"status":"satisfied"}]'></textarea></label>
                <label>Exceptions JSON<textarea rows="7" data-scds-governance-exceptions placeholder='[{"severity":"high","description":"Open issue","status":"open"}]'></textarea></label>
                <label>Conflict declarations JSON<textarea rows="7" data-scds-governance-conflicts placeholder='[{"declared":true,"description":"Prior advisory role","mitigation":"Recusal","status":"recused"}]'></textarea></label>
                <label>Sign-offs JSON<textarea rows="7" data-scds-governance-signoffs placeholder='[{"role":"decision_owner","name":"Owner","status":"signed"},{"role":"independent_reviewer","name":"Reviewer","status":"signed"}]'></textarea></label>
            </div>
            <div class="scds-actions"><button type="button" class="scds-button scds-button-primary" data-scds-governance-evaluate>Evaluate Governance</button><button type="button" class="scds-button" data-scds-governance-transition>Record State Transition</button><button type="button" class="scds-button" data-scds-governance-sample>Load Complete Review Sample</button><button type="button" class="scds-button" data-scds-governance-download>Download Governance JSON</button></div>
            <div class="scds-governance-output" data-scds-governance-output></div>
        </section>
    <?php }

    private function render_panel_collaboration($mode) { ?>
        <section class="scds-panel" data-scds-panel="room">
            <div class="scds-panel-head"><div><p class="scds-kicker">v1.11.0 collaborative workspace</p><h3>Collaborative Decision Room</h3><p>Private WordPress-managed rooms for participants, comments, change requests, snapshots, version comparison, notifications, and approved-version locks.</p></div><span class="scds-status">Private by default</span></div>
            <?php if (!is_user_logged_in()) : ?>
                <div class="scds-note"><strong>Sign-in required.</strong> Decision Rooms are private records and are not available to anonymous visitors.</div>
            <?php else : ?>
            <div class="scds-grid scds-grid-3">
                <label>Room title<input type="text" data-scds-room-title value="Collaborative Decision Room"></label>
                <label>Visibility<select data-scds-room-visibility><option value="private">Private</option><option value="restricted">Restricted</option><option value="institutional">Institutional</option></select></label>
                <label>Your room role<select data-scds-room-role><option value="owner">Owner</option><option value="facilitator">Facilitator</option><option value="editor">Editor</option><option value="reviewer">Reviewer</option><option value="client">Client</option><option value="observer">Observer</option></select></label>
                <label>Comment target type<input type="text" data-scds-room-target-type value="decision_packet"></label>
                <label>Target ID<input type="text" data-scds-room-target-id value="packet-root"></label>
                <label>Snapshot label<input type="text" data-scds-room-snapshot-label value="Decision Packet snapshot"></label>
            </div>
            <label>Comment<textarea rows="3" data-scds-room-comment placeholder="Attach a review comment to the packet, evidence record, assumption, scenario, or brief section."></textarea></label>
            <div class="scds-actions">
                <button type="button" class="scds-button scds-button-primary" data-scds-room-create>Create / evaluate room</button>
                <button type="button" class="scds-button" data-scds-room-comment-add>Add comment</button>
                <button type="button" class="scds-button" data-scds-room-snapshot>Create snapshot</button>
                <button type="button" class="scds-button" data-scds-room-compare>Compare latest snapshots</button>
                <button type="button" class="scds-button" data-scds-room-save>Save to WordPress</button>
                <button type="button" class="scds-button" data-scds-room-refresh>Refresh rooms</button>
                <button type="button" class="scds-button" data-scds-room-download>Download room JSON</button>
            </div>
            <details class="scds-details"><summary>Members and change requests</summary>
                <label>Members JSON<textarea rows="8" data-scds-room-members>[{"name":"Decision owner","email":"","role":"owner","status":"active"}]</textarea></label>
                <label>Change request title<input type="text" data-scds-room-change-title value="Review requested packet change"></label>
                <label>Change request description<textarea rows="3" data-scds-room-change-description></textarea></label>
                <label>Packet patch JSON<textarea rows="6" data-scds-room-patch>{}</textarea></label>
                <label>Resolution / reopen note<textarea rows="3" data-scds-room-resolution placeholder="Explain the resolution, implementation decision, or reason for reopening an approved version."></textarea></label>
                <label>Invitation JSON<textarea rows="5" data-scds-room-invite>{"name":"Review participant","email":"","role":"reviewer","expires_at":""}</textarea></label>
                <div class="scds-actions">
                    <button type="button" class="scds-button" data-scds-room-change-request>Create change request</button>
                    <button type="button" class="scds-button" data-scds-room-comment-resolve>Resolve target comment</button>
                    <button type="button" class="scds-button" data-scds-room-change-resolve>Accept target change</button>
                    <button type="button" class="scds-button" data-scds-room-change-implement>Implement target change</button>
                    <button type="button" class="scds-button" data-scds-room-apply-revision>Apply packet patch</button>
                    <button type="button" class="scds-button" data-scds-room-invite>Invite participant</button>
                    <button type="button" class="scds-button" data-scds-room-lock>Lock approved version</button>
                    <button type="button" class="scds-button" data-scds-room-reopen>Reopen locked version</button>
                    <button type="button" class="scds-button" data-scds-room-contact-handoff>Create Contact &amp; Engagement handoff</button>
                </div>
            </details>
            <div class="scds-output" data-scds-room-output aria-live="polite"></div>
            <div class="scds-output" data-scds-room-list aria-live="polite"></div>
            <?php endif; ?>
        </section>
    <?php }

    private function render_panel_scorecard($mode) { ?>
        <section class="scds-panel" data-scds-panel="scorecard">
            <div class="scds-panel-head"><p class="scds-section-kicker">Four-pillar scorecard</p><h3>Environmental, social, economic, and governance scoring</h3><p>Use transparent weights and indicators to compare viability across the four pillars.</p></div>
            <div class="scds-form-grid">
                <label>Baseline annual emissions (tCO₂e)<input type="number" data-scds-field="baselineEmissions" value="1200" min="0" step="10"></label>
                <label>Expected emissions reduction (%)<input type="number" data-scds-field="reductionRate" value="32" min="0" max="100"></label>
                <label>Implementation/adoption rate (%)<input type="number" data-scds-field="adoptionRate" value="65" min="0" max="100"></label>
                <label>CAPEX ($)<input type="number" data-scds-field="capex" value="950000" min="0" step="1000"></label>
                <label>Annual savings ($)<input type="number" data-scds-field="annualSavings" value="185000" min="0" step="1000"></label>
                <label>Discount rate (%)<input type="number" data-scds-field="discountRate" value="7" min="0" max="40" step="0.1"></label>
                <label>Model years<input type="number" data-scds-field="modelYears" value="5" min="1" max="50"></label>
                <label>Implementation complexity<select data-scds-field="complexity"><option>Low</option><option selected>Medium</option><option>High</option><option>Very high</option></select></label>
            </div>
            <div class="scds-weight-grid"><label>Environmental weight<input type="number" data-scds-field="weightEnv" value="30"></label><label>Social weight<input type="number" data-scds-field="weightSocial" value="20"></label><label>Economic weight<input type="number" data-scds-field="weightEconomic" value="30"></label><label>Governance weight<input type="number" data-scds-field="weightGovernance" value="20"></label></div>
        </section>
    <?php }

    private function render_panel_risk($mode) { ?>
        <section class="scds-panel" data-scds-panel="risk">
            <div class="scds-panel-head"><p class="scds-section-kicker">Risk and resilience</p><h3>Map exposure, vulnerability, and mitigation capacity</h3><p>Screen risk across cost, implementation, environmental, stakeholder, and governance dimensions.</p></div>
            <div class="scds-form-grid">
                <label>Exposure score (0–100)<input type="number" data-scds-field="exposure" value="55" min="0" max="100"></label>
                <label>Vulnerability score (0–100)<input type="number" data-scds-field="vulnerability" value="48" min="0" max="100"></label>
                <label>Resilience / mitigation score (0–100)<input type="number" data-scds-field="resilience" value="62" min="0" max="100"></label>
                <label>Stakeholder sensitivity (0–100)<input type="number" data-scds-field="stakeholderSensitivity" value="45" min="0" max="100"></label>
                <label>Governance readiness (0–100)<input type="number" data-scds-field="governanceReadiness" value="68" min="0" max="100"></label>
                <label>Data confidence (0–100)<input type="number" data-scds-field="dataConfidence" value="70" min="0" max="100"></label>
            </div>
        </section>
    <?php }

    private function render_panel_scenario($mode) { ?>
        <section class="scds-panel" data-scds-panel="scenario">
            <div class="scds-panel-head">
                <p class="scds-section-kicker">Advanced Scenario &amp; Sensitivity Studio</p>
                <h3>Compare alternatives, vary assumptions, find thresholds, and inspect uncertainty</h3>
                <p>Model any number of alternatives, apply weighted criteria, run one-way and two-variable sensitivity screens, search for break-even points, compare time horizons, and review stakeholder distribution and reversibility.</p>
            </div>
            <div class="scds-note"><strong>v1.11.0:</strong> scenario analysis is now an auditable studio rather than a fixed comparison table. Screening outputs remain conditional on the assumptions entered and should be routed to Workbench for probabilistic simulation, optimization, engineering, or domain forecasting.</div>
            <div class="scds-scenario-studio-grid">
                <label>Alternatives JSON
                    <textarea rows="12" data-scds-scenario-alternatives><?php echo esc_textarea(wp_json_encode([
                        ['id'=>'conservative','label'=>'Conservative','parameters'=>['capex'=>850000,'annualSavings'=>145000,'reductionRate'=>24,'adoptionRate'=>52],'reversibility'=>78,'stakeholderEquity'=>55,'implementationComplexity'=>'Low'],
                        ['id'=>'expected','label'=>'Expected','parameters'=>[],'reversibility'=>60,'stakeholderEquity'=>62,'implementationComplexity'=>'Medium'],
                        ['id'=>'ambitious','label'=>'Ambitious','parameters'=>['capex'=>1120000,'annualSavings'=>235000,'reductionRate'=>44,'adoptionRate'=>82],'reversibility'=>38,'stakeholderEquity'=>74,'implementationComplexity'=>'High']
                    ], JSON_PRETTY_PRINT)); ?></textarea>
                </label>
                <label>Parameter ranges JSON
                    <textarea rows="12" data-scds-scenario-ranges><?php echo esc_textarea(wp_json_encode([
                        'capex'=>['min'=>700000,'max'=>1250000,'steps'=>5],
                        'annualSavings'=>['min'=>100000,'max'=>280000,'steps'=>5],
                        'adoptionRate'=>['min'=>45,'max'=>90,'steps'=>5]
                    ], JSON_PRETTY_PRINT)); ?></textarea>
                </label>
                <label>Criteria JSON
                    <textarea rows="12" data-scds-scenario-criteria><?php echo esc_textarea(wp_json_encode($this->scenario_studio_criteria(), JSON_PRETTY_PRINT)); ?></textarea>
                </label>
            </div>
            <div class="scds-form-grid scds-scenario-controls">
                <label>Sensitivity parameters<input type="text" data-scds-sensitivity-parameters value="capex, annualSavings, adoptionRate"></label>
                <label>Break-even parameter<select data-scds-threshold-parameter><option value="annualSavings">Annual savings</option><option value="capex">CAPEX</option><option value="adoptionRate">Adoption rate</option><option value="reductionRate">Reduction rate</option><option value="discountRate">Discount rate</option></select></label>
                <label>Target metric<select data-scds-threshold-metric><option value="npv">NPV</option><option value="decision_score">Decision score</option><option value="annual_avoided_tco2e">Annual avoided emissions</option><option value="risk_score">Risk score</option></select></label>
                <label>Target value<input type="number" data-scds-threshold-value value="0" step="any"></label>
                <label>Time horizons<input type="text" data-scds-time-horizons value="1, 3, 5, 10"></label>
                <label>Grid points<input type="number" data-scds-grid-points value="5" min="3" max="21"></label>
            </div>
            <div class="scds-actions">
                <button type="button" class="scds-button scds-button-primary" data-scds-scenario-studio-run>Run Advanced Scenario Studio</button>
                <button type="button" class="scds-button" data-scds-scenario-studio-sensitivity>Run Sensitivity</button>
                <button type="button" class="scds-button" data-scds-scenario-studio-threshold>Find Break-Even</button>
                <button type="button" class="scds-button" data-scds-scenario-studio-sample>Restore Sample</button>
                <button type="button" class="scds-button" data-scds-export-scenario-studio-json>Download Studio JSON</button>
                <button type="button" class="scds-button" data-scds-scenario-compare>Compatibility Matrix</button>
                <button type="button" class="scds-button" data-scds-workbench-handoff>Recommend Workbench Handoffs</button>
            </div>
            <div class="scds-scenario-studio-output" data-scds-scenario-studio-output></div>
            <details class="scds-compatibility-details"><summary>Compatibility scenario matrix</summary><div class="scds-scenario-comparison" data-scds-scenario-output></div></details>
        </section>
    <?php }

    private function render_panel_handoff($mode) { ?>
        <section class="scds-panel" data-scds-panel="handoff">
            <div class="scds-panel-head"><p class="scds-section-kicker">Workbench handoff</p><h3>Send deeper calculations, graphs, and technical checks to Workbench</h3><p>Decision Studio synthesizes the decision. Workbench performs deeper symbolic, graph, engineering, scenario, risk, economics, environmental QA/QC, and domain-specific analysis.</p></div>
            <div class="scds-note"><strong>v1.11.0:</strong> handoff recommendations include tool IDs, reasons, priorities, shortcodes, and a payload summary that can be used to continue analysis in Workbench.</div>
            <div class="scds-actions"><button type="button" class="scds-button scds-button-primary" data-scds-workbench-handoff>Generate Workbench Handoff Plan</button><button type="button" class="scds-button" data-scds-export-handoff-json>Download Handoff JSON</button><button type="button" class="scds-button" data-scds-scenario-compare>Refresh Scenario Matrix</button></div>
            <div class="scds-workbench-handoff" data-scds-handoff-output></div>
        </section>
    <?php }


    private function render_panel_export_center($mode) { ?>
        <section class="scds-panel" data-scds-panel="export">
            <div class="scds-panel-head">
                <p class="scds-section-kicker">Saved Decision Packets &amp; Export Center</p>
                <h3>Save the packet, reload prior work, and export the full decision bundle</h3>
                <p>Decision Studio can preserve the current Decision Packet as a browser-saved working record, generate a complete export bundle, and prepare JSON, Markdown, HTML, audit, readiness, scenario, and Workbench handoff exports.</p>
            </div>
            <div class="scds-note"><strong>v1.11.0:</strong> saved packets are working records for review and continuation. Reviewed and public exports are governed by the current approval gate; internal draft exports remain available for controlled working use.</div>
            <div class="scds-form-grid scds-export-controls">
                <label>Export audience
                    <select data-scds-export-audience>
                        <option value="internal">Internal working draft</option>
                        <option value="reviewed">Reviewed institutional export</option>
                        <option value="public">Public decision dossier</option>
                    </select>
                </label>
            </div>
            <div class="scds-actions">
                <button type="button" class="scds-button scds-button-primary" data-scds-save-packet-local>Save Packet Locally</button>
                <button type="button" class="scds-button" data-scds-refresh-packets>Refresh Saved Packets</button>
                <button type="button" class="scds-button" data-scds-export-bundle-json>Download Export Bundle JSON</button>
                <button type="button" class="scds-button" data-scds-export-bundle-md>Download Brief Markdown</button>
                <button type="button" class="scds-button" data-scds-export-bundle-html>Download Brief HTML</button>
                <button type="button" class="scds-button" data-scds-print>Print / Save PDF</button>
            </div>
            <div class="scds-export-layout">
                <div class="scds-export-panel">
                    <h4>Saved packets</h4>
                    <div class="scds-saved-packets" data-scds-saved-packets></div>
                </div>
                <div class="scds-export-panel">
                    <h4>Export bundle</h4>
                    <div class="scds-export-output" data-scds-export-output></div>
                </div>
            </div>
        </section>
    <?php }

    private function render_panel_report($mode) { ?>
        <section class="scds-panel" data-scds-panel="report">
            <div class="scds-panel-head">
                <p class="scds-section-kicker">Integrated brief generator</p>
                <h3>Professional decision memo from the full Decision Packet</h3>
                <p>Generate a structured brief that synthesizes framing, evidence, scenarios, impact records, claim review, finance, recovery, four-pillar scores, audit/provenance, and Workbench handoffs.</p>
            </div>
            <div class="scds-note"><strong>v1.11.0:</strong> the brief generator now includes readiness status, scenario comparison matrix, Workbench handoff details, audit appendix summary, and Markdown/HTML/JSON exports.</div>
            <div class="scds-actions">
                <button type="button" class="scds-button scds-button-primary" data-scds-integrated-brief>Generate Integrated Brief</button>
                <button type="button" class="scds-button" data-scds-run>Generate Basic Brief</button>
                <button type="button" class="scds-button" data-scds-ai-brief>Generate AI Decision Brief</button>
                <button type="button" class="scds-button" data-scds-export-integrated-md>Download Markdown</button>
                <button type="button" class="scds-button" data-scds-export-integrated-html>Download HTML</button>
                <button type="button" class="scds-button" data-scds-export-integrated-json>Download JSON</button>
                <button type="button" class="scds-button" data-scds-print>Print / Save PDF</button>
            </div>
            <div class="scds-report" data-scds-report></div>
        </section>
    <?php }

    private function render_panel_ai($mode) { ?>
        <section class="scds-panel" data-scds-panel="ai"><div class="scds-panel-head"><p class="scds-section-kicker">AI Decision Briefing Layer</p><h3>Assumption critique, risk interpretation, and decision caveats</h3><p>Generate a cautious, site-scoped decision-support brief through the configured backend AI provider when available. If the backend or provider is unavailable, Decision Studio returns a deterministic fallback brief.</p></div><div class="scds-note"><strong>AI boundary:</strong> AI output is a drafting and interpretation aid. It does not approve, certify, assure, or replace professional judgment.</div><div class="scds-actions"><button type="button" class="scds-button scds-button-primary" data-scds-ai-brief>Generate AI Decision Brief</button><button type="button" class="scds-button" data-scds-backend-status>Check Backend / AI Status</button></div><div class="scds-ai-output" data-scds-ai-output></div></section>
    <?php }

    private function render_panel_audit($mode) { ?>
        <section class="scds-panel" data-scds-panel="audit">
            <div class="scds-panel-head">
                <p class="scds-section-kicker">Audit &amp; Provenance</p>
                <h3>Decision packet ledger, sources, assumptions, calculations, claims, changes, and review status</h3>
                <p>Generate a structured audit appendix that shows what was entered, which module artifacts are present, which sources support the decision, which calculations were used, and which assumptions still require review.</p>
            </div>
            <div class="scds-note"><strong>v1.11.0:</strong> audit works with the readiness gate so unresolved evidence, source, calculation, finance, claim, and review issues can be surfaced before export.</div>
            <div class="scds-actions"><button type="button" class="scds-button scds-button-primary" data-scds-audit-generate>Generate Audit Appendix</button><button type="button" class="scds-button" data-scds-export-audit-json>Download Audit JSON</button><button type="button" class="scds-button" data-scds-print>Print / Save PDF</button></div>
            <div class="scds-audit-list" data-scds-audit></div>
            <div class="scds-workbench-links" data-scds-workbench-links></div>
        </section>
    <?php }

    public function register_admin_menu() {
        add_menu_page('SC Decision Studio', 'SC Decision Studio', 'manage_options', 'scds-dashboard', [$this, 'render_admin_dashboard'], 'dashicons-chart-area', 59);
        add_submenu_page('scds-dashboard', 'Projects', 'Projects', 'manage_options', 'scds-projects', [$this, 'render_admin_projects']);
        add_submenu_page('scds-dashboard', 'Collaborative Decision Rooms', 'Decision Rooms', 'manage_options', 'scds-rooms', [$this, 'render_admin_rooms']);
        add_submenu_page('scds-dashboard', 'Integrated Workflow', 'Integrated Workflow', 'manage_options', 'scds-integrations', [$this, 'render_admin_integrations']);
        add_submenu_page('scds-dashboard', 'Scenario Templates', 'Scenario Templates', 'manage_options', 'scds-templates', [$this, 'render_admin_templates']);
        add_submenu_page('scds-dashboard', 'Scenario & Workbench Handoff', 'Scenario & Handoff', 'manage_options', 'scds-scenario-handoff', [$this, 'render_admin_scenario_handoff']);
        add_submenu_page('scds-dashboard', 'Scorecard Builder', 'Scorecard Builder', 'manage_options', 'scds-scorecard', [$this, 'render_admin_scorecard']);
        add_submenu_page('scds-dashboard', 'Report Templates', 'Report Templates', 'manage_options', 'scds-reports', [$this, 'render_admin_reports']);
        add_submenu_page('scds-dashboard', 'AI Briefing Layer', 'AI Briefing Layer', 'manage_options', 'scds-ai-briefing', [$this, 'render_admin_ai_briefing']);
        add_submenu_page('scds-dashboard', 'Validation Dashboard', 'Validation Dashboard', 'manage_options', 'scds-validation', [$this, 'render_admin_validation']);
        add_submenu_page('scds-dashboard', 'Export Center', 'Export Center', 'manage_options', 'scds-export', [$this, 'render_admin_export']);
        add_submenu_page('scds-dashboard', 'Public Landing & Demo', 'Public Landing & Demo', 'manage_options', 'scds-public-pages', [$this, 'render_admin_public_pages']);
        add_submenu_page('scds-dashboard', 'Release Diagnostics', 'Release Diagnostics', 'manage_options', 'scds-diagnostics', [$this, 'render_admin_diagnostics']);
        add_submenu_page('scds-dashboard', 'Methodology Settings', 'Methodology Settings', 'manage_options', 'scds-settings', [$this, 'render_admin_settings']);
    }

    private function admin_wrap_start($title, $subtitle='') { echo '<div class="wrap scds-admin"><h1>' . esc_html($title) . '</h1>'; if ($subtitle) echo '<p>' . esc_html($subtitle) . '</p>'; }
    private function admin_wrap_end() { echo '</div>'; }

    public function render_admin_dashboard() {
        $this->admin_wrap_start('Sustainable Catalyst Decision Studio v' . self::VERSION, 'Integrated decision-support workflow for framing, evidence, scenarios, impact, claims, finance, recovery, and four-pillar reports, saved Decision Packets, and export bundles.');
        echo '<div class="scds-admin-grid">';
        $cards = [
            ['Projects', 'Track project drafts and generated decision briefs.', 'admin.php?page=scds-projects'],
            ['Integrated Workflow', 'Map Canvas, Data, Analytics R, Impact, Narrative Risk, Finance, Grit, and Decision Studio.', 'admin.php?page=scds-integrations'],
            ['Scenario Templates', 'Baseline, conservative, expected, ambitious, stress, and transition cases.', 'admin.php?page=scds-templates'],
            ['Scorecard Builder', 'Define four-pillar weights and indicator logic.', 'admin.php?page=scds-scorecard'],
            ['Validation Dashboard', 'Review module status, warnings, sample inputs, and expected outputs.', 'admin.php?page=scds-validation'],
            ['Export Center', 'Download saved packet exports, decision bundles, validation, and methodology exports.', 'admin.php?page=scds-export'],
            ['Public Landing & Demo', 'Copy launch-ready landing and demo shortcodes and product-page structure.', 'admin.php?page=scds-public-pages'],
            ['Release Diagnostics', 'Check build identity, database migration state, backend health, and version parity.', 'admin.php?page=scds-diagnostics'],
            ['Methodology Settings', 'Configure backend URL, integration boundaries, and default display mode.', 'admin.php?page=scds-settings'],
        ];
        foreach ($cards as $c) echo '<div class="card"><h2>' . esc_html($c[0]) . '</h2><p>' . esc_html($c[1]) . '</p><a class="button button-primary" href="' . esc_url(admin_url($c[2])) . '">Open</a></div>';
        echo '</div><h2>Shortcodes</h2><textarea readonly style="width:100%;height:130px">[sc_decision_studio mode="landing" title="Sustainable Catalyst Decision Studio"]&#10;[sc_decision_studio mode="demo" title="Decision Studio Demo"]&#10;[sc_decision_studio mode="full"]&#10;[sc_decision_studio mode="project-intake"]&#10;[sc_decision_studio mode="scorecard"]&#10;[sc_decision_studio mode="risk"]&#10;[sc_decision_studio mode="scenario"]&#10;[sc_decision_studio mode="report"]&#10;[sc_decision_studio mode="packets"]&#10;[sc_decision_studio mode="export"]&#10;[sc_decision_studio mode="readiness"]&#10;[sc_decision_studio mode="drawer" title="Open Decision Studio"]</textarea>';
        $this->admin_wrap_end();
    }


    public function render_admin_integrations() {
        $this->admin_wrap_start('Integrated Platform Workflow', 'Decision Studio v1.11.0 maps specialized modules into one Decision Packet, compares scenarios, routes deeper analysis to Workbench, and prepares saved packet/export workflows.');
        echo '<p>Use this map as the integration contract for the next build: module artifact exports should feed the Decision Packet sections listed below.</p>';
        echo '<table class="widefat striped"><thead><tr><th>Step</th><th>Module</th><th>Role</th><th>Feeds Decision Packet</th><th>URL</th></tr></thead><tbody>';
        foreach ($this->module_integrations() as $m) {
            echo '<tr><td>' . intval($m['step']) . '</td><td><strong>' . esc_html($m['name']) . '</strong><br><code>' . esc_html($m['id']) . '</code></td><td>' . esc_html($m['summary']) . '</td><td><code>' . esc_html($m['artifact_key']) . '</code><br>' . esc_html($m['feeds']) . '</td><td><a href="' . esc_url($m['url']) . '">' . esc_html($m['url']) . '</a></td></tr>';
        }
        echo '</tbody></table>';
        echo '<h2>Decision Packet template</h2><pre style="background:#fff;padding:18px;border:1px solid #ccd0d4;white-space:pre-wrap">' . esc_html(wp_json_encode($this->decision_packet_template(), JSON_PRETTY_PRINT)) . '</pre>';
        $this->admin_wrap_end();
    }

    public function render_admin_projects() {
        global $wpdb; $table = $wpdb->prefix . self::PROJECTS_TABLE; $rows = $wpdb->get_results("SELECT * FROM $table ORDER BY id DESC LIMIT 100", ARRAY_A);
        $this->admin_wrap_start('Decision Studio Projects', 'Saved project drafts and generated analyses.');
        echo '<table class="widefat striped"><thead><tr><th>ID</th><th>Project</th><th>Sector</th><th>Status</th><th>Updated</th></tr></thead><tbody>';
        if (!$rows) echo '<tr><td colspan="5">No saved projects yet. Public visitors can still run local analysis without saving.</td></tr>';
        foreach ($rows as $r) echo '<tr><td>' . intval($r['id']) . '</td><td>' . esc_html($r['project_name']) . '</td><td>' . esc_html($r['sector']) . '</td><td>' . esc_html($r['status']) . '</td><td>' . esc_html($r['updated_at']) . '</td></tr>';
        echo '</tbody></table>'; $this->admin_wrap_end();
    }

    public function render_admin_rooms() {
        global $wpdb; $table=$wpdb->prefix.self::ROOMS_TABLE; $rows=$wpdb->get_results("SELECT id,room_uuid,title,visibility,status,owner_user_id,created_at,updated_at FROM $table ORDER BY id DESC LIMIT 100",ARRAY_A);
        $this->admin_wrap_start('Collaborative Decision Rooms','Private WordPress-managed collaboration workspaces. Room JSON remains canonical in WordPress; the FastAPI backend provides contract validation and deterministic room actions.');
        $this->render_csv_table($rows ?: []); $this->admin_wrap_end();
    }

    public function render_admin_templates() { $this->admin_wrap_start('Scenario Templates', 'Bundled scenario structures for sustainability decisions.'); $this->render_csv_table($this->scenario_templates()); $this->admin_wrap_end(); }
    public function render_admin_scenario_handoff() { $this->admin_wrap_start('Scenario Comparison and Workbench Handoff', 'v1.11.0 collaborative decision-room layer for comparing alternatives, testing sensitivity and thresholds, routing deeper computation to Workbench, and feeding governed export bundles.'); echo '<p><strong>Endpoints:</strong> /scenario-studio/template, /scenario-studio/analyze, /scenario-studio/sensitivity, /scenario-studio/threshold, /decision-packet/scenario-studio, /workbench/handoff, /decision-packet/workbench-handoff.</p>'; echo '<pre style="background:#fff;padding:18px;border:1px solid #ccd0d4;white-space:pre-wrap">' . esc_html(wp_json_encode($this->workbench_handoff_catalog(), JSON_PRETTY_PRINT)) . '</pre>'; $this->admin_wrap_end(); }
    public function render_admin_scorecard() { $this->admin_wrap_start('Scorecard Builder', 'Default indicators and weights for four-pillar decision support.'); $this->render_csv_table($this->scorecard_rows()); $this->admin_wrap_end(); }
    public function render_admin_reports() { $this->admin_wrap_start('Report Templates', 'Decision brief structure used by the public interface and backend.'); echo '<pre style="background:#fff;padding:18px;border:1px solid #ccd0d4;white-space:pre-wrap">' . esc_html($this->report_template_markdown()) . '</pre>'; $this->admin_wrap_end(); }

    public function render_admin_ai_briefing() {
        $s = $this->settings();
        $this->admin_wrap_start('AI Decision Briefing Layer', 'Backend-routed AI decision briefs with deterministic fallback, assumption critique, and responsible-use caveats.');
        echo '<div class="notice notice-info"><p><strong>Backend-only key pattern:</strong> Store Gemini/OpenAI keys in Render or server environment variables, not in WordPress. WordPress only calls the Decision Studio backend.</p></div>';
        echo '<table class="widefat striped"><tbody>';
        echo '<tr><th>AI briefing enabled</th><td>' . esc_html($s['ai_briefing_enabled'] === '1' ? 'Yes' : 'No') . '</td></tr>';
        echo '<tr><th>Backend URL</th><td><code>' . esc_html($s['backend_url'] ?: 'Not configured') . '</code></td></tr>';
        echo '<tr><th>Backend enabled</th><td>' . esc_html($s['backend_enabled'] === '1' ? 'Yes' : 'No') . '</td></tr>';
        echo '<tr><th>Frontend fallback</th><td>Deterministic WordPress brief if backend or AI provider is unavailable.</td></tr>';
        echo '</tbody></table>';
        echo '<h2>Backend environment variables</h2><pre style="background:#fff;padding:18px;border:1px solid #ccd0d4;white-space:pre-wrap">SCDS_AI_PROVIDER=gemini
SCDS_GEMINI_API_KEY=&lt;set-in-render&gt;
SCDS_GEMINI_MODEL=&lt;your-model&gt;

# or
SCDS_AI_PROVIDER=openai
SCDS_OPENAI_API_KEY=&lt;set-in-render&gt;
SCDS_OPENAI_MODEL=&lt;your-model&gt;</pre>';
        $this->admin_wrap_end();
    }

    public function render_admin_validation() {
        global $wpdb; $table = $wpdb->prefix . self::VALIDATION_TABLE; $rows = $wpdb->get_results("SELECT * FROM $table ORDER BY FIELD(status,'needs_review','experimental','validated'), module_name", ARRAY_A);
        $this->admin_wrap_start('Validation Dashboard', 'Module status, sample inputs, warnings, and validation readiness.');
        echo '<table class="widefat striped"><thead><tr><th>Module</th><th>Status</th><th>Warnings</th><th>Last Validated</th></tr></thead><tbody>';
        foreach ($rows as $r) echo '<tr><td><strong>' . esc_html($r['module_name']) . '</strong><br><code>' . esc_html($r['module_id']) . '</code></td><td>' . esc_html($r['status']) . '</td><td>' . esc_html($r['warnings']) . '</td><td>' . esc_html($r['last_validated']) . '</td></tr>';
        echo '</tbody></table>'; $this->admin_wrap_end();
    }

    public function render_admin_export() {
        global $wpdb; $table = $wpdb->prefix . self::PROJECTS_TABLE; $rows = $wpdb->get_results("SELECT id,project_name,status,updated_at FROM $table ORDER BY id DESC LIMIT 50", ARRAY_A);
        $this->admin_wrap_start('Export Center', 'Saved Decision Packets, export bundles, validation datasets, scenario templates, and Workbench integration maps.');
        echo '<p><a class="button button-primary" href="' . esc_url(rest_url('scds/v1/export/validation.csv')) . '">Download Validation CSV</a> <a class="button" href="' . esc_url(rest_url('scds/v1/export/templates.csv')) . '">Download Scenario Templates CSV</a> <a class="button" href="' . esc_url(rest_url('scds/v1/export/tool-map.csv')) . '">Download Tool Map CSV</a></p>';
        echo '<h2>Saved Decision Packets</h2>';
        if ($rows) { echo '<table class="widefat striped"><thead><tr><th>ID</th><th>Project</th><th>Status</th><th>Updated</th><th>Export</th></tr></thead><tbody>'; foreach($rows as $r){ echo '<tr><td>'.intval($r['id']).'</td><td>'.esc_html($r['project_name']).'</td><td>'.esc_html($r['status']).'</td><td>'.esc_html($r['updated_at']).'</td><td><a class="button" href="'.esc_url(rest_url('scds/v1/packets/'.intval($r['id']).'/export')).'">Packet JSON</a></td></tr>'; } echo '</tbody></table>'; }
        else { echo '<p>No WordPress-saved Decision Packets yet. The public interface can still save packets locally in the browser.</p>'; }
        echo '<h2>Export Bundle Template</h2><pre style="background:#fff;padding:18px;border:1px solid #ccd0d4;white-space:pre-wrap">' . esc_html(wp_json_encode($this->export_center_template(), JSON_PRETTY_PRINT)) . '</pre>';
        echo '<h2>Workbench Integration Map</h2>'; $this->render_csv_table($this->workbench_tool_map()); $this->admin_wrap_end();
    }


    public function render_admin_public_pages() {
        $this->admin_wrap_start('Public Landing & Demo', 'Decision Studio v1.11.0 launch-ready public page structure, demo flow, and shortcode guidance.');
        $template = $this->public_landing_template();
        echo '<h2>Recommended shortcodes</h2><textarea readonly style="width:100%;height:145px">[sc_decision_studio mode="landing" title="Sustainable Catalyst Decision Studio"]&#10;[sc_decision_studio mode="demo" title="Decision Studio Demo"]&#10;[sc_decision_studio mode="full" title="Sustainable Catalyst Decision Studio"]&#10;[sc_decision_studio mode="room" title="Collaborative Decision Room"]&#10;[sc_decision_studio mode="export" title="Decision Studio Export Center"]</textarea>';
        echo '<h2>Workflow copy</h2><p><strong>Use Knowledge Library to source. Research Librarian to route. Site Intelligence to observe. Workbench to calculate. Research Lab to test. Platform Core to connect. Decision Studio to compare, collaborate, govern, and decide.</strong></p>';
        echo '<h2>Landing template</h2><pre style="background:#fff;padding:18px;border:1px solid #ccd0d4;white-space:pre-wrap">' . esc_html(wp_json_encode($template, JSON_PRETTY_PRINT)) . '</pre>';
        $this->admin_wrap_end();
    }

    public function render_admin_diagnostics() {
        $diagnostics = $this->backend_diagnostics();
        $this->admin_wrap_start('Decision Studio Release Diagnostics', 'Production identity, migration, backend health, and WordPress/backend version parity for v' . self::VERSION . '.');
        $state = $diagnostics['state'] ?? 'unknown';
        $class = $state === 'matched' ? 'notice-success' : ($state === 'backend-disabled' ? 'notice-info' : 'notice-warning');
        echo '<div class="notice ' . esc_attr($class) . '"><p><strong>State:</strong> ' . esc_html($state) . '</p></div>';
        echo '<table class="widefat striped"><tbody>';
        echo '<tr><th>WordPress plugin</th><td><code>' . esc_html(self::VERSION) . '</code></td></tr>';
        echo '<tr><th>Build fingerprint</th><td><code>' . esc_html(self::BUILD_FINGERPRINT) . '</code></td></tr>';
        echo '<tr><th>Database schema</th><td><code>' . esc_html((string) get_option(self::DB_VERSION_OPTION, 'not-recorded')) . '</code></td></tr>';
        echo '<tr><th>Backend version</th><td><code>' . esc_html((string) ($diagnostics['backend_version'] ?? 'not connected')) . '</code></td></tr>';
        echo '<tr><th>Version parity</th><td>' . esc_html(isset($diagnostics['version_matches']) ? ($diagnostics['version_matches'] ? 'Matched' : 'Mismatched') : 'Not checked') . '</td></tr>';
        echo '</tbody></table>';
        echo '<h2>Diagnostic payload</h2><pre style="background:#fff;padding:18px;border:1px solid #ccd0d4;white-space:pre-wrap">' . esc_html(wp_json_encode($diagnostics, JSON_PRETTY_PRINT)) . '</pre>';
        $this->admin_wrap_end();
    }

    public function render_admin_settings() {
        $s = $this->settings();
        $this->admin_wrap_start('Decision Studio Settings', 'Backend-ready settings and public boundary language.');
        echo '<form method="post">'; wp_nonce_field('scds_save_settings');
        echo '<table class="form-table"><tbody>';
        $this->settings_row('brand_title', 'Brand title', $s['brand_title']);
        $this->settings_row('brand_subtitle', 'Brand subtitle', $s['brand_subtitle'], true);
        $this->settings_row('methodology_note', 'Methodology note', $s['methodology_note'], true);
        $this->settings_row('backend_url', 'FastAPI backend URL', $s['backend_url']);
        $this->settings_row('backend_api_key', 'Backend API key', $s['backend_api_key']);
        echo '<tr><th>Backend enabled</th><td><label><input type="checkbox" name="scds_settings[backend_enabled]" value="1" ' . checked($s['backend_enabled'], '1', false) . '> Use backend when available</label></td></tr>';
        echo '<tr><th>AI Decision Briefing</th><td><label><input type="checkbox" name="scds_settings[ai_briefing_enabled]" value="1" ' . checked($s['ai_briefing_enabled'], '1', false) . '> Enable AI briefing UI and backend calls when configured</label><p class="description">Provider keys should live only in the backend environment.</p></td></tr>';
        echo '<tr><th>Workbench integration</th><td><label><input type="checkbox" name="scds_settings[workbench_integration]" value="1" ' . checked($s['workbench_integration'], '1', false) . '> Show related Workbench shortcodes and calculators</label></td></tr>';
        echo '<tr><th>Default display</th><td><select name="scds_settings[default_display]"><option value="full" ' . selected($s['default_display'], 'full', false) . '>Full</option><option value="compact" ' . selected($s['default_display'], 'compact', false) . '>Compact</option><option value="drawer" ' . selected($s['default_display'], 'drawer', false) . '>Drawer</option></select></td></tr>';
        echo '</tbody></table><p><button class="button button-primary" type="submit" name="scds_save_settings" value="1">Save Settings</button></p></form>'; $this->admin_wrap_end();
    }

    private function settings_row($key, $label, $value, $textarea=false) { echo '<tr><th><label for="' . esc_attr($key) . '">' . esc_html($label) . '</label></th><td>'; if ($textarea) echo '<textarea id="' . esc_attr($key) . '" name="scds_settings[' . esc_attr($key) . ']" rows="3" class="large-text">' . esc_textarea($value) . '</textarea>'; else echo '<input id="' . esc_attr($key) . '" type="text" name="scds_settings[' . esc_attr($key) . ']" value="' . esc_attr($value) . '" class="regular-text">'; echo '</td></tr>'; }

    public function maybe_save_settings() {
        if (!isset($_POST['scds_save_settings']) || !current_user_can('manage_options') || !check_admin_referer('scds_save_settings')) return;
        $incoming = isset($_POST['scds_settings']) && is_array($_POST['scds_settings']) ? wp_unslash($_POST['scds_settings']) : [];
        $settings = $this->settings();
        foreach (['brand_title','brand_subtitle','methodology_note','backend_url','backend_api_key','default_display'] as $key) if (isset($incoming[$key])) $settings[$key] = sanitize_text_field($incoming[$key]);
        $settings['backend_enabled'] = isset($incoming['backend_enabled']) ? '1' : '0';
        $settings['ai_briefing_enabled'] = isset($incoming['ai_briefing_enabled']) ? '1' : '0';
        $settings['workbench_integration'] = isset($incoming['workbench_integration']) ? '1' : '0';
        update_option(self::OPTION_KEY, $settings);
        add_action('admin_notices', function(){ echo '<div class="notice notice-success"><p>Decision Studio settings saved.</p></div>'; });
    }

    public function protect_public_rest_request($result, $server, $request) {
        if ($result !== null) return $result;
        $route = (string) $request->get_route();
        if (strpos($route, '/scds/v1/') !== 0 || strtoupper($request->get_method()) !== 'POST') return $result;
        if (current_user_can('manage_options')) return $result;

        $body = (string) $request->get_body();
        $content_length = (int) $request->get_header('content-length');
        if ($content_length > self::MAX_PUBLIC_REQUEST_BYTES || strlen($body) > self::MAX_PUBLIC_REQUEST_BYTES) {
            return new WP_Error('scds_request_too_large', 'Decision Studio request exceeds the public payload limit.', ['status'=>413, 'max_request_bytes'=>self::MAX_PUBLIC_REQUEST_BYTES]);
        }

        $forwarded = sanitize_text_field((string) $request->get_header('x-forwarded-for'));
        $ip = $forwarded ? trim(explode(',', $forwarded)[0]) : sanitize_text_field($_SERVER['REMOTE_ADDR'] ?? 'unknown');
        $window = (int) floor(time() / 60);
        $rate_key = 'scds_rl_' . md5($ip . '|' . $route . '|' . $window);
        $count = (int) get_transient($rate_key);
        if ($count >= self::PUBLIC_RATE_LIMIT) {
            return new WP_Error('scds_rate_limit', 'Too many Decision Studio requests. Please try again shortly.', ['status'=>429, 'retry_after'=>60]);
        }
        set_transient($rate_key, $count + 1, 70);
        return $result;
    }

    private function release_manifest() {
        return [
            'release'=>self::VERSION,
            'release_name'=>'Collaborative Decision Rooms',
            'release_date'=>self::RELEASE_DATE,
            'build_fingerprint'=>self::BUILD_FINGERPRINT,
            'source_commit'=>self::SOURCE_COMMIT,
            'database_version'=>self::DB_VERSION,
            'decision_packet_schema'=>'scds-decision-packet/1.4',
            'platform_artifact_schema'=>'scds-platform-artifact/1.0',
            'evidence_record_schema'=>'scds-evidence-record/1.0',
            'governance_schema'=>'scds-decision-governance/1.0',
            'review_event_schema'=>'scds-review-event/1.0',
            'scenario_studio_schema'=>'scds-scenario-studio/1.0',
            'collaboration_room_schema'=>self::COLLABORATION_ROOM_SCHEMA,
            'collaboration_event_schema'=>self::COLLABORATION_EVENT_SCHEMA,
            'compatibility'=>[
                'wordpress_plugin'=>self::VERSION,
                'backend'=>self::VERSION,
                'api_namespace'=>'scds/v1',
                'shortcodes_preserved'=>true,
                'packet_schema_breaking_changes'=>false,
                'typed_platform_artifacts'=>true,
                'legacy_artifact_adapters_preserved'=>true,
                'governance_center'=>true,
                'immutable_review_history'=>true,
                'advanced_scenario_studio'=>true,
                'one_way_sensitivity'=>true,
                'multi_variable_sensitivity'=>true,
                'threshold_break_even_analysis'=>true,
                'collaborative_decision_rooms'=>true,
                'wordpress_canonical_room_persistence'=>true,
                'private_room_sharing'=>true,
                'locked_approved_versions'=>true,
            ],
        ];
    }

    private function backend_diagnostics() {
        $s = $this->settings();
        $base = [
            'ok'=>true,
            'plugin_version'=>self::VERSION,
            'plugin_build'=>self::BUILD_FINGERPRINT,
            'database_version'=>(string) get_option(self::DB_VERSION_OPTION, 'not-recorded'),
            'installed_version'=>(string) get_option(self::INSTALLED_VERSION_OPTION, 'not-recorded'),
            'backend_enabled'=>$s['backend_enabled'] === '1',
            'backend_configured'=>!empty($s['backend_url']),
            'version_matches'=>null,
            'state'=>'backend-disabled',
            'release'=>$this->release_manifest(),
        ];
        if ($s['backend_enabled'] !== '1' || empty($s['backend_url'])) return $base;

        $health = $this->backend_request('/health', [], 'GET');
        if (is_wp_error($health)) {
            $base['ok'] = false;
            $base['state'] = 'backend-unavailable';
            $base['error'] = $health->get_error_message();
            return $base;
        }
        $backend_version = sanitize_text_field((string) ($health['version'] ?? 'unknown'));
        $matches = hash_equals(self::VERSION, $backend_version);
        $base['backend_health'] = $health;
        $base['backend_version'] = $backend_version;
        $base['backend_build'] = sanitize_text_field((string) ($health['build_fingerprint'] ?? 'unknown'));
        $base['version_matches'] = $matches;
        $base['state'] = $matches ? 'matched' : 'version-mismatch';
        $base['ok'] = $matches;

        $ai = $this->backend_request('/ai/status', [], 'GET');
        if (!is_wp_error($ai)) $base['ai'] = $ai;
        return $base;
    }

    public function register_rest_routes() {
        register_rest_route('scds/v1', '/health', ['methods'=>'GET','callback'=>[$this,'rest_health'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/release', ['methods'=>'GET','callback'=>[$this,'rest_release'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/analyze', ['methods'=>'POST','callback'=>[$this,'rest_analyze'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/templates', ['methods'=>'GET','callback'=>[$this,'rest_templates'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/public/landing-template', ['methods'=>'GET','callback'=>[$this,'rest_public_landing_template'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/public/demo-template', ['methods'=>'GET','callback'=>[$this,'rest_public_demo_template'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/integrations', ['methods'=>'GET','callback'=>[$this,'rest_integrations'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/integrations/adapters', ['methods'=>'GET','callback'=>[$this,'rest_adapters'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/integrations/platform', ['methods'=>'GET','callback'=>[$this,'rest_platform_integrations'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/integrations/contracts', ['methods'=>'GET','callback'=>[$this,'rest_handoff_contracts'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/integrations/validate', ['methods'=>'POST','callback'=>[$this,'rest_validate_typed_artifact'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/integrations/import-batch', ['methods'=>'POST','callback'=>[$this,'rest_import_artifact_batch'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/decision-packet/platform-handoffs', ['methods'=>'GET','callback'=>[$this,'rest_platform_handoff_template'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/integrations/import', ['methods'=>'POST','callback'=>[$this,'rest_import_artifact'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/decision-packet/import', ['methods'=>'POST','callback'=>[$this,'rest_import_artifact'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/decision-packet/template', ['methods'=>'GET','callback'=>[$this,'rest_decision_packet_template'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/governance/states', ['methods'=>'GET','callback'=>[$this,'rest_governance_states'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/governance/template', ['methods'=>'GET','callback'=>[$this,'rest_governance_template'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/governance/evaluate', ['methods'=>'POST','callback'=>[$this,'rest_governance_evaluate'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/governance/transition', ['methods'=>'POST','callback'=>[$this,'rest_governance_evaluate'],'permission_callback'=>function(){ return current_user_can('edit_posts'); }]);
        register_rest_route('scds/v1', '/decision-packet/governance', ['methods'=>'POST','callback'=>[$this,'rest_governance_evaluate'],'permission_callback'=>function(){ return current_user_can('edit_posts'); }]);
        register_rest_route('scds/v1', '/governance/history/verify', ['methods'=>'POST','callback'=>[$this,'rest_governance_history_verify'],'permission_callback'=>function(){ return current_user_can('edit_posts'); }]);
        register_rest_route('scds/v1', '/collaboration/template', ['methods'=>'GET','callback'=>[$this,'rest_collaboration_template'],'permission_callback'=>function(){ return is_user_logged_in(); }]);
        register_rest_route('scds/v1', '/collaboration/action', ['methods'=>'POST','callback'=>[$this,'rest_collaboration_action'],'permission_callback'=>function(){ return current_user_can('edit_posts'); }]);
        register_rest_route('scds/v1', '/decision-packet/collaboration', ['methods'=>'POST','callback'=>[$this,'rest_collaboration_action'],'permission_callback'=>function(){ return current_user_can('edit_posts'); }]);
        register_rest_route('scds/v1', '/rooms', ['methods'=>'GET','callback'=>[$this,'rest_list_rooms'],'permission_callback'=>function(){ return is_user_logged_in(); }]);
        register_rest_route('scds/v1', '/rooms', ['methods'=>'POST','callback'=>[$this,'rest_save_room'],'permission_callback'=>function(){ return current_user_can('edit_posts'); }]);
        register_rest_route('scds/v1', '/rooms/(?P<id>\d+)', ['methods'=>'GET','callback'=>[$this,'rest_get_room'],'permission_callback'=>function(){ return is_user_logged_in(); }]);
        register_rest_route('scds/v1', '/rooms/(?P<id>\d+)/action', ['methods'=>'POST','callback'=>[$this,'rest_room_action'],'permission_callback'=>function(){ return current_user_can('edit_posts'); }]);
        register_rest_route('scds/v1', '/rooms/(?P<id>\d+)', ['methods'=>'DELETE','callback'=>[$this,'rest_delete_room'],'permission_callback'=>function(){ return current_user_can('delete_posts'); }]);
        register_rest_route('scds/v1', '/audit/template', ['methods'=>'GET','callback'=>[$this,'rest_audit_template'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/audit/generate', ['methods'=>'POST','callback'=>[$this,'rest_audit_generate'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/integrated-brief', ['methods'=>'POST','callback'=>[$this,'rest_integrated_brief'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/brief-readiness', ['methods'=>'POST','callback'=>[$this,'rest_brief_readiness'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/decision-packet/readiness', ['methods'=>'POST','callback'=>[$this,'rest_brief_readiness'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/review/status', ['methods'=>'POST','callback'=>[$this,'rest_brief_readiness'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/review/status-template', ['methods'=>'GET','callback'=>[$this,'rest_review_status_template'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/scenario-comparison/template', ['methods'=>'GET','callback'=>[$this,'rest_scenario_comparison_template'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/scenario-comparison', ['methods'=>'POST','callback'=>[$this,'rest_scenario_comparison'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/decision-packet/scenario-comparison', ['methods'=>'POST','callback'=>[$this,'rest_scenario_comparison'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/scenario-studio/template', ['methods'=>'GET','callback'=>[$this,'rest_scenario_studio_template'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/scenario-studio/analyze', ['methods'=>'POST','callback'=>[$this,'rest_scenario_studio_analyze'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/scenario-studio/sensitivity', ['methods'=>'POST','callback'=>[$this,'rest_scenario_studio_sensitivity'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/scenario-studio/threshold', ['methods'=>'POST','callback'=>[$this,'rest_scenario_studio_threshold'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/decision-packet/scenario-studio', ['methods'=>'POST','callback'=>[$this,'rest_scenario_studio_analyze'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/workbench/handoffs', ['methods'=>'GET','callback'=>[$this,'rest_workbench_handoffs'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/workbench/handoff', ['methods'=>'POST','callback'=>[$this,'rest_workbench_handoff'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/decision-packet/workbench-handoff', ['methods'=>'POST','callback'=>[$this,'rest_workbench_handoff'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/decision-packet/storage-template', ['methods'=>'GET','callback'=>[$this,'rest_packet_storage_template'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/decision-packet/save-template', ['methods'=>'POST','callback'=>[$this,'rest_packet_save_template'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/export-center/template', ['methods'=>'GET','callback'=>[$this,'rest_export_center_template'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/export-center/bundle', ['methods'=>'POST','callback'=>[$this,'rest_export_center_bundle'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/decision-packet/export-bundle', ['methods'=>'POST','callback'=>[$this,'rest_export_center_bundle'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/packets', ['methods'=>'GET','callback'=>[$this,'rest_list_packets'],'permission_callback'=>function(){ return current_user_can('edit_posts'); }]);
        register_rest_route('scds/v1', '/packets', ['methods'=>'POST','callback'=>[$this,'rest_save_decision_packet'],'permission_callback'=>function(){ return current_user_can('edit_posts'); }]);
        register_rest_route('scds/v1', '/packets/(?P<id>\d+)', ['methods'=>'GET','callback'=>[$this,'rest_get_packet'],'permission_callback'=>function(){ return current_user_can('edit_posts'); }]);
        register_rest_route('scds/v1', '/packets/(?P<id>\d+)', ['methods'=>'DELETE','callback'=>[$this,'rest_delete_packet'],'permission_callback'=>function(){ return current_user_can('delete_posts'); }]);
        register_rest_route('scds/v1', '/packets/(?P<id>\d+)/export', ['methods'=>'GET','callback'=>[$this,'rest_export_packet_json'],'permission_callback'=>function(){ return current_user_can('edit_posts'); }]);
        register_rest_route('scds/v1', '/decision-packet/brief', ['methods'=>'POST','callback'=>[$this,'rest_integrated_brief'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/backend-status', ['methods'=>'GET','callback'=>[$this,'rest_backend_status'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/ai-brief', ['methods'=>'POST','callback'=>[$this,'rest_ai_brief'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/projects', ['methods'=>'POST','callback'=>[$this,'rest_save_project'],'permission_callback'=>function(){ return current_user_can('edit_posts'); }]);
        register_rest_route('scds/v1', '/export/validation.csv', ['methods'=>'GET','callback'=>[$this,'rest_export_validation_csv'],'permission_callback'=>function(){ return current_user_can('manage_options'); }]);
        register_rest_route('scds/v1', '/export/templates.csv', ['methods'=>'GET','callback'=>[$this,'rest_export_templates_csv'],'permission_callback'=>function(){ return current_user_can('manage_options'); }]);
        register_rest_route('scds/v1', '/export/tool-map.csv', ['methods'=>'GET','callback'=>[$this,'rest_export_tool_map_csv'],'permission_callback'=>function(){ return current_user_can('manage_options'); }]);
    }



    public function rest_public_landing_template() { return rest_ensure_response(['ok'=>true,'version'=>self::VERSION,'landing'=>$this->public_landing_template()]); }
    public function rest_public_demo_template() { return rest_ensure_response(['ok'=>true,'version'=>self::VERSION,'demo'=>['demo_version'=>self::VERSION,'headline'=>'Decision Studio Demo','public_copy'=>'Use Knowledge Library to source. Use Research Librarian to route. Use Site Intelligence to observe. Use Workbench to model. Use Research Lab to validate. Use Platform Core to trace. Use Decision Studio to decide.','shortcodes'=>['[sc_decision_studio mode="demo"]','[sc_decision_studio mode="workflow"]','[sc_decision_studio mode="readiness"]','[sc_decision_studio mode="export"]']]]); }

    public function rest_adapters() {
        if ($this->settings()['backend_enabled'] === '1' && !empty($this->settings()['backend_url'])) {
            $backend = $this->backend_request('/integrations/adapters', [], 'GET');
            if (!is_wp_error($backend) && is_array($backend)) return rest_ensure_response($backend);
        }
        return rest_ensure_response(['ok'=>true,'version'=>self::VERSION,'adapters'=>$this->artifact_adapter_catalog()]);
    }

    public function rest_platform_integrations() {
        if ($this->settings()['backend_enabled']==='1'&&!empty($this->settings()['backend_url'])) { $backend=$this->backend_request('/integrations/platform',[],'GET'); if(!is_wp_error($backend))return rest_ensure_response($backend); }
        return rest_ensure_response(['ok'=>true,'version'=>self::VERSION,'schema'=>'scds-platform-artifact/1.0','products'=>$this->module_integrations(),'contracts'=>$this->platform_handoff_contracts(),'legacy_modules'=>['catalyst-canvas','catalyst-data','catalyst-analytics-r','global-impact-catalyst','catalyst-narrative-risk','catalyst-finance','catalyst-grit']]);
    }

    public function rest_handoff_contracts() {
        if ($this->settings()['backend_enabled']==='1'&&!empty($this->settings()['backend_url'])) { $backend=$this->backend_request('/integrations/contracts',[],'GET'); if(!is_wp_error($backend))return rest_ensure_response($backend); }
        return rest_ensure_response(['ok'=>true,'version'=>self::VERSION,'artifact_schema'=>'scds-platform-artifact/1.0','evidence_schema'=>'scds-evidence-record/1.0','contracts'=>$this->platform_handoff_contracts()]);
    }

    public function rest_validate_typed_artifact(WP_REST_Request $request) {
        $payload=$request->get_json_params(); if(!is_array($payload))$payload=[];
        if ($this->settings()['backend_enabled']==='1'&&!empty($this->settings()['backend_url'])) { $backend=$this->backend_request('/integrations/validate',$payload); if(!is_wp_error($backend))return rest_ensure_response($backend); }
        $result=$this->validate_typed_artifact_local(is_array($payload['artifact']??null)?$payload['artifact']:[],sanitize_text_field($payload['sourceProduct']??''),!empty($payload['strict']));
        return new WP_REST_Response($result,$result['ok']?200:422);
    }

    public function rest_import_artifact_batch(WP_REST_Request $request) {
        $payload=$request->get_json_params(); if(!is_array($payload))$payload=[];
        if ($this->settings()['backend_enabled']==='1'&&!empty($this->settings()['backend_url'])) { $backend=$this->backend_request('/integrations/import-batch',$payload); if(!is_wp_error($backend))return rest_ensure_response($backend); }
        $packet=is_array($payload['packet']??null)?$payload['packet']:$this->decision_packet_template();$imports=[];$rejected=[];
        foreach(array_slice($this->arr($payload['artifacts']??[]),0,100) as $index=>$artifact){if(!is_array($artifact)){$rejected[]=['index'=>$index,'errors'=>['Artifact must be an object.']];continue;}$validation=$this->validate_typed_artifact_local($artifact,'',!empty($payload['strict']));if(!empty($payload['strict'])&&!$validation['ok']){$rejected[]=['index'=>$index,'errors'=>$validation['errors']];continue;}$result=$this->import_artifact_into_packet($artifact,'',$packet);$packet=$result['decision_packet'];$imports[]=$result['import_result']['summary'];}
        return rest_ensure_response(['ok'=>empty($rejected)||empty($payload['strict']),'version'=>self::VERSION,'imported_count'=>count($imports),'rejected_count'=>count($rejected),'imports'=>$imports,'rejected'=>$rejected,'decision_packet'=>$packet]);
    }

    public function rest_platform_handoff_template() { return rest_ensure_response(['ok'=>true,'version'=>self::VERSION,'artifact_schema'=>'scds-platform-artifact/1.0','evidence_schema'=>'scds-evidence-record/1.0','contracts'=>$this->platform_handoff_contracts(),'decision_packet'=>$this->decision_packet_template()]); }

    public function rest_import_artifact(WP_REST_Request $request) {
        $payload = $request->get_json_params(); if (!is_array($payload)) $payload = [];
        $artifact = isset($payload['artifact']) && is_array($payload['artifact']) ? $payload['artifact'] : [];
        $module_id = sanitize_text_field($payload['moduleId'] ?? '');
        $packet = isset($payload['packet']) && is_array($payload['packet']) ? $payload['packet'] : $this->decision_packet_template();
        if ($this->settings()['backend_enabled'] === '1' && !empty($this->settings()['backend_url'])) {
            $backend = $this->backend_request('/integrations/import', ['artifact'=>$artifact,'moduleId'=>$module_id,'packet'=>$packet,'preserveRaw'=>true]);
            if (!is_wp_error($backend) && is_array($backend)) return rest_ensure_response($backend);
        }
        return rest_ensure_response($this->import_artifact_into_packet($artifact, $module_id, $packet));
    }

    public function rest_integrations() { return rest_ensure_response(['ok'=>true,'version'=>self::VERSION,'modules'=>$this->module_integrations(),'workflow'=>array_map(function($m){ return $m['phase']; }, $this->module_integrations())]); }
    public function rest_decision_packet_template() { return rest_ensure_response(['ok'=>true,'version'=>self::VERSION,'decision_packet'=>$this->decision_packet_template(),'modules'=>$this->module_integrations()]); }
    public function rest_audit_template() { return rest_ensure_response(['ok'=>true,'version'=>self::VERSION,'audit'=>$this->audit_provenance_template()]); }
    public function rest_audit_generate(WP_REST_Request $request) { $payload = $request->get_json_params(); if (!is_array($payload)) $payload = []; $inputs = isset($payload['inputs']) && is_array($payload['inputs']) ? $payload['inputs'] : []; $results = isset($payload['results']) && is_array($payload['results']) ? $payload['results'] : $this->analyze_inputs($inputs); return rest_ensure_response($this->generate_audit_provenance($inputs, $results, $payload)); }


    public function rest_review_status_template() { return rest_ensure_response(['ok'=>true,'version'=>self::VERSION,'review_status_catalog'=>$this->review_status_catalog(),'sections'=>$this->readiness_sections()]); }

    public function rest_brief_readiness(WP_REST_Request $request) {
        $payload = $request->get_json_params(); if (!is_array($payload)) $payload = [];
        $inputs = isset($payload['inputs']) && is_array($payload['inputs']) ? $payload['inputs'] : [];
        $results = isset($payload['results']) && is_array($payload['results']) ? $payload['results'] : $this->analyze_inputs($inputs);
        $packet = isset($payload['packet']) && is_array($payload['packet']) ? $payload['packet'] : [];
        $audit = isset($payload['audit']) && is_array($payload['audit']) ? $payload['audit'] : [];
        if ($this->settings()['backend_enabled']==='1') {
            $backend = $this->backend_request('/brief-readiness', ['inputs'=>$inputs,'results'=>$results,'packet'=>$packet,'audit'=>$audit,'moduleArtifacts'=>isset($payload['moduleArtifacts'])?$payload['moduleArtifacts']:[],'reviewOverrides'=>isset($payload['reviewOverrides'])?$payload['reviewOverrides']:[]]);
            if (!is_wp_error($backend)) return rest_ensure_response($backend);
        }
        return rest_ensure_response($this->generate_brief_readiness($inputs, $results, $packet, $audit));
    }

    public function rest_integrated_brief(WP_REST_Request $request) {
        $payload = $request->get_json_params(); if (!is_array($payload)) $payload = [];
        $inputs = isset($payload['inputs']) && is_array($payload['inputs']) ? $payload['inputs'] : [];
        $results = isset($payload['results']) && is_array($payload['results']) ? $payload['results'] : $this->analyze_inputs($inputs);
        $packet = isset($payload['packet']) && is_array($payload['packet']) ? $payload['packet'] : $this->decision_packet_template();
        $audit = isset($payload['audit']) && is_array($payload['audit']) ? $payload['audit'] : [];
        if ($this->settings()['backend_enabled'] === '1' && !empty($this->settings()['backend_url'])) {
            $backend = $this->backend_request('/integrated-brief', ['inputs'=>$inputs,'results'=>$results,'packet'=>$packet,'audit'=>$audit,'moduleArtifacts'=>isset($payload['moduleArtifacts'])?$payload['moduleArtifacts']:[],'includeAI'=>false]);
            if (!is_wp_error($backend) && is_array($backend)) return rest_ensure_response($backend);
        }
        return rest_ensure_response($this->generate_integrated_brief($inputs, $results, $packet, $audit));
    }

    public function rest_scenario_comparison_template() { return rest_ensure_response(['ok'=>true,'version'=>self::VERSION,'template'=>$this->scenario_comparison_template()]); }

    public function rest_scenario_comparison(WP_REST_Request $request) {
        $payload = $request->get_json_params(); if (!is_array($payload)) $payload = [];
        $inputs = isset($payload['inputs']) && is_array($payload['inputs']) ? $payload['inputs'] : [];
        $results = isset($payload['results']) && is_array($payload['results']) ? $payload['results'] : $this->analyze_inputs($inputs);
        $packet = isset($payload['packet']) && is_array($payload['packet']) ? $payload['packet'] : [];
        $scenarios = isset($payload['scenarios']) && is_array($payload['scenarios']) ? $payload['scenarios'] : [];
        if ($this->settings()['backend_enabled'] === '1' && !empty($this->settings()['backend_url'])) {
            $backend = $this->backend_request('/scenario-comparison', ['inputs'=>$inputs,'results'=>$results,'packet'=>$packet,'scenarios'=>$scenarios]);
            if (!is_wp_error($backend) && is_array($backend)) return rest_ensure_response($backend);
        }
        return rest_ensure_response($this->generate_scenario_comparison($inputs, $results, $packet, $scenarios));
    }

    public function rest_scenario_studio_template() { return rest_ensure_response(['ok'=>true,'version'=>self::VERSION,'template'=>$this->scenario_studio_template()]); }

    private function rest_scenario_studio_proxy(WP_REST_Request $request, $backend_path, $mode) {
        $payload = $request->get_json_params(); if(!is_array($payload)) $payload=[];
        if ($this->settings()['backend_enabled']==='1' && !empty($this->settings()['backend_url'])) {
            $backend=$this->backend_request($backend_path,$payload);
            if(!is_wp_error($backend)&&is_array($backend)) return rest_ensure_response($backend);
        }
        $inputs=isset($payload['inputs'])&&is_array($payload['inputs'])?$payload['inputs']:[];
        return rest_ensure_response($this->generate_scenario_studio($inputs,$payload,$mode));
    }
    public function rest_scenario_studio_analyze(WP_REST_Request $request) { return $this->rest_scenario_studio_proxy($request,'/scenario-studio/analyze','full'); }
    public function rest_scenario_studio_sensitivity(WP_REST_Request $request) { return $this->rest_scenario_studio_proxy($request,'/scenario-studio/sensitivity','sensitivity'); }
    public function rest_scenario_studio_threshold(WP_REST_Request $request) { return $this->rest_scenario_studio_proxy($request,'/scenario-studio/threshold','threshold'); }

    public function rest_workbench_handoffs() { return rest_ensure_response(['ok'=>true,'version'=>self::VERSION,'catalog'=>$this->workbench_handoff_catalog()]); }

    public function rest_workbench_handoff(WP_REST_Request $request) {
        $payload = $request->get_json_params(); if (!is_array($payload)) $payload = [];
        $inputs = isset($payload['inputs']) && is_array($payload['inputs']) ? $payload['inputs'] : [];
        $results = isset($payload['results']) && is_array($payload['results']) ? $payload['results'] : $this->analyze_inputs($inputs);
        $packet = isset($payload['packet']) && is_array($payload['packet']) ? $payload['packet'] : [];
        $comparison = isset($payload['scenarioComparison']) && is_array($payload['scenarioComparison']) ? $payload['scenarioComparison'] : [];
        $readiness = isset($payload['readiness']) && is_array($payload['readiness']) ? $payload['readiness'] : [];
        if ($this->settings()['backend_enabled'] === '1' && !empty($this->settings()['backend_url'])) {
            $backend = $this->backend_request('/workbench/handoff', ['inputs'=>$inputs,'results'=>$results,'packet'=>$packet,'scenarioComparison'=>$comparison,'readiness'=>$readiness,'requestedTools'=>isset($payload['requestedTools'])?$payload['requestedTools']:[]]);
            if (!is_wp_error($backend) && is_array($backend)) return rest_ensure_response($backend);
        }
        return rest_ensure_response($this->generate_workbench_handoff($inputs, $results, $packet, $comparison, $readiness));
    }



    public function rest_packet_storage_template() { return rest_ensure_response(['ok'=>true,'version'=>self::VERSION,'storage_template'=>$this->export_center_template(),'decision_packet'=>$this->decision_packet_template()]); }
    public function rest_export_center_template() { return rest_ensure_response(['ok'=>true,'version'=>self::VERSION,'export_center'=>$this->export_center_template()]); }

    public function rest_packet_save_template(WP_REST_Request $request) {
        $payload = $request->get_json_params(); if(!is_array($payload)) $payload=[];
        $inputs = isset($payload['inputs']) && is_array($payload['inputs']) ? $payload['inputs'] : [];
        $results = isset($payload['results']) && is_array($payload['results']) ? $payload['results'] : $this->analyze_inputs($inputs);
        $packet = isset($payload['packet']) && is_array($payload['packet']) ? $payload['packet'] : $this->decision_packet_template();
        $audit = isset($payload['audit']) && is_array($payload['audit']) ? $payload['audit'] : $this->generate_audit_provenance($inputs,$results,['packet'=>$packet])['audit'];
        $readiness = isset($payload['readiness']) && is_array($payload['readiness']) ? $payload['readiness'] : $this->generate_brief_readiness($inputs,$results,$packet,$audit)['readiness'];
        $scenario = isset($payload['scenarioComparison']) && is_array($payload['scenarioComparison']) ? $payload['scenarioComparison'] : $this->generate_scenario_comparison($inputs,$results,$packet,[])['scenario_comparison'];
        $scenario_studio = isset($payload['scenarioStudio']) && is_array($payload['scenarioStudio']) ? $payload['scenarioStudio'] : ($packet['scenario_studio'] ?? $this->generate_scenario_studio($inputs,['packet'=>$packet],'full')['scenario_studio']); $packet['scenario_studio']=$scenario_studio;
        $handoff = isset($payload['workbenchHandoff']) && is_array($payload['workbenchHandoff']) ? $payload['workbenchHandoff'] : $this->generate_workbench_handoff($inputs,$results,$packet,$scenario,$readiness)['workbench_handoff'];
        $briefData = isset($payload['integratedBrief']) && is_array($payload['integratedBrief']) ? $payload['integratedBrief'] : $this->generate_integrated_brief($inputs,$results,$packet,$audit);
        $brief = isset($briefData['brief']) ? $briefData['brief'] : $briefData;
        $title = sanitize_text_field($payload['title'] ?? ($packet['project']['project_name'] ?? ($inputs['projectName'] ?? 'Decision Packet')));
        $collaboration=isset($payload['collaboration'])&&is_array($payload['collaboration'])?$payload['collaboration']:($packet['collaboration_room']??$this->collaboration_room_template()); $packet['collaboration_room']=$collaboration; $governance=$packet['governance_center'] ?? $this->governance_template(); $requested_status=sanitize_key($payload['status'] ?? 'draft'); $governance_status=sanitize_key($governance['current_state'] ?? $requested_status); $saved_status=($requested_status==='draft'&&$governance_status!=='draft')?$governance_status:$requested_status;
        $saved = ['packet_version'=>self::VERSION,'decision_packet_id'=>$packet['decision_packet_id'] ?? ('SCDS-' . strtoupper(substr(preg_replace('/[^A-Za-z0-9]/','',$title),0,10)) . '-DRAFT'),'title'=>$title,'project_name'=>$title,'decision_question'=>$packet['project']['decision_question'] ?? ($inputs['decisionQuestion'] ?? ''),'status'=>$saved_status,'inputs'=>$inputs,'results'=>$results,'decision_packet'=>$packet,'audit'=>$audit,'readiness'=>$readiness,'scenario_comparison'=>$scenario,'scenario_studio'=>$scenario_studio,'workbench_handoff'=>$handoff,'integrated_brief'=>$brief,'governance'=>$packet['governance_center'] ?? $this->governance_template(),'collaboration'=>$collaboration,'notes'=>sanitize_textarea_field($payload['notes'] ?? ''),'warnings'=>['Saved packet is a working record, not approval or professional signoff.']];
        return rest_ensure_response(['ok'=>true,'version'=>self::VERSION,'saved_packet'=>$saved,'export_center'=>$this->export_center_template()]);
    }

    public function rest_export_center_bundle(WP_REST_Request $request) {
        $payload = $request->get_json_params(); if(!is_array($payload)) $payload=[];
        $inputs = isset($payload['inputs']) && is_array($payload['inputs']) ? $payload['inputs'] : [];
        $results = isset($payload['results']) && is_array($payload['results']) ? $payload['results'] : $this->analyze_inputs($inputs);
        $packet = isset($payload['packet']) && is_array($payload['packet']) ? $payload['packet'] : $this->decision_packet_template();
        $audit = isset($payload['audit']) && is_array($payload['audit']) ? $payload['audit'] : $this->generate_audit_provenance($inputs,$results,['packet'=>$packet])['audit'];
        $readiness = isset($payload['readiness']) && is_array($payload['readiness']) ? $payload['readiness'] : $this->generate_brief_readiness($inputs,$results,$packet,$audit)['readiness'];
        $scenario = isset($payload['scenarioComparison']) && is_array($payload['scenarioComparison']) ? $payload['scenarioComparison'] : $this->generate_scenario_comparison($inputs,$results,$packet,[])['scenario_comparison'];
        $scenario_studio = isset($payload['scenarioStudio']) && is_array($payload['scenarioStudio']) ? $payload['scenarioStudio'] : ($packet['scenario_studio'] ?? $this->generate_scenario_studio($inputs,['packet'=>$packet],'full')['scenario_studio']); $packet['scenario_studio']=$scenario_studio;
        $handoff = isset($payload['workbenchHandoff']) && is_array($payload['workbenchHandoff']) ? $payload['workbenchHandoff'] : $this->generate_workbench_handoff($inputs,$results,$packet,$scenario,$readiness)['workbench_handoff'];
        $briefData = isset($payload['integratedBrief']) && is_array($payload['integratedBrief']) ? $payload['integratedBrief'] : $this->generate_integrated_brief($inputs,$results,$packet,$audit);
        $brief = isset($briefData['brief']) ? $briefData['brief'] : $briefData;
        $governance = isset($payload['governance']) && is_array($payload['governance']) ? $payload['governance'] : ($packet['governance_center'] ?? $this->governance_template()); $packet['governance_center']=$governance; $collaboration=isset($payload['collaboration'])&&is_array($payload['collaboration'])?$payload['collaboration']:($packet['collaboration_room']??$this->collaboration_room_template()); $packet['collaboration_room']=$collaboration;
        $audience = sanitize_key($payload['exportAudience'] ?? 'internal'); $gate = is_array($governance['export_gate'] ?? null) ? $governance['export_gate'] : []; if($audience==='reviewed' && empty($gate['reviewed_export_allowed'])) return new WP_Error('scds_governance_export_blocked','Reviewed export is blocked by the current decision-governance state.',['status'=>409,'export_audience'=>$audience,'governance_export_gate'=>$gate]); if($audience==='public' && empty($gate['public_export_allowed'])) return new WP_Error('scds_governance_export_blocked','Public export is blocked by the current decision-governance state.',['status'=>409,'export_audience'=>$audience,'governance_export_gate'=>$gate]);
        $bundle = ['bundle_version'=>self::VERSION,'label'=>sanitize_text_field($payload['exportLabel'] ?? 'Decision Studio Export Bundle'),'export_audience'=>$audience,'release_classification'=>($audience==='internal'&&empty($gate['reviewed_export_allowed']))?'internal_draft':$audience,'decision_packet_id'=>$packet['decision_packet_id'] ?? ($audit['decision_packet_id'] ?? 'SCDS-DRAFT'),'project_name'=>$packet['project']['project_name'] ?? ($inputs['projectName'] ?? 'Decision project'),'decision_question'=>$packet['project']['decision_question'] ?? ($inputs['decisionQuestion'] ?? ''),'exports'=>['decision_packet_json'=>$packet,'inputs_json'=>$inputs,'results_json'=>$results,'integrated_brief_json'=>$brief,'integrated_brief_markdown'=>$this->integrated_brief_markdown($brief),'integrated_brief_html'=>$this->integrated_brief_html($brief),'audit_json'=>$audit,'readiness_json'=>$readiness,'scenario_comparison_json'=>$scenario,'scenario_studio_json'=>$scenario_studio,'workbench_handoff_json'=>$handoff,'governance_json'=>$governance,'collaboration_json'=>$collaboration,'room_activity_json'=>$collaboration['activity_timeline']??[],'snapshot_comparison_json'=>$collaboration['snapshot_comparisons']??[]],'export_manifest'=>$this->export_center_template()['exports'],'warnings'=>$this->export_center_template()['warnings'],'governance_export_gate'=>$governance['export_gate'] ?? []];
        return rest_ensure_response(['ok'=>true,'version'=>self::VERSION,'export_bundle'=>$bundle,'export_center'=>$this->export_center_template()]);
    }

    public function rest_save_decision_packet(WP_REST_Request $request) {
        global $wpdb; $payload = $request->get_json_params(); if(!is_array($payload)) $payload=[];
        $saved = $this->rest_packet_save_template($request)->get_data()['saved_packet'];
        $table=$wpdb->prefix.self::PROJECTS_TABLE;
        $wpdb->insert($table,['project_name'=>$saved['project_name'],'sector'=>$saved['inputs']['sector'] ?? '','location'=>$saved['inputs']['location'] ?? '','decision_question'=>$saved['decision_question'],'status'=>$saved['status'],'inputs_json'=>wp_json_encode($saved['inputs']),'results_json'=>wp_json_encode($saved['results']),'packet_json'=>wp_json_encode($saved['decision_packet']),'audit_json'=>wp_json_encode($saved['audit']),'readiness_json'=>wp_json_encode($saved['readiness']),'scenario_comparison_json'=>wp_json_encode($saved['scenario_comparison']),'scenario_studio_json'=>wp_json_encode($saved['scenario_studio']??[]),'workbench_handoff_json'=>wp_json_encode($saved['workbench_handoff']),'integrated_brief_json'=>wp_json_encode($saved['integrated_brief']),'governance_json'=>wp_json_encode($saved['governance'] ?? []),'collaboration_json'=>wp_json_encode($saved['collaboration'] ?? ($saved['decision_packet']['collaboration_room'] ?? [])),'export_bundle_json'=>'','updated_at'=>current_time('mysql')]);
        return rest_ensure_response(['ok'=>true,'version'=>self::VERSION,'id'=>$wpdb->insert_id,'saved_packet'=>$saved]);
    }
    public function rest_list_packets() { global $wpdb; $table=$wpdb->prefix.self::PROJECTS_TABLE; $rows=$wpdb->get_results("SELECT id,project_name,sector,location,decision_question,status,created_at,updated_at FROM $table ORDER BY id DESC LIMIT 100", ARRAY_A); return rest_ensure_response(['ok'=>true,'version'=>self::VERSION,'packets'=>$rows ?: []]); }
    public function rest_get_packet(WP_REST_Request $request) { global $wpdb; $id=intval($request['id']); $table=$wpdb->prefix.self::PROJECTS_TABLE; $row=$wpdb->get_row($wpdb->prepare("SELECT * FROM $table WHERE id=%d",$id), ARRAY_A); if(!$row) return new WP_Error('not_found','Packet not found',['status'=>404]); foreach(['inputs_json','results_json','packet_json','audit_json','readiness_json','scenario_comparison_json','scenario_studio_json','workbench_handoff_json','integrated_brief_json','governance_json','collaboration_json','export_bundle_json'] as $k){ if(isset($row[$k])) $row[$k]=json_decode($row[$k], true); } return rest_ensure_response(['ok'=>true,'version'=>self::VERSION,'packet'=>$row]); }
    public function rest_delete_packet(WP_REST_Request $request) { global $wpdb; $id=intval($request['id']); $table=$wpdb->prefix.self::PROJECTS_TABLE; $wpdb->delete($table,['id'=>$id],['%d']); return rest_ensure_response(['ok'=>true,'version'=>self::VERSION,'deleted_id'=>$id]); }
    public function rest_export_packet_json(WP_REST_Request $request) { $res=$this->rest_get_packet($request); if(is_wp_error($res)) return $res; $data=$res->get_data(); return new WP_REST_Response(wp_json_encode($data, JSON_PRETTY_PRINT), 200, ['Content-Type'=>'application/json; charset=utf-8','Content-Disposition'=>'attachment; filename="decision-studio-packet-'.$request['id'].'-v'.self::VERSION.'.json"']); }

    public function rest_health() { return rest_ensure_response(['ok'=>true,'ready'=>true,'version'=>self::VERSION,'plugin'=>'sustainable-catalyst-decision-studio','build_fingerprint'=>self::BUILD_FINGERPRINT,'database_version'=>(string)get_option(self::DB_VERSION_OPTION,'not-recorded'),'installed_version'=>(string)get_option(self::INSTALLED_VERSION_OPTION,'not-recorded'),'limits'=>['max_request_bytes'=>self::MAX_PUBLIC_REQUEST_BYTES,'public_rate_limit'=>self::PUBLIC_RATE_LIMIT],'governance_schema'=>'scds-decision-governance/1.0','review_event_schema'=>'scds-review-event/1.0','scenario_studio_schema'=>'scds-scenario-studio/1.0','collaboration_room_schema'=>self::COLLABORATION_ROOM_SCHEMA,'collaboration_event_schema'=>self::COLLABORATION_EVENT_SCHEMA,'release'=>$this->release_manifest()]); }
    public function rest_release() { return rest_ensure_response(['ok'=>true,'version'=>self::VERSION,'release'=>$this->release_manifest()]); }
    public function rest_templates() { return rest_ensure_response(['scenario_templates'=>$this->scenario_templates(),'scenario_studio'=>$this->scenario_studio_template(),'scorecard'=>$this->scorecard_rows(),'workbench_tools'=>$this->workbench_tool_map()]); }
    public function rest_analyze(WP_REST_Request $request) { $inputs = $request->get_json_params(); if (!is_array($inputs)) $inputs = []; return rest_ensure_response(['ok'=>true,'source'=>'wordpress_deterministic_fallback','inputs'=>$inputs,'results'=>$this->analyze_inputs($inputs),'warnings'=>[$this->settings()['methodology_note']]]); }

    public function rest_backend_status() {
        return rest_ensure_response($this->backend_diagnostics());
    }

    public function rest_ai_brief(WP_REST_Request $request) {
        $payload = $request->get_json_params(); if (!is_array($payload)) $payload = [];
        $inputs = isset($payload['inputs']) && is_array($payload['inputs']) ? $payload['inputs'] : [];
        $results = isset($payload['results']) && is_array($payload['results']) ? $payload['results'] : $this->analyze_inputs($inputs);
        $s = $this->settings();
        if ($s['ai_briefing_enabled'] === '1' && $s['backend_enabled'] === '1' && !empty($s['backend_url'])) {
            $backend = $this->backend_request('/brief', ['inputs'=>$inputs, 'results'=>$results, 'useAI'=>true, 'audience'=>'Sustainable Catalyst decision reviewer']);
            if (!is_wp_error($backend) && is_array($backend)) {
                $backend['source_proxy'] = 'wordpress_to_backend';
                return rest_ensure_response($backend);
            }
        }
        return rest_ensure_response(['ok'=>true,'version'=>self::VERSION,'source'=>'wordpress_deterministic_ai_brief_fallback','brief'=>$this->deterministic_ai_brief($inputs,$results),'results'=>$results]);
    }

    private function backend_request($path, $payload=[], $method='POST') {
        $s = $this->settings();
        $url = rtrim($s['backend_url'], '/') . $path;
        $args = ['timeout'=>25, 'headers'=>['Content-Type'=>'application/json']];
        if (!empty($s['backend_api_key'])) $args['headers']['X-SCDS-API-Key'] = $s['backend_api_key'];
        if ($method === 'GET') {
            $response = wp_remote_get($url, $args);
        } else {
            $args['body'] = wp_json_encode($payload);
            $response = wp_remote_post($url, $args);
        }
        if (is_wp_error($response)) return $response;
        $code = wp_remote_retrieve_response_code($response);
        $body = json_decode(wp_remote_retrieve_body($response), true);
        if ($code < 200 || $code >= 300 || !is_array($body)) return new WP_Error('scds_backend_error', 'Backend request failed or returned invalid JSON.');
        return $body;
    }

    private function deterministic_ai_brief($inputs, $results) {
        $scores = isset($results['scores']) && is_array($results['scores']) ? $results['scores'] : [];
        $risk = isset($results['risk']) && is_array($results['risk']) ? $results['risk'] : [];
        $finance = isset($results['finance']) && is_array($results['finance']) ? $results['finance'] : [];
        $emissions = isset($results['emissions']) && is_array($results['emissions']) ? $results['emissions'] : [];
        $name = sanitize_text_field($inputs['projectName'] ?? 'This decision');
        $weighted = floatval($scores['weighted'] ?? 0);
        $risk_score = floatval($risk['risk_score'] ?? 0);
        $status = sanitize_text_field($results['status'] ?? 'Decision requires review');
        return [
            'ai_used'=>false,
            'source'=>'wordpress_deterministic_fallback',
            'executive_summary'=>$name . ' is assessed as: ' . $status . '. Weighted score: ' . round($weighted,1) . '/100. Risk score: ' . round($risk_score,1) . '/100.',
            'assumption_critique'=>['Verify baseline, adoption, cost, savings, time horizon, discount rate, and data confidence.', 'Clarify whether environmental, social, economic, and governance indicators are measured or estimated.', 'Document assumptions so the brief can be audited later.'],
            'risk_interpretation'=>'Risk should be read as a screen combining exposure, vulnerability, stakeholder sensitivity, resilience, governance readiness, and data confidence.',
            'scenario_interpretation'=>'Scenario results should be interpreted as sensitivity comparisons rather than forecasts.',
            'stakeholder_impact_summary'=>'Review affected workers, customers, communities, suppliers, public institutions, and long-term users before implementation.',
            'governance_readiness'=>'Confirm accountability, monitoring, data ownership, escalation paths, and post-implementation review.',
            'recommendation_caveats'=>['Educational decision support only.', 'Not legal, financial, engineering, medical, tax, compliance, ESG/SDG assurance, or investment advice.', 'AI-generated text must remain subordinate to human review and professional judgment.'],
            'metrics_snapshot'=>['weighted_score'=>$weighted,'risk_score'=>$risk_score,'npv'=>$finance['npv'] ?? null,'annual_avoided_tco2e'=>$emissions['annual_avoided_tco2e'] ?? null],
            'workbench_handoffs'=>$this->recommended_workbench_shortcodes(),
        ];
    }

    public function rest_save_project(WP_REST_Request $request) {
        global $wpdb; $payload = $request->get_json_params(); if (!is_array($payload)) $payload = [];
        $inputs = isset($payload['inputs']) && is_array($payload['inputs']) ? $payload['inputs'] : [];
        $results = isset($payload['results']) && is_array($payload['results']) ? $payload['results'] : [];
        $table = $wpdb->prefix . self::PROJECTS_TABLE;
        $wpdb->insert($table, ['project_name'=>sanitize_text_field($inputs['projectName'] ?? 'Untitled decision'), 'sector'=>sanitize_text_field($inputs['sector'] ?? ''), 'location'=>sanitize_text_field($inputs['location'] ?? ''), 'decision_question'=>sanitize_textarea_field($inputs['decisionQuestion'] ?? ''), 'status'=>'draft', 'inputs_json'=>wp_json_encode($inputs), 'results_json'=>wp_json_encode($results), 'created_at'=>current_time('mysql'), 'updated_at'=>current_time('mysql')]);
        return rest_ensure_response(['ok'=>true,'id'=>$wpdb->insert_id]);
    }

    private function analyze_inputs($i) {
        $n = function($key,$fallback) use ($i) { return isset($i[$key]) && is_numeric($i[$key]) ? floatval($i[$key]) : $fallback; };
        $baseline = $n('baselineEmissions',1200); $reduction = $n('reductionRate',32); $adoption = $n('adoptionRate',65); $capex = $n('capex',950000); $savings = $n('annualSavings',185000); $discount = $n('discountRate',7)/100; $years = max(1, intval($n('modelYears',5)));
        $npv = -$capex; for ($t=1;$t<=$years;$t++) $npv += $savings / pow(1+$discount,$t);
        $annual_avoided = $baseline * ($reduction/100) * ($adoption/100); $total_avoided = $annual_avoided * $years; $payback = $savings > 0 ? $capex/$savings : 999; $roi = $capex > 0 ? (($savings*$years - $capex)/$capex)*100 : 0;
        $complexity = sanitize_text_field($i['complexity'] ?? 'Medium'); $penalty = ['Low'=>2,'Medium'=>8,'High'=>15,'Very high'=>24][$complexity] ?? 8;
        $env = max(0,min(100,30 + $reduction*.45 + $adoption*.22 - $penalty*.35));
        $social = max(0,min(100,56 + $n('socialBenefit',58)*.18 + $adoption*.08 - $penalty*.42));
        $econ = max(0,min(100,48 + ($npv/max($capex,1))*34 + min(20,$roi/6) - $penalty*.48));
        $gov = max(0,min(100,45 + $n('governanceReadiness',68)*.45 + $n('dataConfidence',70)*.12 - $penalty*.3));
        $wt = max(1,$n('weightEnv',30)+$n('weightSocial',20)+$n('weightEconomic',30)+$n('weightGovernance',20));
        $weighted = ($env*$n('weightEnv',30)+$social*$n('weightSocial',20)+$econ*$n('weightEconomic',30)+$gov*$n('weightGovernance',20))/$wt;
        $risk = max(0,min(100,(($n('exposure',55)*.35)+($n('vulnerability',48)*.35)+($n('stakeholderSensitivity',45)*.2)-($n('resilience',62)*.18)-($n('governanceReadiness',68)*.08)+20)));
        $status = $weighted >= 75 && $risk < 55 ? 'Strong candidate with review' : ($weighted >= 60 ? 'Promising but needs mitigation' : 'Needs redesign or stronger evidence');
        return ['scores'=>['environmental'=>$env,'social'=>$social,'economic'=>$econ,'governance'=>$gov,'weighted'=>$weighted],'finance'=>['npv'=>$npv,'payback_years'=>$payback,'roi_percent'=>$roi],'emissions'=>['annual_avoided_tco2e'=>$annual_avoided,'total_avoided_tco2e'=>$total_avoided],'risk'=>['risk_score'=>$risk,'risk_level'=>$risk>=70?'High':($risk>=45?'Medium':'Low')],'status'=>$status,'scenarios'=>$this->scenario_outputs($baseline,$reduction,$adoption,$capex,$savings,$discount,$years),'workbench_shortcodes'=>$this->recommended_workbench_shortcodes()];
    }

    private function scenario_outputs($baseline,$reduction,$adoption,$capex,$savings,$discount,$years) {
        $defs = [['Baseline',0,0,0,0],['Conservative',.75,.75,1.15,.8],['Expected',1,1,1,1],['Ambitious',1.15,1.25,1.05,1.1]]; $out=[];
        foreach($defs as $d){ $npv=-$capex*$d[3]; for($t=1;$t<=$years;$t++) $npv += ($savings*$d[4])/pow(1+$discount,$t); $out[]=['label'=>$d[0],'annual_avoided_tco2e'=>$baseline*($reduction*$d[1]/100)*min(100,$adoption*$d[2])/100,'npv'=>$npv,'payback_years'=>($savings*$d[4])>0?($capex*$d[3])/($savings*$d[4]):999]; } return $out;
    }

    private function recommended_workbench_shortcodes() { return ['[sc_workbench mode="tool" display="compact" tool="risk-resilience-impact-matrix"]','[sc_workbench mode="tool" display="compact" tool="economics-forecasting-and-scenario-tool"]','[sc_workbench mode="tool" display="drawer" tool="environmental-monitoring-qaqc-tool"]']; }

    private function scenario_comparison_template() {
        return ['comparison_version'=>self::VERSION,'default_options'=>['Baseline','Conservative','Expected','Ambitious','Stress test'],'metrics'=>['annual_avoided_tco2e','total_avoided_tco2e','npv','payback_years','risk_score','confidence','implementation_complexity'],'warnings'=>['Scenario comparison is a decision-support screen, not a forecast.','Use reviewed sources and Workbench calculations before relying on outputs.']];
    }

    private function packet_scenarios($packet) {
        $out = [];
        if (isset($packet['scenarios']) && is_array($packet['scenarios'])) {
            if (isset($packet['scenarios']['records']) && is_array($packet['scenarios']['records'])) $out = array_merge($out, $packet['scenarios']['records']);
            elseif (array_keys($packet['scenarios']) === range(0, count($packet['scenarios'])-1)) $out = array_merge($out, $packet['scenarios']);
        }
        if (isset($packet['scenario_analysis']) && is_array($packet['scenario_analysis'])) {
            if (array_keys($packet['scenario_analysis']) === range(0, count($packet['scenario_analysis'])-1)) $out = array_merge($out, $packet['scenario_analysis']); else $out[] = $packet['scenario_analysis'];
        }
        return array_values(array_filter($out, 'is_array'));
    }

    private function generate_scenario_comparison($inputs, $results, $packet=[], $scenarios=[]) {
        if (!$scenarios) $scenarios = $this->packet_scenarios($packet);
        if (!$scenarios) $scenarios = isset($results['scenarios']) && is_array($results['scenarios']) ? $results['scenarios'] : [];
        $baseline_emissions = max(1, floatval($inputs['baselineEmissions'] ?? 1200));
        $years = max(1, intval($inputs['modelYears'] ?? 5));
        $capex = max(1, floatval($inputs['capex'] ?? 950000));
        $risk_default = floatval($results['risk']['risk_score'] ?? 50);
        $matrix = [];
        foreach ($scenarios as $idx=>$item) {
            if (!is_array($item)) continue;
            $label = sanitize_text_field($item['label'] ?? $item['name'] ?? $item['scenario'] ?? $item['demo'] ?? ('Option '.($idx+1)));
            $annual = floatval($item['annual_avoided_tco2e'] ?? $item['annual_avoided'] ?? $item['emissions_reduction'] ?? 0);
            $total = isset($item['total_avoided_tco2e']) ? floatval($item['total_avoided_tco2e']) : $annual*$years;
            $npv = isset($item['npv']) ? floatval($item['npv']) : null;
            $payback = isset($item['payback_years']) ? floatval($item['payback_years']) : (isset($item['payback']) ? floatval($item['payback']) : null);
            $risk = isset($item['risk_score']) ? floatval($item['risk_score']) : $risk_default;
            $confidence = floatval($item['confidence'] ?? $item['data_confidence'] ?? ($inputs['dataConfidence'] ?? 70));
            $npv_component = $npv === null ? 50 : max(0,min(100,50 + ($npv/$capex)*35));
            $emissions_component = max(0,min(100,($annual/$baseline_emissions)*100));
            $payback_component = $payback === null ? 50 : max(0,min(100,100 - ($payback/$years)*55));
            $score = max(0,min(100,($emissions_component*.26)+($npv_component*.26)+($payback_component*.16)+((100-$risk)*.20)+($confidence*.12)));
            $matrix[] = ['option_id'=>'scenario-'.($idx+1),'label'=>$label,'annual_avoided_tco2e'=>$annual,'total_avoided_tco2e'=>$total,'npv'=>$npv,'payback_years'=>$payback,'risk_score'=>$risk,'confidence'=>$confidence,'decision_score'=>round($score,2),'implementation_complexity'=>sanitize_text_field($item['implementation_complexity'] ?? $item['complexity'] ?? ($inputs['complexity'] ?? 'Medium')),'interpretation'=>sanitize_text_field($item['interpretation'] ?? $item['decision_note'] ?? $item['summary'] ?? 'Scenario generated from Decision Studio assumptions or imported artifact.')];
        }
        $baseline = $matrix ? $matrix[0] : [];
        foreach ($matrix as $i=>$row) {
            $matrix[$i]['delta_vs_baseline'] = ['annual_avoided_tco2e'=>round(($row['annual_avoided_tco2e']??0)-($baseline['annual_avoided_tco2e']??0),4),'npv'=>($row['npv']===null||($baseline['npv']??null)===null)?null:round($row['npv']-$baseline['npv'],2),'risk_score'=>round(($row['risk_score']??0)-($baseline['risk_score']??0),2)];
            $matrix[$i]['tradeoff_note'] = $row['decision_score']>=70 ? 'High-scoring option; verify assumptions and implementation limits before export.' : ($row['decision_score']>=50 ? 'Moderate option; review tradeoffs, sources, and mitigation requirements.' : 'Weak option under current assumptions; consider redesign or stronger evidence.');
        }
        $ranked = $matrix; usort($ranked, function($a,$b){ return ($b['decision_score']??0) <=> ($a['decision_score']??0); });
        $comparison = ['comparison_version'=>self::VERSION,'scenario_count'=>count($matrix),'recommended_option'=>$ranked[0]['label'] ?? 'No option selected','recommended_option_id'=>$ranked[0]['option_id'] ?? null,'matrix'=>$matrix,'ranked_options'=>$ranked,'sensitivity_flags'=>['Review savings volatility and CAPEX volatility before treating scenario ranks as stable.','Use Workbench Graph Studio or economics forecasting for deeper sensitivity curves.','Use Catalyst Data records to replace screening-level assumptions with source-backed indicators.'],'workbench_handoff_candidates'=>['economics-forecasting-and-scenario-tool','risk-resilience-impact-matrix','graph-studio-parameter-sensitivity','environmental-monitoring-qaqc-tool'],'warnings'=>$this->scenario_comparison_template()['warnings']];
        return ['ok'=>true,'version'=>self::VERSION,'scenario_comparison'=>$comparison,'results'=>$results,'decision_packet'=>$packet];
    }

    private function scenario_studio_criteria() {
        return [
            ['id'=>'financial_value','label'=>'Financial value','metric'=>'npv','weight'=>20,'direction'=>'higher'],
            ['id'=>'emissions_impact','label'=>'Emissions impact','metric'=>'annual_avoided_tco2e','weight'=>18,'direction'=>'higher'],
            ['id'=>'risk_resilience','label'=>'Risk and resilience','metric'=>'risk_score','weight'=>16,'direction'=>'lower'],
            ['id'=>'evidence_confidence','label'=>'Evidence confidence','metric'=>'confidence','weight'=>10,'direction'=>'higher'],
            ['id'=>'stakeholder_equity','label'=>'Stakeholder and distributional impact','metric'=>'stakeholder_equity','weight'=>10,'direction'=>'higher'],
            ['id'=>'implementation_feasibility','label'=>'Implementation feasibility','metric'=>'implementation_feasibility','weight'=>10,'direction'=>'higher'],
            ['id'=>'reversibility','label'=>'Reversibility and option value','metric'=>'reversibility','weight'=>8,'direction'=>'higher'],
            ['id'=>'time_to_value','label'=>'Time to value','metric'=>'payback_years','weight'=>8,'direction'=>'lower'],
        ];
    }
    private function scenario_studio_template() { return ['schema'=>'scds-scenario-studio/1.0','studio_version'=>self::VERSION,'alternative_limit'=>100,'criteria'=>$this->scenario_studio_criteria(),'analyses'=>['weighted and unweighted ranking','one-way sensitivity','two-variable screening grid','threshold and break-even search','uncertainty envelopes','time-horizon comparison','stakeholder distribution','dominance and tradeoff analysis','reversibility and option value'],'workbench_boundary'=>'Use Workbench for probabilistic simulation, optimization, engineering models, and domain-specific forecasting.','warnings'=>['Scenario outputs are conditional decision-support results, not forecasts or guarantees.','Ranges are assumption bounds, not probability distributions.']]; }
    private function scenario_clamp($v){ return max(0,min(100,floatval($v))); }
    private function scenario_linspace($low,$high,$points){ $points=max(2,intval($points)); $out=[]; for($i=0;$i<$points;$i++)$out[]=round($low+($high-$low)*$i/($points-1),8); return $out; }
    private function scenario_ranges($inputs,$provided=[]){
        $capex=floatval($inputs['capex']??950000); $savings=floatval($inputs['annualSavings']??185000); $cv=floatval($inputs['capexVolatility']??18)/100; $sv=floatval($inputs['savingsVolatility']??15)/100;
        $ranges=['capex'=>['min'=>max(0,$capex*(1-$cv)),'max'=>$capex*(1+$cv),'steps'=>5],'annualSavings'=>['min'=>max(0,$savings*(1-$sv)),'max'=>$savings*(1+$sv),'steps'=>5],'adoptionRate'=>['min'=>max(0,floatval($inputs['adoptionRate']??65)-15),'max'=>min(100,floatval($inputs['adoptionRate']??65)+15),'steps'=>5],'reductionRate'=>['min'=>max(0,floatval($inputs['reductionRate']??32)-12),'max'=>min(100,floatval($inputs['reductionRate']??32)+12),'steps'=>5],'discountRate'=>['min'=>max(0,floatval($inputs['discountRate']??7)-3),'max'=>min(100,floatval($inputs['discountRate']??7)+3),'steps'=>5]];
        foreach((array)$provided as $key=>$raw){ if(is_array($raw)){ $low=$raw['min']??($raw['low']??($raw[0]??null)); $high=$raw['max']??($raw['high']??($raw[1]??null)); if(is_numeric($low)&&is_numeric($high)){ if($low>$high){$tmp=$low;$low=$high;$high=$tmp;} $ranges[$key]=['min'=>floatval($low),'max'=>floatval($high),'steps'=>max(3,min(21,intval($raw['steps']??5)))]; } } }
        return $ranges;
    }
    private function scenario_default_alternatives($inputs){ return [
        ['id'=>'baseline','label'=>'Baseline','parameters'=>['reductionRate'=>0,'adoptionRate'=>0,'annualSavings'=>0,'capex'=>0],'reversibility'=>90,'stakeholderEquity'=>45,'implementationComplexity'=>'Low'],
        ['id'=>'conservative','label'=>'Conservative','parameters'=>['reductionRate'=>floatval($inputs['reductionRate']??32)*.75,'adoptionRate'=>floatval($inputs['adoptionRate']??65)*.8,'annualSavings'=>floatval($inputs['annualSavings']??185000)*.8,'capex'=>floatval($inputs['capex']??950000)*1.1],'reversibility'=>75,'stakeholderEquity'=>55,'implementationComplexity'=>'Low'],
        ['id'=>'expected','label'=>'Expected','parameters'=>[],'reversibility'=>60,'stakeholderEquity'=>floatval($inputs['socialBenefit']??58),'implementationComplexity'=>$inputs['complexity']??'Medium'],
        ['id'=>'ambitious','label'=>'Ambitious','parameters'=>['reductionRate'=>min(100,floatval($inputs['reductionRate']??32)*1.3),'adoptionRate'=>min(100,floatval($inputs['adoptionRate']??65)*1.2),'annualSavings'=>floatval($inputs['annualSavings']??185000)*1.12,'capex'=>floatval($inputs['capex']??950000)*1.18],'reversibility'=>40,'stakeholderEquity'=>70,'implementationComplexity'=>'High'],
        ['id'=>'stress-test','label'=>'Stress Test','parameters'=>['reductionRate'=>floatval($inputs['reductionRate']??32)*.65,'adoptionRate'=>floatval($inputs['adoptionRate']??65)*.65,'annualSavings'=>floatval($inputs['annualSavings']??185000)*.65,'capex'=>floatval($inputs['capex']??950000)*1.25,'exposure'=>70,'vulnerability'=>63,'governanceReadiness'=>53],'reversibility'=>45,'stakeholderEquity'=>48,'implementationComplexity'=>'High']
    ]; }
    private function scenario_eval($inputs,$alternative,$criteria,$extra=[]){
        $params=is_array($alternative['parameters']??null)?$alternative['parameters']:[]; $model=array_merge($inputs,$params,$extra); $results=$this->analyze_inputs($model);
        $npv=floatval($results['finance']['npv']??0); $capex=max(1,floatval($model['capex']??950000)); $annual=floatval($results['emissions']['annual_avoided_tco2e']??0); $baseline=max(1,floatval($model['baselineEmissions']??1200)); $risk=floatval($results['risk']['risk_score']??50); $confidence=$this->scenario_clamp($model['dataConfidence']??70); $equity=$this->scenario_clamp($alternative['stakeholderEquity']??($model['socialBenefit']??58)); $rev=$this->scenario_clamp($alternative['reversibility']??55); $complexity=strtolower($alternative['implementationComplexity']??($model['complexity']??'medium')); $complexity_score=in_array($complexity,['low','simple'],true)?88:(in_array($complexity,['high','very high'],true)?42:65); $feas=$this->scenario_clamp($complexity_score*.55+floatval($model['governanceReadiness']??68)*.3+$confidence*.15); $payback=$results['finance']['payback_years']??null; $payback_score=$payback===null?50:$this->scenario_clamp(100-(floatval($payback)/max(1,intval($model['modelYears']??5)))*70);
        $scores=['financial_value'=>$this->scenario_clamp(50+($npv/$capex)*35),'emissions_impact'=>$this->scenario_clamp($annual/$baseline*100),'risk_resilience'=>$this->scenario_clamp(100-$risk),'evidence_confidence'=>$confidence,'stakeholder_equity'=>$equity,'implementation_feasibility'=>$feas,'reversibility'=>$rev,'time_to_value'=>$payback_score];
        $total=0; foreach($criteria as $c)$total+=max(0,floatval($c['weight']??0)); if($total<=0)$total=1; $rows=[];$weighted=0;$unweighted=0; foreach($criteria as $c){$id=$c['id']??($c['metric']??'criterion');$score=floatval($scores[$id]??50);$w=max(0,floatval($c['weight']??0));$weighted+=$score*$w/$total;$unweighted+=$score;$rows[]=['criterion_id'=>$id,'label'=>$c['label']??$id,'weight'=>round($w/$total*100,4),'score'=>round($score,2),'weighted_contribution'=>round($score*$w/$total,2)];}
        $option=$this->scenario_clamp($rev*.65+$feas*.2+$confidence*.15);
        return ['alternative_id'=>sanitize_key($alternative['id']??('alternative-'.wp_rand(1,9999))),'label'=>sanitize_text_field($alternative['label']??($alternative['name']??'Alternative')),'parameters'=>$model,'metrics'=>['npv'=>$npv,'roi_percent'=>$results['finance']['roi_percent']??0,'payback_years'=>$payback,'annual_avoided_tco2e'=>$annual,'total_avoided_tco2e'=>$results['emissions']['total_avoided_tco2e']??0,'risk_score'=>$risk,'confidence'=>$confidence,'stakeholder_equity'=>$equity,'implementation_feasibility'=>round($feas,2),'reversibility'=>$rev,'option_value'=>round($option,2)],'criteria'=>$rows,'decision_score'=>round($weighted,2),'unweighted_score'=>round($unweighted/max(1,count($criteria)),2),'stakeholder_distribution'=>['records'=>$alternative['stakeholder_impacts']??[],'equity_score'=>$equity],'implementation_complexity'=>$alternative['implementationComplexity']??($model['complexity']??'Medium')];
    }
    private function scenario_dominance($evaluations){
        $rows=[];
        foreach((array)$evaluations as $left){
            $left_scores=[]; foreach((array)($left['criteria']??[]) as $row){$left_scores[$row['criterion_id']??'']=floatval($row['score']??0);}
            $dominated=[];
            foreach((array)$evaluations as $right){
                if(($left['alternative_id']??'')===($right['alternative_id']??'')) continue;
                $right_scores=[]; foreach((array)($right['criteria']??[]) as $row){$right_scores[$row['criterion_id']??'']=floatval($row['score']??0);}
                $shared=array_intersect(array_keys($left_scores),array_keys($right_scores)); if(!$shared) continue;
                $all=true;$any=false; foreach($shared as $key){if($left_scores[$key]<$right_scores[$key]){$all=false;break;} if($left_scores[$key]>$right_scores[$key])$any=true;}
                if($all&&$any)$dominated[]=$right['alternative_id']??'';
            }
            $rows[]=['alternative_id'=>$left['alternative_id']??'','dominates'=>array_values(array_filter($dominated)),'dominated_count'=>count(array_filter($dominated))];
        }
        return $rows;
    }
    private function generate_scenario_studio($inputs,$payload=[],$mode='full'){
        $alternatives=isset($payload['alternatives'])&&is_array($payload['alternatives'])&&$payload['alternatives']?$payload['alternatives']:$this->scenario_default_alternatives($inputs); $alternatives=array_slice($alternatives,0,100); $criteria=isset($payload['criteria'])&&is_array($payload['criteria'])&&$payload['criteria']?$payload['criteria']:$this->scenario_studio_criteria(); $ranges=$this->scenario_ranges($inputs,$payload['parameterRanges']??[]); $params=isset($payload['sensitivityParameters'])&&is_array($payload['sensitivityParameters'])?$payload['sensitivityParameters']:array_slice(array_keys($ranges),0,4); $grid=max(3,min(21,intval($payload['gridPoints']??5)));
        $evaluations=[];foreach($alternatives as $alt)if(is_array($alt))$evaluations[]=$this->scenario_eval($inputs,$alt,$criteria); $weighted=$evaluations;$unweighted=$evaluations;usort($weighted,function($a,$b){return $b['decision_score']<=>$a['decision_score'];});usort($unweighted,function($a,$b){return $b['unweighted_score']<=>$a['unweighted_score'];});$ranking=[];foreach($weighted as $i=>$e)$ranking[]=['rank'=>$i+1,'alternative_id'=>$e['alternative_id'],'label'=>$e['label'],'score'=>$e['decision_score']];$uranking=[];foreach($unweighted as $i=>$e)$uranking[]=['rank'=>$i+1,'alternative_id'=>$e['alternative_id'],'label'=>$e['label'],'score'=>$e['unweighted_score']];$recommended=$weighted[0]??[];$rid=$recommended['alternative_id']??'';$rindex=0;foreach($evaluations as $i=>$e)if($e['alternative_id']===$rid)$rindex=$i;$ralt=$alternatives[$rindex]??($alternatives[0]??[]);
        $series=[];foreach($params as $parameter){if(!isset($ranges[$parameter]))continue;$obs=[];foreach($this->scenario_linspace($ranges[$parameter]['min'],$ranges[$parameter]['max'],$ranges[$parameter]['steps']??$grid) as $value){$ev=$this->scenario_eval($inputs,$ralt,$criteria,[$parameter=>$value]);$obs[]=['parameter_value'=>$value,'decision_score'=>$ev['decision_score'],'npv'=>$ev['metrics']['npv'],'annual_avoided_tco2e'=>$ev['metrics']['annual_avoided_tco2e'],'risk_score'=>$ev['metrics']['risk_score']];}$scores=array_column($obs,'decision_score');$series[]=['parameter'=>$parameter,'min'=>$ranges[$parameter]['min'],'max'=>$ranges[$parameter]['max'],'observations'=>$obs,'score_range'=>round(max($scores)-min($scores),2),'most_sensitive'=>false];}if($series){$maxi=0;foreach($series as $i=>$x)if($x['score_range']>$series[$maxi]['score_range'])$maxi=$i;$series[$maxi]['most_sensitive']=true;}
        $multi=['parameters'=>[],'grid'=>[]];$valid=array_values(array_filter($params,function($p)use($ranges){return isset($ranges[$p]);}));if(count($valid)>=2){$x=$valid[0];$y=$valid[1];$multi['parameters']=[$x,$y];$multi['x_values']=$this->scenario_linspace($ranges[$x]['min'],$ranges[$x]['max'],3);$multi['y_values']=$this->scenario_linspace($ranges[$y]['min'],$ranges[$y]['max'],3);foreach($multi['x_values'] as $xv)foreach($multi['y_values'] as $yv){$ev=$this->scenario_eval($inputs,$ralt,$criteria,[$x=>$xv,$y=>$yv]);$multi['grid'][]=[$x=>$xv,$y=>$yv,'decision_score'=>$ev['decision_score'],'npv'=>$ev['metrics']['npv'],'risk_score'=>$ev['metrics']['risk_score']];}}
        $target=is_array($payload['thresholdTarget']??null)?$payload['thresholdTarget']:[];$tp=$target['parameter']??'annualSavings';$tm=$target['metric']??'npv';$tv=floatval($target['value']??0);$spec=$ranges[$tp]??['min'=>0,'max'=>max(1,floatval($inputs[$tp]??100)*2)];$tobs=[];$break=null;foreach($this->scenario_linspace($spec['min'],$spec['max'],$grid*5) as $value){$ev=$this->scenario_eval($inputs,$ralt,$criteria,[$tp=>$value]);$mv=$tm==='decision_score'?$ev['decision_score']:floatval($ev['metrics'][$tm]??0);$met=$mv>=$tv;$row=['parameter_value'=>$value,'metric_value'=>$mv,'target_met'=>$met];$tobs[]=$row;if($met&&$break===null)$break=$row;}$threshold=['parameter'=>$tp,'metric'=>$tm,'operator'=>'>=','target_value'=>$tv,'range'=>$spec,'break_even'=>$break,'observations'=>$tobs,'found'=>$break!==null,'screening_resolution'=>count($tobs)];
        $unc=[];foreach($alternatives as $i=>$alt){if(!is_array($alt))continue;$low=[];$high=[];foreach($ranges as $k=>$sp){$low[$k]=$sp['min'];$high[$k]=$sp['max'];}$le=$this->scenario_eval($inputs,$alt,$criteria,$low);$he=$this->scenario_eval($inputs,$alt,$criteria,$high);$base=$evaluations[$i]['decision_score']??0;$scores=[$le['decision_score'],$base,$he['decision_score']];$unc[]=['alternative_id'=>$evaluations[$i]['alternative_id']??'','label'=>$evaluations[$i]['label']??'','screening_low'=>min($scores),'base'=>$base,'screening_high'=>max($scores),'spread'=>round(max($scores)-min($scores),2),'interpretation'=>'Combined range endpoints; not a probability interval.'];}
        $horizons=isset($payload['timeHorizons'])&&is_array($payload['timeHorizons'])?$payload['timeHorizons']:[1,3,intval($inputs['modelYears']??5),10];$hrows=[];foreach(array_unique($horizons) as $h){$h=max(1,min(50,intval($h)));$ev=$this->scenario_eval($inputs,$ralt,$criteria,['modelYears'=>$h]);$hrows[]=['years'=>$h,'decision_score'=>$ev['decision_score'],'npv'=>$ev['metrics']['npv'],'total_avoided_tco2e'=>$ev['metrics']['total_avoided_tco2e'],'payback_years'=>$ev['metrics']['payback_years']];}usort($hrows,function($a,$b){return $a['years']<=>$b['years'];});
        $studio=['schema'=>'scds-scenario-studio/1.0','studio_version'=>self::VERSION,'analysis_mode'=>$mode,'alternative_count'=>count($evaluations),'criteria'=>$criteria,'parameter_ranges'=>$ranges,'alternatives'=>$evaluations,'weighted_ranking'=>$ranking,'unweighted_ranking'=>$uranking,'recommended_alternative_id'=>$rid,'recommended_alternative'=>$recommended,'dominance_analysis'=>$this->scenario_dominance($evaluations),'one_way_sensitivity'=>['parameters'=>$series,'tornado_ranking'=>array_map(function($x){return ['parameter'=>$x['parameter'],'score_range'=>$x['score_range']];},$series)],'multi_variable_sensitivity'=>$multi,'threshold_analysis'=>$threshold,'uncertainty_envelopes'=>$unc,'time_horizon_comparison'=>$hrows,'stakeholder_distribution'=>array_map(function($e){return ['alternative_id'=>$e['alternative_id']]+$e['stakeholder_distribution'];},$evaluations),'reversibility_option_value'=>array_map(function($e){return ['alternative_id'=>$e['alternative_id'],'label'=>$e['label'],'reversibility'=>$e['metrics']['reversibility'],'option_value'=>$e['metrics']['option_value']];},$evaluations),'chart_data'=>['alternative_scores'=>array_map(function($e){return ['label'=>$e['label'],'weighted'=>$e['decision_score'],'unweighted'=>$e['unweighted_score']];},$evaluations),'sensitivity_series'=>$series,'time_horizon_series'=>$hrows],'workbench_handoff'=>['recommended_tools'=>['economics-forecasting-and-scenario-tool','graph-studio-parameter-sensitivity','risk-resilience-impact-matrix','systems-modeling-tool']],'warnings'=>$this->scenario_studio_template()['warnings']];
        $packet=isset($payload['packet'])&&is_array($payload['packet'])?array_merge($this->decision_packet_template(),$payload['packet']):$this->decision_packet_template();$packet['scenario_studio']=$studio;$packet['sensitivity_analysis']=$studio['one_way_sensitivity'];$packet['threshold_analysis']=$threshold;$packet['uncertainty_analysis']=['envelopes'=>$unc,'multi_variable'=>$multi];
        $response=['ok'=>true,'version'=>self::VERSION,'schema'=>'scds-scenario-studio/1.0','scenario_studio'=>$studio,'decision_packet'=>$packet];if($mode==='sensitivity'){$response['sensitivity_analysis']=$studio['one_way_sensitivity'];$response['multi_variable_sensitivity']=$multi;}if($mode==='threshold')$response['threshold_analysis']=$threshold;return $response;
    }

    private function workbench_handoff_catalog() {
        return [
            ['tool_id'=>'economics-forecasting-and-scenario-tool','label'=>'Economics Forecasting and Scenario Tool','mode'=>'advanced_calculators','use_when'=>'NPV, ROI, payback, benefit-cost, or scenario assumptions need sensitivity review.','shortcode'=>'[sc_workbench_advanced_calculators title="Economics Forecasting and Scenario Tool"]'],
            ['tool_id'=>'risk-resilience-impact-matrix','label'=>'Risk and Resilience Matrix','mode'=>'risk','use_when'=>'Exposure, vulnerability, stakeholder sensitivity, resilience, or mitigation tradeoffs drive the decision.','shortcode'=>'[sc_workbench topic="risk-resilience" title="Risk and Resilience Matrix" display="compact"]'],
            ['tool_id'=>'graph-studio-parameter-sensitivity','label'=>'Graph Studio Parameter Sensitivity','mode'=>'graph','use_when'=>'A user needs curves, parameter sliders, or scenario visualizations.','shortcode'=>'[sc_workbench_graph_studio title="Scenario Sensitivity Graph"]'],
            ['tool_id'=>'engineering-mode-calculation-note','label'=>'Engineering Mode Calculation Note','mode'=>'engineering','use_when'=>'The decision includes equipment, infrastructure, energy systems, buildings, safety margins, or unit-sensitive formulas.','shortcode'=>'[sc_workbench_engineering_mode title="Engineering Review Note"]'],
            ['tool_id'=>'environmental-monitoring-qaqc-tool','label'=>'Environmental Monitoring QA/QC','mode'=>'environmental','use_when'=>'Data confidence, source quality, indicators, thresholds, or monitoring records need validation.','shortcode'=>'[sc_workbench topic="environmental-monitoring" title="Environmental QA/QC Review" display="compact"]'],
            ['tool_id'=>'chalkboard-symbolic-formula-review','label'=>'Chalkboard Translator and Symbolic Formula Review','mode'=>'symbolic','use_when'=>'Formulas, equations, or assumptions should be translated into readable math and symbolic form.','shortcode'=>'[sc_workbench_chalkboard title="Formula Review"]'],
            ['tool_id'=>'advanced-domain-calculator-library','label'=>'Advanced Domain Calculator Library','mode'=>'advanced','use_when'=>'The decision needs econometrics, psychometrics, computational science, architecture, infrastructure, pattern recognition, or astrophysics calculators.','shortcode'=>'[sc_workbench_advanced_calculators title="Advanced Calculator Library"]'],
        ];
    }

    private function generate_workbench_handoff($inputs, $results, $packet=[], $comparison=[], $readiness=[]) {
        if (!$comparison) $comparison = $this->generate_scenario_comparison($inputs, $results, $packet)['scenario_comparison'];
        $selected = [];
        $add = function($id,$reason,$priority='recommended',$payload=[]) use (&$selected) { foreach($this->workbench_handoff_catalog() as $tool){ if($tool['tool_id']===$id && !isset($selected[$id])) { $selected[$id]=array_merge($tool,['reason'=>$reason,'priority'=>$priority,'payload'=>$payload]); } } };
        if (floatval($inputs['capex']??0)>0 || floatval($inputs['annualSavings']??0)>0) $add('economics-forecasting-and-scenario-tool','Finance outputs or scenario assumptions should be stress-tested before relying on NPV, ROI, or payback.','high');
        if (floatval($inputs['exposure']??55)>=50 || floatval($inputs['vulnerability']??48)>=50 || floatval($results['risk']['risk_score']??0)>=45) $add('risk-resilience-impact-matrix','Risk posture is material; inspect exposure, vulnerability, resilience, mitigation, and cascade effects.','high');
        if (($comparison['scenario_count']??0)>=3) $add('graph-studio-parameter-sensitivity','Multiple scenarios are present; graph scenario sensitivity and key assumption curves.','recommended');
        if (in_array(($inputs['sector']??''), ['Real estate and buildings','Energy and utilities','Manufacturing','Transportation and logistics'], true)) $add('engineering-mode-calculation-note','Engineering-adjacent assumptions may require unit-aware review and professional boundary notes.','review');
        if (floatval($inputs['dataConfidence']??70)<75) $add('environmental-monitoring-qaqc-tool','Evidence/source confidence needs QA/QC before reviewed export.','high');
        if (!$selected) $add('graph-studio-parameter-sensitivity','Use Workbench for exploratory visualization if the decision needs deeper analysis.','optional');
        return ['ok'=>true,'version'=>self::VERSION,'workbench_handoff'=>['handoff_version'=>self::VERSION,'decision_packet_id'=>$packet['decision_packet_id']??'SCDS-DRAFT','recommended_handoffs'=>array_values($selected),'catalog'=>$this->workbench_handoff_catalog(),'payload_summary'=>['projectName'=>$inputs['projectName']??'Decision project','decisionQuestion'=>$inputs['decisionQuestion']??'','weighted_score'=>$results['scores']['weighted']??null,'risk_score'=>$results['risk']['risk_score']??null,'npv'=>$results['finance']['npv']??null,'scenario_count'=>$comparison['scenario_count']??0],'workflow_note'=>'Decision Studio decides and synthesizes; Workbench calculates, graphs, checks formulas, and supports deeper domain analysis.','warnings'=>['Workbench handoffs are analytical supports, not professional approval, certification, assurance, or expert signoff.']],'scenario_comparison'=>$comparison,'results'=>$results,'decision_packet'=>$packet];
    }

    private function csv_response($filename, $rows) { $fh = fopen('php://temp','w+'); if ($rows) { fputcsv($fh, array_keys($rows[0])); foreach($rows as $row) fputcsv($fh, $row); } rewind($fh); $csv = stream_get_contents($fh); fclose($fh); return new WP_REST_Response($csv, 200, ['Content-Type'=>'text/csv; charset=utf-8','Content-Disposition'=>'attachment; filename="'.$filename.'"']); }
    public function rest_export_templates_csv() { return $this->csv_response('scds-scenario-templates-v1.11.0.csv', $this->scenario_templates()); }
    public function rest_export_tool_map_csv() { return $this->csv_response('scds-workbench-tool-map-v1.11.0.csv', $this->workbench_tool_map()); }
    public function rest_export_validation_csv() { global $wpdb; $rows=$wpdb->get_results('SELECT module_id,module_name,status,warnings,last_validated FROM '.$wpdb->prefix.self::VALIDATION_TABLE, ARRAY_A); return $this->csv_response('scds-validation-dashboard-v1.11.0.csv', $rows ?: []); }


    private function artifact_adapter_catalog() {
        return [
            ['module_id'=>'knowledge-library','name'=>'Knowledge Library','artifact_key'=>'knowledge_library_evidence','packet_section'=>'evidence_registry','detects'=>['citation','bibliography','quotes','source_record','evidence_notes'],'summary'=>'Sources, quotations, citations, bibliographies, collections, and evidence notes.'],
            ['module_id'=>'research-librarian','name'=>'Research Librarian','artifact_key'=>'research_guidance','packet_section'=>'research_routes','detects'=>['research_route','recommended_sources','evidence_gaps','follow_up_questions','related_titles'],'summary'=>'Research routes, source recommendations, related titles, evidence gaps, and follow-up questions.'],
            ['module_id'=>'site-intelligence','name'=>'Site Intelligence','artifact_key'=>'site_intelligence_evidence','packet_section'=>'live_evidence','detects'=>['indicator','geography','period','value','methodology','freshness'],'summary'=>'Indicators, observations, methods, source health, freshness, and confidence.'],
            ['module_id'=>'research-lab','name'=>'Research Lab','artifact_key'=>'research_lab_artifacts','packet_section'=>'experimental_evidence','detects'=>['experiment','hypothesis','method','dataset','validation','instruments'],'summary'=>'Experiments, notebooks, datasets, instruments, validation results, and limitations.'],
            ['module_id'=>'platform-core','name'=>'Platform Core','artifact_key'=>'platform_core_records','packet_section'=>'platform_registry','detects'=>['entity','identifiers','evidence_ledger','relationships','provenance','signatures'],'summary'=>'Canonical entities, Evidence Ledger records, provenance links, relationships, and signatures.'],
            ['module_id'=>'catalyst-canvas','name'=>'Catalyst Canvas','artifact_key'=>'framing','packet_section'=>'decision_framing','detects'=>['challenge','audience','point_of_view','how_might_we','prototype','test_plan']],
            ['module_id'=>'catalyst-data','name'=>'Catalyst Data','artifact_key'=>'evidence_records','packet_section'=>'evidence_and_measurement.records','detects'=>['entity','indicator','period','values','source','confidence','trace_path']],
            ['module_id'=>'catalyst-analytics-r','name'=>'Catalyst Analytics R','artifact_key'=>'scenario_analysis','packet_section'=>'scenarios.records','detects'=>['demo','inputs','final','composite_score','budget_ratio','trajectory']],
            ['module_id'=>'global-impact-catalyst','name'=>'Global Impact Catalyst','artifact_key'=>'impact_records','packet_section'=>'impact_measurement.records','detects'=>['initiative','goal','sdg_theme','indicator','baseline_value','current_value','target_value']],
            ['module_id'=>'catalyst-narrative-risk','name'=>'Narrative Risk','artifact_key'=>'claim_reviews','packet_section'=>'claim_and_risk_review.records','detects'=>['claim','risk_score','risk_level','components','flags','review_actions']],
            ['module_id'=>'catalyst-finance','name'=>'Catalyst Finance','artifact_key'=>'finance_analysis','packet_section'=>'financial_tradeoffs','detects'=>['project','inputs','results','interpretation','npv','payback_years']],
            ['module_id'=>'catalyst-grit','name'=>'Catalyst Grit','artifact_key'=>'execution_recovery','packet_section'=>'execution_and_recovery','detects'=>['challenge','impact_severity','pressure_level','energy_level','support_level','clarity_level','recovery_score']],
            ['module_id'=>'workbench','name'=>'Sustainable Catalyst Workbench','artifact_key'=>'workbench_calculations','packet_section'=>'calculation_trace','detects'=>['calculation','formula','inputs','results','assumptions','validation_checks','report']],
        ];
    }

    private function detect_artifact_module($artifact, $module_id='') {
        $mid = sanitize_key(str_replace('_','-', $module_id));
        $aliases = ['canvas'=>'catalyst-canvas','data'=>'catalyst-data','analytics-r'=>'catalyst-analytics-r','impact'=>'global-impact-catalyst','global-impact'=>'global-impact-catalyst','narrative-risk'=>'catalyst-narrative-risk','finance'=>'catalyst-finance','grit'=>'catalyst-grit','calculation'=>'workbench','library'=>'knowledge-library','knowledge'=>'knowledge-library','librarian'=>'research-librarian','research-guidance'=>'research-librarian','site'=>'site-intelligence','intelligence'=>'site-intelligence','lab'=>'research-lab','core'=>'platform-core','platform'=>'platform-core'];
        if (isset($aliases[$mid])) $mid = $aliases[$mid];
        foreach ($this->artifact_adapter_catalog() as $a) if ($a['module_id'] === $mid || $a['artifact_key'] === $mid) return $a;
        $source = is_array($artifact['source'] ?? null) ? $artifact['source'] : [];
        $source_product = sanitize_key(str_replace('_','-', strval($artifact['source_product'] ?? ($artifact['sourceProduct'] ?? ($source['product'] ?? ($source['product_id'] ?? ''))))));
        if ($source_product) { $candidate = $this->adapter_by_id($source_product); if (($candidate['module_id'] ?? '') === $source_product) return $candidate; }
        $payload = is_array($artifact['payload'] ?? null) ? $artifact['payload'] : $artifact;
        $artifact_type = sanitize_key(str_replace('_','-', strval($artifact['artifact_type'] ?? ($artifact['type'] ?? ''))));
        if (in_array($artifact_type, ['source-record','quotation-evidence','citation-bundle','bibliography','collection-context'], true)) return $this->adapter_by_id('knowledge-library');
        if (in_array($artifact_type, ['research-route','source-recommendations','evidence-gap-report','related-titles'], true)) return $this->adapter_by_id('research-librarian');
        if (in_array($artifact_type, ['indicator-record','country-dossier','live-observation','methodology-record','source-health'], true)) return $this->adapter_by_id('site-intelligence');
        if (in_array($artifact_type, ['experiment','notebook','dataset','instrument-run','validation-result','scientific-report'], true)) return $this->adapter_by_id('research-lab');
        if (in_array($artifact_type, ['entity-record','evidence-ledger-record','provenance-link','signed-manifest','relationship-bundle'], true)) return $this->adapter_by_id('platform-core');
        $artifact = $payload;
        $record_type = strtolower(strval($artifact['record_type'] ?? ''));
        if ($record_type === 'global_impact_catalyst_record') return $this->adapter_by_id('global-impact-catalyst');
        if ($record_type === 'catalyst_narrative_risk_record') return $this->adapter_by_id('catalyst-narrative-risk');
        if ($record_type === 'catalyst_grit_record') return $this->adapter_by_id('catalyst-grit');
        $keys = array_keys($artifact);
        $has = function($k) use ($artifact) { return array_key_exists($k, $artifact); };
        if ($has('point_of_view') || $has('how_might_we') || ($has('challenge') && $has('audience') && $has('prototype'))) return $this->adapter_by_id('catalyst-canvas');
        if ($has('entity') && $has('indicator') && $has('period') && $has('values') && $has('source')) return $this->adapter_by_id('catalyst-data');
        if (($has('final') && $has('composite_score')) || ($has('trajectory') && $has('inputs'))) return $this->adapter_by_id('catalyst-analytics-r');
        if ($has('initiative') && $has('goal') && $has('baseline_value') && $has('target_value')) return $this->adapter_by_id('global-impact-catalyst');
        if ($has('claim') && $has('risk_score') && $has('risk_level')) return $this->adapter_by_id('catalyst-narrative-risk');
        if ($has('project') && $has('inputs') && $has('results') && $has('interpretation')) return $this->adapter_by_id('catalyst-finance');
        if ($has('impact_severity') && $has('pressure_level')) return $this->adapter_by_id('catalyst-grit');
        return $this->adapter_by_id('workbench');
    }

    private function adapter_by_id($id) { $catalog=$this->artifact_adapter_catalog(); foreach ($catalog as $a) if ($a['module_id'] === $id) return $a; foreach ($catalog as $a) if ($a['module_id'] === 'workbench') return $a; return $catalog[0]; }
    private function arr($value) { if (is_array($value)) return array_values($value); if ($value === null || $value === '') return []; return [$value]; }
    private function source_entry($title,$type,$confidence,$used_for,$notes='') { return ['source_title'=>$title ?: 'Unspecified source','source_type'=>$type ?: 'unspecified','confidence'=>$confidence ?: 'unspecified','used_for'=>$used_for ?: 'unspecified','method_notes'=>$notes ?: '']; }
    private function assumption_entry($label,$value,$source,$used_in,$sensitivity='medium',$status='needs review') { return ['assumption'=>$label,'value'=>$value,'module_or_source'=>$source,'used_in'=>$used_in,'sensitivity'=>$sensitivity,'review_status'=>$status]; }
    private function merge_list($a,$b) { $base = is_array($a) ? $a : []; foreach((is_array($b)?$b:[$b]) as $item) if ($item !== null && $item !== '') $base[] = $item; return $base; }

    private function platform_handoff_contracts() {
        $required = ['artifact_schema','artifact_id','artifact_type','source','provenance','payload'];
        return [
            ['product_id'=>'knowledge-library','product_name'=>'Knowledge Library','artifact_types'=>['source_record','quotation_evidence','citation_bundle','bibliography','collection_context'],'packet_targets'=>['evidence_registry','sources','citations','quotations'],'required_envelope'=>$required],
            ['product_id'=>'research-librarian','product_name'=>'Research Librarian','artifact_types'=>['research_route','source_recommendations','evidence_gap_report','related_titles'],'packet_targets'=>['research_routes','sources','evidence_gaps','follow_up_questions'],'required_envelope'=>$required],
            ['product_id'=>'site-intelligence','product_name'=>'Site Intelligence','artifact_types'=>['indicator_record','country_dossier','live_observation','methodology_record','source_health'],'packet_targets'=>['live_evidence','evidence_registry','sources','methodologies'],'required_envelope'=>$required],
            ['product_id'=>'workbench','product_name'=>'Workbench','artifact_types'=>['calculation','model_output','graph','code_result','technical_report'],'packet_targets'=>['calculation_trace','workbench_calculations','assumptions','technical_artifacts'],'required_envelope'=>$required],
            ['product_id'=>'research-lab','product_name'=>'Research Lab','artifact_types'=>['experiment','notebook','dataset','instrument_run','validation_result','scientific_report'],'packet_targets'=>['experimental_evidence','datasets','evidence_registry','calculation_trace'],'required_envelope'=>$required],
            ['product_id'=>'platform-core','product_name'=>'Platform Core','artifact_types'=>['entity_record','evidence_ledger_record','provenance_link','signed_manifest','relationship_bundle'],'packet_targets'=>['platform_registry','entities','evidence_ledger','provenance_links'],'required_envelope'=>$required],
        ];
    }

    private function platform_contract($product_id) {
        $id = sanitize_key(str_replace('_','-', strval($product_id)));
        $aliases=['library'=>'knowledge-library','knowledge'=>'knowledge-library','librarian'=>'research-librarian','research-guidance'=>'research-librarian','site'=>'site-intelligence','intelligence'=>'site-intelligence','lab'=>'research-lab','core'=>'platform-core','platform'=>'platform-core'];
        if(isset($aliases[$id])) $id=$aliases[$id];
        foreach($this->platform_handoff_contracts() as $contract) if($contract['product_id']===$id) return $contract;
        return null;
    }

    private function canonical_hash($value) {
        if (is_array($value)) { ksort($value); foreach($value as $key=>$item) if(is_array($item)) $value[$key]=$this->canonical_sort($item); }
        return 'sha256:' . hash('sha256', wp_json_encode($value, JSON_UNESCAPED_SLASHES|JSON_UNESCAPED_UNICODE));
    }

    private function canonical_sort($value) {
        if (!is_array($value)) return $value;
        if (array_keys($value) !== range(0, count($value)-1)) ksort($value);
        foreach($value as $key=>$item) if(is_array($item)) $value[$key]=$this->canonical_sort($item);
        return $value;
    }

    private function typed_envelope($artifact, $module_id='') {
        $adapter=$this->detect_artifact_module($artifact,$module_id); $source=is_array($artifact['source']??null)?$artifact['source']:[]; $provenance=is_array($artifact['provenance']??null)?$artifact['provenance']:[]; $payload=is_array($artifact['payload']??null)?$artifact['payload']:$artifact;
        $product=$module_id ?: ($artifact['source_product']??($artifact['sourceProduct']??($source['product']??($source['product_id']??$adapter['module_id'])))); $contract=$this->platform_contract($product); $product=$contract?$contract['product_id']:$adapter['module_id'];
        $calculated=$this->canonical_hash($payload); $supplied=sanitize_text_field($provenance['integrity_hash']??($artifact['integrity_hash']??''));
        return ['artifact_schema'=>sanitize_text_field($artifact['artifact_schema']??'scds-platform-artifact/1.0'),'artifact_id'=>sanitize_text_field($artifact['artifact_id']??($artifact['id']??substr(str_replace('sha256:','',$calculated),0,20))),'artifact_type'=>sanitize_key($artifact['artifact_type']??($artifact['type']??$adapter['artifact_key'])),'source'=>['product'=>$product,'product_version'=>sanitize_text_field($source['product_version']??($source['version']??($artifact['source_version']??'unknown'))),'artifact_url'=>esc_url_raw($source['artifact_url']??($source['url']??($artifact['url']??''))),'created_at'=>sanitize_text_field($source['created_at']??($artifact['created_at']??'')),'exported_at'=>sanitize_text_field($source['exported_at']??($artifact['exported_at']??gmdate('c'))) ],'provenance'=>['methodology'=>$provenance['methodology']??($artifact['methodology']??($payload['methodology']??'')),'freshness'=>$provenance['freshness']??($artifact['freshness']??($payload['freshness']??'unspecified')),'confidence'=>$provenance['confidence']??($artifact['confidence']??($payload['confidence']??'unspecified')),'integrity_hash'=>$supplied?:$calculated,'calculated_integrity_hash'=>$calculated,'integrity_verified'=>($supplied && hash_equals($supplied,$calculated)),'transformation_history'=>array_merge($this->arr($provenance['transformation_history']??[]),[['at'=>gmdate('c'),'action'=>'normalized','by'=>'decision-studio','version'=>self::VERSION]])],'payload'=>$payload];
    }

    private function validate_typed_artifact_local($artifact,$source_product='',$strict=false) {
        $envelope=$this->typed_envelope($artifact,$source_product); $contract=$this->platform_contract($envelope['source']['product']); $errors=[]; $warnings=[];
        if(!$contract) $errors[]='Unsupported platform source product: '.$envelope['source']['product'];
        if($envelope['artifact_schema']!=='scds-platform-artifact/1.0') { if($strict) $errors[]='Artifact schema differs from scds-platform-artifact/1.0.'; else $warnings[]='Artifact schema differs from scds-platform-artifact/1.0.'; }
        if(empty($envelope['payload'])||!is_array($envelope['payload'])) $errors[]='Artifact payload must be a non-empty object.';
        $original=is_array($artifact['provenance']??null)?sanitize_text_field($artifact['provenance']['integrity_hash']??''):sanitize_text_field($artifact['integrity_hash']??'');
        if($original&&!$envelope['provenance']['integrity_verified']) $errors[]='Supplied integrity hash does not match the canonical payload hash.';
        return ['ok'=>empty($errors),'version'=>self::VERSION,'schema'=>'scds-platform-artifact/1.0','product_id'=>$envelope['source']['product'],'contract'=>$contract,'envelope'=>$envelope,'errors'=>$errors,'warnings'=>$warnings];
    }

    private function normalize_typed_artifact($artifact,$module_id='') {
        $validation=$this->validate_typed_artifact_local($artifact,$module_id,false); $envelope=$validation['envelope']; $mid=$envelope['source']['product']; $payload=$envelope['payload']; $adapter=$this->adapter_by_id($mid); $name=$adapter['name'];
        $base=['evidence_schema'=>'scds-evidence-record/1.0','artifact_id'=>$envelope['artifact_id'],'artifact_type'=>$envelope['artifact_type'],'source_product'=>$mid,'source_version'=>$envelope['source']['product_version'],'source_url'=>$envelope['source']['artifact_url'],'methodology'=>$envelope['provenance']['methodology'],'freshness'=>$envelope['provenance']['freshness'],'confidence'=>$envelope['provenance']['confidence'],'integrity_hash'=>$envelope['provenance']['calculated_integrity_hash'],'integrity_verified'=>$envelope['provenance']['integrity_verified']];
        $patch=['platform_handoffs'=>[$envelope],'integrity_checks'=>[['artifact_id'=>$envelope['artifact_id'],'source_product'=>$mid,'supplied_hash'=>$envelope['provenance']['integrity_hash'],'calculated_hash'=>$envelope['provenance']['calculated_integrity_hash'],'verified'=>$envelope['provenance']['integrity_verified']]],'audit_trail'=>[['event'=>'Typed platform artifact imported','module'=>$name,'module_id'=>$mid,'artifact_id'=>$envelope['artifact_id'],'version'=>self::VERSION]]]; $title=$name.' artifact';
        if($mid==='knowledge-library') { $record=array_merge($base,['title'=>$payload['title']??($payload['source_title']??'Knowledge Library source'),'source_type'=>$payload['source_type']??'research source','citation'=>$payload['citation']??'','authors'=>$payload['authors']??[],'published_at'=>$payload['published_at']??'','evidence_notes'=>$payload['evidence_notes']??'','collection'=>$payload['collection']??'']); $patch['evidence_registry']=[$record]; $patch['knowledge_library_evidence']=[$record]; $patch['sources']=[$this->source_entry($record['title'],$record['source_type'],$base['confidence'],'Knowledge Library evidence',$record['evidence_notes'])]; if($record['citation'])$patch['citations']=[['artifact_id'=>$envelope['artifact_id'],'citation'=>$record['citation'],'style'=>$payload['citation_style']??'Harvard','title'=>$record['title']]]; $patch['quotations']=[]; foreach($this->arr($payload['quotes']??($payload['quotations']??[])) as $quote)$patch['quotations'][]=['artifact_id'=>$envelope['artifact_id'],'source_title'=>$record['title'],'quote'=>is_array($quote)?($quote['text']??''):strval($quote),'locator'=>is_array($quote)?($quote['locator']??''):'','context'=>is_array($quote)?($quote['context']??''):'' ]; $title=$record['title']; }
        elseif($mid==='research-librarian'){ $route=array_merge($base,['query'=>$payload['query']??'','route'=>$payload['route']??($payload['research_route']??[]),'recommended_sources'=>$this->arr($payload['recommended_sources']??[]),'related_titles'=>$this->arr($payload['related_titles']??[]),'notes'=>$payload['notes']??'']); $patch['research_routes']=[$route];$patch['research_guidance']=$route;$patch['evidence_gaps']=$this->arr($payload['evidence_gaps']??[]);$patch['follow_up_questions']=$this->arr($payload['follow_up_questions']??[]);$title=$route['query']?:'Research route'; }
        elseif($mid==='site-intelligence'){ $record=array_merge($base,['indicator'=>$payload['indicator']??[],'geography'=>$payload['geography']??($payload['country']??($payload['region']??'')),'period'=>$payload['period']??($payload['observed_at']??''),'value'=>$payload['value']??null,'unit'=>$payload['unit']??'','source'=>$payload['source']??[],'source_health'=>$payload['source_health']??[],'observation_type'=>$envelope['artifact_type']]); $patch['live_evidence']=[$record];$patch['site_intelligence_evidence']=[$record];$patch['evidence_registry']=[$record];$src=is_array($payload['source']??null)?$payload['source']:['name'=>$payload['source']??'Site Intelligence source'];$patch['sources']=[$this->source_entry($src['name']??'Site Intelligence source',$src['type']??'public data source',$base['confidence'],is_string($record['indicator'])?$record['indicator']:'indicator evidence',strval($base['methodology']))];$patch['methodologies']=$this->arr($payload['methodology_records']??($payload['methodology']??[]));$title=is_string($record['indicator'])?$record['indicator']:'Site Intelligence observation'; }
        elseif($mid==='workbench'){ $calc=array_merge($base,['calculation'=>$payload['calculation']??($payload['title']??'Workbench artifact'),'formula'=>$payload['formula']??'','inputs'=>$payload['inputs']??[],'results'=>$payload['results']??($payload['result']??null),'assumptions'=>$this->arr($payload['assumptions']??[]),'validation_checks'=>$this->arr($payload['validation_checks']??($payload['checks']??[])),'warnings'=>$this->arr($payload['warnings']??[]),'graph'=>$payload['graph']??[],'report'=>$payload['report']??[]]);$patch['workbench_calculations']=[$calc];$patch['technical_artifacts']=[$calc];$patch['calculation_trace']=[['artifact_id'=>$envelope['artifact_id'],'calculation'=>$calc['calculation'],'formula'=>$calc['formula'],'inputs'=>$calc['inputs'],'result'=>$calc['results'],'validation_status'=>'imported from Workbench','validation_checks'=>$calc['validation_checks']]];$title=$calc['calculation']; }
        elseif($mid==='research-lab'){ $record=array_merge($base,['title'=>$payload['title']??($payload['experiment']??'Research Lab artifact'),'hypothesis'=>$payload['hypothesis']??'','method'=>$payload['method']??[],'results'=>$payload['results']??[],'validation'=>$payload['validation']??[],'limitations'=>$this->arr($payload['limitations']??[]),'instruments'=>$this->arr($payload['instruments']??[]),'notebook'=>$payload['notebook']??[]]);$patch['experimental_evidence']=[$record];$patch['research_lab_artifacts']=[$record];$patch['datasets']=$this->arr($payload['datasets']??($payload['dataset']??[]));$patch['evidence_registry']=[$record];$title=$record['title']; }
        elseif($mid==='platform-core'){ $entity=is_array($payload['entity']??null)?$payload['entity']:['name'=>$payload['entity']??($payload['name']??'Platform entity')];$record=array_merge($base,['entity'=>$entity,'identifiers'=>$payload['identifiers']??[],'relationships'=>$this->arr($payload['relationships']??[]),'signatures'=>$this->arr($payload['signatures']??[])]);$patch['platform_registry']=[$record];$patch['platform_core_records']=[$record];$patch['entities']=[$entity];$patch['evidence_ledger']=$this->arr($payload['evidence_ledger']??($payload['evidence_records']??[]));$patch['provenance_links']=$this->arr($payload['provenance_links']??($payload['provenance']??[]));$title=$entity['name']??'Platform Core entity'; }
        $patch['module_artifacts_raw']=[$adapter['artifact_key']=>$artifact]; $summary=['module_id'=>$mid,'module_name'=>$name,'artifact_key'=>$adapter['artifact_key'],'packet_section'=>$adapter['packet_section'],'artifact_id'=>$envelope['artifact_id'],'artifact_type'=>$envelope['artifact_type'],'title'=>$title,'status'=>'typed_and_normalized','integrity_verified'=>$envelope['provenance']['integrity_verified']];
        return ['ok'=>$validation['ok'],'version'=>self::VERSION,'schema'=>'scds-platform-artifact/1.0','adapter'=>$adapter,'contract'=>$validation['contract'],'summary'=>$summary,'packet_patch'=>$patch,'warnings'=>$validation['warnings'],'validation'=>$validation,'artifact'=>$envelope];
    }

    private function normalize_artifact($artifact, $module_id='') {
        $adapter = $this->detect_artifact_module($artifact, $module_id); $mid=$adapter['module_id']; $name=$adapter['name'];
        if ($this->platform_contract($mid)) return $this->normalize_typed_artifact($artifact, $mid);
        $patch = ['audit_trail'=>[['event'=>'Artifact imported','module'=>$name,'module_id'=>$mid,'version'=>self::VERSION]]];
        $summary = ['module_id'=>$mid,'module_name'=>$name,'artifact_key'=>$adapter['artifact_key'],'packet_section'=>$adapter['packet_section'],'status'=>'normalized'];
        if ($mid === 'catalyst-canvas') {
            $framing = ['challenge'=>$artifact['challenge'] ?? '', 'audience'=>$artifact['audience'] ?? '', 'goal'=>$artifact['goal'] ?? '', 'constraint'=>$artifact['constraint'] ?? '', 'framework'=>$artifact['framework'] ?? '', 'persona'=>$artifact['persona'] ?? [], 'point_of_view'=>$artifact['point_of_view'] ?? ($artifact['pov'] ?? ''), 'how_might_we'=>$this->arr($artifact['how_might_we'] ?? []), 'prototype'=>$artifact['prototype'] ?? [], 'test_plan'=>$artifact['test_plan'] ?? [], 'review_questions'=>$this->arr($artifact['review_questions'] ?? [])];
            $patch['decision_framing']=$framing; $patch['framing']=$framing; $summary['title']=$framing['challenge'] ?: ($framing['goal'] ?: 'Canvas framing');
        } elseif ($mid === 'catalyst-data') {
            $record = ['entity'=>$artifact['entity'] ?? [], 'indicator'=>$artifact['indicator'] ?? [], 'period'=>$artifact['period'] ?? '', 'values'=>$artifact['values'] ?? [], 'source'=>$artifact['source'] ?? [], 'confidence'=>$artifact['confidence'] ?? null, 'review_status'=>$artifact['review_status'] ?? 'needs review', 'method_notes'=>$artifact['method_notes'] ?? '', 'trace_path'=>$this->arr($artifact['trace_path'] ?? [])];
            $source = is_array($artifact['source'] ?? null) ? $artifact['source'] : ['name'=>$artifact['source'] ?? 'Catalyst Data source','type'=>'measurement source'];
            $patch['evidence_and_measurement']=['records'=>[$record]]; $patch['evidence_records']=[$record]; $patch['sources']=[$this->source_entry($source['name'] ?? 'Catalyst Data source', $source['type'] ?? 'measurement source', $artifact['confidence'] ?? '', $artifact['indicator']['name'] ?? 'measurement record', $artifact['method_notes'] ?? '')]; $summary['title']=$artifact['indicator']['name'] ?? 'Catalyst Data record';
        } elseif ($mid === 'catalyst-analytics-r') {
            $scenario = ['scenario_name'=>$artifact['inputs']['scenarioName'] ?? ($artifact['demo'] ?? 'Catalyst Analytics R scenario'), 'inputs'=>$artifact['inputs'] ?? [], 'final'=>$artifact['final'] ?? [], 'composite_score'=>$artifact['composite_score'] ?? null, 'budget_ratio'=>$artifact['budget_ratio'] ?? null, 'interpretation_notes'=>$this->arr($artifact['interpretation_notes'] ?? []), 'trajectory'=>$this->arr($artifact['trajectory'] ?? [])];
            $patch['scenarios']=['records'=>[$scenario]]; $patch['scenario_analysis']=$scenario; $summary['title']=$scenario['scenario_name'];
        } elseif ($mid === 'global-impact-catalyst') {
            $record = ['initiative'=>$artifact['initiative'] ?? '', 'goal'=>$artifact['goal'] ?? '', 'sdg_theme'=>$artifact['sdg_theme'] ?? '', 'indicator'=>$artifact['indicator'] ?? '', 'unit'=>$artifact['unit'] ?? '', 'baseline_value'=>$artifact['baseline_value'] ?? null, 'current_value'=>$artifact['current_value'] ?? null, 'target_value'=>$artifact['target_value'] ?? null, 'metrics'=>$artifact['metrics'] ?? [], 'confidence'=>$artifact['confidence'] ?? '', 'review_status'=>$artifact['review_status'] ?? 'needs review', 'interpretation_notes'=>$this->arr($artifact['interpretation_notes'] ?? [])];
            $patch['impact_measurement']=['records'=>[$record]]; $patch['impact_records']=[$record]; $patch['sources']=[$this->source_entry($artifact['source'] ?? 'Global Impact source', 'impact source', $artifact['confidence'] ?? '', $artifact['indicator'] ?? 'impact indicator', $artifact['method_notes'] ?? '')]; $summary['title']=$record['initiative'] ?: 'Global Impact record';
        } elseif ($mid === 'catalyst-narrative-risk') {
            $record = ['claim'=>$artifact['claim'] ?? '', 'risk_score'=>$artifact['risk_score'] ?? null, 'risk_level'=>$artifact['risk_level'] ?? '', 'components'=>$artifact['components'] ?? [], 'flags'=>$this->arr($artifact['flags'] ?? []), 'review_actions'=>$this->arr($artifact['review_actions'] ?? []), 'decision_note'=>$artifact['decision_note'] ?? '', 'inputs'=>$artifact['inputs'] ?? []];
            $patch['claim_and_risk_review']=['records'=>[$record]]; $patch['claim_reviews']=[$record]; $patch['risks']=[['risk'=>$record['claim'] ?: 'Narrative risk','score'=>$record['risk_score'],'level'=>$record['risk_level'],'module_or_source'=>$name,'flags'=>$record['flags']]]; $summary['title']=$record['claim'] ?: 'Narrative Risk record';
        } elseif ($mid === 'catalyst-finance') {
            $results = is_array($artifact['results'] ?? null) ? $artifact['results'] : $artifact; $finance=['project'=>$artifact['project'] ?? [], 'inputs'=>$artifact['inputs'] ?? [], 'results'=>$results, 'interpretation'=>$artifact['interpretation'] ?? [], 'metadata'=>$artifact['metadata'] ?? []];
            $patch['financial_tradeoffs']=$finance; $patch['finance_analysis']=$finance; $patch['calculation_trace']=[]; foreach(['npv'=>'NPV','roi_percent'=>'ROI','payback_years'=>'Payback','benefit_cost_ratio'=>'Benefit-cost ratio','carbon_cost_per_ton'=>'Carbon cost per ton'] as $k=>$label){ if(isset($results[$k])) $patch['calculation_trace'][]=['calculation'=>$label,'formula'=>'Catalyst Finance scenario engine','result'=>$results[$k],'validation_status'=>'requires finance review']; } $summary['title']=$artifact['project']['name'] ?? 'Catalyst Finance analysis';
        } elseif ($mid === 'catalyst-grit') {
            $recovery=['challenge'=>$artifact['challenge'] ?? '', 'domain'=>$artifact['domain'] ?? '', 'impact_severity'=>$artifact['impact_severity'] ?? null, 'pressure_level'=>$artifact['pressure_level'] ?? null, 'energy_level'=>$artifact['energy_level'] ?? null, 'support_level'=>$artifact['support_level'] ?? null, 'clarity_level'=>$artifact['clarity_level'] ?? null, 'recovery_score'=>$artifact['recovery_score'] ?? null, 'resilience_state'=>$artifact['resilience_state'] ?? '', 'recovery_actions'=>$this->arr($artifact['recovery_actions'] ?? []), 'risk_flags'=>$this->arr($artifact['risk_flags'] ?? []), 'next_actions'=>$this->arr($artifact['next_actions'] ?? []), 'decision_note'=>$artifact['decision_note'] ?? ''];
            $patch['execution_and_recovery']=$recovery; $patch['execution_recovery']=$recovery; $patch['risks']=[['risk'=>'Execution/recovery risk','score'=>$recovery['recovery_score'],'level'=>$recovery['resilience_state'],'module_or_source'=>$name,'flags'=>$recovery['risk_flags']]]; $summary['title']=$recovery['challenge'] ?: 'Catalyst Grit recovery record';
        } else {
            $calc=['calculation'=>$artifact['calculation'] ?? ($artifact['title'] ?? 'Workbench calculation'), 'formula'=>$artifact['formula'] ?? '', 'inputs'=>$artifact['inputs'] ?? [], 'results'=>$artifact['results'] ?? ($artifact['result'] ?? null), 'assumptions'=>$artifact['assumptions'] ?? [], 'validation_checks'=>$artifact['validation_checks'] ?? ($artifact['checks'] ?? []), 'warnings'=>$artifact['warnings'] ?? [], 'report'=>$artifact['report'] ?? []];
            $patch['workbench_calculations']=[$calc]; $patch['calculation_trace']=[['calculation'=>$calc['calculation'],'formula'=>$calc['formula'],'inputs'=>$calc['inputs'],'result'=>$calc['results'],'validation_status'=>'imported from Workbench']]; $summary['title']=$calc['calculation'];
        }
        $patch['module_artifacts_raw']=[$adapter['artifact_key']=>$artifact];
        return ['ok'=>true,'version'=>self::VERSION,'adapter'=>$adapter,'summary'=>$summary,'packet_patch'=>$patch,'warnings'=>[],'artifact'=>$artifact];
    }

    private function apply_packet_patch($packet, $patch) {
        if (!is_array($packet) || !$packet) $packet = $this->decision_packet_template();
        foreach($patch as $key=>$value) {
            if (in_array($key, ['assumptions','risks','sources','audit_trail','calculation_trace','claim_reviews','workbench_calculations','evidence_registry','citations','quotations','research_routes','evidence_gaps','follow_up_questions','live_evidence','methodologies','experimental_evidence','datasets','technical_artifacts','platform_registry','entities','evidence_ledger','provenance_links','platform_handoffs','integrity_checks'], true)) $packet[$key] = $this->merge_list($packet[$key] ?? [], $value);
            elseif ($key === 'evidence_and_measurement' || $key === 'scenarios' || $key === 'impact_measurement' || $key === 'claim_and_risk_review') { if(!isset($packet[$key]) || !is_array($packet[$key])) $packet[$key]=['records'=>[]]; $packet[$key]['records']=$this->merge_list($packet[$key]['records'] ?? [], $value['records'] ?? []); }
            elseif (isset($packet[$key]) && is_array($packet[$key]) && is_array($value)) $packet[$key] = array_merge($packet[$key], $value);
            else $packet[$key] = $value;
        }
        return $packet;
    }

    private function import_artifact_into_packet($artifact, $module_id='', $packet=[]) {
        $normalized = $this->normalize_artifact($artifact, $module_id);
        $updated = $this->apply_packet_patch($packet, $normalized['packet_patch']);
        return ['ok'=>true,'version'=>self::VERSION,'import_result'=>$normalized,'decision_packet'=>$updated,'analysis'=>['ok'=>true,'version'=>self::VERSION,'decision_packet_version'=>'1.11.0']];
    }

    private function module_integrations() {
        return [
            ['step'=>1,'phase'=>'Source','id'=>'knowledge-library','name'=>'Knowledge Library','label'=>'Sources and citations','url'=>'/knowledge-library/','artifact_key'=>'knowledge_library_evidence','packet_section'=>'evidence_registry','feeds'=>'Sources, quotations, citations, bibliographies, collection context, and evidence notes.','summary'=>'Import durable source records, quotations, Harvard-style citations, bibliographies, collections, and evidence notes.'],
            ['step'=>2,'phase'=>'Research','id'=>'research-librarian','name'=>'Research Librarian','label'=>'Research routes and gaps','url'=>'/research-librarian/','artifact_key'=>'research_guidance','packet_section'=>'research_routes','feeds'=>'Research path, source recommendations, unanswered questions, and evidence gaps.','summary'=>'Import research routes, recommended sources, evidence gaps, related titles, and follow-up questions.'],
            ['step'=>3,'phase'=>'Observe','id'=>'site-intelligence','name'=>'Site Intelligence','label'=>'Indicators and observations','url'=>'/platform/site-intelligence/','artifact_key'=>'site_intelligence_evidence','packet_section'=>'live_evidence','feeds'=>'Indicators, observations, geographic context, source health, freshness, and methodology.','summary'=>'Import indicators, country dossiers, live observations, methodology records, source health, and freshness context.'],
            ['step'=>4,'phase'=>'Model','id'=>'workbench','name'=>'Workbench','label'=>'Calculations and models','url'=>'/platform/workbench/','artifact_key'=>'workbench_calculations','packet_section'=>'calculation_trace','feeds'=>'Calculated outputs, formulas, graphs, assumptions, validation checks, warnings, and reports.','summary'=>'Import formulas, calculations, graphs, models, code outputs, validation checks, assumptions, and technical reports.'],
            ['step'=>5,'phase'=>'Validate','id'=>'research-lab','name'=>'Research Lab','label'=>'Experiments and scientific artifacts','url'=>'/lab/','artifact_key'=>'research_lab_artifacts','packet_section'=>'experimental_evidence','feeds'=>'Experimental methods, datasets, results, validation status, limitations, and provenance.','summary'=>'Import experiments, notebooks, datasets, instrument context, validation results, provenance, and scientific reports.'],
            ['step'=>6,'phase'=>'Trace','id'=>'platform-core','name'=>'Platform Core','label'=>'Entities and Evidence Ledger','url'=>'/platform/','artifact_key'=>'platform_core_records','packet_section'=>'platform_registry','feeds'=>'Canonical entity identity, Evidence Ledger links, provenance, integrity, and relationships.','summary'=>'Import canonical entities, Evidence Ledger records, provenance links, identifiers, signatures, and shared exchange metadata.'],
            ['step'=>7,'phase'=>'Decide','id'=>'decision-studio','name'=>'Decision Studio','label'=>'Decision synthesis','url'=>'/platform/decision-studio/','artifact_key'=>'synthesis','packet_section'=>'integrated_decision_brief','feeds'=>'Integrated synthesis, alternatives, assumptions, risks, caveats, readiness, and audit.','summary'=>'Synthesize typed evidence into scenarios, readiness findings, an auditable brief, and export bundle.'],
        ];
    }


    private function governance_state_catalog() {
        return ['governance_version'=>self::VERSION,'schema'=>'scds-decision-governance/1.0','states'=>[['id'=>'draft','label'=>'Draft'],['id'=>'evidence_gathering','label'=>'Evidence gathering'],['id'=>'analysis','label'=>'Analysis'],['id'=>'review','label'=>'Review'],['id'=>'revision_required','label'=>'Revision required'],['id'=>'approved','label'=>'Approved'],['id'=>'rejected','label'=>'Rejected'],['id'=>'deferred','label'=>'Deferred'],['id'=>'implemented','label'=>'Implemented'],['id'=>'retired','label'=>'Retired']],'transitions'=>['draft'=>['evidence_gathering','analysis','deferred','retired'],'evidence_gathering'=>['analysis','review','revision_required','deferred','retired'],'analysis'=>['evidence_gathering','review','revision_required','deferred','retired'],'review'=>['revision_required','approved','rejected','deferred'],'revision_required'=>['evidence_gathering','analysis','review','deferred','retired'],'approved'=>['implemented','revision_required','retired'],'rejected'=>['revision_required','retired'],'deferred'=>['evidence_gathering','analysis','review','retired'],'implemented'=>['revision_required','retired'],'retired'=>[]]];
    }

    private function governance_template() {
        return ['governance_version'=>self::VERSION,'schema'=>'scds-decision-governance/1.0','current_state'=>'draft','decision_owner'=>['name'=>'','role'=>'','organization'=>'','accountable'=>true],'reviewers'=>[],'approval_conditions'=>[],'exceptions'=>[],'conflict_declarations'=>[],'signoffs'=>[],'review_history'=>[],'approval_expires_at'=>'','reassessment_due_at'=>'','transition_status'=>['allowed'=>true,'requested_state'=>'draft','blockers'=>[]],'export_gate'=>['internal_draft_allowed'=>true,'reviewed_export_allowed'=>false,'public_export_allowed'=>false,'professional_reliance_allowed'=>false,'blocking_reasons'=>[['code'=>'decision_not_approved','severity'=>'high','message'=>'Decision has not been approved by accountable human reviewers.']]],'warnings'=>['Decision Studio records governance actions but does not approve decisions autonomously.','AI may flag gaps or contradictions but cannot provide sign-off, certification, assurance, or regulated professional approval.']];
    }

    private function governance_status($item,$default='open') { return sanitize_key($item['status'] ?? $default); }

    private function governance_blockers($owner,$reviewers,$conditions,$exceptions,$conflicts,$signoffs) {
        $blockers=[];
        if (empty(trim(strval($owner['name'] ?? '')))) $blockers[]=['code'=>'missing_decision_owner','severity'=>'high','message'=>'An accountable decision owner is required before approval.'];
        foreach($conditions as $item) if (($item['required'] ?? true) && !in_array($this->governance_status($item,'pending'),['satisfied','waived'],true)) $blockers[]=['code'=>'unsatisfied_approval_condition','severity'=>sanitize_key($item['severity'] ?? 'high'),'record_id'=>$item['condition_id'] ?? '','message'=>$item['description'] ?? 'Required approval condition is not satisfied.'];
        foreach($exceptions as $item) if (!in_array($this->governance_status($item),['closed','resolved','accepted'],true) && in_array(sanitize_key($item['severity'] ?? 'medium'),['critical','high'],true)) $blockers[]=['code'=>'open_material_exception','severity'=>sanitize_key($item['severity'] ?? 'high'),'record_id'=>$item['exception_id'] ?? '','message'=>$item['description'] ?? 'A material exception remains open.'];
        foreach($conflicts as $item) { $declared=(bool)($item['declared'] ?? true); $mitigated=in_array($this->governance_status($item),['mitigated','resolved','recused'],true)||!empty(trim(strval($item['mitigation'] ?? ''))); if($declared&&!$mitigated) $blockers[]=['code'=>'unmitigated_conflict','severity'=>'high','record_id'=>$item['conflict_id'] ?? '','message'=>$item['description'] ?? 'A declared conflict has not been mitigated.']; }
        $reviewer_ok=false; foreach($reviewers as $r) if(in_array($this->governance_status($r,'assigned'),['approved','accepted','complete'],true)) $reviewer_ok=true;
        if(!$reviewer_ok) $blockers[]=['code'=>'missing_reviewer_approval','severity'=>'high','message'=>'At least one assigned human reviewer must complete review before approval.'];
        $roles=[]; foreach($signoffs as $s) if(in_array($this->governance_status($s,'signed'),['signed','approved','accepted'],true)) $roles[]=sanitize_key($s['role'] ?? '');
        if(!array_intersect(['decision_owner','accountable_owner'],$roles)) $blockers[]=['code'=>'missing_owner_signoff','severity'=>'high','message'=>'The accountable decision owner has not signed off.'];
        if(!array_intersect(['governance_reviewer','independent_reviewer','review_chair'],$roles)) $blockers[]=['code'=>'missing_governance_signoff','severity'=>'high','message'=>'An independent governance or review sign-off is required.'];
        return $blockers;
    }

    private function append_review_event($history,$event_type,$actor,$actor_role,$from,$to,$reason,$details=[]) {
        $history=is_array($history)?array_values($history):[]; $previous=$history?strval($history[count($history)-1]['event_hash'] ?? 'GENESIS'):'GENESIS';
        $event=['event_schema'=>'scds-review-event/1.0','sequence'=>count($history)+1,'recorded_at'=>gmdate('c'),'event_type'=>$event_type,'actor'=>$actor?:'unspecified-human-actor','actor_role'=>$actor_role?:'unspecified-role','from_state'=>$from,'to_state'=>$to,'reason'=>$reason,'details'=>$details,'previous_hash'=>$previous];
        $event['event_hash']='sha256:'.$this->canonical_hash($event); $history[]=$event; return $history;
    }

    private function verify_review_history($history) {
        $previous='GENESIS'; $problems=[]; foreach(array_values(is_array($history)?$history:[]) as $i=>$raw){ $item=is_array($raw)?$raw:[]; $supplied=strval($item['event_hash'] ?? ''); unset($item['event_hash']); if(strval($item['previous_hash'] ?? '')!==$previous)$problems[]=['sequence'=>$i+1,'code'=>'previous_hash_mismatch']; $expected='sha256:'.$this->canonical_hash($item); if($supplied!==$expected)$problems[]=['sequence'=>$i+1,'code'=>'event_hash_mismatch']; $previous=$supplied?:$expected; } return ['ok'=>empty($problems),'event_count'=>count(is_array($history)?$history:[]),'problems'=>$problems,'head_hash'=>$previous];
    }

    private function evaluate_governance_local($payload) {
        $packet=isset($payload['packet'])&&is_array($payload['packet'])?array_replace_recursive($this->decision_packet_template(),$payload['packet']):$this->decision_packet_template(); $existing=is_array($packet['governance_center'] ?? null)?$packet['governance_center']:[];
        $current=sanitize_key($payload['currentState'] ?? ($existing['current_state'] ?? 'draft')); $requested=sanitize_key($payload['requestedState'] ?? $current); $catalog=$this->governance_state_catalog(); $valid=array_column($catalog['states'],'id'); if(!in_array($current,$valid,true))$current='draft';
        $owner=is_array($payload['decisionOwner'] ?? null)?$payload['decisionOwner']:($existing['decision_owner'] ?? []); $reviewers=is_array($payload['reviewers'] ?? null)&&$payload['reviewers']?$payload['reviewers']:($existing['reviewers'] ?? []); $conditions=is_array($payload['approvalConditions'] ?? null)&&$payload['approvalConditions']?$payload['approvalConditions']:($existing['approval_conditions'] ?? []); $exceptions=is_array($payload['exceptions'] ?? null)&&$payload['exceptions']?$payload['exceptions']:($existing['exceptions'] ?? []); $conflicts=is_array($payload['conflictDeclarations'] ?? null)&&$payload['conflictDeclarations']?$payload['conflictDeclarations']:($existing['conflict_declarations'] ?? []); $signoffs=is_array($payload['signoffs'] ?? null)&&$payload['signoffs']?$payload['signoffs']:($existing['signoffs'] ?? []); $history=is_array($payload['reviewHistory'] ?? null)&&$payload['reviewHistory']?$payload['reviewHistory']:($existing['review_history'] ?? []);
        $transition=[]; if(!in_array($requested,$valid,true))$transition[]=['code'=>'unknown_state','severity'=>'high','message'=>'Unknown requested state: '.$requested]; elseif($requested!==$current&&!in_array($requested,$catalog['transitions'][$current]??[],true))$transition[]=['code'=>'invalid_transition','severity'=>'high','message'=>'Transition from '.$current.' to '.$requested.' is not allowed.']; $approval=$this->governance_blockers($owner,$reviewers,$conditions,$exceptions,$conflicts,$signoffs); if(in_array($requested,['approved','implemented'],true))$transition=array_merge($transition,$approval); $forced=!empty($payload['forceTransition']); $allowed=empty($transition)||$forced; $final=$allowed?$requested:$current;
        if($requested!==$current)$history=$this->append_review_event($history,$forced&&!empty($transition)?'state_transition_forced':'state_transition',sanitize_text_field($payload['actor']??''),sanitize_key($payload['actorRole']??''),$current,$final,sanitize_textarea_field($payload['reason']??''),['blockers_at_transition'=>$transition,'forced'=>$forced]); $integrity=$this->verify_review_history($history); $export=$approval; if(!in_array($final,['approved','implemented'],true))$export[]=['code'=>'decision_not_approved','severity'=>'high','message'=>'Reviewed or public export requires an approved or implemented decision state.']; if(!$integrity['ok'])$export[]=['code'=>'review_history_integrity_failed','severity'=>'critical','message'=>'The immutable review history hash chain did not verify.'];
        $confidential=false; foreach($exceptions as $item)if(!empty($item['confidential'])&&!in_array($this->governance_status($item),['closed','resolved'],true))$confidential=true;
        $governance=['governance_version'=>self::VERSION,'schema'=>'scds-decision-governance/1.0','current_state'=>$final,'decision_owner'=>$owner,'reviewers'=>$reviewers,'approval_conditions'=>$conditions,'exceptions'=>$exceptions,'conflict_declarations'=>$conflicts,'signoffs'=>$signoffs,'review_history'=>$history,'review_history_integrity'=>$integrity,'approval_expires_at'=>sanitize_text_field($payload['approvalExpiresAt']??($existing['approval_expires_at']??'')),'reassessment_due_at'=>sanitize_text_field($payload['reassessmentDueAt']??($existing['reassessment_due_at']??'')),'transition_status'=>['allowed'=>$allowed,'from_state'=>$current,'requested_state'=>$requested,'final_state'=>$final,'forced'=>$forced,'blockers'=>$transition],'export_gate'=>['internal_draft_allowed'=>$final!=='retired','reviewed_export_allowed'=>in_array($final,['approved','implemented'],true)&&empty($export),'public_export_allowed'=>in_array($final,['approved','implemented'],true)&&empty($export)&&!$confidential,'professional_reliance_allowed'=>false,'blocking_reasons'=>$export],'warnings'=>$this->governance_template()['warnings']];
        $packet['governance_center']=$governance; return ['ok'=>true,'version'=>self::VERSION,'governance'=>$governance,'decision_packet'=>$packet,'state_catalog'=>$catalog];
    }

    public function rest_governance_states(){ return rest_ensure_response(['ok'=>true,'version'=>self::VERSION]+$this->governance_state_catalog()); }
    public function rest_governance_template(){ return rest_ensure_response(['ok'=>true,'version'=>self::VERSION,'governance'=>$this->governance_template(),'state_catalog'=>$this->governance_state_catalog()]); }
    public function rest_governance_evaluate(WP_REST_Request $request){ $payload=$request->get_json_params(); if(!is_array($payload))$payload=[]; if($this->settings()['backend_enabled']==='1'&&!empty($this->settings()['backend_url'])){ $backend=$this->backend_request('/governance/evaluate',$payload); if(!is_wp_error($backend)&&is_array($backend))return rest_ensure_response($backend); } return rest_ensure_response($this->evaluate_governance_local($payload)); }
    public function rest_governance_history_verify(WP_REST_Request $request){ $payload=$request->get_json_params(); if(!is_array($payload))$payload=[]; return rest_ensure_response(['ok'=>true,'version'=>self::VERSION,'integrity'=>$this->verify_review_history($payload['reviewHistory']??[])]); }

    private function collaboration_role_permissions($role) {
        $map=['owner'=>['manage_room','manage_members','comment','request_change','resolve','snapshot','apply_revision','lock','share'],'facilitator'=>['manage_members','comment','request_change','resolve','snapshot','apply_revision','lock','share'],'editor'=>['comment','request_change','snapshot','apply_revision'],'reviewer'=>['comment','request_change','resolve','snapshot'],'client'=>['comment','request_change'],'observer'=>[]];
        $role=sanitize_key($role ?: 'observer'); return $map[$role] ?? [];
    }
    private function collaboration_room_template() { return ['room_version'=>self::VERSION,'schema'=>self::COLLABORATION_ROOM_SCHEMA,'event_schema'=>self::COLLABORATION_EVENT_SCHEMA,'room_id'=>'','title'=>'Collaborative Decision Room','visibility'=>'private','status'=>'active','owner'=>[],'members'=>[],'comments'=>[],'change_requests'=>[],'snapshots'=>[],'snapshot_comparisons'=>[],'activity_timeline'=>[],'notifications'=>[],'share_grants'=>[],'locked_version'=>[],'contact_engagement_handoffs'=>[],'canonical_persistence'=>'wordpress','warnings'=>['Private room access is controlled by WordPress authentication and capabilities.','AI cannot approve, sign, certify, or impersonate a human reviewer.','Approved versions remain locked until an authorized human explicitly reopens them with a reason.']]; }
    private function collaboration_hash($value){ return 'sha256:'.hash('sha256',wp_json_encode($value,JSON_UNESCAPED_SLASHES|JSON_UNESCAPED_UNICODE)); }
    private function collaboration_event(&$room,$type,$actor,$role,$target_type='room',$target_id='',$details=[]){ $events=is_array($room['activity_timeline']??null)?$room['activity_timeline']:[]; $previous=$events?($events[count($events)-1]['event_hash']??'GENESIS'):'GENESIS'; $event=['event_schema'=>self::COLLABORATION_EVENT_SCHEMA,'sequence'=>count($events)+1,'recorded_at'=>gmdate('c'),'event_type'=>$type,'actor'=>$actor,'actor_role'=>$role,'target_type'=>$target_type,'target_id'=>$target_id,'details'=>$details,'previous_hash'=>$previous]; $event['event_hash']=$this->collaboration_hash($event); $events[]=$event; $room['activity_timeline']=array_slice($events,-5000); }
    private function collaboration_notify(&$room,$actor,$event_type,$target_id,$message){ $items=is_array($room['notifications']??null)?$room['notifications']:[]; foreach((array)($room['members']??[]) as $member){$recipient=$member['email']??($member['user_id']??($member['name']??''));if(!$recipient||strval($recipient)===strval($actor))continue;$items[]=['notification_id'=>'notification-'.wp_generate_uuid4(),'created_at'=>gmdate('c'),'recipient'=>$recipient,'event_type'=>$event_type,'target_id'=>$target_id,'message'=>$message,'status'=>'pending'];} $room['notifications']=array_slice($items,-2000); }
    private function collaboration_snapshot($packet,$actor,$label='Decision Packet snapshot'){ $copy=$packet; if(isset($copy['collaboration_room']))$copy['collaboration_room']=['room_id'=>$copy['collaboration_room']['room_id']??'','schema'=>self::COLLABORATION_ROOM_SCHEMA,'locked_version'=>$copy['collaboration_room']['locked_version']??[]]; $hash=$this->collaboration_hash($copy); return ['snapshot_id'=>'snapshot-'.substr($hash,7,16).'-'.time(),'created_at'=>gmdate('c'),'created_by'=>$actor,'label'=>$label,'packet_version'=>$packet['packet_version']??self::VERSION,'governance_state'=>$packet['governance_center']['current_state']??'draft','content_hash'=>$hash,'packet'=>$copy,'locked'=>false]; }
    private function collaboration_diff($before,$after,$prefix=''){ $out=[]; if(is_array($before)&&is_array($after)){ foreach(array_unique(array_merge(array_keys($before),array_keys($after))) as $key){ $path=$prefix===''?$key:$prefix.'.'.$key; if(!array_key_exists($key,$before))$out[]=['path'=>$path,'change'=>'added','before'=>null,'after'=>$after[$key]]; elseif(!array_key_exists($key,$after))$out[]=['path'=>$path,'change'=>'removed','before'=>$before[$key],'after'=>null]; else $out=array_merge($out,$this->collaboration_diff($before[$key],$after[$key],$path)); if(count($out)>=1000)break; } } elseif($before!==$after)$out[]=['path'=>$prefix?:'$','change'=>'changed','before'=>$before,'after'=>$after]; return array_slice($out,0,1000); }
    private function collaboration_merge($target,$patch){ $target=is_array($target)?$target:[]; foreach((array)$patch as $key=>$value){ if(is_array($value)&&isset($target[$key])&&is_array($target[$key]))$target[$key]=$this->collaboration_merge($target[$key],$value);else $target[$key]=$value; } return $target; }
    private function verify_collaboration_history($events){ $previous='GENESIS';$problems=[];foreach(array_values(is_array($events)?$events:[]) as $i=>$raw){$item=is_array($raw)?$raw:[];$supplied=strval($item['event_hash']??'');unset($item['event_hash']);if(strval($item['previous_hash']??'')!==$previous)$problems[]=['sequence'=>$i+1,'code'=>'previous_hash_mismatch'];$expected=$this->collaboration_hash($item);if($supplied!==$expected)$problems[]=['sequence'=>$i+1,'code'=>'event_hash_mismatch'];$previous=$supplied?:$expected;}return ['ok'=>empty($problems),'event_count'=>count(is_array($events)?$events:[]),'problems'=>$problems,'head_hash'=>$previous]; }
    private function collaboration_action_local($payload){ $packet=is_array($payload['packet']??null)?array_replace_recursive($this->decision_packet_template(),$payload['packet']):$this->decision_packet_template(); $room=$this->collaboration_room_template(); if(is_array($payload['room']??null))$room=array_replace_recursive($room,$payload['room']); $actor=sanitize_text_field($payload['actor']??wp_get_current_user()->display_name); $role=sanitize_key($payload['actorRole']??'editor'); if(empty($room['owner'])&&$actor){$room['owner']=['name'=>$actor,'role'=>'owner'];if(empty($room['members']))$room['members'][]=['member_id'=>'member-'.wp_generate_uuid4(),'name'=>$actor,'email'=>'','user_id'=>get_current_user_id(),'role'=>'owner','status'=>'active'];} $action=sanitize_key(str_replace('-','_',$payload['action']??'evaluate')); $data=is_array($payload['payload']??null)?$payload['payload']:[]; $room['room_id']=$room['room_id']?:'room-'.wp_generate_uuid4(); $room['visibility']=in_array($room['visibility'],['private','restricted','institutional'],true)?$room['visibility']:'private'; $permissions=$this->collaboration_role_permissions($role); $deny=function($permission)use($permissions,$room,$packet,$role){ return in_array($permission,$permissions,true)?null:new WP_Error('scds_collaboration_permission_denied','The current room role cannot perform this action.',['status'=>403,'required_permission'=>$permission,'actor_role'=>$role,'room'=>$room,'decision_packet'=>$packet]); };
        $extra=[]; if($action==='add_comment'){ if($e=$deny('comment'))return $e; $content=sanitize_textarea_field($data['content']??''); if(!$content)return new WP_Error('scds_comment_required','Comment content is required.',['status'=>400]); $comment=['comment_id'=>'comment-'.wp_generate_uuid4(),'created_at'=>gmdate('c'),'author'=>$actor,'author_role'=>$role,'target_type'=>sanitize_key($payload['targetType']??'decision_packet'),'target_id'=>sanitize_text_field($payload['targetId']??''),'content'=>$content,'status'=>'open']; $room['comments'][]=$comment; $this->collaboration_event($room,'comment_added',$actor,$role,'comment',$comment['comment_id']);$this->collaboration_notify($room,$actor,'comment_added',$comment['comment_id'],'New Decision Room comment from '.$actor.'.'); $extra['comment']=$comment; }
        elseif($action==='resolve_comment'){ if($e=$deny('resolve'))return $e;$id=sanitize_text_field($data['comment_id']??($payload['targetId']??''));foreach($room['comments'] as &$item){if(($item['comment_id']??'')===$id){$item['status']='resolved';$item['resolved_at']=gmdate('c');$item['resolved_by']=$actor;$item['resolution']=sanitize_textarea_field($data['resolution']??($payload['reason']??''));$extra['comment']=$item;break;}}unset($item);if(empty($extra['comment']))return new WP_Error('scds_comment_not_found','Comment not found.',['status'=>404]);$this->collaboration_event($room,'comment_resolved',$actor,$role,'comment',$id,['resolution'=>$extra['comment']['resolution']??'']); }
        elseif($action==='create_change_request'){ if($e=$deny('request_change'))return $e; $cr=['change_request_id'=>'change-'.wp_generate_uuid4(),'created_at'=>gmdate('c'),'requested_by'=>$actor,'requested_by_role'=>$role,'title'=>sanitize_text_field($data['title']??'Requested Decision Packet change'),'description'=>sanitize_textarea_field($data['description']??''),'target_type'=>sanitize_key($payload['targetType']??'decision_packet'),'target_id'=>sanitize_text_field($payload['targetId']??''),'status'=>'open','packet_patch'=>is_array($data['packet_patch']??null)?$data['packet_patch']:[],'resolution'=>[]]; $room['change_requests'][]=$cr; $this->collaboration_event($room,'change_request_created',$actor,$role,'change_request',$cr['change_request_id']);$this->collaboration_notify($room,$actor,'change_request_created',$cr['change_request_id'],'New Decision Room change request: '.$cr['title'].'.'); $extra['change_request']=$cr; }
        elseif($action==='snapshot'||$action==='create_snapshot'){ if($e=$deny('snapshot'))return $e; $snapshot=$this->collaboration_snapshot($packet,$actor,sanitize_text_field($data['label']??'Decision Packet snapshot')); $room['snapshots'][]=$snapshot; $this->collaboration_event($room,'snapshot_created',$actor,$role,'snapshot',$snapshot['snapshot_id'],['content_hash'=>$snapshot['content_hash']]); $extra['snapshot']=$snapshot; }
        elseif($action==='compare_snapshots'){ $shots=$room['snapshots']??[]; if(count($shots)<2)return new WP_Error('scds_two_snapshots_required','Two snapshots are required.',['status'=>409]); $before=$shots[count($shots)-2];$after=$shots[count($shots)-1];$changes=$this->collaboration_diff($before['packet']??[],$after['packet']??[]);$comparison=['comparison_id'=>'comparison-'.wp_generate_uuid4(),'created_at'=>gmdate('c'),'before_snapshot_id'=>$before['snapshot_id']??'','after_snapshot_id'=>$after['snapshot_id']??'','before_hash'=>$before['content_hash']??'','after_hash'=>$after['content_hash']??'','change_count'=>count($changes),'changed_paths'=>array_column($changes,'path'),'changes'=>$changes];$room['snapshot_comparisons'][]=$comparison;$this->collaboration_event($room,'snapshots_compared',$actor,$role,'comparison',$comparison['comparison_id'],['change_count'=>count($changes)]);$extra['comparison']=$comparison; }
        elseif($action==='resolve_change_request'){ if($e=$deny('resolve'))return $e; $id=sanitize_text_field($data['change_request_id']??($payload['targetId']??''));$status=sanitize_key($data['status']??'accepted');if(!in_array($status,['accepted','rejected','deferred','implemented'],true))$status='accepted';foreach($room['change_requests'] as &$item){if(($item['change_request_id']??'')===$id){if($status==='implemented'&&!empty($room['locked_version']['locked']))return new WP_Error('scds_approved_version_locked','Approved version is locked.',['status'=>409]);$item['status']=$status;$item['resolved_at']=gmdate('c');$item['resolved_by']=$actor;$item['resolution']=['status'=>$status,'reason'=>sanitize_textarea_field($data['resolution']??($payload['reason']??''))];if($status==='implemented'&&!empty($item['packet_patch'])){$before=$this->collaboration_snapshot($packet,$actor,'Before implemented change request');$packet=$this->collaboration_merge($packet,$item['packet_patch']);$after=$this->collaboration_snapshot($packet,$actor,'After implemented change request');$room['snapshots'][]=$before;$room['snapshots'][]=$after;$changes=$this->collaboration_diff($before['packet'],$after['packet']);$comparison=['comparison_id'=>'comparison-'.wp_generate_uuid4(),'created_at'=>gmdate('c'),'before_snapshot_id'=>$before['snapshot_id'],'after_snapshot_id'=>$after['snapshot_id'],'before_hash'=>$before['content_hash'],'after_hash'=>$after['content_hash'],'change_count'=>count($changes),'changed_paths'=>array_column($changes,'path'),'changes'=>$changes];$room['snapshot_comparisons'][]=$comparison;$extra['comparison']=$comparison;}$extra['change_request']=$item;break;}}unset($item);if(empty($extra['change_request']))return new WP_Error('scds_change_request_not_found','Change request not found.',['status'=>404]);$this->collaboration_event($room,'change_request_resolved',$actor,$role,'change_request',$id,['status'=>$status]); }
        elseif($action==='apply_revision'){ if($e=$deny('apply_revision'))return $e;if(!empty($room['locked_version']['locked']))return new WP_Error('scds_approved_version_locked','Approved version is locked.',['status'=>409]);$patch=is_array($data['packet_patch']??null)?$data['packet_patch']:[];if(!$patch)return new WP_Error('scds_packet_patch_required','Packet patch is required.',['status'=>400]);$before=$this->collaboration_snapshot($packet,$actor,'Before revision');$packet=$this->collaboration_merge($packet,$patch);$after=$this->collaboration_snapshot($packet,$actor,'After revision');$room['snapshots'][]=$before;$room['snapshots'][]=$after;$changes=$this->collaboration_diff($before['packet'],$after['packet']);$comparison=['comparison_id'=>'comparison-'.wp_generate_uuid4(),'created_at'=>gmdate('c'),'before_snapshot_id'=>$before['snapshot_id'],'after_snapshot_id'=>$after['snapshot_id'],'before_hash'=>$before['content_hash'],'after_hash'=>$after['content_hash'],'change_count'=>count($changes),'changed_paths'=>array_column($changes,'path'),'changes'=>$changes];$room['snapshot_comparisons'][]=$comparison;$this->collaboration_event($room,'packet_revision_applied',$actor,$role,'comparison',$comparison['comparison_id'],['change_count'=>count($changes)]);$extra['comparison']=$comparison; }
        elseif($action==='invite_member'){ if($e=$deny('manage_members'))return $e;if(count($room['members']??[])>=200)return new WP_Error('scds_room_member_limit_reached','Decision Room member limit reached.',['status'=>409]);$member=is_array($data['member']??null)?$data['member']:$data;$token=wp_generate_password(32,false,false);$record=['member_id'=>'member-'.wp_generate_uuid4(),'user_id'=>intval($member['user_id']??0),'email'=>sanitize_email($member['email']??''),'name'=>sanitize_text_field($member['name']??'Invited participant'),'role'=>sanitize_key($member['role']??'observer'),'status'=>'invited','invited_at'=>gmdate('c'),'invited_by'=>$actor];$room['members'][]=$record;$grant=['grant_id'=>'grant-'.wp_generate_uuid4(),'member_id'=>$record['member_id'],'role'=>$record['role'],'status'=>'active','expires_at'=>sanitize_text_field($member['expires_at']??''),'token_hash'=>'sha256:'.hash('sha256',$token),'token_hint'=>substr($token,0,4).'…'.substr($token,-4)];$room['share_grants'][]=$grant;$this->collaboration_event($room,'member_invited',$actor,$role,'member',$record['member_id'],['role'=>$record['role']]);$extra['member']=$record;$extra['share_grant']=$grant;$extra['share_token_once']=$token; }
        elseif($action==='lock_version'){ if($e=$deny('lock'))return $e;$state=sanitize_key($packet['governance_center']['current_state']??'draft');if(!in_array($state,['approved','implemented'],true))return new WP_Error('scds_governance_approval_required','Governance approval is required before locking a version.',['status'=>409,'governance_state'=>$state]);$snapshot=$this->collaboration_snapshot($packet,$actor,sanitize_text_field($data['label']??'Approved Decision Packet'));$snapshot['locked']=true;$room['snapshots'][]=$snapshot;$room['locked_version']=['locked'=>true,'snapshot_id'=>$snapshot['snapshot_id'],'content_hash'=>$snapshot['content_hash'],'locked_at'=>gmdate('c'),'locked_by'=>$actor,'governance_state'=>$state];$room['status']='locked';$this->collaboration_event($room,'approved_version_locked',$actor,$role,'snapshot',$snapshot['snapshot_id'],['content_hash'=>$snapshot['content_hash']]);$extra['snapshot']=$snapshot; }
        elseif($action==='reopen_version'){ if($e=$deny('lock'))return $e;$reason=sanitize_textarea_field($payload['reason']??($data['reason']??''));if(!$reason)return new WP_Error('scds_reopen_reason_required','A reopen reason is required.',['status'=>400]);$previous=$room['locked_version']??[];$room['locked_version']=['locked'=>false,'reopened_at'=>gmdate('c'),'reopened_by'=>$actor,'reason'=>$reason,'previous_lock'=>$previous];$room['status']='active';$this->collaboration_event($room,'approved_version_reopened',$actor,$role,'room',$room['room_id'],['reason'=>$reason]); }
        elseif($action==='contact_handoff'){ if($e=$deny('share'))return $e; $handoff=['schema'=>'sc-contact-engagement-handoff/1.0','handoff_id'=>'engagement-'.wp_generate_uuid4(),'created_at'=>gmdate('c'),'source_product'=>'decision-studio','source_version'=>self::VERSION,'decision_room_id'=>$room['room_id'],'project_name'=>$packet['project']['project_name']??'','decision_question'=>$packet['project']['decision_question']??'','participants'=>$room['members']??[],'collaboration_needs'=>$data['collaboration_needs']??[],'private_workspace_required'=>true,'requested_next_action'=>sanitize_text_field($data['requested_next_action']??'Create or connect a private engagement workspace.'),'notes'=>sanitize_textarea_field($data['notes']??'')];$room['contact_engagement_handoffs'][]=$handoff;$this->collaboration_event($room,'contact_engagement_handoff_created',$actor,$role,'handoff',$handoff['handoff_id']);$extra['contact_engagement_handoff']=$handoff; }
        $room['activity_integrity']=$this->verify_collaboration_history($room['activity_timeline']??[]); $room['metrics']=['member_count'=>count($room['members']??[]),'open_comment_count'=>count(array_filter($room['comments']??[],fn($i)=>($i['status']??'open')==='open')),'open_change_request_count'=>count(array_filter($room['change_requests']??[],fn($i)=>($i['status']??'open')==='open')),'snapshot_count'=>count($room['snapshots']??[]),'pending_notification_count'=>count(array_filter($room['notifications']??[],fn($i)=>($i['status']??'pending')==='pending'))]; $packet['packet_version']=self::VERSION;$packet['collaboration_room_schema']=self::COLLABORATION_ROOM_SCHEMA;$packet['collaboration_event_schema']=self::COLLABORATION_EVENT_SCHEMA;$packet['collaboration_room']=$room; return ['ok'=>true,'version'=>self::VERSION,'schema'=>self::COLLABORATION_ROOM_SCHEMA,'room'=>$room,'decision_packet'=>$packet,'actor_permissions'=>$permissions]+$extra; }
    public function rest_collaboration_template(){ return rest_ensure_response(['ok'=>true,'version'=>self::VERSION,'room'=>$this->collaboration_room_template(),'decision_packet'=>$this->decision_packet_template()]); }
    public function rest_collaboration_action(WP_REST_Request $request){ $payload=$request->get_json_params();if(!is_array($payload))$payload=[];if($this->settings()['backend_enabled']==='1'&&!empty($this->settings()['backend_url'])){$backend=$this->backend_request('/collaboration/action',$payload);if(!is_wp_error($backend)&&is_array($backend))return rest_ensure_response($backend);} $local=$this->collaboration_action_local($payload);return is_wp_error($local)?$local:rest_ensure_response($local); }
    private function sync_room_relations($room_id,$room){ global $wpdb;$members=$wpdb->prefix.self::ROOM_MEMBERS_TABLE;$events=$wpdb->prefix.self::ROOM_EVENTS_TABLE;$wpdb->delete($members,['room_id'=>intval($room_id)],['%d']);foreach(array_slice(is_array($room['members']??null)?$room['members']:[],0,200) as $member){$uid=intval($member['user_id']??0);if(!$uid&&!empty($member['email'])){$user=get_user_by('email',sanitize_email($member['email']));if($user)$uid=intval($user->ID);}$wpdb->insert($members,['room_id'=>intval($room_id),'user_id'=>$uid,'email'=>sanitize_email($member['email']??''),'display_name'=>sanitize_text_field($member['name']??''),'role'=>sanitize_key($member['role']??'observer'),'status'=>sanitize_key($member['status']??'invited'),'invited_by'=>get_current_user_id(),'invited_at'=>current_time('mysql')]);}$wpdb->delete($events,['room_id'=>intval($room_id)],['%d']);foreach(array_slice(is_array($room['activity_timeline']??null)?$room['activity_timeline']:[],-5000) as $event){$wpdb->insert($events,['room_id'=>intval($room_id),'event_type'=>sanitize_key($event['event_type']??'room_event'),'actor_user_id'=>get_current_user_id(),'actor_name'=>sanitize_text_field($event['actor']??''),'target_type'=>sanitize_key($event['target_type']??'room'),'target_id'=>sanitize_text_field($event['target_id']??''),'event_json'=>wp_json_encode($event),'created_at'=>current_time('mysql')]);} }
    private function room_row_allowed($row){ if(current_user_can('manage_options'))return true;$uid=get_current_user_id();if(intval($row['owner_user_id']??0)===$uid)return true;global $wpdb;$members=$wpdb->prefix.self::ROOM_MEMBERS_TABLE;return (bool)$wpdb->get_var($wpdb->prepare("SELECT id FROM $members WHERE room_id=%d AND user_id=%d AND status IN ('active','accepted','invited') LIMIT 1",intval($row['id']),$uid)); }
    public function rest_save_room(WP_REST_Request $request){ global $wpdb;$payload=$request->get_json_params();if(!is_array($payload))$payload=[];$result=$this->collaboration_action_local($payload+['action'=>$payload['action']??'evaluate']);if(is_wp_error($result))return $result;$room=$result['room'];$packet=$result['decision_packet'];$table=$wpdb->prefix.self::ROOMS_TABLE;$uuid=sanitize_text_field($room['room_id']);$existing=$wpdb->get_row($wpdb->prepare("SELECT * FROM $table WHERE room_uuid=%s",$uuid),ARRAY_A);$data=['room_uuid'=>$uuid,'project_id'=>intval($payload['project_id']??0),'title'=>sanitize_text_field($room['title']??'Collaborative Decision Room'),'visibility'=>sanitize_key($room['visibility']??'private'),'status'=>sanitize_key($room['status']??'active'),'owner_user_id'=>get_current_user_id(),'room_json'=>wp_json_encode($room),'packet_json'=>wp_json_encode($packet),'locked_version_hash'=>sanitize_text_field($room['locked_version']['content_hash']??''),'updated_at'=>current_time('mysql')];if($existing){if(!$this->room_row_allowed($existing))return new WP_Error('scds_room_forbidden','You cannot update this room.',['status'=>403]);$wpdb->update($table,$data,['id'=>intval($existing['id'])]);$id=intval($existing['id']);}else{$wpdb->insert($table,$data);$id=intval($wpdb->insert_id);}$this->sync_room_relations($id,$room);return rest_ensure_response(['ok'=>true,'version'=>self::VERSION,'id'=>$id,'room'=>$room,'decision_packet'=>$packet]); }
    public function rest_list_rooms(){ global $wpdb;$table=$wpdb->prefix.self::ROOMS_TABLE;$uid=get_current_user_id();if(current_user_can('manage_options'))$rows=$wpdb->get_results("SELECT id,room_uuid,title,visibility,status,owner_user_id,created_at,updated_at FROM $table ORDER BY id DESC LIMIT 100",ARRAY_A);else{$members=$wpdb->prefix.self::ROOM_MEMBERS_TABLE;$rows=$wpdb->get_results($wpdb->prepare("SELECT DISTINCT r.id,r.room_uuid,r.title,r.visibility,r.status,r.owner_user_id,r.created_at,r.updated_at FROM $table r LEFT JOIN $members m ON m.room_id=r.id WHERE r.owner_user_id=%d OR m.user_id=%d ORDER BY r.id DESC LIMIT 100",$uid,$uid),ARRAY_A);}return rest_ensure_response(['ok'=>true,'version'=>self::VERSION,'rooms'=>$rows?:[]]); }
    public function rest_get_room(WP_REST_Request $request){ global $wpdb;$table=$wpdb->prefix.self::ROOMS_TABLE;$row=$wpdb->get_row($wpdb->prepare("SELECT * FROM $table WHERE id=%d",intval($request['id'])),ARRAY_A);if(!$row)return new WP_Error('not_found','Decision Room not found.',['status'=>404]);if(!$this->room_row_allowed($row))return new WP_Error('scds_room_forbidden','You cannot access this room.',['status'=>403]);$row['room_json']=json_decode($row['room_json'],true);$row['packet_json']=json_decode($row['packet_json'],true);return rest_ensure_response(['ok'=>true,'version'=>self::VERSION,'room_record'=>$row]); }
    public function rest_room_action(WP_REST_Request $request){ $loaded=$this->rest_get_room($request);if(is_wp_error($loaded))return $loaded;$record=$loaded->get_data()['room_record'];$payload=$request->get_json_params();if(!is_array($payload))$payload=[];$payload['room']=$record['room_json'];$payload['packet']=$record['packet_json'];$result=$this->collaboration_action_local($payload);if(is_wp_error($result))return $result;global $wpdb;$table=$wpdb->prefix.self::ROOMS_TABLE;$wpdb->update($table,['room_json'=>wp_json_encode($result['room']),'packet_json'=>wp_json_encode($result['decision_packet']),'locked_version_hash'=>sanitize_text_field($result['room']['locked_version']['content_hash']??''),'status'=>sanitize_key($result['room']['status']??'active'),'updated_at'=>current_time('mysql')],['id'=>intval($request['id'])]);$this->sync_room_relations(intval($request['id']),$result['room']);return rest_ensure_response($result+['id'=>intval($request['id'])]); }
    public function rest_delete_room(WP_REST_Request $request){ global $wpdb;$table=$wpdb->prefix.self::ROOMS_TABLE;$row=$wpdb->get_row($wpdb->prepare("SELECT * FROM $table WHERE id=%d",intval($request['id'])),ARRAY_A);if(!$row||!$this->room_row_allowed($row))return new WP_Error('scds_room_forbidden','You cannot delete this room.',['status'=>403]);$wpdb->delete($table,['id'=>intval($request['id'])]);return rest_ensure_response(['ok'=>true,'version'=>self::VERSION,'deleted_id'=>intval($request['id'])]); }

    private function decision_packet_template() {
        return [
            'packet_version'=>'1.11.0','artifact_schema'=>'scds-platform-artifact/1.0','evidence_record_schema'=>'scds-evidence-record/1.0',
            'governance_schema'=>'scds-decision-governance/1.0',
            'review_event_schema'=>'scds-review-event/1.0','scenario_studio_schema'=>'scds-scenario-studio/1.0','collaboration_room_schema'=>self::COLLABORATION_ROOM_SCHEMA,'collaboration_event_schema'=>self::COLLABORATION_EVENT_SCHEMA,'governance_schema'=>'scds-decision-governance/1.0',
            'workflow'=>'Knowledge Library → Research Librarian → Site Intelligence → Workbench → Research Lab → Platform Core → Decision Studio',
            'project'=>['project_name'=>'','organization_type'=>'','sector'=>'','location'=>'','time_horizon'=>'','decision_question'=>''],
            'decision_framing'=>[],'evidence_registry'=>[],'citations'=>[],'quotations'=>[],'research_routes'=>[],'evidence_gaps'=>[],'follow_up_questions'=>[],'live_evidence'=>[],'methodologies'=>[],'experimental_evidence'=>[],'datasets'=>[],'technical_artifacts'=>[],'platform_registry'=>[],'entities'=>[],'evidence_ledger'=>[],'provenance_links'=>[],'platform_handoffs'=>[],'integrity_checks'=>[],
            'framing'=>[],'evidence_records'=>[],'scenario_analysis'=>[],'impact_records'=>[],'claim_reviews'=>[],'finance_analysis'=>[],'execution_recovery'=>[],'synthesis'=>[],'scenario_comparison'=>[],'scenario_studio'=>[],'sensitivity_analysis'=>[],'threshold_analysis'=>[],'uncertainty_analysis'=>[],'workbench_handoffs'=>[],'four_pillar_scores'=>[],'assumptions'=>[],'risks'=>[],'sources'=>[],'audit_trail'=>[],'calculation_trace'=>[],'workbench_calculations'=>[],'audit_and_provenance'=>$this->audit_provenance_template(),'governance_center'=>$this->governance_template(),'collaboration_room'=>$this->collaboration_room_template(),
            'module_slots'=>array_map(function($m){ return ['module_id'=>$m['id'],'name'=>$m['name'],'artifact_key'=>$m['artifact_key'],'packet_section'=>$m['packet_section'],'status'=>'empty']; }, $this->module_integrations()),
        ];
    }


    private function audit_provenance_template() {
        return [
            'audit_version'=>'1.11.0',
            'decision_packet_id'=>'SCDS-DRAFT',
            'review_status'=>[
                'status'=>'draft',
                'prepared_by'=>'',
                'reviewed_by'=>'',
                'required_reviews'=>['data/source review','finance assumptions review','risk and claims review','professional review where regulated or safety-critical'],
                'open_questions'=>[],
            ],
            'module_artifact_ledger'=>[],
            'source_ledger'=>[],
            'assumptions_register'=>[],
            'calculation_trace'=>[],
            'claim_trace'=>[],
            'change_log'=>[],
            'warnings'=>['Educational decision support only; not certification, assurance, legal, financial, engineering, medical, tax, compliance, or investment advice.'],
        ];
    }

    private function generate_audit_provenance($inputs, $results, $payload=[]) {
        $modules = $this->module_integrations();
        $packet = isset($payload['packet']) && is_array($payload['packet']) ? $payload['packet'] : [];
        $artifacts = isset($payload['moduleArtifacts']) && is_array($payload['moduleArtifacts']) ? $payload['moduleArtifacts'] : [];
        $ledger = [];
        foreach ($modules as $m) {
            $key = $m['artifact_key'];
            $present = !empty($artifacts[$key]) || !empty($packet[$key]);
            $ledger[] = ['module_id'=>$m['id'],'module_name'=>$m['name'],'artifact_key'=>$key,'status'=>$present?'attached':'missing','used_in_brief'=>$m['feeds'] ?? $m['summary']];
        }
        $source_ledger = [[
            'source_title'=>'User-provided Decision Studio inputs',
            'source_type'=>'manual input',
            'confidence'=>$inputs['dataConfidence'] ?? 70,
            'used_for'=>'baseline calculations, scoring, finance, and risk screen',
            'method_notes'=>'Replace or supplement with Catalyst Data records before relying on the brief.',
        ]];
        $assumptions = [
            ['assumption'=>'Baseline emissions','value'=>$inputs['baselineEmissions'] ?? 1200,'unit'=>'tCO2e/year','module_or_source'=>'Decision Studio input','used_in'=>'emissions calculation','sensitivity'=>'high','review_status'=>'needs verification'],
            ['assumption'=>'Reduction rate','value'=>$inputs['reductionRate'] ?? 32,'unit'=>'%','module_or_source'=>'Decision Studio input','used_in'=>'emissions calculation','sensitivity'=>'high','review_status'=>'needs verification'],
            ['assumption'=>'Adoption rate','value'=>$inputs['adoptionRate'] ?? 65,'unit'=>'%','module_or_source'=>'Decision Studio input','used_in'=>'emissions and scenarios','sensitivity'=>'high','review_status'=>'needs verification'],
            ['assumption'=>'CAPEX','value'=>$inputs['capex'] ?? 950000,'unit'=>'currency','module_or_source'=>'Decision Studio / Catalyst Finance','used_in'=>'NPV, ROI, payback','sensitivity'=>'high','review_status'=>'needs finance review'],
            ['assumption'=>'Annual savings','value'=>$inputs['annualSavings'] ?? 185000,'unit'=>'currency/year','module_or_source'=>'Decision Studio / Catalyst Finance','used_in'=>'NPV, ROI, payback','sensitivity'=>'high','review_status'=>'needs finance review'],
            ['assumption'=>'Discount rate','value'=>$inputs['discountRate'] ?? 7,'unit'=>'%','module_or_source'=>'Decision Studio / Catalyst Finance','used_in'=>'NPV','sensitivity'=>'medium','review_status'=>'needs finance review'],
            ['assumption'=>'Model years','value'=>$inputs['modelYears'] ?? 5,'unit'=>'years','module_or_source'=>'Decision Studio input','used_in'=>'NPV and total emissions','sensitivity'=>'medium','review_status'=>'needs review'],
        ];
        $calcs = [
            ['calculation'=>'Annual avoided emissions','formula'=>'baseline_emissions × reduction_rate × adoption_rate','result'=>$results['emissions']['annual_avoided_tco2e'] ?? null,'unit'=>'tCO2e/year','validation_status'=>'requires source review'],
            ['calculation'=>'Total avoided emissions','formula'=>'annual_avoided × model_years','result'=>$results['emissions']['total_avoided_tco2e'] ?? null,'unit'=>'tCO2e','validation_status'=>'requires boundary review'],
            ['calculation'=>'NPV','formula'=>'-capex + Σ annual_savings/(1+r)^t','result'=>$results['finance']['npv'] ?? null,'unit'=>'currency','validation_status'=>'requires finance review'],
            ['calculation'=>'ROI','formula'=>'((annual_savings × years - capex) / capex) × 100','result'=>$results['finance']['roi_percent'] ?? null,'unit'=>'%','validation_status'=>'requires finance review'],
            ['calculation'=>'Four-pillar weighted score','formula'=>'weighted average of E/S/E/G scores','result'=>$results['scores']['weighted'] ?? null,'unit'=>'0-100 score','validation_status'=>'decision-support screen only'],
            ['calculation'=>'Risk score','formula'=>'risk screen from exposure, vulnerability, stakeholder sensitivity, resilience, and governance readiness','result'=>$results['risk']['risk_score'] ?? null,'unit'=>'0-100 score','validation_status'=>'decision-support screen only'],
        ];
        $claim_trace = [[
            'claim'=>'The current decision can proceed under the reported posture.',
            'evidence_strength'=>'screening-level only',
            'uncertainty'=>'medium to high until module artifacts are imported',
            'source_basis'=>'Decision Studio inputs and deterministic model',
            'review_status'=>'needs Narrative Risk review',
        ]];
        $audit = $this->audit_provenance_template();
        $audit['review_status']['status'] = sanitize_text_field($payload['reviewStatus'] ?? 'draft');
        $audit['review_status']['open_questions'] = ['Which imported artifacts are missing or incomplete?','Which assumptions have high sensitivity?','Which sources require verification?','Which professional reviews are required before action?'];
        $audit['module_artifact_ledger'] = $ledger;
        $audit['source_ledger'] = $source_ledger;
        $audit['assumptions_register'] = $assumptions;
        $audit['calculation_trace'] = $calcs;
        $audit['claim_trace'] = $claim_trace;
        $audit['change_log'] = [['event'=>'Audit generated','detail'=>'Audit appendix generated from current Decision Studio inputs and artifacts.','version'=>self::VERSION]];
        $attached = 0; foreach ($ledger as $row) if ($row['status']==='attached') $attached++;
        return ['ok'=>true,'version'=>self::VERSION,'audit'=>$audit,'audit_summary'=>['module_artifact_completeness_percent'=>round(100*$attached/max(1,count($ledger)),1),'sources_count'=>count($source_ledger),'assumptions_count'=>count($assumptions),'calculation_trace_count'=>count($calcs),'claim_trace_count'=>count($claim_trace),'review_status'=>$audit['review_status']['status'],'high_priority_reviews'=>['Verify source records and data confidence.','Review high-sensitivity financial assumptions.','Attach Narrative Risk claim review before external use.','Use professional review for regulated or safety-critical decisions.']]];
    }


    private function records_from_packet($packet, $section, $legacy='') {
        if (isset($packet[$section]) && is_array($packet[$section])) {
            if (isset($packet[$section]['records']) && is_array($packet[$section]['records'])) return $packet[$section]['records'];
            if (array_keys($packet[$section]) === range(0, count($packet[$section])-1)) return $packet[$section];
        }
        if ($legacy && isset($packet[$legacy]) && is_array($packet[$legacy])) {
            if (array_keys($packet[$legacy]) === range(0, count($packet[$legacy])-1)) return $packet[$legacy];
            return [$packet[$legacy]];
        }
        return [];
    }

    private function text_or_default($value, $default='Not specified') {
        if ($value === null || $value === '' || $value === [] || $value === false) return $default;
        if (is_array($value)) {
            foreach (['name','title','label','summary','description','value'] as $k) if (isset($value[$k]) && $value[$k] !== '') return sanitize_text_field(strval($value[$k]));
            return substr(wp_json_encode($value), 0, 220);
        }
        return sanitize_text_field(strval($value));
    }

    private function brief_num($value, $suffix='') {
        if (is_numeric($value)) return rtrim(rtrim(number_format((float)$value, abs((float)$value) >= 1000 ? 0 : 1), '0'), '.') . $suffix;
        return $this->text_or_default($value, 'n/a');
    }

    private function brief_money($value) { return is_numeric($value) ? '$' . number_format((float)$value, 0) : $this->text_or_default($value, 'n/a'); }


    private function review_status_catalog() { return ['review_version'=>self::VERSION,'states'=>[['id'=>'not_started','label'=>'Not started'],['id'=>'needs_evidence','label'=>'Needs evidence'],['id'=>'needs_review','label'=>'Needs review'],['id'=>'needs_expert_review','label'=>'Needs expert review'],['id'=>'ready_for_draft','label'=>'Ready for draft'],['id'=>'ready_for_export','label'=>'Ready for export']],'export_gate'=>['draft_minimum'=>50,'reviewed_export_minimum'=>75,'professional_reliance'=>'Requires qualified human review regardless of score.']]; }
    private function readiness_sections() { return [['id'=>'framing','label'=>'Problem Framing','module_id'=>'catalyst-canvas','weight'=>10,'required'=>true,'expert_review'=>false],['id'=>'evidence','label'=>'Evidence & Measurement','module_id'=>'catalyst-data','weight'=>16,'required'=>true,'expert_review'=>false],['id'=>'scenarios','label'=>'Scenario Analysis','module_id'=>'catalyst-analytics-r','weight'=>10,'required'=>false,'expert_review'=>false],['id'=>'impact','label'=>'Impact Measurement','module_id'=>'global-impact-catalyst','weight'=>12,'required'=>true,'expert_review'=>false],['id'=>'claims','label'=>'Claim & Narrative Risk','module_id'=>'catalyst-narrative-risk','weight'=>12,'required'=>true,'expert_review'=>true],['id'=>'finance','label'=>'Financial Tradeoffs','module_id'=>'catalyst-finance','weight'=>14,'required'=>true,'expert_review'=>true],['id'=>'recovery','label'=>'Execution & Recovery','module_id'=>'catalyst-grit','weight'=>8,'required'=>false,'expert_review'=>false],['id'=>'audit','label'=>'Audit & Provenance','module_id'=>'audit','weight'=>10,'required'=>true,'expert_review'=>false],['id'=>'synthesis','label'=>'Integrated Brief','module_id'=>'decision-studio','weight'=>8,'required'=>true,'expert_review'=>false]]; }
    private function section_value($packet, $sid, $results=[], $audit=[]) { if($sid==='framing') return $packet['decision_framing'] ?? ($packet['framing'] ?? ($packet['project']['decision_question'] ?? null)); if($sid==='evidence') return $packet['evidence_and_measurement']['records'] ?? ($packet['evidence_records'] ?? ($packet['sources'] ?? ($audit['source_ledger'] ?? []))); if($sid==='scenarios') return $packet['scenarios']['records'] ?? ($packet['scenario_analysis'] ?? ($results['scenarios'] ?? [])); if($sid==='impact') return $packet['impact_measurement']['records'] ?? ($packet['impact_records'] ?? []); if($sid==='claims') return $packet['claim_and_risk_review']['records'] ?? ($packet['claim_reviews'] ?? ($audit['claim_trace'] ?? [])); if($sid==='finance') return $packet['financial_tradeoffs'] ?? ($packet['finance_analysis'] ?? ($results['finance'] ?? [])); if($sid==='recovery') return $packet['execution_and_recovery'] ?? ($packet['execution_recovery'] ?? []); if($sid==='audit') return $packet['audit_and_provenance'] ?? ($audit ?: ($packet['audit_trail'] ?? [])); if($sid==='synthesis') return $packet['integrated_decision_brief'] ?? ($results['scores'] ?? ($results['status'] ?? null)); return null; }
    private function section_present($v) { return !($v===null || $v==='' || $v===[] || $v===new stdClass()); }
    private function review_state($score, $flags, $required, $expert) { $critical=false; $high=false; foreach($flags as $f){ if(($f['severity']??'')==='critical')$critical=true; if(($f['severity']??'')==='high')$high=true; } if($score<=0)return 'not_started'; if($critical||($required&&$score<40))return 'needs_evidence'; if($expert&&($high||$score<90))return 'needs_expert_review'; if($score<70||$high)return 'needs_review'; if($score<90)return 'ready_for_draft'; return 'ready_for_export'; }
    private function generate_brief_readiness($inputs, $results, $packet=[], $audit=[]) {
        if(!$packet) $packet = $this->decision_packet_template();
        if(!$audit) $audit = $this->generate_audit_provenance($inputs, $results, ['packet'=>$packet])['audit'];
        $source_count = count(is_array($packet['sources'] ?? null)?$packet['sources']:[]) + count(is_array($audit['source_ledger'] ?? null)?$audit['source_ledger']:[]);
        $assumption_count = count(is_array($packet['assumptions'] ?? null)?$packet['assumptions']:[]);
        $calculation_count = count(is_array($packet['calculation_trace'] ?? null)?$packet['calculation_trace']:[]);
        $slots = is_array($packet['module_slots'] ?? null)?$packet['module_slots']:[]; $attached=[]; foreach($slots as $m){ if(is_array($m)&&($m['status']??'')==='attached') $attached[$m['module_id']??'']=true; }
        $sections=[]; $issues=[]; $total=0; $weighted=0;
        foreach($this->readiness_sections() as $sec){ $sid=$sec['id']; $value=$this->section_value($packet,$sid,$results,$audit); $present=$this->section_present($value); $score=$present?55:0; $flags=[]; if(isset($attached[$sec['module_id']]))$score+=20;
            if($sid==='framing'){ if(!empty($inputs['decisionQuestion']))$score+=20; }
            elseif($sid==='evidence'){ if($source_count>0)$score+=min(25,$source_count*8); else $flags[]=['severity'=>'critical','section'=>$sid,'issue'=>'No source or evidence records are attached.','action'=>'Import Catalyst Data records or add source ledger entries.']; if(floatval($inputs['dataConfidence']??70)<60)$flags[]=['severity'=>'high','section'=>$sid,'issue'=>'Data confidence is below 60.','action'=>'Document source quality, method notes, and review status.']; }
            elseif($sid==='scenarios'){ if($present)$score+=25; else {$score=35; $flags[]=['severity'=>'medium','section'=>$sid,'issue'=>'No imported scenario artifact is attached.','action'=>'Import Catalyst Analytics R or use built-in scenarios as a draft.'];} }
            elseif($sid==='impact'){ if($present)$score+=25; else $flags[]=['severity'=>'high','section'=>$sid,'issue'=>'Impact record is missing.','action'=>'Import Global Impact Catalyst.']; }
            elseif($sid==='claims'){ if($present)$score+=20; else $flags[]=['severity'=>'high','section'=>$sid,'issue'=>'Claim review is missing.','action'=>'Import Narrative Risk before publishing claims.']; }
            elseif($sid==='finance'){ if($present)$score+=15; if(floatval($inputs['capex']??0)>0&&floatval($inputs['annualSavings']??0)>0)$score+=15; else $flags[]=['severity'=>'high','section'=>$sid,'issue'=>'Finance assumptions are incomplete.','action'=>'Enter CAPEX and annual savings or import Catalyst Finance.']; if(!$assumption_count)$flags[]=['severity'=>'medium','section'=>$sid,'issue'=>'No imported assumptions register is attached.','action'=>'Generate audit/provenance before final export.']; }
            elseif($sid==='recovery'){ if($present)$score+=30; else {$score=35; $flags[]=['severity'=>'medium','section'=>$sid,'issue'=>'Execution/recovery artifact is missing.','action'=>'Import Catalyst Grit.'];} }
            elseif($sid==='audit'){ if($present)$score+=20; if($source_count)$score+=15; if($assumption_count||!empty($audit['assumptions_register']))$score+=15; if($calculation_count||!empty($audit['calculation_trace']))$score+=15; if(!$source_count)$flags[]=['severity'=>'critical','section'=>$sid,'issue'=>'Audit source ledger is incomplete.','action'=>'Generate audit/provenance after importing evidence.']; }
            elseif($sid==='synthesis'){ if(!empty($results['scores']))$score+=25; if(!empty($results['risk']))$score+=15; if(!empty($results['finance']))$score+=10; if(!empty($results['emissions']))$score+=10; }
            $score=max(0,min(100,$score)); foreach($flags as $f)$issues[]=$f; $state=$this->review_state($score,$flags,$sec['required'],$sec['expert_review']); $sections[]=['id'=>$sid,'label'=>$sec['label'],'module_id'=>$sec['module_id'],'required'=>$sec['required'],'expert_review'=>$sec['expert_review'],'score'=>round($score,1),'review_state'=>$state,'status_label'=>ucwords(str_replace('_',' ',$state)),'present'=>$present,'flags'=>$flags]; $total+=$sec['weight']; $weighted+=$sec['weight']*$score; }
        $readiness=round($weighted/max(1,$total),1); $critical=0; $high=0; foreach($issues as $i){ if(($i['severity']??'')==='critical')$critical++; if(($i['severity']??'')==='high')$high++; } $expert=0; $required_block=false; foreach($sections as $s){ if($s['review_state']==='needs_expert_review')$expert++; if($s['required'] && in_array($s['review_state'],['not_started','needs_evidence'],true))$required_block=true; }
        $overall = ($critical||$required_block)?'needs_evidence':($expert?'needs_expert_review':($readiness>=85&&$high===0?'ready_for_export':($readiness>=65?'ready_for_draft':'needs_review')));
        $next=[]; foreach(array_slice($issues,0,8) as $i)$next[]=$i['action']??($i['issue']??'Review unresolved issue.'); if(!$next)$next=['Generate the integrated brief, export the audit appendix, and complete applicable expert reviews.'];
        $readiness_obj=['ok'=>true,'version'=>self::VERSION,'readiness_version'=>self::VERSION,'readiness_percent'=>$readiness,'overall_review_state'=>$overall,'overall_status_label'=>ucwords(str_replace('_',' ',$overall)),'sections'=>$sections,'unresolved_issues'=>$issues,'counts'=>['sources'=>$source_count,'assumptions'=>$assumption_count,'calculations'=>$calculation_count,'critical_issues'=>$critical,'high_issues'=>$high,'sections_ready_for_export'=>count(array_filter($sections,function($s){return $s['review_state']==='ready_for_export';})),'sections_needing_expert_review'=>$expert],'export_gate'=>['draft_brief_allowed'=>$readiness>=50,'reviewed_export_allowed'=>$readiness>=75&&$critical===0&&!$required_block,'professional_reliance_allowed'=>false,'blocking_issues'=>array_values(array_filter($issues,function($i){return in_array($i['severity']??'',['critical','high'],true);} ))],'required_reviews'=>['Data/source review','Finance assumptions review','Narrative/claim risk review','Professional review for regulated, safety-critical, financial, legal, engineering, medical, tax, compliance, assurance, or certification use'],'next_actions'=>array_values(array_unique($next)),'warnings'=>['Brief readiness is a workflow quality gate, not approval, assurance, certification, or professional signoff.','Professional reliance remains disallowed without qualified human review regardless of readiness score.']];
        return ['ok'=>true,'version'=>self::VERSION,'readiness'=>$readiness_obj,'decision_packet'=>$packet,'results'=>$results,'audit'=>$audit,'review_status_catalog'=>$this->review_status_catalog()];
    }

    private function integrated_brief_markdown($brief) {
        $bullets = function($items) { if (!is_array($items) || !$items) return "- None recorded."; return implode("\n", array_map(function($x){ return '- ' . (is_array($x) ? wp_json_encode($x) : sanitize_text_field(strval($x))); }, $items)); };
        $md = [];
        $md[] = '# ' . ($brief['title'] ?? 'Integrated Decision Brief');
        $md[] = '';
        $md[] = '**Decision Packet:** ' . ($brief['decision_packet_id'] ?? 'SCDS-DRAFT');
        $md[] = '**Recommendation posture:** ' . ($brief['recommendation_posture'] ?? 'Review required');
        $md[] = '**Brief readiness:** ' . ($brief['brief_readiness']['readiness_percent'] ?? 'n/a') . '%';
        $md[] = '';
        $md[] = '## Executive Summary'; $md[] = $brief['executive_summary'] ?? '';
        $md[] = ''; $md[] = '## Decision Question'; $md[] = $brief['decision_question'] ?? 'Not specified';
        $sections = ['problem_framing'=>'Problem Framing','four_pillar_analysis'=>'Four-Pillar Sustainability Analysis','scenario_comparison'=>'Scenario Comparison','financial_tradeoffs'=>'Financial Tradeoffs','impact_measurement'=>'Impact Measurement','claim_and_narrative_risk'=>'Claim and Narrative Risk','execution_and_recovery'=>'Execution and Recovery Risk','assumptions_and_uncertainties'=>'Assumptions and Uncertainties','evidence_and_source_ledger'=>'Evidence and Source Ledger','audit_appendix_summary'=>'Audit Appendix Summary'];
        foreach ($sections as $key=>$title) { $md[]=''; $md[]='## '.$title; $md[] = isset($brief[$key]['findings']) ? $bullets($brief[$key]['findings']) : ($brief[$key]['summary'] ?? 'Not specified'); }
        $md[]=''; $md[]='## Next Review Actions'; $md[]=$bullets($brief['next_review_actions'] ?? []);
        $md[]=''; $md[]='## Boundaries'; $md[]='Educational decision support only. Not professional advice, certification, assurance, or approval.';
        return implode("\n", $md) . "\n";
    }

    private function integrated_brief_html($brief) {
        $ul = function($items) { if (!is_array($items) || !$items) return '<p>None recorded.</p>'; $out='<ul>'; foreach($items as $i) $out.='<li>'.esc_html(is_array($i)?wp_json_encode($i):strval($i)).'</li>'; return $out.'</ul>'; };
        $html = '<div class="scds-integrated-brief"><h2>' . esc_html($brief['title'] ?? 'Integrated Decision Brief') . '</h2>';
        $html .= '<p><strong>Decision Packet:</strong> ' . esc_html($brief['decision_packet_id'] ?? 'SCDS-DRAFT') . '</p>';
        $html .= '<p><strong>Recommendation posture:</strong> ' . esc_html($brief['recommendation_posture'] ?? 'Review required') . '</p>';
        $html .= '<p><strong>Brief readiness:</strong> ' . esc_html($brief['brief_readiness']['readiness_percent'] ?? 'n/a') . '%</p>';
        $html .= '<h3>Executive Summary</h3><p>' . esc_html($brief['executive_summary'] ?? '') . '</p>';
        $html .= '<h3>Decision Question</h3><p>' . esc_html($brief['decision_question'] ?? 'Not specified') . '</p>';
        $sections = ['problem_framing'=>'Problem Framing','four_pillar_analysis'=>'Four-Pillar Sustainability Analysis','scenario_comparison'=>'Scenario Comparison','financial_tradeoffs'=>'Financial Tradeoffs','impact_measurement'=>'Impact Measurement','claim_and_narrative_risk'=>'Claim and Narrative Risk','execution_and_recovery'=>'Execution and Recovery Risk','assumptions_and_uncertainties'=>'Assumptions and Uncertainties','evidence_and_source_ledger'=>'Evidence and Source Ledger','audit_appendix_summary'=>'Audit Appendix Summary'];
        foreach ($sections as $key=>$title) { $html .= '<h3>' . esc_html($title) . '</h3>'; $html .= isset($brief[$key]['findings']) ? $ul($brief[$key]['findings']) : '<p>' . esc_html($brief[$key]['summary'] ?? 'Not specified') . '</p>'; }
        $html .= '<h3>Next Review Actions</h3>' . $ul($brief['next_review_actions'] ?? []);
        $html .= '<h3>Boundaries</h3><p>Educational decision support only. Not professional advice, certification, assurance, or approval.</p></div>';
        return $html;
    }

    private function generate_integrated_brief($inputs, $results, $packet=[], $audit=[]) {
        if (!$packet) $packet = $this->decision_packet_template();
        if (!$audit) $audit = $this->generate_audit_provenance($inputs, $results, ['packet'=>$packet])['audit'];
        $scores = $results['scores'] ?? [];
        $risk = $results['risk'] ?? [];
        $emissions = $results['emissions'] ?? [];
        $finance = $packet['financial_tradeoffs'] ?? ($packet['finance_analysis'] ?? []);
        $finance_results = is_array($finance) && isset($finance['results']) && is_array($finance['results']) ? $finance['results'] : ($results['finance'] ?? []);
        $weighted = (float)($scores['weighted'] ?? 0); $risk_score = (float)($risk['risk_score'] ?? 0);
        $readiness = 0; $filled=[]; $missing=[];
        foreach($this->module_integrations() as $m){ $key=$m['artifact_key']; $present=!empty($packet[$key]) || (!empty($m['decision_packet_section']) && !empty($packet[$m['decision_packet_section']])); if($present)$filled[]=$m['id']; else $missing[]=$m['id']; }
        $readiness = round(100*count($filled)/max(1,count($this->module_integrations())),1);
        $posture = ($weighted >= 75 && $risk_score < 55) ? 'Advance with mitigations' : (($weighted >= 60 && $risk_score < 70) ? 'Continue due diligence' : 'Revise before approval');
        if ($readiness < 50) $posture .= ' — incomplete packet';
        $framing = $packet['decision_framing'] ?? ($packet['framing'] ?? []);
        $project_name = $inputs['projectName'] ?? ($packet['project']['project_name'] ?? 'Decision project');
        $decision_question = !empty($framing['decision_question']) ? $framing['decision_question'] : ($inputs['decisionQuestion'] ?? 'Decision question not specified');
        $scenarios = $this->records_from_packet($packet, 'scenarios', 'scenario_analysis');
        $scenario_findings=[]; if($scenarios){ foreach(array_slice($scenarios,0,4) as $sc) $scenario_findings[]=$this->text_or_default($sc['demo'] ?? ($sc['name'] ?? ($sc['label'] ?? 'Imported scenario'))) . ': ' . $this->text_or_default($sc['interpretation'] ?? ($sc['decision_note'] ?? ($sc['summary'] ?? 'Imported scenario artifact attached.'))); } else { foreach(array_slice($results['scenarios'] ?? [],0,5) as $sc) $scenario_findings[]=$this->text_or_default($sc['label'] ?? 'Scenario').': annual avoided emissions '.$this->brief_num($sc['annual_avoided_tco2e'] ?? '').' tCO2e; NPV '.$this->brief_money($sc['npv'] ?? null).'; payback '.$this->brief_num($sc['payback_years'] ?? '', ' years').'.'; }
        $impacts=$this->records_from_packet($packet,'impact_measurement','impact_records'); $impact_findings=[]; foreach(array_slice($impacts,0,5) as $i)$impact_findings[]=$this->text_or_default($i['initiative'] ?? ($i['goal'] ?? ($i['indicator'] ?? 'Impact record'))).': baseline '.$this->text_or_default($i['baseline_value'] ?? ($i['baseline'] ?? 'n/a')).', current '.$this->text_or_default($i['current_value'] ?? ($i['current'] ?? 'n/a')).', target '.$this->text_or_default($i['target_value'] ?? ($i['target'] ?? 'n/a')).'.'; if(!$impact_findings)$impact_findings=['No Global Impact artifact is attached yet; impact claims remain draft.'];
        $claims=$this->records_from_packet($packet,'claim_and_risk_review','claim_reviews'); $claim_findings=[]; foreach(array_slice($claims,0,5) as $c)$claim_findings[]=$this->text_or_default($c['claim'] ?? 'Imported claim').': risk '.$this->text_or_default($c['risk_level'] ?? 'unspecified').', evidence '.$this->text_or_default($c['evidence_strength'] ?? 'unspecified').'.'; if(!$claim_findings)$claim_findings=['No Narrative Risk artifact is attached yet; external-facing claims remain provisional.'];
        $recovery=$packet['execution_and_recovery'] ?? ($packet['execution_recovery'] ?? []); $recovery_findings = $recovery ? ['Recovery state: '.$this->text_or_default($recovery['resilience_state'] ?? 'unspecified').'; recovery score '.$this->text_or_default($recovery['recovery_score'] ?? 'n/a').'.'] : ['No Catalyst Grit recovery artifact is attached yet; execution pressure and next actions require review.'];
        $source_findings=[]; $sources=$packet['sources'] ?? ($audit['source_ledger'] ?? []); foreach(array_slice(is_array($sources)?$sources:[],0,5) as $src)$source_findings[]=$this->text_or_default($src['source_title'] ?? ($src['name'] ?? 'Source')).': confidence '.$this->text_or_default($src['confidence'] ?? 'unspecified').'; used for '.$this->text_or_default($src['used_for'] ?? 'unspecified').'.'; if(!$source_findings)$source_findings=['No explicit source ledger has been attached; import Catalyst Data records before external reliance.'];
        $assumption_findings=[]; foreach(array_slice($packet['assumptions'] ?? [],0,5) as $a)$assumption_findings[]=$this->text_or_default($a['assumption'] ?? 'Assumption').': '.$this->text_or_default($a['value'] ?? 'n/a').'; sensitivity '.$this->text_or_default($a['sensitivity'] ?? 'unspecified').'.'; if(!$assumption_findings)$assumption_findings=['Core assumptions include baseline emissions, reduction rate, adoption rate, CAPEX, annual savings, discount rate, and model years.'];
        $ledger = $audit['module_artifact_ledger'] ?? []; $attached=0; foreach(is_array($ledger)?$ledger:[] as $l) if(($l['status'] ?? '')==='attached') $attached++;
        $brief = ['brief_version'=>self::VERSION,'title'=>'Integrated Decision Brief: '.$project_name,'decision_packet_id'=>$audit['decision_packet_id'] ?? 'SCDS-DRAFT','decision_question'=>$decision_question,'recommendation_posture'=>$posture,'brief_readiness'=>['readiness_percent'=>$readiness,'filled_modules'=>$filled,'missing_modules'=>$missing],'executive_summary'=>$project_name.' is currently assessed as "'.($results['status'] ?? 'Decision requires review').'". The weighted score is '.$this->brief_num($weighted).'/100, risk is '.$this->text_or_default($risk['risk_level'] ?? 'Unknown').' ('.$this->brief_num($risk_score).'/100), estimated NPV is '.$this->brief_money($finance_results['npv'] ?? null).', and estimated annual avoided emissions are '.$this->brief_num($emissions['annual_avoided_tco2e'] ?? null).' tCO2e. Recommendation posture: '.$posture.'.','problem_framing'=>['summary'=>$this->text_or_default($framing['challenge'] ?? ($framing['point_of_view'] ?? ($inputs['constraints'] ?? 'Problem framing is not yet fully imported from Catalyst Canvas.')))],'four_pillar_analysis'=>['findings'=>['Environmental score: '.$this->brief_num($scores['environmental'] ?? null).'/100.','Social score: '.$this->brief_num($scores['social'] ?? null).'/100.','Economic score: '.$this->brief_num($scores['economic'] ?? null).'/100.','Governance score: '.$this->brief_num($scores['governance'] ?? null).'/100.','Weighted score: '.$this->brief_num($weighted).'/100.']],'scenario_comparison'=>['findings'=>$scenario_findings],'financial_tradeoffs'=>['findings'=>['NPV: '.$this->brief_money($finance_results['npv'] ?? null).'.','ROI: '.$this->brief_num($finance_results['roi_percent'] ?? null, '%').'.','Payback: '.$this->brief_num($finance_results['payback_years'] ?? null, ' years').'.','Finance outputs remain estimates until assumptions and source data are reviewed.']],'impact_measurement'=>['findings'=>$impact_findings],'claim_and_narrative_risk'=>['findings'=>$claim_findings],'execution_and_recovery'=>['findings'=>$recovery_findings],'assumptions_and_uncertainties'=>['findings'=>$assumption_findings],'evidence_and_source_ledger'=>['findings'=>$source_findings],'audit_appendix_summary'=>['findings'=>['Module artifact ledger: '.$attached.'/'.(is_array($ledger)&&count($ledger)?count($ledger):count($this->module_integrations())).' modules attached.','Calculation trace entries: '.count($packet['calculation_trace'] ?? []).'.','Review status: '.$this->text_or_default($audit['review_status']['status'] ?? 'draft').'.']],'next_review_actions'=>['Attach or verify Catalyst Data source records for every major claim and calculation.','Review Catalyst Finance assumptions and rerun sensitivity tests.','Attach Narrative Risk review before publishing external-facing claims.','Use Workbench for deeper symbolic, graph, engineering, or domain-specific calculations.','Mark required expert reviews before regulated, safety-critical, financial, legal, engineering, or assurance use.'],'workbench_handoffs'=>$results['workbench_handoffs'] ?? [],'warnings'=>['Educational decision support only; not professional advice or certification.','Imported artifacts and user-provided inputs are not independently verified.']];
        return ['ok'=>true,'version'=>self::VERSION,'brief'=>$brief,'exports'=>['markdown'=>$this->integrated_brief_markdown($brief),'html'=>$this->integrated_brief_html($brief),'json'=>$brief],'results'=>$results,'decision_packet'=>$packet,'audit'=>$audit,'readiness'=>['workflow_readiness_percent'=>$readiness,'filled_modules'=>$filled,'missing_modules'=>$missing]];
    }


    private function export_center_template() { return ['export_center_version'=>self::VERSION,'saved_packet_fields'=>['decision_packet_id','project_name','decision_question','status','updated_at','inputs','results','decision_packet','audit','readiness','scenario_comparison','scenario_studio','workbench_handoff','integrated_brief','governance','collaboration'],'exports'=>[['id'=>'packet_json','label'=>'Decision Packet JSON','description'=>'Complete normalized packet.'],['id'=>'integrated_brief_markdown','label'=>'Integrated Brief Markdown','description'=>'Reviewable decision memo.'],['id'=>'integrated_brief_html','label'=>'Integrated Brief HTML','description'=>'Browser-printable decision memo.'],['id'=>'audit_json','label'=>'Audit & Provenance JSON','description'=>'Evidence, assumptions, calculations, claims, changes, and review ledger.'],['id'=>'readiness_json','label'=>'Readiness JSON','description'=>'Section readiness, unresolved issues, and export gates.'],['id'=>'scenario_json','label'=>'Scenario Comparison JSON','description'=>'Compatibility scenario matrix and ranking.'],['id'=>'scenario_studio_json','label'=>'Advanced Scenario Studio JSON','description'=>'Alternatives, criteria, sensitivity, thresholds, uncertainty, stakeholders, time horizons, and option value.'],['id'=>'handoff_json','label'=>'Workbench Handoff JSON','description'=>'Workbench tool recommendations and payload summary.'],['id'=>'governance_json','label'=>'Decision Governance JSON','description'=>'Decision state, owner, reviewers, conditions, exceptions, conflicts, sign-offs, export gates, and immutable review history.'],['id'=>'collaboration_json','label'=>'Collaborative Decision Room JSON','description'=>'Members, comments, change requests, snapshots, comparisons, notifications, sharing grants, approved-version locks, and activity history.']],'warnings'=>['Saved Decision Packets are working records, not approvals or professional signoff.','Exports preserve user-entered and imported content; review sensitive information before sharing.']]; }

    private function scenario_templates() { return [ ['template_id'=>'baseline','name'=>'Baseline','purpose'=>'Current path with no intervention'], ['template_id'=>'conservative','name'=>'Conservative','purpose'=>'Lower adoption, higher cost, slower benefits'], ['template_id'=>'expected','name'=>'Expected','purpose'=>'Central planning assumption'], ['template_id'=>'ambitious','name'=>'Ambitious','purpose'=>'Higher adoption and faster benefits'], ['template_id'=>'stress','name'=>'Stress Test','purpose'=>'Costs rise, benefits lag, governance weakens'], ['template_id'=>'transition','name'=>'Transition Pathway','purpose'=>'Staged implementation over multiple years'] ]; }
    private function scorecard_rows() { return [ ['pillar'=>'Environmental','default_weight'=>'30','indicators'=>'emissions, energy, land, water, biodiversity, pollution'], ['pillar'=>'Social','default_weight'=>'20','indicators'=>'health, access, equity, labor, community, capability'], ['pillar'=>'Economic','default_weight'=>'30','indicators'=>'NPV, ROI, payback, affordability, productivity, resilience'], ['pillar'=>'Governance','default_weight'=>'20','indicators'=>'accountability, evidence, controls, transparency, capacity, audit trail'] ]; }
    private function workbench_tool_map() { return [ ['decision_module'=>'Risk matrix','workbench_shortcode'=>'[sc_workbench mode="tool" display="compact" tool="risk-resilience-impact-matrix"]'], ['decision_module'=>'Economics and scenarios','workbench_shortcode'=>'[sc_workbench mode="tool" display="compact" tool="economics-forecasting-and-scenario-tool"]'], ['decision_module'=>'Environmental QA/QC','workbench_shortcode'=>'[sc_workbench mode="tool" display="drawer" tool="environmental-monitoring-qaqc-tool"]'], ['decision_module'=>'Systems modeling','workbench_shortcode'=>'[sc_workbench mode="tool" display="compact" tool="systems-modeling-tool"]'], ['decision_module'=>'Global impact','workbench_shortcode'=>'[sc_workbench mode="tool" display="compact" tool="global-impact-assessment-matrix"]'] ]; }
    private function report_template_markdown() { return "# Integrated Decision Brief\n\n## Executive Summary\n## Decision Question\n## Project Description\n## Assumptions\n## Four-Pillar Analysis\n## Environmental Analysis\n## Social Analysis\n## Economic Analysis\n## Governance Analysis\n## Risk Matrix\n## Scenario Comparison\n## Sensitivity Notes\n## Recommended Next Questions\n## Limitations\n## Audit Trail\n"; }
    private function render_csv_table($rows) { if (!$rows) { echo '<p>No rows available.</p>'; return; } echo '<table class="widefat striped"><thead><tr>'; foreach(array_keys($rows[0]) as $h) echo '<th>' . esc_html($h) . '</th>'; echo '</tr></thead><tbody>'; foreach($rows as $row){ echo '<tr>'; foreach($row as $cell) echo '<td>' . esc_html($cell) . '</td>'; echo '</tr>'; } echo '</tbody></table>'; }
}

register_activation_hook(__FILE__, ['Sustainable_Catalyst_Decision_Studio', 'activate']);
new Sustainable_Catalyst_Decision_Studio();
