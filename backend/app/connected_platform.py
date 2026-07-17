from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field

CONNECTED_PLATFORM_SCHEMA = "scds-connected-decision-platform/2.0"
LIFECYCLE_ASSESSMENT_SCHEMA = "scds-decision-lifecycle-assessment/1.0"
DECISION_INTELLIGENCE_GRAPH_SCHEMA = "scds-decision-intelligence-graph/1.0"
ACTION_QUEUE_SCHEMA = "scds-decision-action-queue/1.0"
PORTFOLIO_INDEX_SCHEMA = "scds-decision-portfolio-index/1.0"
CONNECTED_EXCHANGE_SCHEMA = "scds-connected-platform-exchange/1.0"
LIFECYCLE_EVENT_SCHEMA = "scds-decision-lifecycle-event/1.0"


class ConnectedPlatformRequest(BaseModel):
    packet: Dict[str, Any] = Field(default_factory=dict)
    packets: List[Dict[str, Any]] = Field(default_factory=list)
    actor: str = ""
    actorRole: str = ""
    requestedStage: str = ""
    transitionReason: str = ""
    includeGraph: bool = True
    includeExchange: bool = True
    notes: str = ""
    action: str = "assess"


LIFECYCLE_STAGES: List[Dict[str, Any]] = [
    {"id": "frame", "label": "Frame", "products": ["Decision Studio"], "purpose": "Define the decision question, boundaries, owners, and institutional context."},
    {"id": "research", "label": "Research", "products": ["Research Librarian", "Knowledge Library"], "purpose": "Route research, identify relevant sources, and expose evidence gaps."},
    {"id": "evidence", "label": "Gather Evidence", "products": ["Knowledge Library", "Site Intelligence"], "purpose": "Attach durable sources, citations, live observations, confidence, freshness, and provenance."},
    {"id": "model", "label": "Model", "products": ["Workbench", "Research Lab"], "purpose": "Calculate, simulate, test, validate, and document technical assumptions."},
    {"id": "compare", "label": "Compare", "products": ["Decision Studio", "Workbench"], "purpose": "Compare alternatives, scenarios, sensitivity, thresholds, stakeholders, and time horizons."},
    {"id": "challenge", "label": "Challenge Assumptions", "products": ["Decision Studio", "Research Librarian"], "purpose": "Review assumptions, claims, contradictions, risks, exceptions, and contested evidence."},
    {"id": "review", "label": "Review", "products": ["Decision Studio"], "purpose": "Coordinate reviewers, comments, change requests, conditions, conflicts, and sign-offs."},
    {"id": "approve", "label": "Approve", "products": ["Decision Studio"], "purpose": "Record a named-human governance decision and lock the reviewed version."},
    {"id": "publish", "label": "Publish", "products": ["Decision Studio", "Knowledge Library", "Publications", "Channel"], "purpose": "Create governed internal, institutional, or public decision publications."},
    {"id": "implement", "label": "Implement", "products": ["Decision Studio", "Contact and Engagement"], "purpose": "Assign commitments, owners, milestones, and implementation status."},
    {"id": "monitor", "label": "Monitor", "products": ["Site Intelligence", "Decision Studio"], "purpose": "Track observations, targets, milestones, risks, and actual-versus-expected results."},
    {"id": "reassess", "label": "Reassess", "products": ["Decision Studio", "Platform Core"], "purpose": "Record reassessments, amendments, retirement, lessons, and durable Decision Registry state."},
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _hash(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _nonempty(value: Any) -> bool:
    return value not in (None, "", {}, [])


def _records(packet: Dict[str, Any], *paths: str) -> List[Any]:
    for path in paths:
        value: Any = packet
        for part in path.split("."):
            if not isinstance(value, dict):
                value = None
                break
            value = value.get(part)
        if isinstance(value, list) and value:
            return value
    return []


def _dict(packet: Dict[str, Any], *paths: str) -> Dict[str, Any]:
    for path in paths:
        value: Any = packet
        for part in path.split("."):
            if not isinstance(value, dict):
                value = None
                break
            value = value.get(part)
        if isinstance(value, dict) and value:
            return value
    return {}


def _decision_question(packet: Dict[str, Any]) -> str:
    return str(
        _dict(packet, "decision_framing").get("decision_question")
        or _dict(packet, "project").get("decision_question")
        or packet.get("decision_question")
        or ""
    ).strip()


def connected_platform_template(app_version: str, packet_schema: str) -> Dict[str, Any]:
    return {
        "schema": CONNECTED_PLATFORM_SCHEMA,
        "version": app_version,
        "decision_packet_schema": packet_schema,
        "lifecycle": deepcopy(LIFECYCLE_STAGES),
        "product_roles": {
            "Research Librarian": "Research routing, evidence gaps, and follow-up questions.",
            "Knowledge Library": "Durable sources, citations, quotations, collections, and reviewed publication handoffs.",
            "Site Intelligence": "Live and comparative indicators, monitoring observations, freshness, and methodology.",
            "Research Lab": "Experiments, notebooks, datasets, validation results, and scientific limitations.",
            "Workbench": "Calculations, simulations, sensitivity, optimization, graphs, and technical reports.",
            "Decision Studio": "Alternatives, governance, collaboration, approval, publication, implementation, monitoring, and reassessment.",
            "Platform Core": "Shared identity, provenance, Evidence Ledger, Decision Registry, events, and exchange manifests.",
        },
        "human_controls": [
            "Lifecycle assessment may recommend actions but cannot approve a decision.",
            "Approval, amendment, suspension, retirement, publication delivery, and professional sign-off require authorized humans.",
            "Connected product routes are structured handoffs; they do not claim external acceptance or execution.",
        ],
        "portfolio_limit": 100,
    }


def _stage_signals(packet: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    governance = _dict(packet, "governance_center")
    collaboration = _dict(packet, "collaboration_room")
    publication = _dict(packet, "publication_studio")
    outcomes = _dict(packet, "outcome_monitoring")
    scenario = _dict(packet, "scenario_studio", "scenario_comparison")
    review_history = _records(packet, "governance_center.review_history")
    reviewers = _records(packet, "governance_center.reviewers")
    signoffs = _records(packet, "governance_center.signoffs")
    comments = _records(packet, "collaboration_room.comments")
    changes = _records(packet, "collaboration_room.change_requests")
    evidence = (
        _records(packet, "evidence_registry")
        or _records(packet, "evidence_and_measurement.records")
        or _records(packet, "sources")
        or _records(packet, "evidence_ledger")
    )
    research = _records(packet, "research_routes") or _records(packet, "evidence_plan") or _records(packet, "follow_up_questions")
    models = (
        _records(packet, "technical_artifacts")
        or _records(packet, "calculation_trace")
        or _records(packet, "workbench_handoffs")
        or _records(packet, "experimental_evidence")
        or _records(packet, "model_plan")
    )
    alternatives = _records(packet, "scenario_studio.alternatives") or _records(packet, "scenario_comparison.matrix") or _records(packet, "scenarios.records")
    challenges = (
        _records(packet, "assumptions")
        or _records(packet, "risks")
        or _records(packet, "claim_and_risk_review.records")
        or _records(packet, "governance_center.exceptions")
        or _records(packet, "evidence_gaps")
    )
    owner = _dict(packet, "governance_center.owner")
    governance_state = str(governance.get("current_state", "draft"))
    approved = governance_state in {"approved", "implemented", "retired"}
    locked = _nonempty(collaboration.get("locked_version")) or bool(collaboration.get("locked", False))
    publications = _records(packet, "publication_registry") or ([publication] if publication else [])
    commitments = _records(packet, "outcome_monitoring.commitments")
    milestones = _records(packet, "outcome_monitoring.milestones")
    targets = _records(packet, "outcome_monitoring.targets")
    observations = _records(packet, "outcome_monitoring.observations")
    registry = _dict(packet, "decision_registry_entry")
    reassessments = _records(packet, "reassessment_history")
    amendments = _records(packet, "implementation_amendments")
    monitoring_status = str(outcomes.get("monitoring_status") or outcomes.get("status") or "")
    implementation_status = str(outcomes.get("implementation_status") or "")

    return {
        "frame": {"count": 1 if _decision_question(packet) else 0, "complete": bool(_decision_question(packet)), "missing": [] if _decision_question(packet) else ["decision_question"]},
        "research": {"count": len(research), "complete": bool(research), "missing": [] if research else ["research_route_or_evidence_plan"]},
        "evidence": {"count": len(evidence), "complete": bool(evidence), "missing": [] if evidence else ["reviewable_evidence_record"]},
        "model": {"count": len(models), "complete": bool(models), "missing": [] if models else ["calculation_experiment_or_model"]},
        "compare": {"count": len(alternatives), "complete": len(alternatives) >= 2, "missing": [] if len(alternatives) >= 2 else ["at_least_two_alternatives"]},
        "challenge": {"count": len(challenges), "complete": bool(challenges), "missing": [] if challenges else ["assumption_risk_or_evidence_gap_review"]},
        "review": {"count": len(reviewers) + len(comments) + len(changes) + len(review_history), "complete": bool(owner) and bool(reviewers or review_history) and bool(signoffs), "missing": [item for item, present in {"decision_owner": bool(owner), "reviewer_or_review_event": bool(reviewers or review_history), "human_signoff": bool(signoffs)}.items() if not present]},
        "approve": {"count": len(signoffs), "complete": approved, "missing": [] if approved else ["approved_or_implemented_governance_state"]},
        "publish": {"count": len(publications), "complete": bool(publications), "missing": [] if publications else ["governed_publication"]},
        "implement": {"count": len(commitments) + len(milestones), "complete": implementation_status in {"implemented", "amended", "suspended", "retired"} or (bool(commitments) and bool(milestones)), "missing": [item for item, present in {"implementation_commitment": bool(commitments), "implementation_milestone": bool(milestones)}.items() if not present]},
        "monitor": {"count": len(targets) + len(observations), "complete": bool(targets) and bool(observations) and monitoring_status in {"on_track", "watch", "reassessment_required", "closed"}, "missing": [item for item, present in {"monitoring_target": bool(targets), "monitoring_observation": bool(observations), "monitoring_status": bool(monitoring_status)}.items() if not present]},
        "reassess": {"count": len(reassessments) + len(amendments) + (1 if registry else 0), "complete": bool(registry) and (bool(reassessments) or implementation_status == "retired"), "missing": [item for item, present in {"decision_registry_entry": bool(registry), "reassessment_or_retirement": bool(reassessments) or implementation_status == "retired"}.items() if not present]},
        "approved_locked": {"complete": approved and locked, "count": int(approved) + int(locked), "missing": []},
    }


def assess_lifecycle(packet: Dict[str, Any], app_version: str, packet_schema: str) -> Dict[str, Any]:
    signals = _stage_signals(packet)
    stages: List[Dict[str, Any]] = []
    blockers: List[Dict[str, Any]] = []
    first_incomplete = "complete"
    prior_complete = True
    complete_count = 0
    for index, stage in enumerate(LIFECYCLE_STAGES):
        signal = signals[stage["id"]]
        complete = bool(signal["complete"])
        if complete:
            status = "complete"
            complete_count += 1
        elif not prior_complete:
            status = "blocked_by_prior_stage"
        elif signal["count"]:
            status = "attention"
        else:
            status = "not_started"
        if not complete and first_incomplete == "complete":
            first_incomplete = stage["id"]
        missing = list(signal.get("missing", []))
        if not complete:
            severity = "critical" if stage["id"] in {"frame", "evidence", "review", "approve"} else "high" if stage["id"] in {"model", "compare", "monitor"} else "medium"
            blockers.append({"stage": stage["id"], "severity": severity, "missing": missing, "products": stage["products"]})
        stages.append({
            **stage,
            "sequence": index + 1,
            "status": status,
            "complete": complete,
            "record_count": signal.get("count", 0),
            "missing": missing,
        })
        prior_complete = prior_complete and complete

    percent = round((complete_count / len(LIFECYCLE_STAGES)) * 100, 1)
    governance = _dict(packet, "governance_center")
    assessment = {
        "schema": LIFECYCLE_ASSESSMENT_SCHEMA,
        "version": app_version,
        "decision_packet_schema": packet_schema,
        "generated_at": _utc_now(),
        "decision_packet_id": str(packet.get("decision_packet_id") or "SCDS-DRAFT"),
        "decision_question": _decision_question(packet),
        "current_stage": first_incomplete,
        "lifecycle_completion_percent": percent,
        "completed_stages": complete_count,
        "total_stages": len(LIFECYCLE_STAGES),
        "stages": stages,
        "blockers": blockers,
        "governance_state": governance.get("current_state", "draft"),
        "human_approval_required": True,
        "automatic_approval_allowed": False,
        "status": "complete" if complete_count == len(LIFECYCLE_STAGES) else ("decision_approved_in_progress" if signals["approve"]["complete"] else "active"),
    }
    assessment["content_hash"] = _hash({k: v for k, v in assessment.items() if k != "content_hash"})
    return assessment


def build_action_queue(assessment: Dict[str, Any], app_version: str) -> Dict[str, Any]:
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    actions: List[Dict[str, Any]] = []
    for blocker in assessment.get("blockers", []):
        stage_id = blocker.get("stage", "")
        stage = next((item for item in LIFECYCLE_STAGES if item["id"] == stage_id), {})
        missing = blocker.get("missing", []) or ["stage_evidence"]
        for item in missing:
            actions.append({
                "action_id": f"{stage_id}:{item}",
                "stage": stage_id,
                "stage_label": stage.get("label", stage_id.title()),
                "severity": blocker.get("severity", "medium"),
                "action": f"Add or review {str(item).replace('_', ' ')}.",
                "route_to": blocker.get("products", stage.get("products", ["Decision Studio"])),
                "human_confirmation_required": stage_id in {"review", "approve", "publish", "implement", "reassess"},
            })
    actions.sort(key=lambda item: (severity_order.get(item["severity"], 9), next((i for i, s in enumerate(LIFECYCLE_STAGES) if s["id"] == item["stage"]), 99)))
    queue = {
        "schema": ACTION_QUEUE_SCHEMA,
        "version": app_version,
        "generated_at": _utc_now(),
        "decision_packet_id": assessment.get("decision_packet_id", "SCDS-DRAFT"),
        "current_stage": assessment.get("current_stage", "frame"),
        "actions": actions[:50],
        "action_count": len(actions[:50]),
        "human_controlled_actions": sum(1 for item in actions[:50] if item["human_confirmation_required"]),
    }
    queue["content_hash"] = _hash(queue)
    return queue


def _node_id(prefix: str, value: Any) -> str:
    return prefix + "-" + hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()[:12]


def build_intelligence_graph(packet: Dict[str, Any], app_version: str) -> Dict[str, Any]:
    packet_id = str(packet.get("decision_packet_id") or "SCDS-DRAFT")
    nodes: List[Dict[str, Any]] = [{"id": f"decision:{packet_id}", "type": "decision", "label": _decision_question(packet) or packet_id, "source": "Decision Studio"}]
    edges: List[Dict[str, Any]] = []

    groups = [
        ("evidence", _records(packet, "evidence_registry", "evidence_and_measurement.records", "sources"), "supports", "Knowledge Library"),
        ("indicator", _records(packet, "live_evidence", "outcome_monitoring.observations"), "observes", "Site Intelligence"),
        ("model", _records(packet, "technical_artifacts", "calculation_trace", "workbench_handoffs"), "models", "Workbench"),
        ("experiment", _records(packet, "experimental_evidence", "datasets"), "tests", "Research Lab"),
        ("alternative", _records(packet, "scenario_studio.alternatives", "scenario_comparison.matrix", "scenarios.records"), "compares", "Decision Studio"),
        ("risk", _records(packet, "risks", "claim_and_risk_review.records", "governance_center.exceptions"), "challenges", "Decision Studio"),
        ("publication", _records(packet, "publication_registry"), "publishes", "Decision Studio"),
        ("reassessment", _records(packet, "reassessment_history"), "reassesses", "Decision Studio"),
    ]
    for node_type, records, relation, source in groups:
        for record in records[:100]:
            label = ""
            if isinstance(record, dict):
                for key in ("title", "name", "label", "claim", "indicator", "publication_id", "event_id", "id"):
                    if record.get(key):
                        label = str(record[key])
                        break
            label = label or f"{node_type.title()} record"
            node_id = _node_id(node_type, record)
            nodes.append({"id": node_id, "type": node_type, "label": label[:240], "source": source, "content_hash": _hash(record)})
            edges.append({"id": _node_id("edge", [node_id, packet_id, relation]), "from": node_id, "to": f"decision:{packet_id}", "relationship": relation})

    entities = _records(packet, "entities")
    for entity in entities[:100]:
        label = str(entity.get("name") or entity.get("label") or "Entity") if isinstance(entity, dict) else str(entity)
        node_id = _node_id("entity", entity)
        nodes.append({"id": node_id, "type": "entity", "label": label[:240], "source": "Platform Core", "content_hash": _hash(entity)})
        edges.append({"id": _node_id("edge", [node_id, packet_id, "governs"]), "from": f"decision:{packet_id}", "to": node_id, "relationship": "concerns"})

    graph = {
        "schema": DECISION_INTELLIGENCE_GRAPH_SCHEMA,
        "version": app_version,
        "generated_at": _utc_now(),
        "decision_packet_id": packet_id,
        "nodes": nodes,
        "edges": edges,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "truncated": any(len(records) > 100 for _, records, _, _ in groups) or len(entities) > 100,
        "boundaries": ["Graph relationships are derived from packet structure and require human interpretation.", "No causal claim is created solely by an edge in this graph."],
    }
    graph["content_hash"] = _hash({k: v for k, v in graph.items() if k != "content_hash"})
    return graph


def _portfolio_record(packet: Dict[str, Any], app_version: str, packet_schema: str) -> Dict[str, Any]:
    assessment = assess_lifecycle(packet, app_version, packet_schema)
    governance = _dict(packet, "governance_center")
    outcomes = _dict(packet, "outcome_monitoring")
    risks = _records(packet, "risks", "governance_center.exceptions", "outcome_monitoring.emerging_risks")
    high_risks = sum(1 for risk in risks if isinstance(risk, dict) and str(risk.get("severity") or risk.get("risk_level") or "").lower() in {"high", "critical"})
    return {
        "decision_packet_id": assessment["decision_packet_id"],
        "decision_question": assessment["decision_question"],
        "project_name": _dict(packet, "project").get("project_name", ""),
        "current_stage": assessment["current_stage"],
        "lifecycle_completion_percent": assessment["lifecycle_completion_percent"],
        "governance_state": governance.get("current_state", "draft"),
        "monitoring_status": outcomes.get("monitoring_status") or outcomes.get("status") or "not_started",
        "implementation_status": outcomes.get("implementation_status") or "not_implemented",
        "high_or_critical_risks": high_risks,
        "attention_required": bool(assessment["blockers"]) or high_risks > 0 or str(outcomes.get("monitoring_status", "")) == "reassessment_required",
        "packet_hash": _hash(packet),
    }


def build_portfolio_index(packets: List[Dict[str, Any]], app_version: str, packet_schema: str) -> Dict[str, Any]:
    capped = [packet for packet in packets[:100] if isinstance(packet, dict)]
    records = [_portfolio_record(packet, app_version, packet_schema) for packet in capped]
    records.sort(key=lambda item: (not item["attention_required"], item["lifecycle_completion_percent"], item["decision_packet_id"]))
    index = {
        "schema": PORTFOLIO_INDEX_SCHEMA,
        "version": app_version,
        "decision_packet_schema": packet_schema,
        "generated_at": _utc_now(),
        "records": records,
        "record_count": len(records),
        "attention_count": sum(1 for item in records if item["attention_required"]),
        "approved_count": sum(1 for item in records if item["governance_state"] in {"approved", "implemented", "retired"}),
        "reassessment_required_count": sum(1 for item in records if item["monitoring_status"] == "reassessment_required"),
        "truncated": len(packets) > 100,
    }
    index["content_hash"] = _hash({k: v for k, v in index.items() if k != "content_hash"})
    return index


def build_connected_exchange(packet: Dict[str, Any], assessment: Dict[str, Any], graph: Dict[str, Any], app_version: str, packet_schema: str) -> Dict[str, Any]:
    sections = {
        "decision_framing": packet.get("decision_framing", {}),
        "evidence_registry": packet.get("evidence_registry", []),
        "scenario_studio": packet.get("scenario_studio", {}),
        "governance_center": packet.get("governance_center", {}),
        "publication_registry": packet.get("publication_registry", []),
        "outcome_monitoring": packet.get("outcome_monitoring", {}),
        "decision_registry_entry": packet.get("decision_registry_entry", {}),
        "platform_core_gateway": packet.get("platform_core_gateway", {}),
    }
    manifest_records = [{"section": key, "content_hash": _hash(value)} for key, value in sections.items() if _nonempty(value)]
    exchange = {
        "schema": CONNECTED_EXCHANGE_SCHEMA,
        "version": app_version,
        "decision_packet_schema": packet_schema,
        "generated_at": _utc_now(),
        "decision_packet_id": assessment.get("decision_packet_id", "SCDS-DRAFT"),
        "lifecycle_assessment_hash": assessment.get("content_hash", ""),
        "intelligence_graph_hash": graph.get("content_hash", ""),
        "manifest_records": manifest_records,
        "product_routes": connected_platform_template(app_version, packet_schema)["product_roles"],
        "exchange_status": "prepared_not_delivered",
        "external_acceptance_claimed": False,
        "human_confirmation_required": True,
    }
    exchange["content_hash"] = _hash({k: v for k, v in exchange.items() if k != "content_hash"})
    return exchange


def verify_lifecycle_history(history: List[Dict[str, Any]]) -> Dict[str, Any]:
    previous = "GENESIS"
    for index, event in enumerate(history):
        candidate = deepcopy(event)
        supplied_hash = str(candidate.pop("event_hash", ""))
        if candidate.get("previous_hash") != previous:
            return {"ok": False, "valid": False, "index": index, "reason": "previous_hash_mismatch"}
        expected = _hash(candidate)
        if supplied_hash != expected:
            return {"ok": False, "valid": False, "index": index, "reason": "event_hash_mismatch", "expected": expected, "supplied": supplied_hash}
        previous = supplied_hash
    return {"ok": True, "valid": True, "event_count": len(history), "last_hash": previous}


def _append_lifecycle_event(history: List[Dict[str, Any]], actor: str, actor_role: str, from_stage: str, to_stage: str, reason: str) -> List[Dict[str, Any]]:
    new_history = deepcopy(history)
    previous = new_history[-1].get("event_hash", "GENESIS") if new_history else "GENESIS"
    event = {
        "schema": LIFECYCLE_EVENT_SCHEMA,
        "event_id": "life-" + hashlib.sha256(f"{actor}|{from_stage}|{to_stage}|{_utc_now()}|{len(new_history)}".encode()).hexdigest()[:18],
        "sequence": len(new_history) + 1,
        "event_type": "lifecycle_stage_confirmed",
        "actor": actor.strip(),
        "actor_role": actor_role.strip(),
        "from_stage": from_stage,
        "to_stage": to_stage,
        "reason": reason.strip(),
        "created_at": _utc_now(),
        "previous_hash": previous,
        "automatic_transition": False,
    }
    event["event_hash"] = _hash(event)
    new_history.append(event)
    return new_history


def orchestrate_connected_platform(
    req: ConnectedPlatformRequest,
    app_version: str,
    packet_schema: str,
    packet_template_factory: Optional[Callable[[], Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    packet = packet_template_factory() if packet_template_factory else {}
    packet.update(deepcopy(req.packet or {}))
    packet["packet_version"] = app_version
    packet["decision_packet_schema"] = packet_schema
    packet["connected_platform_schema"] = CONNECTED_PLATFORM_SCHEMA

    assessment = assess_lifecycle(packet, app_version, packet_schema)
    history = list(packet.get("lifecycle_history", [])) if isinstance(packet.get("lifecycle_history"), list) else []
    requested = req.requestedStage.strip().lower()
    if req.action == "transition" or requested:
        stage_ids = [stage["id"] for stage in LIFECYCLE_STAGES]
        if not req.actor.strip():
            return {"ok": False, "version": app_version, "error": "human_actor_required", "message": "A named human actor is required to confirm a lifecycle transition."}
        if requested not in stage_ids:
            return {"ok": False, "version": app_version, "error": "invalid_lifecycle_stage", "allowed_stages": stage_ids}
        requested_stage = next(stage for stage in assessment["stages"] if stage["id"] == requested)
        if not requested_stage["complete"]:
            return {"ok": False, "version": app_version, "error": "lifecycle_stage_incomplete", "stage": requested, "missing": requested_stage["missing"]}
        current_confirmed = str(packet.get("connected_platform", {}).get("confirmed_stage") or "frame") if isinstance(packet.get("connected_platform"), dict) else "frame"
        history = _append_lifecycle_event(history, req.actor, req.actorRole or "decision_owner", current_confirmed, requested, req.transitionReason)

    graph = build_intelligence_graph(packet, app_version) if req.includeGraph else {"schema": DECISION_INTELLIGENCE_GRAPH_SCHEMA, "nodes": [], "edges": [], "node_count": 0, "edge_count": 0}
    queue = build_action_queue(assessment, app_version)
    portfolio_packets = req.packets or [packet]
    portfolio = build_portfolio_index(portfolio_packets, app_version, packet_schema)
    exchange = build_connected_exchange(packet, assessment, graph, app_version, packet_schema) if req.includeExchange else {}
    confirmed_stage = history[-1]["to_stage"] if history else str(packet.get("connected_platform", {}).get("confirmed_stage") or "") if isinstance(packet.get("connected_platform"), dict) else ""
    platform = {
        "schema": CONNECTED_PLATFORM_SCHEMA,
        "version": app_version,
        "decision_packet_schema": packet_schema,
        "generated_at": _utc_now(),
        "confirmed_stage": confirmed_stage,
        "lifecycle_assessment": assessment,
        "action_queue": queue,
        "intelligence_graph": graph,
        "portfolio_index": portfolio,
        "connected_exchange": exchange,
        "lifecycle_history": history,
        "lifecycle_history_verification": verify_lifecycle_history(history),
        "notes": req.notes,
        "human_approval_required": True,
        "automatic_approval_allowed": False,
        "automatic_external_delivery_allowed": False,
    }
    platform["content_hash"] = _hash({k: v for k, v in platform.items() if k != "content_hash"})

    packet["connected_platform"] = platform
    packet["lifecycle_assessment"] = assessment
    packet["decision_intelligence_graph"] = graph
    packet["decision_action_queue"] = queue
    packet["decision_portfolio_index"] = portfolio
    packet["connected_exchange"] = exchange
    packet["lifecycle_history"] = history
    formats = packet.setdefault("export_center", {}).setdefault("available_formats", [])
    for item in ["connected_platform_json", "lifecycle_assessment_json", "decision_intelligence_graph_json", "decision_action_queue_json", "decision_portfolio_index_json", "connected_exchange_json"]:
        if item not in formats:
            formats.append(item)

    return {
        "ok": True,
        "version": app_version,
        "schema": CONNECTED_PLATFORM_SCHEMA,
        "connected_platform": platform,
        "lifecycle_assessment": assessment,
        "action_queue": queue,
        "intelligence_graph": graph,
        "portfolio_index": portfolio,
        "connected_exchange": exchange,
        "decision_packet": packet,
        "template": connected_platform_template(app_version, packet_schema),
    }
