from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from pydantic import BaseModel, Field

DEPENDENCY_GRAPH_SCHEMA = "scds-decision-dependency-graph/1.0"
DEPENDENCY_DIAGNOSTICS_SCHEMA = "scds-dependency-diagnostics/1.0"
CHANGE_IMPACT_SCHEMA = "scds-change-impact-assessment/1.0"

BOUNDARY = (
    "The dependency graph records explicit and structural relationships inside a Decision Object. "
    "An edge is not causal proof, node degree is not importance, and downstream reachability is not automatic invalidation, approval, or recommendation."
)


class DependencyGraphRequest(BaseModel):
    packet: Dict[str, Any] = Field(default_factory=dict)
    decisionObject: Dict[str, Any] = Field(default_factory=dict)
    graph: Dict[str, Any] = Field(default_factory=dict)
    explicitEdges: List[Dict[str, Any]] = Field(default_factory=list)
    changedNodeIds: List[str] = Field(default_factory=list)
    includeStructuralEdges: bool = True


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return deepcopy(value)
    if value in (None, "", {}):
        return []
    return [deepcopy(value)]


def _label(record: Any, fallback: str) -> str:
    if isinstance(record, dict):
        for key in (
            "label", "title", "name", "question", "summary", "claim", "indicator", "signal_id",
            "scenario_id", "criterion_id", "alternative_id", "matrix_id", "request_id", "handoff_id",
            "uncertainty_id", "context_id", "artifact_id", "id",
        ):
            if record.get(key) not in (None, ""):
                return str(record[key])[:240]
    if isinstance(record, str) and record.strip():
        return record.strip()[:240]
    return fallback


def _stable_key(kind: str, record: Any, index: int) -> str:
    if isinstance(record, dict):
        for key in (
            "node_id", "decision_id", "evidence_id", "source_id", "assumption_id", "model_id", "artifact_id",
            "handoff_id", "scenario_id", "criterion_id", "alternative_id", "uncertainty_id", "matrix_id",
            "scenario_set_id", "scenario_comparison_id", "stress_test_suite_id", "request_id", "context_id",
            "snapshot_id", "bundle_id", "id",
        ):
            value = record.get(key)
            if value not in (None, ""):
                return str(value)
    return f"{kind}:{index}:{_hash(record)[:16]}"


def _node_id(kind: str, key: str) -> str:
    safe = str(key).strip()
    return f"{kind}:{safe}" if safe else f"{kind}:{_hash([kind, key])[:16]}"


def _edge_id(source: str, target: str, relationship: str, origin: str = "structural") -> str:
    return f"edge:{_hash([source, target, relationship, origin])[:20]}"


def _aliases(record: Any, node_id: str) -> List[str]:
    out = [node_id]
    if isinstance(record, dict):
        for key in (
            "node_id", "decision_id", "evidence_id", "source_id", "assumption_id", "model_id", "artifact_id",
            "handoff_id", "scenario_id", "criterion_id", "alternative_id", "uncertainty_id", "matrix_id",
            "scenario_set_id", "scenario_comparison_id", "stress_test_suite_id", "request_id", "context_id",
            "snapshot_id", "bundle_id", "id", "signal_id",
        ):
            value = record.get(key)
            if value not in (None, ""):
                out.append(str(value))
    return list(dict.fromkeys(out))


def _records(obj: Dict[str, Any], *keys: str) -> List[Any]:
    for key in keys:
        value: Any = obj
        for part in key.split("."):
            if not isinstance(value, dict):
                value = None
                break
            value = value.get(part)
        if isinstance(value, list) and value:
            return deepcopy(value)
    return []


def _add_edge(
    edges: List[Dict[str, Any]],
    seen: Set[Tuple[str, str, str]],
    source: str,
    target: str,
    relationship: str,
    *,
    origin: str = "structural",
    explicit: bool = False,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    if not source or not target or source == target:
        return
    key = (source, target, relationship)
    if key in seen:
        return
    seen.add(key)
    edges.append({
        "edge_id": _edge_id(source, target, relationship, origin),
        "from": source,
        "to": target,
        "relationship": relationship,
        "origin": origin,
        "explicit": bool(explicit),
        "causal_claim": False,
        "automatic_invalidation": False,
        "metadata": deepcopy(metadata or {}),
    })


def _refs(record: Any) -> List[Tuple[str, str]]:
    if not isinstance(record, dict):
        return []
    mapping = {
        "depends_on": "depends_on",
        "dependency_refs": "depends_on",
        "evidence_refs": "supported_by",
        "source_refs": "supported_by",
        "assumption_refs": "conditioned_by",
        "model_refs": "modeled_by",
        "scenario_refs": "scenario_context",
        "criterion_refs": "evaluated_by",
        "alternative_refs": "concerns_alternative",
        "context_refs": "contextualized_by",
        "target_refs": "qualifies",
        "target_ref": "qualifies",
        "target_id": "qualifies",
    }
    out: List[Tuple[str, str]] = []
    for field, rel in mapping.items():
        value = record.get(field)
        for ref in _list(value):
            if isinstance(ref, dict):
                ref = ref.get("id") or ref.get("ref") or ref.get("node_id") or ""
            if str(ref).strip():
                out.append((str(ref).strip(), rel))
    return out


def graph_template(app_version: str) -> Dict[str, Any]:
    return {
        "schema": DEPENDENCY_GRAPH_SCHEMA,
        "version": app_version,
        "graph_id": "",
        "decision_id": "",
        "generated_at": "",
        "nodes": [],
        "edges": [],
        "diagnostics": diagnostics_template(app_version),
        "graph_fingerprint": "",
        "boundary": BOUNDARY,
    }


def diagnostics_template(app_version: str) -> Dict[str, Any]:
    return {
        "schema": DEPENDENCY_DIAGNOSTICS_SCHEMA,
        "version": app_version,
        "node_count": 0,
        "edge_count": 0,
        "orphan_node_ids": [],
        "root_node_ids": [],
        "leaf_node_ids": [],
        "cycle_node_ids": [],
        "unresolved_references": [],
        "high_fanout_nodes": [],
        "unsupported_recommendation": False,
        "structural_note": "Fan-out describes graph structure only; it is not a measure of importance, truth, or causal influence.",
    }


def impact_template(app_version: str) -> Dict[str, Any]:
    return {
        "schema": CHANGE_IMPACT_SCHEMA,
        "version": app_version,
        "assessment_id": "",
        "graph_id": "",
        "changed_node_ids": [],
        "directly_affected_node_ids": [],
        "transitively_affected_node_ids": [],
        "review_queue": [],
        "unresolved_changed_node_ids": [],
        "automatic_invalidation": False,
        "causal_claim": False,
        "recommendation_changed": False,
        "boundary": "Reachability identifies records that may require review. It does not prove causality or automatically invalidate a conclusion.",
    }


def build_dependency_graph(
    decision_object: Dict[str, Any],
    *,
    app_version: str,
    explicit_edges: Optional[List[Dict[str, Any]]] = None,
    include_structural_edges: bool = True,
) -> Dict[str, Any]:
    obj = deepcopy(decision_object or {})
    decision_id = str(obj.get("decision_id") or "DRAFT")
    decision_node = f"decision:{decision_id}"
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    edge_seen: Set[Tuple[str, str, str]] = set()
    alias_index: Dict[str, str] = {decision_id: decision_node, decision_node: decision_node}
    unresolved: List[Dict[str, Any]] = []
    by_kind: Dict[str, List[str]] = {}

    def add_node(kind: str, record: Any, index: int, source_product: str, fallback: str) -> str:
        key = _stable_key(kind, record, index)
        nid = _node_id(kind, key)
        if any(n["node_id"] == nid for n in nodes):
            return nid
        node = {
            "node_id": nid,
            "node_type": kind,
            "label": _label(record, fallback),
            "source_product": source_product,
            "record_fingerprint": _hash(record),
            "record": deepcopy(record),
            "review_state": str(record.get("review_state") or record.get("status") or "") if isinstance(record, dict) else "",
        }
        nodes.append(node)
        by_kind.setdefault(kind, []).append(nid)
        for alias in _aliases(record, nid):
            alias_index.setdefault(alias, nid)
        return nid

    nodes.append({
        "node_id": decision_node,
        "node_type": "decision",
        "label": str(obj.get("question") or decision_id)[:240],
        "source_product": "decision-studio",
        "record_fingerprint": _hash({"decision_id": decision_id, "question": obj.get("question", "")}),
        "record": {"decision_id": decision_id, "question": obj.get("question", ""), "status": obj.get("status", "draft")},
        "review_state": str(obj.get("status") or "draft"),
    })
    by_kind["decision"] = [decision_node]

    groups = [
        ("evidence", _records(obj, "evidence"), "decision-studio", "Evidence"),
        ("assumption", _records(obj, "assumptions"), "decision-studio", "Assumption"),
        ("model", _records(obj, "models"), "workbench/research-lab", "Model / analysis"),
        ("scenario", _records(obj, "scenarios"), "decision-studio", "Scenario"),
        ("criterion", _records(obj, "criteria"), "decision-studio", "Criterion"),
        ("alternative", _records(obj, "alternatives"), "decision-studio", "Alternative"),
        ("uncertainty", _records(obj, "uncertainties"), "decision-studio", "Uncertainty"),
        ("tradeoff", _records(obj, "tradeoffs"), "decision-studio", "Tradeoff"),
        ("analysis_request", _records(obj, "analysis_requests"), "decision-studio", "Analysis request"),
    ]
    # Rich first-class records introduced in v2.3-v2.7.
    for matrix in _records(obj, "tradeoff_matrices"):
        groups[7][1].append(matrix)
    for register in _records(obj, "uncertainty_registers"):
        groups[6][1].append(register)
    for sensitivity in _records(obj, "sensitivity_analyses"):
        groups[6][1].append(sensitivity)
    for comparison in _records(obj, "scenario_comparisons"):
        groups[7][1].append(comparison)
    for stress in _records(obj, "stress_test_suites"):
        groups[7][1].append(stress)
    for handoff in _records(obj, "analysis_handoffs", "computation_handoffs"):
        groups[2][1].append(handoff)

    # Site Intelligence context should not be duplicated when already projected into evidence.
    evidence_fingerprints = {_hash(x) for x in groups[0][1]}
    for ctx in _records(obj, "real_world_context"):
        if _hash(ctx) not in evidence_fingerprints:
            groups[0][1].append(ctx)
            evidence_fingerprints.add(_hash(ctx))

    records_by_node: Dict[str, Any] = {}
    for kind, records, source_product, fallback in groups:
        for index, record in enumerate(records):
            nid = add_node(kind, record, index, source_product, fallback)
            records_by_node[nid] = record

    recommendation = obj.get("recommendation")
    if recommendation not in (None, "", {}, []):
        rec_id = add_node("recommendation", recommendation, 0, "decision-studio", "Recommendation")
        records_by_node[rec_id] = recommendation
    decision_record = obj.get("decision")
    if decision_record not in (None, "", {}, []):
        rec_id = add_node("decision_record", decision_record, 0, "decision-studio", "Recorded decision")
        records_by_node[rec_id] = decision_record

    # Pass 1: explicit references carried by records.
    for nid, record in records_by_node.items():
        for ref, relationship in _refs(record):
            upstream = alias_index.get(ref)
            if upstream:
                _add_edge(edges, edge_seen, upstream, nid, relationship, origin="record-reference", explicit=True)
            else:
                unresolved.append({"node_id": nid, "reference": ref, "relationship": relationship})

    # Site Intelligence explicit scenario links are already recorded on contextual evidence.
    for nid in by_kind.get("evidence", []):
        record = records_by_node.get(nid)
        if not isinstance(record, dict):
            continue
        if str(record.get("source_product") or "").lower() == "site-intelligence" or record.get("evidence_role") == "contextual_evidence":
            for ref in _list(record.get("scenario_refs")):
                target = alias_index.get(str(ref))
                if target:
                    _add_edge(edges, edge_seen, nid, target, "contextualizes", origin="site-intelligence", explicit=True, metadata={"automatic_score_change": False})

    if include_structural_edges:
        tradeoff_targets = by_kind.get("tradeoff", [])
        recommendation_targets = by_kind.get("recommendation", [])
        decision_record_targets = by_kind.get("decision_record", [])
        primary_tradeoff = tradeoff_targets[-1] if tradeoff_targets else ""
        primary_rec = recommendation_targets[-1] if recommendation_targets else ""
        primary_decision_record = decision_record_targets[-1] if decision_record_targets else ""

        for nid in by_kind.get("criterion", []):
            _add_edge(edges, edge_seen, nid, primary_tradeoff or decision_node, "frames_evaluation")
        for nid in by_kind.get("alternative", []):
            _add_edge(edges, edge_seen, nid, primary_tradeoff or decision_node, "candidate_in_evaluation")
        for nid in by_kind.get("scenario", []):
            _add_edge(edges, edge_seen, nid, primary_tradeoff or primary_rec or decision_node, "conditions_evaluation")
        for nid in by_kind.get("assumption", []):
            if by_kind.get("scenario"):
                for target in by_kind["scenario"][:20]:
                    _add_edge(edges, edge_seen, nid, target, "conditions_scenario")
            else:
                _add_edge(edges, edge_seen, nid, primary_tradeoff or decision_node, "conditions_evaluation")
        for nid in by_kind.get("model", []):
            target = (by_kind.get("scenario") or [primary_tradeoff or decision_node])[0]
            _add_edge(edges, edge_seen, nid, target, "informs")
        for nid in by_kind.get("evidence", []):
            # Keep explicit scenario links when present; otherwise context informs evaluation/decision.
            if not any(e["from"] == nid for e in edges):
                _add_edge(edges, edge_seen, nid, primary_tradeoff or primary_rec or decision_node, "supports_review")
        for nid in by_kind.get("uncertainty", []):
            if not any(e["from"] == nid for e in edges):
                _add_edge(edges, edge_seen, nid, primary_tradeoff or primary_rec or decision_node, "qualifies")
        for nid in by_kind.get("analysis_request", []):
            _add_edge(edges, edge_seen, nid, primary_tradeoff or decision_node, "requests_missing_analysis")
        for nid in tradeoff_targets:
            _add_edge(edges, edge_seen, nid, primary_rec or primary_decision_record or decision_node, "informs_recommendation")
        if primary_rec:
            _add_edge(edges, edge_seen, primary_rec, primary_decision_record or decision_node, "proposes")
        if primary_decision_record:
            _add_edge(edges, edge_seen, primary_decision_record, decision_node, "records_outcome")

    # Explicit caller-supplied edges are accepted only when both endpoints resolve.
    for edge in explicit_edges or []:
        if not isinstance(edge, dict):
            continue
        raw_from = str(edge.get("from") or edge.get("source") or "")
        raw_to = str(edge.get("to") or edge.get("target") or "")
        source = alias_index.get(raw_from, raw_from if raw_from in alias_index.values() else "")
        target = alias_index.get(raw_to, raw_to if raw_to in alias_index.values() else "")
        relationship = str(edge.get("relationship") or "depends_on")
        if source and target:
            _add_edge(edges, edge_seen, source, target, relationship, origin="caller-explicit", explicit=True, metadata=edge.get("metadata") if isinstance(edge.get("metadata"), dict) else {})
        else:
            unresolved.append({"node_id": "", "reference": {"from": raw_from, "to": raw_to}, "relationship": relationship})

    graph = {
        "schema": DEPENDENCY_GRAPH_SCHEMA,
        "version": app_version,
        "graph_id": "",
        "decision_id": decision_id,
        "generated_at": _now(),
        "nodes": nodes,
        "edges": edges,
        "diagnostics": {},
        "boundary": BOUNDARY,
    }
    graph["graph_id"] = f"dependency-graph:{decision_id}:{_hash({'nodes': [(n['node_id'], n['record_fingerprint']) for n in nodes], 'edges': [(e['from'], e['to'], e['relationship']) for e in edges]})[:16]}"
    graph["diagnostics"] = dependency_diagnostics(graph, app_version=app_version, unresolved_references=unresolved)
    graph["graph_fingerprint"] = _hash({k: v for k, v in graph.items() if k != "graph_fingerprint"})
    return graph


def _cycle_nodes(nodes: Iterable[str], edges: List[Dict[str, Any]]) -> List[str]:
    adjacency: Dict[str, List[str]] = {n: [] for n in nodes}
    for edge in edges:
        if edge.get("from") in adjacency and edge.get("to") in adjacency:
            adjacency[edge["from"]].append(edge["to"])
    visiting: Set[str] = set()
    visited: Set[str] = set()
    cycles: Set[str] = set()

    def dfs(node: str, stack: List[str]) -> None:
        if node in visiting:
            if node in stack:
                cycles.update(stack[stack.index(node):])
            return
        if node in visited:
            return
        visiting.add(node)
        stack.append(node)
        for nxt in adjacency.get(node, []):
            dfs(nxt, stack)
        stack.pop()
        visiting.remove(node)
        visited.add(node)

    for node in adjacency:
        dfs(node, [])
    return sorted(cycles)


def dependency_diagnostics(
    graph: Dict[str, Any],
    *,
    app_version: str,
    unresolved_references: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    nodes = [x for x in graph.get("nodes") or [] if isinstance(x, dict) and x.get("node_id")]
    edges = [x for x in graph.get("edges") or [] if isinstance(x, dict)]
    ids = [x["node_id"] for x in nodes]
    indegree = {x: 0 for x in ids}
    outdegree = {x: 0 for x in ids}
    for edge in edges:
        if edge.get("from") in outdegree:
            outdegree[edge["from"]] += 1
        if edge.get("to") in indegree:
            indegree[edge["to"]] += 1
    decision_ids = {x["node_id"] for x in nodes if x.get("node_type") == "decision"}
    orphan = [x for x in ids if x not in decision_ids and indegree[x] == 0 and outdegree[x] == 0]
    roots = [x for x in ids if x not in decision_ids and indegree[x] == 0 and outdegree[x] > 0]
    leaves = [x for x in ids if x not in decision_ids and outdegree[x] == 0 and indegree[x] > 0]
    high_fanout = [
        {"node_id": x, "outdegree": outdegree[x]}
        for x in ids
        if outdegree[x] >= 3
    ]
    high_fanout.sort(key=lambda x: (-x["outdegree"], x["node_id"]))
    recommendation_nodes = [x["node_id"] for x in nodes if x.get("node_type") == "recommendation"]
    unsupported_rec = any(indegree.get(x, 0) == 0 for x in recommendation_nodes)
    return {
        "schema": DEPENDENCY_DIAGNOSTICS_SCHEMA,
        "version": app_version,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "orphan_node_ids": sorted(orphan),
        "root_node_ids": sorted(roots),
        "leaf_node_ids": sorted(leaves),
        "cycle_node_ids": _cycle_nodes(ids, edges),
        "unresolved_references": deepcopy(unresolved_references or []),
        "high_fanout_nodes": high_fanout[:25],
        "unsupported_recommendation": unsupported_rec,
        "structural_note": "Fan-out describes graph structure only; it is not a measure of importance, truth, or causal influence.",
    }


def validate_dependency_graph(graph: Dict[str, Any], *, app_version: str) -> Dict[str, Any]:
    g = graph if isinstance(graph, dict) else {}
    errors: List[str] = []
    warnings: List[str] = []
    if g.get("schema") != DEPENDENCY_GRAPH_SCHEMA:
        errors.append("dependency graph schema is invalid")
    nodes = [x for x in g.get("nodes") or [] if isinstance(x, dict)]
    edges = [x for x in g.get("edges") or [] if isinstance(x, dict)]
    ids = [str(x.get("node_id") or "") for x in nodes]
    if len(ids) != len(set(ids)):
        errors.append("node ids must be unique")
    node_set = set(ids)
    edge_ids = [str(x.get("edge_id") or "") for x in edges]
    if len(edge_ids) != len(set(edge_ids)):
        errors.append("edge ids must be unique")
    for edge in edges:
        if edge.get("from") not in node_set or edge.get("to") not in node_set:
            errors.append(f"edge endpoint missing: {edge.get('edge_id') or 'unknown'}")
        if edge.get("causal_claim") is True:
            errors.append("dependency edge may not assert causality")
        if edge.get("automatic_invalidation") is True:
            errors.append("dependency edge may not automatically invalidate downstream records")
    supplied = str(g.get("graph_fingerprint") or "")
    if supplied:
        expected = _hash({k: v for k, v in g.items() if k != "graph_fingerprint"})
        if supplied != expected:
            errors.append("graph fingerprint does not match graph payload")
    diagnostics = dependency_diagnostics(g, app_version=app_version, unresolved_references=(g.get("diagnostics") or {}).get("unresolved_references") or [])
    if diagnostics["cycle_node_ids"]:
        warnings.append("dependency graph contains one or more cycles requiring review")
    if diagnostics["orphan_node_ids"]:
        warnings.append("dependency graph contains orphan records")
    return {
        "valid": not errors,
        "schema": DEPENDENCY_GRAPH_SCHEMA,
        "app_version": app_version,
        "errors": errors,
        "warnings": warnings,
        "diagnostics": diagnostics,
        "boundary": BOUNDARY,
    }


def assess_change_impact(graph: Dict[str, Any], changed_node_ids: List[str], *, app_version: str) -> Dict[str, Any]:
    nodes = [x for x in graph.get("nodes") or [] if isinstance(x, dict) and x.get("node_id")]
    ids = {x["node_id"] for x in nodes}
    node_map = {x["node_id"]: x for x in nodes}
    changed = list(dict.fromkeys([str(x) for x in changed_node_ids if str(x)]))
    unresolved = [x for x in changed if x not in ids]
    starts = [x for x in changed if x in ids]
    adjacency: Dict[str, List[str]] = {x: [] for x in ids}
    for edge in graph.get("edges") or []:
        if not isinstance(edge, dict):
            continue
        source, target = edge.get("from"), edge.get("to")
        if source in adjacency and target in ids:
            adjacency[source].append(target)
    direct: List[str] = []
    for start in starts:
        direct.extend(adjacency.get(start, []))
    direct = list(dict.fromkeys(direct))
    visited: Set[str] = set(starts)
    queue = list(starts)
    affected: List[str] = []
    while queue:
        current = queue.pop(0)
        for nxt in adjacency.get(current, []):
            if nxt not in visited:
                visited.add(nxt)
                affected.append(nxt)
                queue.append(nxt)
    review_queue = [
        {
            "node_id": nid,
            "node_type": node_map.get(nid, {}).get("node_type", "unknown"),
            "label": node_map.get(nid, {}).get("label", nid),
            "review_reason": "reachable_from_changed_dependency",
        }
        for nid in affected
    ]
    core = {"graph_id": graph.get("graph_id", ""), "changed": starts, "affected": affected}
    return {
        "schema": CHANGE_IMPACT_SCHEMA,
        "version": app_version,
        "assessment_id": f"change-impact:{_hash(core)[:20]}",
        "graph_id": graph.get("graph_id", ""),
        "changed_node_ids": starts,
        "directly_affected_node_ids": direct,
        "transitively_affected_node_ids": affected,
        "review_queue": review_queue,
        "unresolved_changed_node_ids": unresolved,
        "automatic_invalidation": False,
        "causal_claim": False,
        "recommendation_changed": False,
        "boundary": "Reachability identifies records that may require review. It does not prove causality or automatically invalidate a conclusion.",
    }


def attach_dependency_graph(
    decision_object: Dict[str, Any],
    graph: Dict[str, Any],
    validation: Dict[str, Any],
    *,
    app_version: str,
) -> Dict[str, Any]:
    out = deepcopy(decision_object or {})
    out.setdefault("schema", "scds-decision-object/1.0")
    out.setdefault("decision_dependency_graphs", [])
    out["decision_dependency_graphs"] = [
        x for x in out["decision_dependency_graphs"]
        if not isinstance(x, dict) or x.get("graph_id") != graph.get("graph_id")
    ] + [deepcopy(graph)]
    out.setdefault("dependency_diagnostics", [])
    out["dependency_diagnostics"] = [
        x for x in out["dependency_diagnostics"]
        if not isinstance(x, dict) or x.get("graph_id") != graph.get("graph_id")
    ] + [{"graph_id": graph.get("graph_id", ""), **deepcopy(validation.get("diagnostics") or {})}]
    out.setdefault("links", []).append({
        "relationship": "decision_dependency_graph",
        "graph_id": graph.get("graph_id", ""),
        "graph_fingerprint": graph.get("graph_fingerprint", ""),
        "node_count": len(graph.get("nodes") or []),
        "edge_count": len(graph.get("edges") or []),
        "causal_claim": False,
    })
    provenance = out.setdefault("provenance", {})
    provenance.setdefault("records", []).append({
        "at": _now(),
        "action": "decision_dependency_graph_attached",
        "graph_id": graph.get("graph_id", ""),
        "graph_fingerprint": graph.get("graph_fingerprint", ""),
        "node_count": len(graph.get("nodes") or []),
        "edge_count": len(graph.get("edges") or []),
    })
    out["version"] = app_version
    return out
