from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

ANALYSIS_HANDOFF_SCHEMA = "scds-analysis-handoff/1.0"
COMPUTATION_HANDOFF_SCHEMA = "scds-computation-handoff/1.0"
HANDOFF_RECEIPT_SCHEMA = "scds-handoff-receipt/1.0"
ANALYSIS_REQUEST_SCHEMA = "scds-analysis-request/1.0"

PRODUCTS = {
    "research-lab": {"name": "Research Lab", "role": "analysis", "handoff_schema": ANALYSIS_HANDOFF_SCHEMA},
    "workbench": {"name": "Workbench", "role": "computation", "handoff_schema": COMPUTATION_HANDOFF_SCHEMA},
}

BOUNDARY = (
    "Native handoffs preserve source artifacts and lineage. Decision Studio does not execute Lab experiments or "
    "Workbench computations, silently reinterpret source results, or treat receipt as validation, approval, or recommendation."
)


class NativeHandoffRequest(BaseModel):
    decisionObject: Dict[str, Any] = Field(default_factory=dict)
    packet: Dict[str, Any] = Field(default_factory=dict)
    handoff: Dict[str, Any] = Field(default_factory=dict)
    artifact: Dict[str, Any] = Field(default_factory=dict)
    request: Dict[str, Any] = Field(default_factory=dict)
    sourceProduct: str = ""
    targetProduct: str = ""
    sourceVersion: str = ""
    artifactType: str = ""
    artifactSchema: str = ""
    reviewState: str = ""
    assumptions: List[Any] = Field(default_factory=list)
    uncertainty: List[Any] = Field(default_factory=list)
    provenance: List[Any] = Field(default_factory=list)
    links: List[Any] = Field(default_factory=list)
    neededFor: str = ""
    question: str = ""
    returnTo: Dict[str, Any] = Field(default_factory=dict)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug(value: Any) -> str:
    return str(value or "").strip().lower().replace("_", "-").replace(" ", "-")


def _canonical_hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
    return sha256(raw.encode("utf-8")).hexdigest()


def _source_product(value: str) -> str:
    key = _slug(value)
    aliases = {
        "lab": "research-lab",
        "researchlab": "research-lab",
        "research-lab": "research-lab",
        "sustainable-catalyst-lab": "research-lab",
        "work-bench": "workbench",
        "sustainable-catalyst-workbench": "workbench",
        "workbench": "workbench",
    }
    return aliases.get(key, key)


def _decision_id(decision_object: Dict[str, Any], packet: Dict[str, Any]) -> str:
    return str(
        decision_object.get("decision_id")
        or packet.get("decision_packet_id")
        or packet.get("decision_id")
        or ""
    )


def handoff_contracts_template() -> Dict[str, Any]:
    return {
        "analysis_handoff_schema": ANALYSIS_HANDOFF_SCHEMA,
        "computation_handoff_schema": COMPUTATION_HANDOFF_SCHEMA,
        "handoff_receipt_schema": HANDOFF_RECEIPT_SCHEMA,
        "analysis_request_schema": ANALYSIS_REQUEST_SCHEMA,
        "products": deepcopy(PRODUCTS),
        "required_lineage": [
            "source.product",
            "source.version",
            "artifact.artifact_type",
            "artifact.artifact_schema",
            "artifact.payload",
            "artifact.fingerprint",
            "review_state",
            "provenance",
        ],
        "boundary": BOUNDARY,
    }


def native_handoff_template() -> Dict[str, Any]:
    return {
        "schema": ANALYSIS_HANDOFF_SCHEMA,
        "handoff_id": "handoff:research-lab:example",
        "decision_id": "",
        "created_at": "",
        "source": {"product": "research-lab", "name": "Research Lab", "version": "", "role": "analysis"},
        "target": {"product": "decision-studio", "name": "Decision Studio", "role": "choice"},
        "artifact": {
            "artifact_id": "",
            "artifact_type": "experiment-result",
            "artifact_schema": "",
            "payload": {},
            "fingerprint": "",
        },
        "review_state": "needs_review",
        "assumptions": [],
        "uncertainty": [],
        "provenance": [],
        "links": [],
        "request_id": "",
        "boundary": BOUNDARY,
    }


def analysis_request_template() -> Dict[str, Any]:
    return {
        "schema": ANALYSIS_REQUEST_SCHEMA,
        "request_id": "analysis-request:example",
        "decision_id": "",
        "created_at": "",
        "source": {"product": "decision-studio", "name": "Decision Studio", "role": "choice"},
        "target": {"product": "research-lab", "name": "Research Lab", "role": "analysis"},
        "question": "",
        "needed_for": "",
        "requested_artifact_types": [],
        "decision_context": {},
        "assumptions": [],
        "uncertainty": [],
        "provenance": [],
        "return_contract": ANALYSIS_HANDOFF_SCHEMA,
        "request_fingerprint": "",
        "execution": {"requested": True, "performed_by_decision_studio": False},
        "boundary": BOUNDARY,
    }


def build_native_handoff(
    source_product: str,
    artifact: Dict[str, Any],
    *,
    app_version: str,
    decision_id: str = "",
    source_version: str = "",
    artifact_type: str = "",
    artifact_schema: str = "",
    review_state: str = "",
    assumptions: Optional[List[Any]] = None,
    uncertainty: Optional[List[Any]] = None,
    provenance: Optional[List[Any]] = None,
    links: Optional[List[Any]] = None,
    request_id: str = "",
) -> Dict[str, Any]:
    product = _source_product(source_product)
    if product not in PRODUCTS:
        raise ValueError("sourceProduct must be research-lab or workbench")
    info = PRODUCTS[product]
    artifact = deepcopy(artifact or {})
    inferred_type = artifact_type or str(artifact.get("artifact_type") or artifact.get("type") or "analysis-artifact")
    inferred_schema = artifact_schema or str(artifact.get("schema") or "")
    artifact_id = str(artifact.get("artifact_id") or artifact.get("id") or "")
    fingerprint = _canonical_hash(artifact)
    core = {
        "decision_id": decision_id,
        "source_product": product,
        "source_version": source_version,
        "artifact_type": inferred_type,
        "artifact_schema": inferred_schema,
        "artifact_id": artifact_id,
        "artifact_fingerprint": fingerprint,
        "request_id": request_id,
    }
    handoff_id = f"handoff:{product}:{_canonical_hash(core)[:20]}"
    return {
        "schema": info["handoff_schema"],
        "version": app_version,
        "handoff_id": handoff_id,
        "decision_id": decision_id,
        "created_at": _now(),
        "source": {"product": product, "name": info["name"], "version": source_version, "role": info["role"]},
        "target": {"product": "decision-studio", "name": "Decision Studio", "version": app_version, "role": "choice"},
        "artifact": {
            "artifact_id": artifact_id,
            "artifact_type": inferred_type,
            "artifact_schema": inferred_schema,
            "payload": artifact,
            "fingerprint": fingerprint,
        },
        "review_state": review_state or str(artifact.get("review_state") or "needs_review"),
        "assumptions": deepcopy(assumptions or artifact.get("assumptions") or []),
        "uncertainty": deepcopy(uncertainty or artifact.get("uncertainty") or artifact.get("uncertainties") or []),
        "provenance": deepcopy(provenance or artifact.get("provenance") or []),
        "links": deepcopy(links or artifact.get("links") or []),
        "request_id": request_id,
        "boundary": BOUNDARY,
    }


def validate_native_handoff(handoff: Dict[str, Any], *, app_version: str) -> Dict[str, Any]:
    source = handoff.get("source") if isinstance(handoff.get("source"), dict) else {}
    product = _source_product(source.get("product", ""))
    artifact = handoff.get("artifact") if isinstance(handoff.get("artifact"), dict) else {}
    errors: List[str] = []
    warnings: List[str] = []
    if product not in PRODUCTS:
        errors.append("source.product must be research-lab or workbench")
    else:
        expected = PRODUCTS[product]["handoff_schema"]
        if handoff.get("schema") != expected:
            errors.append(f"schema must be {expected} for {product}")
    if not str(handoff.get("handoff_id") or "").strip():
        errors.append("handoff_id is required")
    if not isinstance(artifact.get("payload"), dict):
        errors.append("artifact.payload must be an object")
    expected_fp = _canonical_hash(artifact.get("payload") or {})
    if artifact.get("fingerprint") != expected_fp:
        errors.append("artifact fingerprint does not match payload")
    if not str(source.get("version") or "").strip():
        warnings.append("source.version is empty")
    if not str(artifact.get("artifact_schema") or "").strip():
        warnings.append("artifact.artifact_schema is empty")
    if not handoff.get("provenance"):
        warnings.append("provenance is empty")
    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "source_product": product,
        "app_version": app_version,
    }


def receive_native_handoff(handoff: Dict[str, Any], *, app_version: str) -> Dict[str, Any]:
    validation = validate_native_handoff(handoff, app_version=app_version)
    receipt_core = {
        "handoff_id": handoff.get("handoff_id"),
        "artifact_fingerprint": (handoff.get("artifact") or {}).get("fingerprint"),
        "validation": validation,
    }
    return {
        "schema": HANDOFF_RECEIPT_SCHEMA,
        "version": app_version,
        "receipt_id": f"receipt:{_canonical_hash(receipt_core)[:20]}",
        "created_at": _now(),
        "handoff_id": handoff.get("handoff_id", ""),
        "decision_id": handoff.get("decision_id", ""),
        "source": deepcopy(handoff.get("source") or {}),
        "target": {"product": "decision-studio", "name": "Decision Studio", "version": app_version},
        "accepted": validation["valid"],
        "validation": validation,
        "artifact_fingerprint": (handoff.get("artifact") or {}).get("fingerprint", ""),
        "request_id": handoff.get("request_id", ""),
        "execution": {"performed": False, "mode": "source-owned"},
        "persistence": {"performed": False, "mode": "attached-only-when-requested"},
        "receipt_fingerprint": _canonical_hash(receipt_core),
        "boundary": BOUNDARY,
    }


def build_analysis_request(
    target_product: str,
    *,
    app_version: str,
    decision_id: str = "",
    question: str = "",
    needed_for: str = "",
    requested_artifact_types: Optional[List[str]] = None,
    decision_context: Optional[Dict[str, Any]] = None,
    assumptions: Optional[List[Any]] = None,
    uncertainty: Optional[List[Any]] = None,
    provenance: Optional[List[Any]] = None,
    return_to: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    product = _source_product(target_product)
    if product not in PRODUCTS:
        raise ValueError("targetProduct must be research-lab or workbench")
    info = PRODUCTS[product]
    core = {
        "decision_id": decision_id,
        "target_product": product,
        "question": question,
        "needed_for": needed_for,
        "requested_artifact_types": requested_artifact_types or [],
    }
    request_id = f"analysis-request:{product}:{_canonical_hash(core)[:20]}"
    out = {
        "schema": ANALYSIS_REQUEST_SCHEMA,
        "version": app_version,
        "request_id": request_id,
        "decision_id": decision_id,
        "created_at": _now(),
        "source": {"product": "decision-studio", "name": "Decision Studio", "version": app_version, "role": "choice"},
        "target": {"product": product, "name": info["name"], "role": info["role"]},
        "question": question,
        "needed_for": needed_for,
        "requested_artifact_types": list(requested_artifact_types or []),
        "decision_context": deepcopy(decision_context or {}),
        "assumptions": deepcopy(assumptions or []),
        "uncertainty": deepcopy(uncertainty or []),
        "provenance": deepcopy(provenance or []),
        "return_to": deepcopy(return_to or {"product": "decision-studio", "decision_id": decision_id}),
        "return_contract": info["handoff_schema"],
        "execution": {"requested": True, "performed_by_decision_studio": False},
        "boundary": BOUNDARY,
    }
    out["request_fingerprint"] = _canonical_hash({k: v for k, v in out.items() if k != "request_fingerprint"})
    return out


def attach_native_handoff(
    decision_object: Dict[str, Any],
    handoff: Dict[str, Any],
    receipt: Dict[str, Any],
    *,
    app_version: str,
) -> Dict[str, Any]:
    out = deepcopy(decision_object or {})
    out.setdefault("schema", "scds-decision-object/1.0")
    out.setdefault("decision_id", handoff.get("decision_id", ""))
    product = _source_product(((handoff.get("source") or {}).get("product")))
    key = "analysis_handoffs" if product == "research-lab" else "computation_handoffs"
    out.setdefault(key, []).append(deepcopy(handoff))
    out.setdefault("handoff_receipts", []).append(deepcopy(receipt))
    artifact = deepcopy((handoff.get("artifact") or {}).get("payload") or {})
    if product == "research-lab":
        out.setdefault("models", []).append({
            "source_product": "research-lab",
            "artifact_type": (handoff.get("artifact") or {}).get("artifact_type", ""),
            "artifact_schema": (handoff.get("artifact") or {}).get("artifact_schema", ""),
            "artifact_fingerprint": (handoff.get("artifact") or {}).get("fingerprint", ""),
            "handoff_id": handoff.get("handoff_id", ""),
            "source_artifact": artifact,
        })
    elif product == "workbench":
        out.setdefault("models", []).append({
            "source_product": "workbench",
            "artifact_type": (handoff.get("artifact") or {}).get("artifact_type", ""),
            "artifact_schema": (handoff.get("artifact") or {}).get("artifact_schema", ""),
            "artifact_fingerprint": (handoff.get("artifact") or {}).get("fingerprint", ""),
            "handoff_id": handoff.get("handoff_id", ""),
            "source_artifact": artifact,
        })
    for assumption in handoff.get("assumptions") or []:
        out.setdefault("assumptions", []).append(deepcopy(assumption))
    for uncertainty in handoff.get("uncertainty") or []:
        out.setdefault("uncertainties", []).append(deepcopy(uncertainty))
    out.setdefault("links", []).append({
        "relationship": "native_handoff",
        "source_product": product,
        "handoff_id": handoff.get("handoff_id", ""),
        "artifact_fingerprint": (handoff.get("artifact") or {}).get("fingerprint", ""),
    })
    prov = out.setdefault("provenance", {})
    prov.setdefault("records", []).append({
        "at": _now(),
        "action": "native_handoff_attached",
        "source_product": product,
        "handoff_id": handoff.get("handoff_id", ""),
        "receipt_id": receipt.get("receipt_id", ""),
        "artifact_fingerprint": (handoff.get("artifact") or {}).get("fingerprint", ""),
    })
    out["updated_at"] = _now()
    out["version"] = app_version
    return out


def attach_analysis_request(decision_object: Dict[str, Any], request: Dict[str, Any], *, app_version: str) -> Dict[str, Any]:
    out = deepcopy(decision_object or {})
    out.setdefault("schema", "scds-decision-object/1.0")
    out.setdefault("decision_id", request.get("decision_id", ""))
    out.setdefault("analysis_requests", []).append(deepcopy(request))
    out.setdefault("links", []).append({
        "relationship": "analysis_request",
        "target_product": ((request.get("target") or {}).get("product")),
        "request_id": request.get("request_id", ""),
        "request_fingerprint": request.get("request_fingerprint", ""),
    })
    prov = out.setdefault("provenance", {})
    prov.setdefault("records", []).append({
        "at": _now(),
        "action": "analysis_request_created",
        "target_product": ((request.get("target") or {}).get("product")),
        "request_id": request.get("request_id", ""),
    })
    out["updated_at"] = _now()
    out["version"] = app_version
    return out
