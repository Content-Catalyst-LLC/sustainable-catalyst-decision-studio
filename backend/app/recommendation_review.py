from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field

RECOMMENDATION_CANDIDATE_SCHEMA = "scds-recommendation-candidate/1.0"
RECOMMENDATION_CHALLENGE_SCHEMA = "scds-recommendation-challenge/1.0"
RECOMMENDATION_REVIEW_SCHEMA = "scds-recommendation-review/1.0"

BOUNDARY = (
    "A recommendation candidate is an explicitly selected option prepared for review. "
    "Decision Studio does not automatically select a winner, infer approval from a score, "
    "treat dependency structure as causal proof, or convert a review disposition into execution authority."
)

CHALLENGE_TYPES = {
    "evidence_gap", "assumption_dispute", "model_risk", "scenario_fragility",
    "criterion_weighting", "alternative_omission", "uncertainty", "dependency_break",
    "contextual_conflict", "implementation_risk", "other",
}
DISPOSITIONS = {"accept_for_decision", "accept_with_conditions", "reject", "revise", "defer"}


class RecommendationReviewRequest(BaseModel):
    packet: Dict[str, Any] = Field(default_factory=dict)
    decisionObject: Dict[str, Any] = Field(default_factory=dict)
    graph: Dict[str, Any] = Field(default_factory=dict)
    candidate: Dict[str, Any] = Field(default_factory=dict)
    challenges: List[Dict[str, Any]] = Field(default_factory=list)
    review: Dict[str, Any] = Field(default_factory=dict)
    selectedAlternativeId: str = ""
    rationale: List[Any] = Field(default_factory=list)
    supportNodeIds: List[str] = Field(default_factory=list)
    counterNodeIds: List[str] = Field(default_factory=list)
    conditions: List[Any] = Field(default_factory=list)
    requiredReviews: List[str] = Field(default_factory=list)
    challengeType: str = "other"
    targetNodeIds: List[str] = Field(default_factory=list)
    statement: str = ""
    evidenceRefs: List[str] = Field(default_factory=list)
    actor: str = ""
    challengeAction: str = "create"
    challengeId: str = ""
    challengeResolution: str = ""
    challengeStatus: str = "resolved"
    disposition: str = ""
    dispositionRationale: str = ""
    overrideOpenChallenges: bool = False


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _fingerprint(record: Dict[str, Any], field: str) -> str:
    return _hash({k: v for k, v in record.items() if k != field})


def _alt_id(record: Any) -> str:
    if not isinstance(record, dict):
        return ""
    for key in ("alternative_id", "id", "key", "slug", "name", "label"):
        value = record.get(key)
        if value not in (None, ""):
            return str(value)
    return ""


def _alternatives(obj: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in obj.get("alternatives") or []:
        if isinstance(row, dict):
            out.append(deepcopy(row))
    for aset in obj.get("alternatives_sets") or []:
        if isinstance(aset, dict):
            for row in aset.get("alternatives") or []:
                if isinstance(row, dict):
                    out.append(deepcopy(row))
    return out


def _graph_node_map(graph: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {
        str(node.get("node_id")): node
        for node in graph.get("nodes") or []
        if isinstance(node, dict) and node.get("node_id")
    }


def _find_alternative_node_ids(graph: Dict[str, Any], selected_id: str) -> List[str]:
    matches: List[str] = []
    for node in graph.get("nodes") or []:
        if not isinstance(node, dict) or node.get("node_type") != "alternative":
            continue
        record = node.get("record") or {}
        aliases = {
            str(node.get("node_id") or ""),
            str(record.get("alternative_id") or ""),
            str(record.get("id") or ""),
            str(record.get("name") or ""),
            str(record.get("label") or ""),
        }
        if selected_id in aliases:
            matches.append(str(node.get("node_id")))
    return matches


def _structural_ancestors(graph: Dict[str, Any], starts: List[str]) -> List[str]:
    reverse: Dict[str, List[str]] = {}
    for edge in graph.get("edges") or []:
        if not isinstance(edge, dict):
            continue
        source, target = str(edge.get("from") or ""), str(edge.get("to") or "")
        if source and target:
            reverse.setdefault(target, []).append(source)
    seen: Set[str] = set(starts)
    queue = list(starts)
    found: List[str] = []
    while queue:
        current = queue.pop(0)
        for prev in reverse.get(current, []):
            if prev not in seen:
                seen.add(prev)
                found.append(prev)
                queue.append(prev)
    return found


def recommendation_template(app_version: str) -> Dict[str, Any]:
    return {
        "schema": RECOMMENDATION_CANDIDATE_SCHEMA,
        "version": app_version,
        "candidate_id": "",
        "decision_id": "",
        "selected_alternative_id": "",
        "selected_alternative": {},
        "rationale": [],
        "explicit_support_node_ids": [],
        "explicit_counter_node_ids": [],
        "structural_dependency_node_ids": [],
        "conditions": [],
        "required_reviews": [],
        "created_at": "",
        "candidate_fingerprint": "",
        "human_selection_required": True,
        "automatic_selection": False,
        "automatic_approval": False,
        "boundary": BOUNDARY,
    }


def challenge_template(app_version: str) -> Dict[str, Any]:
    return {
        "schema": RECOMMENDATION_CHALLENGE_SCHEMA,
        "version": app_version,
        "challenge_id": "",
        "candidate_id": "",
        "challenge_type": "other",
        "statement": "",
        "target_node_ids": [],
        "evidence_refs": [],
        "status": "open",
        "raised_by": "",
        "raised_at": "",
        "resolution": "",
        "resolved_by": "",
        "resolved_at": "",
        "challenge_fingerprint": "",
        "automatic_disposition": False,
    }


def review_template(app_version: str) -> Dict[str, Any]:
    return {
        "schema": RECOMMENDATION_REVIEW_SCHEMA,
        "version": app_version,
        "review_id": "",
        "candidate_id": "",
        "review_status": "human_disposition_required",
        "challenge_counts": {"total": 0, "open": 0, "resolved": 0, "withdrawn": 0},
        "open_challenge_ids": [],
        "graph_review_flags": [],
        "required_reviews": [],
        "completed_reviews": [],
        "missing_required_reviews": [],
        "human_disposition": {},
        "decision_ready": False,
        "automatic_approval": False,
        "automatic_recommendation": False,
        "review_fingerprint": "",
        "boundary": BOUNDARY,
    }


def build_recommendation_candidate(
    decision_object: Dict[str, Any],
    graph: Dict[str, Any],
    *,
    app_version: str,
    selected_alternative_id: str,
    rationale: Optional[List[Any]] = None,
    support_node_ids: Optional[List[str]] = None,
    counter_node_ids: Optional[List[str]] = None,
    conditions: Optional[List[Any]] = None,
    required_reviews: Optional[List[str]] = None,
) -> Dict[str, Any]:
    selected_id = str(selected_alternative_id or "").strip()
    if not selected_id:
        raise ValueError("selectedAlternativeId is required; Decision Studio will not select a winner automatically")
    alternatives = _alternatives(decision_object or {})
    selected: Dict[str, Any] = {}
    for alt in alternatives:
        if _alt_id(alt) == selected_id:
            selected = alt
            break
    if alternatives and not selected:
        raise ValueError("selectedAlternativeId does not match an alternative in the Decision Object")
    if not selected:
        selected = {"alternative_id": selected_id, "label": selected_id, "source": "explicit_user_selection"}

    node_map = _graph_node_map(graph or {})
    support = list(dict.fromkeys([str(x) for x in (support_node_ids or []) if str(x)]))
    counters = list(dict.fromkeys([str(x) for x in (counter_node_ids or []) if str(x)]))
    missing = [x for x in support + counters if node_map and x not in node_map]
    if missing:
        raise ValueError("recommendation references unknown graph nodes: " + ", ".join(sorted(set(missing))))
    alt_nodes = _find_alternative_node_ids(graph or {}, selected_id)
    structural = _structural_ancestors(graph or {}, alt_nodes) if alt_nodes else []
    base = {
        "schema": RECOMMENDATION_CANDIDATE_SCHEMA,
        "version": app_version,
        "decision_id": str((decision_object or {}).get("decision_id") or ""),
        "selected_alternative_id": selected_id,
        "selected_alternative": deepcopy(selected),
        "rationale": deepcopy(rationale or []),
        "explicit_support_node_ids": support,
        "explicit_counter_node_ids": counters,
        "structural_dependency_node_ids": structural,
        "conditions": deepcopy(conditions or []),
        "required_reviews": list(dict.fromkeys([str(x) for x in (required_reviews or []) if str(x)])),
        "created_at": _now(),
        "human_selection_required": True,
        "automatic_selection": False,
        "automatic_approval": False,
        "boundary": BOUNDARY,
    }
    core = {k: v for k, v in base.items() if k != "created_at"}
    base["candidate_id"] = f"recommendation:{_hash(core)[:20]}"
    base["candidate_fingerprint"] = _fingerprint(base, "candidate_fingerprint")
    return base


def validate_recommendation_candidate(candidate: Dict[str, Any], *, app_version: str) -> Dict[str, Any]:
    c = candidate if isinstance(candidate, dict) else {}
    errors: List[str] = []
    if c.get("schema") != RECOMMENDATION_CANDIDATE_SCHEMA:
        errors.append("recommendation candidate schema is invalid")
    if not str(c.get("selected_alternative_id") or ""):
        errors.append("selected alternative is required")
    if c.get("automatic_selection") is True:
        errors.append("automatic winner selection is prohibited")
    if c.get("automatic_approval") is True:
        errors.append("automatic approval is prohibited")
    supplied = str(c.get("candidate_fingerprint") or "")
    if supplied and supplied != _fingerprint(c, "candidate_fingerprint"):
        errors.append("candidate fingerprint does not match candidate payload")
    return {"valid": not errors, "version": app_version, "errors": errors, "boundary": BOUNDARY}


def create_challenge(
    candidate: Dict[str, Any],
    *,
    app_version: str,
    challenge_type: str,
    statement: str,
    target_node_ids: Optional[List[str]] = None,
    evidence_refs: Optional[List[str]] = None,
    actor: str = "",
) -> Dict[str, Any]:
    ctype = challenge_type if challenge_type in CHALLENGE_TYPES else "other"
    text = str(statement or "").strip()
    if not text:
        raise ValueError("challenge statement is required")
    if not str(actor or "").strip():
        raise ValueError("challenge actor is required")
    base = {
        "schema": RECOMMENDATION_CHALLENGE_SCHEMA,
        "version": app_version,
        "candidate_id": str(candidate.get("candidate_id") or ""),
        "challenge_type": ctype,
        "statement": text,
        "target_node_ids": list(dict.fromkeys([str(x) for x in (target_node_ids or []) if str(x)])),
        "evidence_refs": list(dict.fromkeys([str(x) for x in (evidence_refs or []) if str(x)])),
        "status": "open",
        "raised_by": str(actor),
        "raised_at": _now(),
        "resolution": "",
        "resolved_by": "",
        "resolved_at": "",
        "automatic_disposition": False,
    }
    core = {k: v for k, v in base.items() if k != "raised_at"}
    base["challenge_id"] = f"challenge:{_hash(core)[:20]}"
    base["challenge_fingerprint"] = _fingerprint(base, "challenge_fingerprint")
    return base


def resolve_challenge(
    challenge: Dict[str, Any],
    *,
    app_version: str,
    actor: str,
    resolution: str,
    status: str = "resolved",
) -> Dict[str, Any]:
    if status not in {"resolved", "accepted", "withdrawn"}:
        raise ValueError("challengeStatus must be resolved, accepted, or withdrawn")
    if not str(actor or "").strip() or not str(resolution or "").strip():
        raise ValueError("resolving a challenge requires actor and resolution")
    out = deepcopy(challenge or {})
    out["version"] = app_version
    out["status"] = status
    out["resolution"] = str(resolution)
    out["resolved_by"] = str(actor)
    out["resolved_at"] = _now()
    out["automatic_disposition"] = False
    out["challenge_fingerprint"] = _fingerprint(out, "challenge_fingerprint")
    return out


def validate_challenge(challenge: Dict[str, Any], *, app_version: str) -> Dict[str, Any]:
    c = challenge if isinstance(challenge, dict) else {}
    errors: List[str] = []
    if c.get("schema") != RECOMMENDATION_CHALLENGE_SCHEMA:
        errors.append("recommendation challenge schema is invalid")
    if not str(c.get("statement") or ""):
        errors.append("challenge statement is required")
    if c.get("automatic_disposition") is True:
        errors.append("automatic challenge disposition is prohibited")
    supplied = str(c.get("challenge_fingerprint") or "")
    if supplied and supplied != _fingerprint(c, "challenge_fingerprint"):
        errors.append("challenge fingerprint does not match challenge payload")
    return {"valid": not errors, "version": app_version, "errors": errors}


def evaluate_recommendation(
    candidate: Dict[str, Any],
    challenges: List[Dict[str, Any]],
    graph: Dict[str, Any],
    *,
    app_version: str,
    completed_reviews: Optional[List[str]] = None,
) -> Dict[str, Any]:
    candidate_validation = validate_recommendation_candidate(candidate, app_version=app_version)
    challenge_rows = [deepcopy(x) for x in challenges if isinstance(x, dict)]
    open_rows = [x for x in challenge_rows if x.get("status", "open") == "open"]
    resolved = [x for x in challenge_rows if x.get("status") in {"resolved", "accepted"}]
    withdrawn = [x for x in challenge_rows if x.get("status") == "withdrawn"]
    required = list(dict.fromkeys([str(x) for x in candidate.get("required_reviews") or [] if str(x)]))
    completed = list(dict.fromkeys([str(x) for x in (completed_reviews or []) if str(x)]))
    missing_reviews = [x for x in required if x not in completed]
    flags: List[Dict[str, Any]] = []
    diagnostics = graph.get("diagnostics") if isinstance(graph, dict) else {}
    diagnostics = diagnostics if isinstance(diagnostics, dict) else {}
    for key in ("orphan_node_ids", "cycle_node_ids", "unresolved_references"):
        if diagnostics.get(key):
            flags.append({"type": key, "count": len(diagnostics.get(key) or []), "requires_review": True})
    if diagnostics.get("unsupported_recommendation"):
        flags.append({"type": "unsupported_recommendation", "count": 1, "requires_review": True})
    if not candidate_validation["valid"]:
        status = "invalid_candidate"
    elif open_rows:
        status = "blocked_by_open_challenges"
    elif missing_reviews:
        status = "required_reviews_incomplete"
    else:
        status = "human_disposition_required"
    review = {
        "schema": RECOMMENDATION_REVIEW_SCHEMA,
        "version": app_version,
        "candidate_id": str(candidate.get("candidate_id") or ""),
        "review_status": status,
        "challenge_counts": {"total": len(challenge_rows), "open": len(open_rows), "resolved": len(resolved), "withdrawn": len(withdrawn)},
        "open_challenge_ids": [str(x.get("challenge_id") or "") for x in open_rows],
        "graph_review_flags": flags,
        "required_reviews": required,
        "completed_reviews": completed,
        "missing_required_reviews": missing_reviews,
        "human_disposition": {},
        "decision_ready": False,
        "automatic_approval": False,
        "automatic_recommendation": False,
        "boundary": BOUNDARY,
    }
    review["review_id"] = f"review:{_hash({k:v for k,v in review.items() if k not in {'review_id','review_fingerprint'}})[:20]}"
    review["review_fingerprint"] = _fingerprint(review, "review_fingerprint")
    return review


def apply_human_disposition(
    review: Dict[str, Any],
    challenges: List[Dict[str, Any]],
    *,
    app_version: str,
    disposition: str,
    actor: str,
    rationale: str,
    override_open_challenges: bool = False,
) -> Dict[str, Any]:
    if disposition not in DISPOSITIONS:
        raise ValueError("disposition must be one of: " + ", ".join(sorted(DISPOSITIONS)))
    if not str(actor or "").strip() or not str(rationale or "").strip():
        raise ValueError("human disposition requires actor and rationale")
    open_ids = [str(x.get("challenge_id") or "") for x in challenges if isinstance(x, dict) and x.get("status", "open") == "open"]
    if open_ids and disposition in {"accept_for_decision", "accept_with_conditions"} and not override_open_challenges:
        raise ValueError("open challenges require explicit overrideOpenChallenges before an accepting disposition")
    out = deepcopy(review or {})
    out["version"] = app_version
    out["human_disposition"] = {
        "disposition": disposition,
        "actor": str(actor),
        "rationale": str(rationale),
        "at": _now(),
        "open_challenge_ids": open_ids,
        "override_open_challenges": bool(override_open_challenges),
        "execution_authorized": False,
        "approval_inferred": False,
    }
    out["review_status"] = "human_disposition_recorded"
    out["decision_ready"] = disposition in {"accept_for_decision", "accept_with_conditions"}
    out["automatic_approval"] = False
    out["automatic_recommendation"] = False
    out["review_fingerprint"] = _fingerprint(out, "review_fingerprint")
    return out


def validate_review(review: Dict[str, Any], *, app_version: str) -> Dict[str, Any]:
    r = review if isinstance(review, dict) else {}
    errors: List[str] = []
    if r.get("schema") != RECOMMENDATION_REVIEW_SCHEMA:
        errors.append("recommendation review schema is invalid")
    if r.get("automatic_approval") is True:
        errors.append("automatic approval is prohibited")
    if r.get("automatic_recommendation") is True:
        errors.append("automatic recommendation is prohibited")
    supplied = str(r.get("review_fingerprint") or "")
    if supplied and supplied != _fingerprint(r, "review_fingerprint"):
        errors.append("review fingerprint does not match review payload")
    return {"valid": not errors, "version": app_version, "errors": errors, "boundary": BOUNDARY}


def attach_recommendation_review(
    decision_object: Dict[str, Any],
    candidate: Dict[str, Any],
    challenges: List[Dict[str, Any]],
    review: Dict[str, Any],
    *,
    app_version: str,
) -> Dict[str, Any]:
    out = deepcopy(decision_object or {})
    out.setdefault("schema", "scds-decision-object/1.0")
    out.setdefault("recommendation_candidates", [])
    out.setdefault("recommendation_challenges", [])
    out.setdefault("recommendation_reviews", [])
    cid = candidate.get("candidate_id")
    out["recommendation_candidates"] = [x for x in out["recommendation_candidates"] if not isinstance(x, dict) or x.get("candidate_id") != cid] + [deepcopy(candidate)]
    existing_challenge_ids = {str(x.get("challenge_id") or "") for x in challenges if isinstance(x, dict)}
    out["recommendation_challenges"] = [x for x in out["recommendation_challenges"] if not isinstance(x, dict) or str(x.get("challenge_id") or "") not in existing_challenge_ids] + deepcopy(challenges)
    rid = review.get("review_id")
    out["recommendation_reviews"] = [x for x in out["recommendation_reviews"] if not isinstance(x, dict) or x.get("review_id") != rid] + [deepcopy(review)]
    out.setdefault("links", []).append({
        "relationship": "recommendation_review",
        "candidate_id": cid,
        "review_id": rid,
        "selected_alternative_id": candidate.get("selected_alternative_id", ""),
        "human_disposition": deepcopy(review.get("human_disposition") or {}),
        "automatic_approval": False,
    })
    provenance = out.setdefault("provenance", {})
    provenance.setdefault("records", []).append({
        "at": _now(),
        "action": "recommendation_review_attached",
        "candidate_id": cid,
        "review_id": rid,
        "candidate_fingerprint": candidate.get("candidate_fingerprint", ""),
        "review_fingerprint": review.get("review_fingerprint", ""),
    })
    out["version"] = app_version
    return out
