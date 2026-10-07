import json
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.services import decision_service as service

ROOT = Path(__file__).resolve().parents[2]

def test_v310_decomposition_preserved_under_current_release():
    client = TestClient(app)
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["version"] == "3.14.0"
    release = client.get("/release").json()["release"]
    assert release["backend_architecture"]["decomposition_release"] is True
    assert release["backend_architecture"]["database_migration"] is False
    assert release["backend_architecture"]["postgresql_live_authority"] is True
    assert release["backend_architecture"]["wordpress_authority_change"] is True

def test_main_is_composition_only():
    main_text = (ROOT / "backend/app/main.py").read_text()
    assert len(main_text.splitlines()) <= 25
    assert "@app.get" not in main_text
    assert "@app.post" not in main_text
    assert "include_router(api_router)" in main_text

def test_routes_match_certified_inventory():
    inv = json.loads((ROOT / "data/backend_route_inventory_v3.1.0.json").read_text())
    expected={(r["path"], r["method"]) for routes in inv["routers"].values() for r in routes}
    actual=set()
    for route in app.routes:
        for method in getattr(route, "methods", set()):
            if method in {"GET","POST","PUT","PATCH","DELETE"}:
                actual.add((route.path, method))
    assert expected <= actual
    assert len(expected) == inv["route_count"]

def test_router_modules_are_decomposed():
    route_dir = ROOT / "backend/app/api/routes"
    modules = sorted(p for p in route_dir.glob("*.py") if p.name != "__init__.py")
    assert len(modules) >= 11
    assert service.APP_VERSION == "3.14.0"
