from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Dict, List

from pydantic import BaseModel, Field

EVIDENCE_BUNDLE_SCHEMA = "scds-evidence-bundle/1.0"
SOURCE_BUNDLE_SCHEMA = "scds-source-bundle/1.0"
EVIDENCE_COVERAGE_SCHEMA = "scds-evidence-coverage/1.0"


class EvidenceBundleRequest(BaseModel):
    packet: Dict[str, Any] = Field(default_factory=dict)
    decisionObject: Dict[str, Any] = Field(default_factory=dict)
    evidenceBundle: Dict[str, Any] = Field(default_factory=dict)
    sourceBundle: Dict[str, Any] = Field(default_factory=dict)
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    bundles: List[Dict[str, Any]] = Field(default_factory=list)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _fingerprint(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _slug(value: Any, fallback: str) -> str:
    text = "".join(ch.lower() if ch.isalnum() else "-" for ch in str(value or "")).strip("-")
    text = "-".join(part for part in text.split("-") if part)
    return text[:80] or fallback


def _source_id(source: Dict[str, Any], index: int) -> str:
    explicit = source.get("source_id") or source.get("id")
    if explicit:
        return str(explicit)
    anchor = source.get("doi") or source.get("url") or source.get("uri") or source.get("title") or source
    return f"src-{_slug(source.get('title'), str(index + 1))}-{_fingerprint(anchor)[:12]}"


def _evidence_id(record: Dict[str, Any], index: int) -> str:
    explicit = record.get("evidence_id") or record.get("id")
    if explicit:
        return str(explicit)
    anchor = record.get("claim") or record.get("statement") or record.get("summary") or record
    return f"ev-{_slug(anchor, str(index + 1))[:40]}-{_fingerprint(anchor)[:12]}"


def source_bundle_template(app_version: str) -> Dict[str, Any]:
    return {
        "schema": SOURCE_BUNDLE_SCHEMA,
        "version": app_version,
        "bundle_id": "",
        "title": "",
        "created_at": "",
        "updated_at": "",
        "sources": [],
        "deduplication": {"input_count": 0, "unique_count": 0, "duplicate_count": 0},
        "provenance": {"created_by": "decision-studio", "records": []},
        "boundary": "A source bundle preserves source identity and provenance. Inclusion does not imply truth, endorsement, freshness, or evidentiary sufficiency.",
    }


def evidence_bundle_template(app_version: str) -> Dict[str, Any]:
    return {
        "schema": EVIDENCE_BUNDLE_SCHEMA,
        "version": app_version,
        "bundle_id": "",
        "decision_id": "",
        "title": "",
        "created_at": "",
        "updated_at": "",
        "source_bundle": source_bundle_template(app_version),
        "evidence_records": [],
        "contradictions": [],
        "coverage": evidence_coverage([], [], app_version),
        "provenance": {"created_by": "decision-studio", "records": []},
        "review": {"status": "needs_review", "reviewed_by": "", "reviewed_at": ""},
        "boundary": "Evidence bundles organize support and challenge relationships. They do not automatically verify claims or authorize decisions.",
    }


def normalize_source(source: Dict[str, Any], index: int) -> Dict[str, Any]:
    raw = deepcopy(source or {})
    sid = _source_id(raw, index)
    citation = raw.get("citation") or raw.get("formatted_citation") or ""
    return {
        "source_id": sid,
        "title": str(raw.get("title") or raw.get("name") or sid),
        "source_type": str(raw.get("source_type") or raw.get("type") or "source"),
        "authors": deepcopy(raw.get("authors") or []),
        "publisher": str(raw.get("publisher") or raw.get("organization") or ""),
        "published_at": str(raw.get("published_at") or raw.get("date") or ""),
        "url": str(raw.get("url") or raw.get("uri") or ""),
        "doi": str(raw.get("doi") or ""),
        "citation": citation,
        "freshness": deepcopy(raw.get("freshness") or {}),
        "quality": deepcopy(raw.get("quality") or raw.get("evidence_quality") or {}),
        "review_status": str(raw.get("review_status") or "needs_review"),
        "provenance": deepcopy(raw.get("provenance") or {}),
        "content_fingerprint": _fingerprint(raw.get("content") if "content" in raw else raw),
        "raw": raw,
    }


def build_source_bundle(sources: List[Dict[str, Any]], app_version: str, title: str = "") -> Dict[str, Any]:
    normalized = [normalize_source(source, i) for i, source in enumerate(sources or []) if isinstance(source, dict)]
    unique: Dict[str, Dict[str, Any]] = {}
    duplicate_links: List[Dict[str, str]] = []
    fingerprint_to_id: Dict[str, str] = {}
    for source in normalized:
        fp = source["content_fingerprint"]
        if fp in fingerprint_to_id:
            duplicate_links.append({"duplicate_source_id": source["source_id"], "canonical_source_id": fingerprint_to_id[fp]})
            continue
        fingerprint_to_id[fp] = source["source_id"]
        unique[source["source_id"]] = source
    now = _utc_now()
    payload = list(unique.values())
    bundle_id = f"source-bundle-{_fingerprint([s['content_fingerprint'] for s in payload])[:16]}"
    return {
        "schema": SOURCE_BUNDLE_SCHEMA,
        "version": app_version,
        "bundle_id": bundle_id,
        "title": title or "Decision source bundle",
        "created_at": now,
        "updated_at": now,
        "sources": payload,
        "deduplication": {
            "input_count": len(normalized),
            "unique_count": len(payload),
            "duplicate_count": len(duplicate_links),
            "duplicate_links": duplicate_links,
        },
        "provenance": {"created_by": "decision-studio", "records": []},
        "boundary": "A source bundle preserves source identity and provenance. Inclusion does not imply truth, endorsement, freshness, or evidentiary sufficiency.",
    }


def normalize_evidence(record: Dict[str, Any], index: int, known_sources: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    raw = deepcopy(record or {})
    rid = _evidence_id(raw, index)
    source_ids = raw.get("source_ids") or raw.get("sources") or []
    if isinstance(source_ids, str):
        source_ids = [source_ids]
    normalized_ids = []
    for source in source_ids:
        if isinstance(source, dict):
            sid = source.get("source_id") or source.get("id")
        else:
            sid = source
        if sid:
            normalized_ids.append(str(sid))
    citations = raw.get("citations") or []
    if isinstance(citations, str):
        citations = [citations]
    return {
        "evidence_id": rid,
        "claim": str(raw.get("claim") or raw.get("statement") or raw.get("summary") or ""),
        "stance": str(raw.get("stance") or raw.get("relationship") or "context"),
        "source_ids": normalized_ids,
        "citations": deepcopy(citations),
        "confidence": deepcopy(raw.get("confidence") or {}),
        "quality": deepcopy(raw.get("quality") or raw.get("evidence_quality") or {}),
        "freshness": deepcopy(raw.get("freshness") or {}),
        "limitations": deepcopy(raw.get("limitations") or []),
        "review_status": str(raw.get("review_status") or "needs_review"),
        "provenance": deepcopy(raw.get("provenance") or {}),
        "unresolved_source_ids": [sid for sid in normalized_ids if sid not in known_sources],
        "content_fingerprint": _fingerprint({
            "claim": raw.get("claim") or raw.get("statement") or raw.get("summary") or "",
            "stance": raw.get("stance") or raw.get("relationship") or "context",
            "sources": sorted(normalized_ids),
        }),
        "raw": raw,
    }


def evidence_coverage(evidence_records: List[Dict[str, Any]], sources: List[Dict[str, Any]], app_version: str) -> Dict[str, Any]:
    cited = [r for r in evidence_records if r.get("source_ids") or r.get("citations")]
    unresolved = [r["evidence_id"] for r in evidence_records if r.get("unresolved_source_ids")]
    needs_review = [r["evidence_id"] for r in evidence_records if r.get("review_status") not in {"reviewed", "accepted", "approved"}]
    claims = [r for r in evidence_records if str(r.get("claim") or "").strip()]
    contradictory_claims: Dict[str, set] = {}
    for record in claims:
        key = " ".join(str(record.get("claim") or "").lower().split())
        contradictory_claims.setdefault(key, set()).add(str(record.get("stance") or "context").lower())
    contradictions = [
        {"claim": claim, "stances": sorted(stances)}
        for claim, stances in contradictory_claims.items()
        if "supports" in stances and "challenges" in stances
    ]
    count = len(evidence_records)
    return {
        "schema": EVIDENCE_COVERAGE_SCHEMA,
        "version": app_version,
        "evidence_count": count,
        "source_count": len(sources),
        "cited_evidence_count": len(cited),
        "uncited_evidence_count": count - len(cited),
        "citation_coverage_percent": round((len(cited) / max(1, count)) * 100, 1),
        "unresolved_source_evidence_ids": unresolved,
        "needs_review_evidence_ids": needs_review,
        "contradiction_count": len(contradictions),
        "contradictions": contradictions,
        "review_ready": count > 0 and (count - len(cited)) == 0 and not unresolved and not needs_review,
    }


def build_evidence_bundle(
    evidence: List[Dict[str, Any]],
    sources: List[Dict[str, Any]],
    app_version: str,
    decision_id: str = "",
    title: str = "",
    source_bundle: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    source_bundle = deepcopy(source_bundle or {})
    if source_bundle.get("schema") != SOURCE_BUNDLE_SCHEMA:
        source_bundle = build_source_bundle(sources, app_version)
    known_sources = {str(s.get("source_id")): s for s in source_bundle.get("sources", []) if isinstance(s, dict)}
    records = [normalize_evidence(record, i, known_sources) for i, record in enumerate(evidence or []) if isinstance(record, dict)]
    unique: Dict[str, Dict[str, Any]] = {}
    duplicate_links: List[Dict[str, str]] = []
    fp_to_id: Dict[str, str] = {}
    for record in records:
        fp = record["content_fingerprint"]
        if fp in fp_to_id:
            duplicate_links.append({"duplicate_evidence_id": record["evidence_id"], "canonical_evidence_id": fp_to_id[fp]})
            continue
        fp_to_id[fp] = record["evidence_id"]
        unique[record["evidence_id"]] = record
    records = list(unique.values())
    coverage = evidence_coverage(records, list(known_sources.values()), app_version)
    now = _utc_now()
    bundle_id = f"evidence-bundle-{_fingerprint([r['content_fingerprint'] for r in records])[:16]}"
    return {
        "schema": EVIDENCE_BUNDLE_SCHEMA,
        "version": app_version,
        "bundle_id": bundle_id,
        "decision_id": decision_id,
        "title": title or "Decision evidence bundle",
        "created_at": now,
        "updated_at": now,
        "source_bundle": source_bundle,
        "evidence_records": records,
        "deduplication": {
            "input_count": len([x for x in evidence or [] if isinstance(x, dict)]),
            "unique_count": len(records),
            "duplicate_count": len(duplicate_links),
            "duplicate_links": duplicate_links,
        },
        "contradictions": deepcopy(coverage["contradictions"]),
        "coverage": coverage,
        "provenance": {"created_by": "decision-studio", "records": []},
        "review": {"status": "needs_review", "reviewed_by": "", "reviewed_at": ""},
        "boundary": "Evidence bundles organize support and challenge relationships. They do not automatically verify claims or authorize decisions.",
    }


def merge_evidence_bundles(bundles: List[Dict[str, Any]], app_version: str, decision_id: str = "") -> Dict[str, Any]:
    all_sources: List[Dict[str, Any]] = []
    all_evidence: List[Dict[str, Any]] = []
    provenance: List[Dict[str, Any]] = []
    for bundle in bundles or []:
        if not isinstance(bundle, dict):
            continue
        source_bundle = bundle.get("source_bundle") if isinstance(bundle.get("source_bundle"), dict) else {}
        for source in source_bundle.get("sources", []) or []:
            if isinstance(source, dict):
                all_sources.append(source.get("raw") if isinstance(source.get("raw"), dict) else source)
        for record in bundle.get("evidence_records", []) or []:
            if isinstance(record, dict):
                all_evidence.append(record.get("raw") if isinstance(record.get("raw"), dict) else record)
        provenance.append({"source_bundle_id": bundle.get("bundle_id", ""), "source_schema": bundle.get("schema", "")})
    merged = build_evidence_bundle(all_evidence, all_sources, app_version, decision_id=decision_id, title="Merged decision evidence bundle")
    merged["provenance"]["records"] = provenance
    return merged


def attach_evidence_bundle(decision_object: Dict[str, Any], bundle: Dict[str, Any], app_version: str) -> Dict[str, Any]:
    out = deepcopy(decision_object or {})
    out.setdefault("evidence_bundles", [])
    existing = [b for b in out["evidence_bundles"] if isinstance(b, dict) and b.get("bundle_id") != bundle.get("bundle_id")]
    out["evidence_bundles"] = existing + [deepcopy(bundle)]
    out["evidence"] = deepcopy(bundle.get("evidence_records", []))
    out.setdefault("provenance", {}).setdefault("records", []).append({
        "at": _utc_now(),
        "action": "evidence_bundle_attached",
        "bundle_id": bundle.get("bundle_id", ""),
        "schema": EVIDENCE_BUNDLE_SCHEMA,
    })
    out["updated_at"] = _utc_now()
    out["version"] = app_version
    return out
