<?php
/**
 * Plugin Name: Sustainable Catalyst Decision Studio
 * Description: Applied sustainability decision-support workflows for project intake, four-pillar scoring, scenarios, risk, reports, and Workbench integration.
 * Version: 1.0.0
 * Author: Content Catalyst LLC
 * Text Domain: sustainable-catalyst-decision-studio
 */

if (!defined('ABSPATH')) {
    exit;
}

class Sustainable_Catalyst_Decision_Studio {
    const VERSION = '1.0.0';
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
            'brand_subtitle' => 'Structured sustainability decision support for projects, policies, procurement choices, scenarios, risk, and four-pillar evaluation.',
            'methodology_note' => 'AI in the toolkit, never in control. Outputs are decision-support drafts and educational analyses, not legal, financial, engineering, medical, sustainability assurance, tax, compliance, or investment advice.',
            'backend_url' => '',
            'backend_api_key' => '',
            'backend_enabled' => '0',
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
        if (!in_array($mode, ['full', 'project-intake', 'scorecard', 'risk', 'scenario', 'report', 'drawer', 'compact'], true)) {
            $mode = 'full';
        }
        $display = sanitize_key($atts['display'] ?: $mode);
        $uid = 'scds-' . wp_generate_uuid4();

        wp_enqueue_style('scds-decision-studio');
        wp_enqueue_script('scds-decision-studio');
        wp_localize_script('scds-decision-studio', 'SCDSDecisionStudio', [
            'restAnalyzeUrl' => esc_url_raw(rest_url('scds/v1/analyze')),
            'restSaveUrl' => esc_url_raw(rest_url('scds/v1/projects')),
            'restTemplatesUrl' => esc_url_raw(rest_url('scds/v1/templates')),
            'nonce' => wp_create_nonce(self::NONCE_ACTION),
            'backendEnabled' => $settings['backend_enabled'] === '1' && !empty($settings['backend_url']),
            'workbenchIntegration' => $settings['workbench_integration'] === '1',
            'methodologyNote' => sanitize_text_field($settings['methodology_note']),
        ]);

        ob_start();
        ?>
        <section id="<?php echo esc_attr($uid); ?>" class="scds-shell scds-mode-<?php echo esc_attr($mode); ?> scds-display-<?php echo esc_attr($display); ?>" data-scds-app data-scds-mode="<?php echo esc_attr($mode); ?>">
            <?php if ($mode === 'drawer') : ?>
                <button type="button" class="scds-drawer-toggle" data-scds-drawer-toggle><?php echo esc_html($atts['title']); ?> →</button>
                <div class="scds-drawer-panel" hidden>
            <?php endif; ?>

            <header class="scds-hero">
                <p class="scds-kicker">Sustainable Catalyst Platform · Decision Studio v1.0.0</p>
                <h2><?php echo esc_html($atts['title']); ?></h2>
                <p><?php echo esc_html($settings['brand_subtitle']); ?></p>
                <div class="scds-note"><strong>Boundary:</strong> <?php echo esc_html($settings['methodology_note']); ?></div>
            </header>

            <nav class="scds-tabs" aria-label="Decision Studio sections">
                <button type="button" class="scds-tab is-active" data-scds-tab="intake">Intake</button>
                <button type="button" class="scds-tab" data-scds-tab="scorecard">Scorecard</button>
                <button type="button" class="scds-tab" data-scds-tab="risk">Risk</button>
                <button type="button" class="scds-tab" data-scds-tab="scenario">Scenarios</button>
                <button type="button" class="scds-tab" data-scds-tab="report">Report</button>
                <button type="button" class="scds-tab" data-scds-tab="audit">Audit</button>
            </nav>

            <div class="scds-panels">
                <?php $this->render_panel_intake($mode); ?>
                <?php $this->render_panel_scorecard($mode); ?>
                <?php $this->render_panel_risk($mode); ?>
                <?php $this->render_panel_scenario($mode); ?>
                <?php $this->render_panel_report($mode); ?>
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
        <section class="scds-panel" data-scds-panel="report"><div class="scds-panel-head"><p class="scds-section-kicker">Decision brief</p><h3>Exportable decision-support report</h3><p>Generate an executive-style brief with assumptions, scores, scenarios, risk, limits, and next questions.</p></div><div class="scds-actions"><button type="button" class="scds-button scds-button-primary" data-scds-run>Generate Brief</button><button type="button" class="scds-button" data-scds-export-json>Download JSON</button><button type="button" class="scds-button" data-scds-export-csv>Download CSV</button><button type="button" class="scds-button" data-scds-print>Print / Save PDF</button></div><div class="scds-report" data-scds-report></div></section>
    <?php }

    private function render_panel_audit($mode) { ?>
        <section class="scds-panel" data-scds-panel="audit"><div class="scds-panel-head"><p class="scds-section-kicker">Audit trail</p><h3>Assumptions, warnings, and Workbench links</h3><p>Keep the decision logic inspectable and connect deeper analysis to Sustainable Catalyst Workbench calculators.</p></div><div class="scds-audit-list" data-scds-audit></div><div class="scds-workbench-links" data-scds-workbench-links></div></section>
    <?php }

    public function register_admin_menu() {
        add_menu_page('SC Decision Studio', 'SC Decision Studio', 'manage_options', 'scds-dashboard', [$this, 'render_admin_dashboard'], 'dashicons-chart-area', 59);
        add_submenu_page('scds-dashboard', 'Projects', 'Projects', 'manage_options', 'scds-projects', [$this, 'render_admin_projects']);
        add_submenu_page('scds-dashboard', 'Scenario Templates', 'Scenario Templates', 'manage_options', 'scds-templates', [$this, 'render_admin_templates']);
        add_submenu_page('scds-dashboard', 'Scorecard Builder', 'Scorecard Builder', 'manage_options', 'scds-scorecard', [$this, 'render_admin_scorecard']);
        add_submenu_page('scds-dashboard', 'Report Templates', 'Report Templates', 'manage_options', 'scds-reports', [$this, 'render_admin_reports']);
        add_submenu_page('scds-dashboard', 'Validation Dashboard', 'Validation Dashboard', 'manage_options', 'scds-validation', [$this, 'render_admin_validation']);
        add_submenu_page('scds-dashboard', 'Export Center', 'Export Center', 'manage_options', 'scds-export', [$this, 'render_admin_export']);
        add_submenu_page('scds-dashboard', 'Methodology Settings', 'Methodology Settings', 'manage_options', 'scds-settings', [$this, 'render_admin_settings']);
    }

    private function admin_wrap_start($title, $subtitle='') { echo '<div class="wrap scds-admin"><h1>' . esc_html($title) . '</h1>'; if ($subtitle) echo '<p>' . esc_html($subtitle) . '</p>'; }
    private function admin_wrap_end() { echo '</div>'; }

    public function render_admin_dashboard() {
        $this->admin_wrap_start('Sustainable Catalyst Decision Studio v1.0.0', 'Applied decision-support workflows for sustainability projects, policy choices, scenarios, risk, and four-pillar reports.');
        echo '<div class="scds-admin-grid">';
        $cards = [
            ['Projects', 'Track project drafts and generated decision briefs.', 'admin.php?page=scds-projects'],
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
        $settings['workbench_integration'] = isset($incoming['workbench_integration']) ? '1' : '0';
        update_option(self::OPTION_KEY, $settings);
        add_action('admin_notices', function(){ echo '<div class="notice notice-success"><p>Decision Studio settings saved.</p></div>'; });
    }

    public function register_rest_routes() {
        register_rest_route('scds/v1', '/health', ['methods'=>'GET','callback'=>[$this,'rest_health'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/analyze', ['methods'=>'POST','callback'=>[$this,'rest_analyze'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/templates', ['methods'=>'GET','callback'=>[$this,'rest_templates'],'permission_callback'=>'__return_true']);
        register_rest_route('scds/v1', '/projects', ['methods'=>'POST','callback'=>[$this,'rest_save_project'],'permission_callback'=>function(){ return current_user_can('edit_posts'); }]);
        register_rest_route('scds/v1', '/export/validation.csv', ['methods'=>'GET','callback'=>[$this,'rest_export_validation_csv'],'permission_callback'=>function(){ return current_user_can('manage_options'); }]);
        register_rest_route('scds/v1', '/export/templates.csv', ['methods'=>'GET','callback'=>[$this,'rest_export_templates_csv'],'permission_callback'=>function(){ return current_user_can('manage_options'); }]);
        register_rest_route('scds/v1', '/export/tool-map.csv', ['methods'=>'GET','callback'=>[$this,'rest_export_tool_map_csv'],'permission_callback'=>function(){ return current_user_can('manage_options'); }]);
    }

    public function rest_health() { return rest_ensure_response(['ok'=>true,'version'=>self::VERSION,'plugin'=>'sustainable-catalyst-decision-studio']); }
    public function rest_templates() { return rest_ensure_response(['scenario_templates'=>$this->scenario_templates(),'scorecard'=>$this->scorecard_rows(),'workbench_tools'=>$this->workbench_tool_map()]); }
    public function rest_analyze(WP_REST_Request $request) { $inputs = $request->get_json_params(); if (!is_array($inputs)) $inputs = []; return rest_ensure_response(['ok'=>true,'source'=>'wordpress_deterministic_fallback','inputs'=>$inputs,'results'=>$this->analyze_inputs($inputs),'warnings'=>[$this->settings()['methodology_note']]]); }

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
    public function rest_export_templates_csv() { return $this->csv_response('scds-scenario-templates-v1.0.0.csv', $this->scenario_templates()); }
    public function rest_export_tool_map_csv() { return $this->csv_response('scds-workbench-tool-map-v1.0.0.csv', $this->workbench_tool_map()); }
    public function rest_export_validation_csv() { global $wpdb; $rows=$wpdb->get_results('SELECT module_id,module_name,status,warnings,last_validated FROM '.$wpdb->prefix.self::VALIDATION_TABLE, ARRAY_A); return $this->csv_response('scds-validation-dashboard-v1.0.0.csv', $rows ?: []); }

    private function scenario_templates() { return [ ['template_id'=>'baseline','name'=>'Baseline','purpose'=>'Current path with no intervention'], ['template_id'=>'conservative','name'=>'Conservative','purpose'=>'Lower adoption, higher cost, slower benefits'], ['template_id'=>'expected','name'=>'Expected','purpose'=>'Central planning assumption'], ['template_id'=>'ambitious','name'=>'Ambitious','purpose'=>'Higher adoption and faster benefits'], ['template_id'=>'stress','name'=>'Stress Test','purpose'=>'Costs rise, benefits lag, governance weakens'], ['template_id'=>'transition','name'=>'Transition Pathway','purpose'=>'Staged implementation over multiple years'] ]; }
    private function scorecard_rows() { return [ ['pillar'=>'Environmental','default_weight'=>'30','indicators'=>'emissions, energy, land, water, biodiversity, pollution'], ['pillar'=>'Social','default_weight'=>'20','indicators'=>'health, access, equity, labor, community, capability'], ['pillar'=>'Economic','default_weight'=>'30','indicators'=>'NPV, ROI, payback, affordability, productivity, resilience'], ['pillar'=>'Governance','default_weight'=>'20','indicators'=>'accountability, evidence, controls, transparency, capacity, audit trail'] ]; }
    private function workbench_tool_map() { return [ ['decision_module'=>'Risk matrix','workbench_shortcode'=>'[sc_workbench mode="tool" display="compact" tool="risk-resilience-impact-matrix"]'], ['decision_module'=>'Economics and scenarios','workbench_shortcode'=>'[sc_workbench mode="tool" display="compact" tool="economics-forecasting-and-scenario-tool"]'], ['decision_module'=>'Environmental QA/QC','workbench_shortcode'=>'[sc_workbench mode="tool" display="drawer" tool="environmental-monitoring-qaqc-tool"]'], ['decision_module'=>'Systems modeling','workbench_shortcode'=>'[sc_workbench mode="tool" display="compact" tool="systems-modeling-tool"]'], ['decision_module'=>'Global impact','workbench_shortcode'=>'[sc_workbench mode="tool" display="compact" tool="global-impact-assessment-matrix"]'] ]; }
    private function report_template_markdown() { return "# Decision Brief\n\n## Executive Summary\n## Decision Question\n## Project Description\n## Assumptions\n## Four-Pillar Analysis\n## Environmental Analysis\n## Social Analysis\n## Economic Analysis\n## Governance Analysis\n## Risk Matrix\n## Scenario Comparison\n## Sensitivity Notes\n## Recommended Next Questions\n## Limitations\n## Audit Trail\n"; }
    private function render_csv_table($rows) { if (!$rows) { echo '<p>No rows available.</p>'; return; } echo '<table class="widefat striped"><thead><tr>'; foreach(array_keys($rows[0]) as $h) echo '<th>' . esc_html($h) . '</th>'; echo '</tr></thead><tbody>'; foreach($rows as $row){ echo '<tr>'; foreach($row as $cell) echo '<td>' . esc_html($cell) . '</td>'; echo '</tr>'; } echo '</tbody></table>'; }
}

register_activation_hook(__FILE__, ['Sustainable_Catalyst_Decision_Studio', 'activate']);
new Sustainable_Catalyst_Decision_Studio();
