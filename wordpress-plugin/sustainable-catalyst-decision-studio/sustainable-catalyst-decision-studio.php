<?php
/**
 * Plugin Name: Sustainable Catalyst Decision Studio
 * Description: Integrated sustainability decision-support workflow for framing, evidence, scenarios, impact, claims, finance, recovery, four-pillar synthesis, and reports.
 * Version: 1.3.0
 * Author: Content Catalyst LLC
 * Text Domain: sustainable-catalyst-decision-studio
 */

if (!defined('ABSPATH')) {
    exit;
}

class Sustainable_Catalyst_Decision_Studio {
    const VERSION = '1.3.0';
    const OPTION_KEY = 'scds_settings';
    const NONCE_ACTION = 'wp_rest';
    const PROJECTS_TABLE = 'scds_projects';
    const REPORTS_TABLE = 'scds_reports';
    const VALIDATION_TABLE = 'scds_validation';

    public function __construct() {
        add_action('init', [$this, 'register_assets']);
        add_shortcode('sc_decision_studio', [$this, 'render_decision_studio_shortcode']);
        add_shortcode('sustainable_catalyst_platform', [$this, 'render_legacy_shortcode']);
        add_shortcode('sustainable_catalyst_platform_cta', [$this, 'render_cta_shortcode']);
        add_action('admin_menu', [$this, 'register_admin_menu']);
        add_action('admin_init', [$this, 'maybe_save_settings']);
        add_action('rest_api_init', [$this, 'register_rest_routes']);
    }

    public static function activate() {
        self::create_tables();
        $defaults = self::default_settings();
        $existing = get_option(self::OPTION_KEY, []);
        update_option(self::OPTION_KEY, wp_parse_args($existing, $defaults));
        self::seed_validation_rows();
        self::maybe_create_page();
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

        dbDelta("CREATE TABLE $projects (
            id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            project_name VARCHAR(255) NOT NULL,
            sector VARCHAR(160) DEFAULT '',
            location VARCHAR(160) DEFAULT '',
            decision_question LONGTEXT,
            status VARCHAR(40) DEFAULT 'draft',
            inputs_json LONGTEXT,
            results_json LONGTEXT,
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
            ['audit-trail-assumptions-log', 'Audit Trail / Assumptions Log', 'validated'],
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
            'brand_subtitle' => 'Integrated sustainability decision support that connects problem framing, evidence records, scenarios, impact measurement, claim review, finance, recovery, and four-pillar synthesis.',
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
        if (!in_array($mode, ['full', 'workflow', 'project-intake', 'scorecard', 'risk', 'scenario', 'report', 'drawer', 'compact'], true)) {
            $mode = 'full';
        }
        $display = sanitize_key($atts['display'] ?: $mode);
        $start_tab = $mode === 'workflow' ? 'workflow' : ($mode === 'project-intake' ? 'intake' : (in_array($mode, ['scorecard', 'risk', 'scenario', 'report'], true) ? $mode : 'intake'));
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
            'restImportArtifactUrl' => esc_url_raw(rest_url('scds/v1/integrations/import')),
            'restDecisionPacketImportUrl' => esc_url_raw(rest_url('scds/v1/decision-packet/import')),
            'restAuditTemplateUrl' => esc_url_raw(rest_url('scds/v1/audit/template')),
            'restAuditGenerateUrl' => esc_url_raw(rest_url('scds/v1/audit/generate')),
            'restIntegratedBriefUrl' => esc_url_raw(rest_url('scds/v1/integrated-brief')),
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
                <button type="button" class="scds-tab" data-scds-tab="scorecard">Scorecard</button>
                <button type="button" class="scds-tab" data-scds-tab="risk">Risk</button>
                <button type="button" class="scds-tab" data-scds-tab="scenario">Scenarios</button>
                <button type="button" class="scds-tab" data-scds-tab="report">Report</button>
                <button type="button" class="scds-tab" data-scds-tab="audit">Audit</button>
            </nav>

            <div class="scds-panels">
                <?php $this->render_panel_intake($mode); ?>
                <?php $this->render_panel_workflow($mode); ?>
                <?php $this->render_panel_scorecard($mode); ?>
                <?php $this->render_panel_risk($mode); ?>
                <?php $this->render_panel_scenario($mode); ?>
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
                <p class="scds-section-kicker">Integrated platform workflow</p>
                <h3>Frame → Anchor → Model → Measure → Review → Evaluate → Sustain → Decide</h3>
                <p>Use Decision Studio as the synthesis layer for the broader Sustainable Catalyst module ecosystem. Each module can contribute a structured artifact to the Decision Packet before the final four-pillar brief is generated.</p>
            </div>
            <div class="scds-workflow-strip" aria-label="Decision Studio integrated workflow">
                <span>Canvas</span><span>Data</span><span>Analytics R</span><span>Impact</span><span>Narrative Risk</span><span>Finance</span><span>Grit</span><span>Decision Studio</span>
            </div>
            <div class="scds-integration-grid">
                <?php foreach ($this->module_integrations() as $module) : ?>
                    <article class="scds-integration-card" data-scds-module="<?php echo esc_attr($module['id']); ?>">
                        <p class="scds-card-label"><?php echo esc_html($module['label']); ?></p>
                        <h4><?php echo esc_html($module['name']); ?></h4>
                        <p><?php echo esc_html($module['summary']); ?></p>
                        <p class="scds-integration-use"><strong>Feeds:</strong> <?php echo esc_html($module['feeds']); ?></p>
                        <div class="scds-card-actions">
                            <a class="scds-mini-button" href="<?php echo esc_url($module['url']); ?>">Open module →</a>
                            <button type="button" class="scds-mini-button" data-scds-mark-artifact="<?php echo esc_attr($module['artifact_key']); ?>">Mark for packet</button>
                        </div>
                    </article>
                <?php endforeach; ?>
            </div>
            <div class="scds-note"><strong>v1.3.0 boundary:</strong> this release adds Module Artifact Adapters. Paste or import a JSON export from a module and Decision Studio will normalize it into the correct Decision Packet section.</div>
            <div class="scds-import-box">
                <div class="scds-panel-head scds-panel-head-small">
                    <p class="scds-section-kicker">Module artifact import</p>
                    <h4>Paste a module JSON export</h4>
                    <p>Choose the module, paste its JSON export, and import it into the Decision Packet. Auto-detect is available for known Catalyst module schemas.</p>
                </div>
                <div class="scds-form-grid">
                    <label>Artifact type
                        <select data-scds-import-module>
                            <option value="">Auto-detect</option>
                            <option value="catalyst-canvas">Catalyst Canvas</option>
                            <option value="catalyst-data">Catalyst Data</option>
                            <option value="catalyst-analytics-r">Catalyst Analytics R</option>
                            <option value="global-impact-catalyst">Global Impact Catalyst</option>
                            <option value="catalyst-narrative-risk">Narrative Risk</option>
                            <option value="catalyst-finance">Catalyst Finance</option>
                            <option value="catalyst-grit">Catalyst Grit</option>
                            <option value="workbench">Workbench calculation/report</option>
                        </select>
                    </label>
                    <label>Import action
                        <select data-scds-import-action>
                            <option value="merge">Merge into current Decision Packet</option>
                            <option value="preview">Preview normalized patch only</option>
                        </select>
                    </label>
                </div>
                <label class="scds-wide">Artifact JSON<textarea rows="8" data-scds-artifact-json placeholder='Paste a Catalyst module JSON export here'></textarea></label>
                <div class="scds-actions"><button type="button" class="scds-button scds-button-primary" data-scds-import-artifact>Import Artifact</button><button type="button" class="scds-button" data-scds-load-sample-artifact>Load Sample Artifact</button><button type="button" class="scds-button" data-scds-download-packet>Download Decision Packet JSON</button></div>
                <div class="scds-import-result" data-scds-import-result></div>
            </div>
            <div class="scds-note"><strong>v1.3.0 boundary:</strong> Module Artifact Adapters normalize structured exports into a Decision Packet. They map fields and preserve provenance, but they do not verify source truth, professional compliance, certification, or decision approval.</div>
            <div class="scds-actions"><button type="button" class="scds-button scds-button-primary" data-scds-packet-template>Preview Decision Packet</button><button type="button" class="scds-button" data-scds-run>Run Current Decision Analysis</button></div>
            <div class="scds-packet-preview" data-scds-packet-preview></div>
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
            <div class="scds-panel-head"><p class="scds-section-kicker">Scenario comparison</p><h3>Baseline, conservative, expected, and ambitious cases</h3><p>Compare outcomes across adoption, emissions, costs, savings, resilience, and uncertainty.</p></div>
            <div class="scds-form-grid"><label>Savings uncertainty (%)<input type="number" data-scds-field="savingsVolatility" value="15" min="0" max="100"></label><label>CAPEX uncertainty (%)<input type="number" data-scds-field="capexVolatility" value="18" min="0" max="100"></label><label>Carbon price assumption ($/tCO₂e)<input type="number" data-scds-field="carbonPrice" value="45" min="0" step="1"></label><label>Social benefit score (0–100)<input type="number" data-scds-field="socialBenefit" value="58" min="0" max="100"></label></div>
        </section>
    <?php }

    private function render_panel_report($mode) { ?>
        <section class="scds-panel" data-scds-panel="report">
            <div class="scds-panel-head">
                <p class="scds-section-kicker">Integrated brief generator</p>
                <h3>Professional decision memo from the full Decision Packet</h3>
                <p>Generate a structured brief that synthesizes framing, evidence, scenarios, impact records, claim review, finance, recovery, four-pillar scores, audit/provenance, and Workbench handoffs.</p>
            </div>
            <div class="scds-note"><strong>v1.3.0:</strong> the brief generator now produces a professional memo with executive summary, recommendation posture, readiness status, module-derived findings, audit appendix summary, and Markdown/HTML/JSON exports.</div>
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
            <div class="scds-note"><strong>v1.3.0 upgrade:</strong> audit now includes a provenance ledger, source ledger, assumptions register, calculation trace, claim trace, change log, review status, and exportable audit appendix.</div>
            <div class="scds-actions"><button type="button" class="scds-button scds-button-primary" data-scds-audit-generate>Generate Audit Appendix</button><button type="button" class="scds-button" data-scds-export-audit-json>Download Audit JSON</button><button type="button" class="scds-button" data-scds-print>Print / Save PDF</button></div>
            <div class="scds-audit-list" data-scds-audit></div>
            <div class="scds-workbench-links" data-scds-workbench-links></div>
        </section>
    <?php }

    public function register_admin_menu() {
        add_menu_page('SC Decision Studio', 'SC Decision Studio', 'manage_options', 'scds-dashboard', [$this, 'render_admin_dashboard'], 'dashicons-chart-area', 59);
        add_submenu_page('scds-dashboard', 'Projects', 'Projects', 'manage_options', 'scds-projects', [$this, 'render_admin_projects']);
        add_submenu_page('scds-dashboard', 'Integrated Workflow', 'Integrated Workflow', 'manage_options', 'scds-integrations', [$this, 'render_admin_integrations']);
        add_submenu_page('scds-dashboard', 'Scenario Templates', 'Scenario Templates', 'manage_options', 'scds-templates', [$this, 'render_admin_templates']);
        add_submenu_page('scds-dashboard', 'Scorecard Builder', 'Scorecard Builder', 'manage_options', 'scds-scorecard', [$this, 'render_admin_scorecard']);
        add_submenu_page('scds-dashboard', 'Report Templates', 'Report Templates', 'manage_options', 'scds-reports', [$this, 'render_admin_reports']);
        add_submenu_page('scds-dashboard', 'AI Briefing Layer', 'AI Briefing Layer', 'manage_options', 'scds-ai-briefing', [$this, 'render_admin_ai_briefing']);
        add_submenu_page('scds-dashboard', 'Validation Dashboard', 'Validation Dashboard', 'manage_options', 'scds-validation', [$this, 'render_admin_validation']);
        add_submenu_page('scds-dashboard', 'Export Center', 'Export Center', 'manage_options', 'scds-export', [$this, 'render_admin_export']);
        add_submenu_page('scds-dashboard', 'Methodology Settings', 'Methodology Settings', 'manage_options', 'scds-settings', [$this, 'render_admin_settings']);
    }

    private function admin_wrap_start($title, $subtitle='') { echo '<div class="wrap scds-admin"><h1>' . esc_html($title) . '</h1>'; if ($subtitle) echo '<p>' . esc_html($subtitle) . '</p>'; }
    private function admin_wrap_end() { echo '</div>'; }

    public function render_admin_dashboard() {
        $this->admin_wrap_start('Sustainable Catalyst Decision Studio v' . self::VERSION, 'Integrated decision-support workflow for framing, evidence, scenarios, impact, claims, finance, recovery, and four-pillar reports.');
        echo '<div class="scds-admin-grid">';
        $cards = [
            ['Projects', 'Track project drafts and generated decision briefs.', 'admin.php?page=scds-projects'],
            ['Integrated Workflow', 'Map Canvas, Data, Analytics R, Impact, Narrative Risk, Finance, Grit, and Decision Studio.', 'admin.php?page=scds-integrations'],
            ['Scenario Templates', 'Baseline, conservative, expected, ambitious, stress, and transition cases.', 'admin.php?page=scds-templates'],
            ['Scorecard Builder', 'Define four-pillar weights and indicator logic.', 'admin.php?page=scds-scorecard'],
            ['Validation Dashboard', 'Review module status, warnings, sample inputs, and expected outputs.', 'admin.php?page=scds-validation'],
            ['Export Center', 'Download project, validation, and methodology exports.', 'admin.php?page=scds-export'],
            ['Methodology Settings', 'Configure backend URL, integration boundaries, and default display mode.', 'admin.php?page=scds-settings'],
        ];
        foreach ($cards as $c) echo '<div class="card"><h2>' . esc_html($c[0]) . '</h2><p>' . esc_html($c[1]) . '</p><a class="button button-primary" href="' . esc_url(admin_url($c[2])) . '">Open</a></div>';
        echo '</div><h2>Shortcodes</h2><textarea readonly style="width:100%;height:130px">[sc_decision_studio mode="full"]&#10;[sc_decision_studio mode="project-intake"]&#10;[sc_decision_studio mode="scorecard"]&#10;[sc_decision_studio mode="risk"]&#10;[sc_decision_studio mode="scenario"]&#10;[sc_decision_studio mode="report"]&#10;[sc_decision_studio mode="drawer" title="Open Decision Studio"]</textarea>';
        $this->admin_wrap_end();
    }


    public function render_admin_integrations() {
        $this->admin_wrap_start('Integrated Platform Workflow', 'Decision Studio v1.3.0 maps specialized Sustainable Catalyst modules into one Decision Packet.');
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

    public function render_admin_templates() { $this->admin_wrap_start('Scenario Templates', 'Bundled scenario structures for sustainability decisions.'); $this->render_csv_table($this->scenario_templates()); $this->admin_wrap_end(); }
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
        $this->admin_wrap_start('Export Center', 'Download planning datasets for external review and future Workbench integration.');
        echo '<p><a class="button button-primary" href="' . esc_url(rest_url('scds/v1/export/validation.csv')) . '">Download Validation CSV</a> <a class="button" href="' . esc_url(rest_url('scds/v1/export/templates.csv')) . '">Download Scenario Templates CSV</a> <a class="button" href="' . esc_url(rest_url('scds/v1/export/tool-map.csv')) . '">Download Tool Map CSV</a></p>';
        echo '<h2>Workbench Integration Map</h2>'; $this->render_csv_table($this->workbench_tool_map()); $this->admin_wrap_end();
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

    public function register_rest_routes() {
        register_rest_route('scds/v1', '/health', ['methods'=>'GET','callback'=>[$this,'rest_health'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/analyze', ['methods'=>'POST','callback'=>[$this,'rest_analyze'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/templates', ['methods'=>'GET','callback'=>[$this,'rest_templates'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/integrations', ['methods'=>'GET','callback'=>[$this,'rest_integrations'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/integrations/adapters', ['methods'=>'GET','callback'=>[$this,'rest_adapters'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/integrations/import', ['methods'=>'POST','callback'=>[$this,'rest_import_artifact'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/decision-packet/import', ['methods'=>'POST','callback'=>[$this,'rest_import_artifact'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/decision-packet/template', ['methods'=>'GET','callback'=>[$this,'rest_decision_packet_template'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/audit/template', ['methods'=>'GET','callback'=>[$this,'rest_audit_template'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/audit/generate', ['methods'=>'POST','callback'=>[$this,'rest_audit_generate'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/integrated-brief', ['methods'=>'POST','callback'=>[$this,'rest_integrated_brief'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/decision-packet/brief', ['methods'=>'POST','callback'=>[$this,'rest_integrated_brief'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/backend-status', ['methods'=>'GET','callback'=>[$this,'rest_backend_status'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/ai-brief', ['methods'=>'POST','callback'=>[$this,'rest_ai_brief'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/projects', ['methods'=>'POST','callback'=>[$this,'rest_save_project'],'permission_callback'=>function(){ return current_user_can('edit_posts'); }]);
        register_rest_route('scds/v1', '/export/validation.csv', ['methods'=>'GET','callback'=>[$this,'rest_export_validation_csv'],'permission_callback'=>function(){ return current_user_can('manage_options'); }]);
        register_rest_route('scds/v1', '/export/templates.csv', ['methods'=>'GET','callback'=>[$this,'rest_export_templates_csv'],'permission_callback'=>function(){ return current_user_can('manage_options'); }]);
        register_rest_route('scds/v1', '/export/tool-map.csv', ['methods'=>'GET','callback'=>[$this,'rest_export_tool_map_csv'],'permission_callback'=>function(){ return current_user_can('manage_options'); }]);
    }


    public function rest_adapters() {
        if ($this->settings()['backend_enabled'] === '1' && !empty($this->settings()['backend_url'])) {
            $backend = $this->backend_request('/integrations/adapters', [], 'GET');
            if (!is_wp_error($backend) && is_array($backend)) return rest_ensure_response($backend);
        }
        return rest_ensure_response(['ok'=>true,'version'=>self::VERSION,'adapters'=>$this->artifact_adapter_catalog()]);
    }

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

    public function rest_health() { return rest_ensure_response(['ok'=>true,'version'=>self::VERSION,'plugin'=>'sustainable-catalyst-decision-studio']); }
    public function rest_templates() { return rest_ensure_response(['scenario_templates'=>$this->scenario_templates(),'scorecard'=>$this->scorecard_rows(),'workbench_tools'=>$this->workbench_tool_map()]); }
    public function rest_analyze(WP_REST_Request $request) { $inputs = $request->get_json_params(); if (!is_array($inputs)) $inputs = []; return rest_ensure_response(['ok'=>true,'source'=>'wordpress_deterministic_fallback','inputs'=>$inputs,'results'=>$this->analyze_inputs($inputs),'warnings'=>[$this->settings()['methodology_note']]]); }

    public function rest_backend_status() {
        $s = $this->settings();
        if ($s['backend_enabled'] !== '1' || empty($s['backend_url'])) {
            return rest_ensure_response(['ok'=>true,'backend_enabled'=>false,'ai_configured'=>false,'source'=>'wordpress_settings']);
        }
        $response = $this->backend_request('/ai/status', [], 'GET');
        if (is_wp_error($response)) {
            return rest_ensure_response(['ok'=>false,'backend_enabled'=>true,'error'=>$response->get_error_message(),'source'=>'wordpress_proxy']);
        }
        return rest_ensure_response($response);
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

    private function csv_response($filename, $rows) { $fh = fopen('php://temp','w+'); if ($rows) { fputcsv($fh, array_keys($rows[0])); foreach($rows as $row) fputcsv($fh, $row); } rewind($fh); $csv = stream_get_contents($fh); fclose($fh); return new WP_REST_Response($csv, 200, ['Content-Type'=>'text/csv; charset=utf-8','Content-Disposition'=>'attachment; filename="'.$filename.'"']); }
    public function rest_export_templates_csv() { return $this->csv_response('scds-scenario-templates-v1.3.0.csv', $this->scenario_templates()); }
    public function rest_export_tool_map_csv() { return $this->csv_response('scds-workbench-tool-map-v1.3.0.csv', $this->workbench_tool_map()); }
    public function rest_export_validation_csv() { global $wpdb; $rows=$wpdb->get_results('SELECT module_id,module_name,status,warnings,last_validated FROM '.$wpdb->prefix.self::VALIDATION_TABLE, ARRAY_A); return $this->csv_response('scds-validation-dashboard-v1.3.0.csv', $rows ?: []); }


    private function artifact_adapter_catalog() {
        return [
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
        $aliases = ['canvas'=>'catalyst-canvas','data'=>'catalyst-data','analytics-r'=>'catalyst-analytics-r','impact'=>'global-impact-catalyst','global-impact'=>'global-impact-catalyst','narrative-risk'=>'catalyst-narrative-risk','finance'=>'catalyst-finance','grit'=>'catalyst-grit','calculation'=>'workbench'];
        if (isset($aliases[$mid])) $mid = $aliases[$mid];
        foreach ($this->artifact_adapter_catalog() as $a) if ($a['module_id'] === $mid || $a['artifact_key'] === $mid) return $a;
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

    private function adapter_by_id($id) { foreach ($this->artifact_adapter_catalog() as $a) if ($a['module_id'] === $id) return $a; return $this->artifact_adapter_catalog()[0]; }
    private function arr($value) { if (is_array($value)) return array_values($value); if ($value === null || $value === '') return []; return [$value]; }
    private function source_entry($title,$type,$confidence,$used_for,$notes='') { return ['source_title'=>$title ?: 'Unspecified source','source_type'=>$type ?: 'unspecified','confidence'=>$confidence ?: 'unspecified','used_for'=>$used_for ?: 'unspecified','method_notes'=>$notes ?: '']; }
    private function assumption_entry($label,$value,$source,$used_in,$sensitivity='medium',$status='needs review') { return ['assumption'=>$label,'value'=>$value,'module_or_source'=>$source,'used_in'=>$used_in,'sensitivity'=>$sensitivity,'review_status'=>$status]; }
    private function merge_list($a,$b) { $base = is_array($a) ? $a : []; foreach((is_array($b)?$b:[$b]) as $item) if ($item !== null && $item !== '') $base[] = $item; return $base; }

    private function normalize_artifact($artifact, $module_id='') {
        $adapter = $this->detect_artifact_module($artifact, $module_id); $mid=$adapter['module_id']; $name=$adapter['name'];
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
            if (in_array($key, ['assumptions','risks','sources','audit_trail','calculation_trace','claim_reviews','workbench_calculations'], true)) $packet[$key] = $this->merge_list($packet[$key] ?? [], $value);
            elseif ($key === 'evidence_and_measurement' || $key === 'scenarios' || $key === 'impact_measurement' || $key === 'claim_and_risk_review') { if(!isset($packet[$key]) || !is_array($packet[$key])) $packet[$key]=['records'=>[]]; $packet[$key]['records']=$this->merge_list($packet[$key]['records'] ?? [], $value['records'] ?? []); }
            elseif (isset($packet[$key]) && is_array($packet[$key]) && is_array($value)) $packet[$key] = array_merge($packet[$key], $value);
            else $packet[$key] = $value;
        }
        return $packet;
    }

    private function import_artifact_into_packet($artifact, $module_id='', $packet=[]) {
        $normalized = $this->normalize_artifact($artifact, $module_id);
        $updated = $this->apply_packet_patch($packet, $normalized['packet_patch']);
        return ['ok'=>true,'version'=>self::VERSION,'import_result'=>$normalized,'decision_packet'=>$updated,'analysis'=>['ok'=>true,'version'=>self::VERSION,'decision_packet_version'=>'1.3.0']];
    }

    private function module_integrations() {
        return [
            ['step'=>1,'phase'=>'Frame','id'=>'catalyst-canvas','name'=>'Catalyst Canvas','label'=>'Problem framing','url'=>'/catalyst-canvas/#demo','artifact_key'=>'framing','feeds'=>'Decision framing: challenge, audience, POV, HMW prompt, prototype, test plan.','summary'=>'Frame a challenge, define an audience, generate POV and HMW prompts, shape a prototype, design a test plan, and export a structured brief.'],
            ['step'=>2,'phase'=>'Anchor','id'=>'catalyst-data','name'=>'Catalyst Data','label'=>'Data records','url'=>'/catalyst-data/#demo','artifact_key'=>'evidence_records','feeds'=>'Evidence and measurement: entity, indicator, source, period, confidence, method notes, review status.','summary'=>'Create a traceable measurement record with entity, indicator, source, period, confidence, method notes, review status, and JSON export.'],
            ['step'=>3,'phase'=>'Model','id'=>'catalyst-analytics-r','name'=>'Catalyst Analytics R','label'=>'Scenario analysis','url'=>'/catalyst-analytics-r/#demo','artifact_key'=>'scenario_analysis','feeds'=>'Scenarios: assumptions, capital values, emissions budget, interpretation notes, model outputs.','summary'=>'Explore a simplified sustainable-development scenario with assumptions, capital values, emissions budget, interpretation notes, and export logic.'],
            ['step'=>4,'phase'=>'Measure','id'=>'global-impact-catalyst','name'=>'Global Impact Catalyst','label'=>'Impact measurement','url'=>'/global-impact-catalyst/#demo','artifact_key'=>'impact_records','feeds'=>'Impact measurement: initiative, goal, SDG-style theme, baseline, current value, target, source.','summary'=>'Create a traceable impact record with initiative, goal, SDG-style theme, indicator, baseline, current value, target, source, and progress notes.'],
            ['step'=>5,'phase'=>'Review','id'=>'catalyst-narrative-risk','name'=>'Narrative Risk','label'=>'Claim review','url'=>'/narrative-risk/#demo','artifact_key'=>'claim_reviews','feeds'=>'Claim and risk review: evidence strength, uncertainty, source type, stakeholder pressure, volatility, consequences.','summary'=>'Evaluate a claim by evidence strength, uncertainty, source type, stakeholder pressure, narrative volatility, consequences, and review status.'],
            ['step'=>6,'phase'=>'Evaluate','id'=>'catalyst-finance','name'=>'Catalyst Finance','label'=>'Tradeoff analysis','url'=>'/catalyst-finance/#demo','artifact_key'=>'finance_analysis','feeds'=>'Financial tradeoffs: NPV, ROI, payback, benefit-cost ratio, carbon cost per ton, risk-adjusted score.','summary'=>'Estimate NPV, ROI, payback, benefit-cost ratio, carbon cost per ton, risk-adjusted score, review flags, and decision notes.'],
            ['step'=>7,'phase'=>'Sustain','id'=>'catalyst-grit','name'=>'Catalyst Grit','label'=>'Recovery tracking','url'=>'/human-systems/catalyst-grit/#demo','artifact_key'=>'execution_recovery','feeds'=>'Execution and recovery: setback, pressure, energy, support, clarity, recovery actions, recovery score.','summary'=>'Describe a setback, assess pressure, impact, energy, support, clarity, recovery actions, and generate a recovery score and next actions.'],
            ['step'=>8,'phase'=>'Decide','id'=>'decision-studio','name'=>'Decision Studio','label'=>'Decision support','url'=>'/platform/decision-studio/','artifact_key'=>'synthesis','feeds'=>'Integrated decision brief: four-pillar synthesis, assumptions, scenarios, outputs, risks, SDG mapping, audit trail.','summary'=>'Generate a four-pillar sustainability decision brief with assumptions, scenarios, calculator-backed outputs, risks, SDG mapping, and auditable review notes.'],
        ];
    }

    private function decision_packet_template() {
        return [
            'packet_version'=>'1.3.0',
            'workflow'=>'Canvas → Data → Analytics R → Global Impact → Narrative Risk → Finance → Grit → Decision Studio',
            'project'=>['project_name'=>'','organization_type'=>'','sector'=>'','location'=>'','time_horizon'=>'','decision_question'=>''],
            'framing'=>[],
            'evidence_records'=>[],
            'scenario_analysis'=>[],
            'impact_records'=>[],
            'claim_reviews'=>[],
            'finance_analysis'=>[],
            'execution_recovery'=>[],
            'synthesis'=>[],
            'four_pillar_scores'=>[],
            'assumptions'=>[],
            'risks'=>[],
            'sources'=>[],
            'audit_trail'=>[],
            'audit_and_provenance'=>$this->audit_provenance_template(),
            'module_slots'=>array_map(function($m){ return ['module_id'=>$m['id'],'name'=>$m['name'],'artifact_key'=>$m['artifact_key'],'status'=>'empty']; }, $this->module_integrations()),
        ];
    }


    private function audit_provenance_template() {
        return [
            'audit_version'=>'1.3.0',
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

    private function scenario_templates() { return [ ['template_id'=>'baseline','name'=>'Baseline','purpose'=>'Current path with no intervention'], ['template_id'=>'conservative','name'=>'Conservative','purpose'=>'Lower adoption, higher cost, slower benefits'], ['template_id'=>'expected','name'=>'Expected','purpose'=>'Central planning assumption'], ['template_id'=>'ambitious','name'=>'Ambitious','purpose'=>'Higher adoption and faster benefits'], ['template_id'=>'stress','name'=>'Stress Test','purpose'=>'Costs rise, benefits lag, governance weakens'], ['template_id'=>'transition','name'=>'Transition Pathway','purpose'=>'Staged implementation over multiple years'] ]; }
    private function scorecard_rows() { return [ ['pillar'=>'Environmental','default_weight'=>'30','indicators'=>'emissions, energy, land, water, biodiversity, pollution'], ['pillar'=>'Social','default_weight'=>'20','indicators'=>'health, access, equity, labor, community, capability'], ['pillar'=>'Economic','default_weight'=>'30','indicators'=>'NPV, ROI, payback, affordability, productivity, resilience'], ['pillar'=>'Governance','default_weight'=>'20','indicators'=>'accountability, evidence, controls, transparency, capacity, audit trail'] ]; }
    private function workbench_tool_map() { return [ ['decision_module'=>'Risk matrix','workbench_shortcode'=>'[sc_workbench mode="tool" display="compact" tool="risk-resilience-impact-matrix"]'], ['decision_module'=>'Economics and scenarios','workbench_shortcode'=>'[sc_workbench mode="tool" display="compact" tool="economics-forecasting-and-scenario-tool"]'], ['decision_module'=>'Environmental QA/QC','workbench_shortcode'=>'[sc_workbench mode="tool" display="drawer" tool="environmental-monitoring-qaqc-tool"]'], ['decision_module'=>'Systems modeling','workbench_shortcode'=>'[sc_workbench mode="tool" display="compact" tool="systems-modeling-tool"]'], ['decision_module'=>'Global impact','workbench_shortcode'=>'[sc_workbench mode="tool" display="compact" tool="global-impact-assessment-matrix"]'] ]; }
    private function report_template_markdown() { return "# Integrated Decision Brief\n\n## Executive Summary\n## Decision Question\n## Project Description\n## Assumptions\n## Four-Pillar Analysis\n## Environmental Analysis\n## Social Analysis\n## Economic Analysis\n## Governance Analysis\n## Risk Matrix\n## Scenario Comparison\n## Sensitivity Notes\n## Recommended Next Questions\n## Limitations\n## Audit Trail\n"; }
    private function render_csv_table($rows) { if (!$rows) { echo '<p>No rows available.</p>'; return; } echo '<table class="widefat striped"><thead><tr>'; foreach(array_keys($rows[0]) as $h) echo '<th>' . esc_html($h) . '</th>'; echo '</tr></thead><tbody>'; foreach($rows as $row){ echo '<tr>'; foreach($row as $cell) echo '<td>' . esc_html($cell) . '</td>'; echo '</tr>'; } echo '</tbody></table>'; }
}

register_activation_hook(__FILE__, ['Sustainable_Catalyst_Decision_Studio', 'activate']);
new Sustainable_Catalyst_Decision_Studio();
