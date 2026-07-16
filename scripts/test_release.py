#!/usr/bin/env python3
"""Static release-integrity checks for Decision Studio."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "1.7.1"
BUILD = "scds-v1.7.1-53b729b"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")
    print(f"PASS: {message}")


backend = (ROOT / "backend/app/main.py").read_text()
plugin_path = ROOT / "wordpress-plugin/sustainable-catalyst-decision-studio/sustainable-catalyst-decision-studio.php"
plugin = plugin_path.read_text()
plugin_readme = (plugin_path.parent / "readme.txt").read_text()
render = (ROOT / "backend/render.yaml").read_text()
manifest = json.loads((ROOT / "data/decision_studio_release_manifest_v1.7.1.json").read_text())
plugin_manifest = json.loads((plugin_path.parent / "data/release_manifest_v1.7.1.json").read_text())

require(f'APP_VERSION = "{VERSION}"' in backend, "backend version marker")
require(f" * Version: {VERSION}" in plugin, "WordPress plugin header version")
require(f"const VERSION = '{VERSION}';" in plugin, "WordPress runtime version")
require(f"Stable tag: {VERSION}" in plugin_readme, "WordPress stable tag")
require(f'BUILD_FINGERPRINT = os.getenv("SCDS_BUILD_FINGERPRINT", "{BUILD}")' in backend, "backend build fingerprint")
require(f"const BUILD_FINGERPRINT = '{BUILD}';" in plugin, "WordPress build fingerprint")
require(manifest == plugin_manifest, "repository and plugin manifests match")
require(manifest["release"] == VERSION, "manifest release version")
require(manifest["compatibility"]["packet_schema_breaking_changes"] is False, "packet schema compatibility declaration")
require("rootDir: backend" in render, "Render backend root directory")
require("buildCommand: pip install -r requirements.txt" in render, "Render build command")
require("startCommand: uvicorn app.main:app" in render, "Render startup command")
require("healthCheckPath: /health" in render, "Render health check")
require("add_action('plugins_loaded', [__CLASS__, 'maybe_upgrade']);" in plugin, "WordPress upgrade hook")
require("public static function maybe_upgrade()" in plugin, "WordPress migration routine")
require("add_filter('rest_pre_dispatch'" in plugin, "WordPress request guard")
require("/release" in backend and "'/release'" in plugin, "release endpoints")
require("version-mismatch" in plugin, "backend parity state")
for shortcode in ("sc_decision_studio", "sustainable_catalyst_platform", "sustainable_catalyst_platform_cta"):
    require(f"add_shortcode('{shortcode}'" in plugin, f"shortcode preserved: {shortcode}")
require((ROOT / "backend/app/__init__.py").exists(), "backend package marker")
require((ROOT / "backend/tests/__init__.py").exists(), "test package marker")
require((ROOT / "backend/pytest.ini").exists(), "pytest configuration")
print("Release integrity checks passed.")
