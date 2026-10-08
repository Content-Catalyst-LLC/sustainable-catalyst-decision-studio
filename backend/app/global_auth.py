from __future__ import annotations

from dataclasses import dataclass, field
from contextvars import ContextVar
import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any

from fastapi import Request

GLOBAL_AUTH_SCHEMA = "scds-global-authentication-authorization/1.0"
AUTHENTICATED_PRINCIPAL_SCHEMA = "scds-authenticated-principal/1.0"
AUTHORIZATION_DECISION_SCHEMA = "scds-authorization-decision/1.0"
GLOBAL_AUTH_VERSION = "1.0"
DEFAULT_ISSUER = "sustainable-catalyst-auth"
DEFAULT_AUDIENCE = "decision-studio"
CURRENT_AUTH_PRINCIPAL: ContextVar[Any] = ContextVar("scds_current_auth_principal", default=None)

# These are Decision Studio resource scopes. Global tokens may carry any subset.
CANONICAL_SCOPES = [
    "repository:read", "repository:write",
    "canvas:read", "canvas:write",
    "finance:read", "finance:write",
    "narrative-risk:read", "narrative-risk:write",
    "global-impact:read", "global-impact:write",
    "composition:read", "composition:write",
    "artifacts:read", "artifacts:write",
    "interoperability:read", "interoperability:write",
    "rooms:read", "rooms:write", "rooms:import",
    "auth:inspect",
    "audit:read", "audit:write",
]


@dataclass(frozen=True)
class AuthPrincipal:
    principal_id: str
    principal_type: str
    institution_id: str | None = None
    roles: frozenset[str] = field(default_factory=frozenset)
    scopes: frozenset[str] = field(default_factory=frozenset)
    session_id: str | None = None
    email: str | None = None
    name: str | None = None
    auth_method: str = "unknown"
    legacy_compatibility: bool = False
    claims: dict[str, Any] = field(default_factory=dict, compare=False, hash=False, repr=False)

    def public_dict(self) -> dict[str, Any]:
        return {
            "schema": AUTHENTICATED_PRINCIPAL_SCHEMA,
            "principal_id": self.principal_id,
            "principal_type": self.principal_type,
            "institution_id": self.institution_id,
            "roles": sorted(self.roles),
            "scopes": sorted(self.scopes),
            "session_id": self.session_id,
            "email": self.email,
            "name": self.name,
            "auth_method": self.auth_method,
            "legacy_compatibility": self.legacy_compatibility,
        }


@dataclass(frozen=True)
class AuthDecision:
    allowed: bool
    principal: AuthPrincipal | None
    required_scope: str | None = None
    status_code: int = 200
    error: str | None = None
    reason: str | None = None

    def public_dict(self) -> dict[str, Any]:
        return {
            "schema": AUTHORIZATION_DECISION_SCHEMA,
            "allowed": self.allowed,
            "required_scope": self.required_scope,
            "status_code": self.status_code,
            "error": self.error,
            "reason": self.reason,
            "principal": self.principal.public_dict() if self.principal else None,
        }


def _b64url_decode(value: str) -> bytes:
    padding = "=" * ((4 - len(value) % 4) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def _json_env(name: str) -> dict[str, Any]:
    raw = os.getenv(name, "{}").strip() or "{}"
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _string_set(value: Any) -> frozenset[str]:
    if isinstance(value, str):
        return frozenset(x for x in value.replace(",", " ").split() if x)
    if isinstance(value, (list, tuple, set, frozenset)):
        return frozenset(str(x) for x in value if str(x))
    return frozenset()


def _audience_matches(claim: Any, expected: str) -> bool:
    if isinstance(claim, str):
        return secrets.compare_digest(claim, expected)
    if isinstance(claim, list):
        return expected in [str(x) for x in claim]
    return False


def _bearer_principal(token: str) -> tuple[AuthPrincipal | None, str | None]:
    secret = os.getenv("SCDS_GLOBAL_AUTH_JWT_SECRET", "").strip()
    if not secret:
        return None, "global_auth_bearer_not_configured"
    try:
        h64, p64, s64 = token.split(".")
        header = json.loads(_b64url_decode(h64))
        payload = json.loads(_b64url_decode(p64))
        signature = _b64url_decode(s64)
    except Exception:
        return None, "invalid_bearer_token"
    if not isinstance(header, dict) or not isinstance(payload, dict) or header.get("alg") != "HS256":
        return None, "unsupported_bearer_token"
    expected_sig = hmac.new(secret.encode("utf-8"), f"{h64}.{p64}".encode("ascii"), hashlib.sha256).digest()
    if not hmac.compare_digest(signature, expected_sig):
        return None, "invalid_bearer_signature"

    now = int(time.time())
    leeway = max(0, int(os.getenv("SCDS_GLOBAL_AUTH_CLOCK_SKEW_SECONDS", "60")))
    try:
        exp = int(payload["exp"])
    except Exception:
        return None, "bearer_exp_required"
    if now > exp + leeway:
        return None, "bearer_token_expired"
    if payload.get("nbf") is not None and now + leeway < int(payload["nbf"]):
        return None, "bearer_token_not_yet_valid"

    issuer = os.getenv("SCDS_GLOBAL_AUTH_ISSUER", DEFAULT_ISSUER).strip() or DEFAULT_ISSUER
    audience = os.getenv("SCDS_GLOBAL_AUTH_AUDIENCE", DEFAULT_AUDIENCE).strip() or DEFAULT_AUDIENCE
    if payload.get("iss") != issuer:
        return None, "bearer_issuer_mismatch"
    if not _audience_matches(payload.get("aud"), audience):
        return None, "bearer_audience_mismatch"
    subject = str(payload.get("sub") or "").strip()
    if not subject:
        return None, "bearer_subject_required"

    principal_type = str(payload.get("principal_type") or "user").strip().lower()
    if principal_type not in {"user", "service"}:
        return None, "invalid_principal_type"
    scopes = set(_string_set(payload.get("scopes"))) | set(_string_set(payload.get("scope")))
    roles = _string_set(payload.get("roles"))
    principal = AuthPrincipal(
        principal_id=subject,
        principal_type=principal_type,
        institution_id=str(payload.get("institution_id") or "").strip() or None,
        roles=roles,
        scopes=frozenset(scopes),
        session_id=str(payload.get("session_id") or payload.get("sid") or "").strip() or None,
        email=str(payload.get("email") or "").strip() or None,
        name=str(payload.get("name") or "").strip() or None,
        auth_method="global-bearer-jwt",
        legacy_compatibility=False,
        claims=payload,
    )
    return principal, None


def _service_principal(key: str) -> tuple[AuthPrincipal | None, str | None]:
    catalog = _json_env("SCDS_SERVICE_API_KEYS")
    item = catalog.get(key)
    if item is None:
        return None, "invalid_service_credential"
    if isinstance(item, list):
        item = {"service_id": "service:configured", "scopes": item}
    if not isinstance(item, dict):
        return None, "invalid_service_credential_configuration"
    service_id = str(item.get("service_id") or item.get("principal_id") or "").strip()
    if not service_id:
        return None, "service_principal_id_required"
    return AuthPrincipal(
        principal_id=service_id,
        principal_type="service",
        institution_id=str(item.get("institution_id") or "").strip() or None,
        roles=_string_set(item.get("roles")),
        scopes=_string_set(item.get("scopes")),
        auth_method="service-api-key",
        legacy_compatibility=False,
    ), None


def _legacy_principal(key: str) -> tuple[AuthPrincipal | None, str | None]:
    repository_key = os.getenv("SCDS_REPOSITORY_API_KEY", "").strip()
    if repository_key and secrets.compare_digest(key, repository_key):
        return AuthPrincipal(
            principal_id="service:decision-studio-repository-compat",
            principal_type="service",
            roles=frozenset({"repository-service"}),
            scopes=frozenset({"*"}),
            auth_method="legacy-api-key",
            legacy_compatibility=True,
        ), None
    super_key = os.getenv("SCDS_API_KEY", "").strip()
    if super_key and secrets.compare_digest(key, super_key):
        return AuthPrincipal(
            principal_id="service:decision-studio-superkey-compat",
            principal_type="service",
            roles=frozenset({"legacy-admin"}),
            scopes=frozenset({"*"}),
            auth_method="legacy-api-key",
            legacy_compatibility=True,
        ), None
    catalog = _json_env("SCDS_INSTITUTIONAL_API_KEYS")
    item = catalog.get(key)
    if isinstance(item, list):
        scopes = _string_set(item)
        institution_id = None
        principal_id = "service:institutional-api-key-compat"
    elif isinstance(item, dict):
        scopes = _string_set(item.get("scopes"))
        institution_id = str(item.get("institution_id") or "").strip() or None
        principal_id = str(item.get("principal_id") or "service:institutional-api-key-compat")
    else:
        return None, "invalid_legacy_api_key"
    return AuthPrincipal(
        principal_id=principal_id,
        principal_type="service",
        institution_id=institution_id,
        roles=frozenset({"institutional-service"}),
        scopes=scopes,
        auth_method="legacy-api-key",
        legacy_compatibility=True,
    ), None


def authenticate_request(request: Request, *, allow_legacy: bool = True) -> AuthDecision:
    authorization = request.headers.get("authorization", "").strip()
    if authorization:
        if not authorization.lower().startswith("bearer "):
            CURRENT_AUTH_PRINCIPAL.set(None)
            return AuthDecision(False, None, status_code=401, error="unsupported_authorization_scheme")
        token = authorization.split(" ", 1)[1].strip()
        principal, error = _bearer_principal(token)
        if error:
            CURRENT_AUTH_PRINCIPAL.set(None)
            return AuthDecision(False, None, status_code=401, error=error)
        CURRENT_AUTH_PRINCIPAL.set(principal)
        return AuthDecision(True, principal)

    service_key = request.headers.get("x-scds-service-key", "").strip()
    if service_key:
        principal, error = _service_principal(service_key)
        if error:
            CURRENT_AUTH_PRINCIPAL.set(None)
            return AuthDecision(False, None, status_code=401, error=error)
        CURRENT_AUTH_PRINCIPAL.set(principal)
        return AuthDecision(True, principal)

    legacy_key = request.headers.get("x-scds-api-key", "").strip()
    if legacy_key:
        if not allow_legacy:
            CURRENT_AUTH_PRINCIPAL.set(None)
            return AuthDecision(False, None, status_code=401, error="legacy_api_key_not_allowed")
        principal, error = _legacy_principal(legacy_key)
        if error:
            CURRENT_AUTH_PRINCIPAL.set(None)
            return AuthDecision(False, None, status_code=401, error=error)
        CURRENT_AUTH_PRINCIPAL.set(principal)
        return AuthDecision(True, principal)

    CURRENT_AUTH_PRINCIPAL.set(None)
    return AuthDecision(False, None, status_code=401, error="authentication_required")



def current_auth_principal() -> AuthPrincipal | None:
    value = CURRENT_AUTH_PRINCIPAL.get()
    return value if isinstance(value, AuthPrincipal) else None

def scope_granted(principal: AuthPrincipal, required_scope: str) -> bool:
    scopes = set(principal.scopes)
    if "*" in scopes or "decision-studio:admin" in scopes or required_scope in scopes:
        return True
    if required_scope.endswith(":read") and required_scope[:-5] + ":write" in scopes:
        return True
    return False


def authorize_request(request: Request, required_scope: str, *, allow_legacy: bool = True) -> AuthDecision:
    decision = authenticate_request(request, allow_legacy=allow_legacy)
    if not decision.allowed or not decision.principal:
        return AuthDecision(False, decision.principal, required_scope=required_scope, status_code=decision.status_code, error=decision.error)
    if not scope_granted(decision.principal, required_scope):
        return AuthDecision(
            False,
            decision.principal,
            required_scope=required_scope,
            status_code=403,
            error="insufficient_scope",
            reason="principal_does_not_hold_required_scope",
        )
    return AuthDecision(True, decision.principal, required_scope=required_scope)


def global_auth_contract() -> dict[str, Any]:
    return {
        "schema": GLOBAL_AUTH_SCHEMA,
        "principal_schema": AUTHENTICATED_PRINCIPAL_SCHEMA,
        "authorization_decision_schema": AUTHORIZATION_DECISION_SCHEMA,
        "version": GLOBAL_AUTH_VERSION,
        "role": "decision-studio-relying-party-global-authentication-and-authorization",
        "authentication_authority": "sustainable-catalyst-global-auth",
        "authorization_enforcement": "decision-studio-resource-and-room-policy",
        "credential_precedence": ["authorization-bearer", "x-scds-service-key", "x-scds-api-key-compatibility"],
        "primary_user_authentication": "bearer-jwt-hs256",
        "service_authentication": "x-scds-service-key",
        "legacy_api_key_status": "compatibility-only",
        "identity_claims": ["sub", "institution_id", "roles", "scopes", "session_id", "email", "name"],
        "token_validation": {
            "signature": "HS256",
            "issuer_required": True,
            "audience_required": True,
            "expiration_required": True,
            "subject_required": True,
            "downgrade_fallback_after_invalid_bearer": False,
        },
        "principles": {
            "decision_studio_does_not_issue_user_credentials": True,
            "global_identity_is_not_duplicated_in_decision_studio": True,
            "institution_identity_is_propagated": True,
            "authorization_is_scope_and_resource_based": True,
            "decision_room_membership_is_enforced_for_user_principals": True,
            "request_body_cannot_impersonate_authenticated_room_actor": True,
            "service_credentials_are_distinct_from_user_sessions": True,
            "legacy_api_keys_are_not_primary_authentication": True,
            "authentication_does_not_imply_decision_approval": True,
            "final_decision_authority_is_human_governed": True,
        },
        "canonical_scopes": list(CANONICAL_SCOPES),
        "final_decision_authority": "human-governed",
        "schema_migration_required": False,
    }


def global_auth_readiness() -> dict[str, Any]:
    return {
        "schema": GLOBAL_AUTH_SCHEMA,
        "bearer_jwt_configured": bool(os.getenv("SCDS_GLOBAL_AUTH_JWT_SECRET", "").strip()),
        "issuer": os.getenv("SCDS_GLOBAL_AUTH_ISSUER", DEFAULT_ISSUER).strip() or DEFAULT_ISSUER,
        "audience": os.getenv("SCDS_GLOBAL_AUTH_AUDIENCE", DEFAULT_AUDIENCE).strip() or DEFAULT_AUDIENCE,
        "service_credentials_configured": bool(_json_env("SCDS_SERVICE_API_KEYS")),
        "legacy_repository_key_configured": bool(os.getenv("SCDS_REPOSITORY_API_KEY", "").strip()),
        "legacy_super_key_configured": bool(os.getenv("SCDS_API_KEY", "").strip()),
        "legacy_institutional_keys_configured": bool(_json_env("SCDS_INSTITUTIONAL_API_KEYS")),
        "global_auth_integration_ready": True,
        "user_authentication_ready": bool(os.getenv("SCDS_GLOBAL_AUTH_JWT_SECRET", "").strip()),
        "service_authentication_ready": bool(_json_env("SCDS_SERVICE_API_KEYS")) or bool(os.getenv("SCDS_REPOSITORY_API_KEY", "").strip()),
        "schema_migration_required": False,
    }
