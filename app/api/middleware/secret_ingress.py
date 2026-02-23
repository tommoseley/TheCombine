"""
HTTP Ingress Secret Detection Middleware.

Per GOV-SEC-T0-002 Section 6: runs canonical detector on raw request body
BEFORE any logging persistence. If secret detected, rejects with HTTP 422
and logs only redacted metadata.

This is Gate 1 of the dual-gate architecture.
"""

import json
import logging
from urllib.parse import parse_qs, unquote_plus

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.secret_detector import scan_text, scan_dict, redact_for_logging, ScanResult

logger = logging.getLogger(__name__)

# Paths that should NOT be scanned (health checks, static assets, auth flows)
_SKIP_PATHS = frozenset([
    "/health",
    "/healthz",
    "/docs",
    "/redoc",
    "/openapi.json",
])


class SecretIngressMiddleware(BaseHTTPMiddleware):
    """
    Gate 1: HTTP ingress secret detection.

    Scans POST/PUT/PATCH request bodies for secret material.
    Rejects with 422 if detected. Never persists rejected payloads.
    """

    async def dispatch(self, request: Request, call_next):
        # Only scan mutating requests with bodies
        if request.method not in ("POST", "PUT", "PATCH"):
            return await call_next(request)

        # Skip non-API paths
        path = request.url.path
        if any(path.startswith(skip) for skip in _SKIP_PATHS):
            return await call_next(request)

        # Read body (may already be cached by BodySizeMiddleware)
        body = await request.body()
        if not body:
            return await call_next(request)

        request_id = getattr(request.state, "request_id", "unknown")

        # Decode body text
        try:
            body_text = body.decode("utf-8", errors="replace")
        except Exception:
            return await call_next(request)

        # Content-type-aware scanning:
        # - JSON bodies: parse and scan dict values
        # - Form-encoded bodies: URL-decode values before scanning
        # - Other: scan raw text
        content_type = request.headers.get("content-type", "")
        scan_result: ScanResult

        if "application/json" in content_type:
            try:
                body_json = json.loads(body_text)
                if isinstance(body_json, dict):
                    scan_result = scan_dict(body_json)
                else:
                    scan_result = scan_text(body_text)
            except (json.JSONDecodeError, ValueError):
                scan_result = scan_text(body_text)
        elif "application/x-www-form-urlencoded" in content_type:
            # URL-decode form values before scanning
            form_values = parse_qs(body_text, keep_blank_values=True)
            form_dict = {k: v[0] if len(v) == 1 else v for k, v in form_values.items()}
            scan_result = scan_dict(form_dict)
        elif "multipart/form-data" in content_type:
            # Skip multipart (file uploads) — too complex to parse here,
            # and secrets in files are caught at the orchestrator gate
            scan_result = ScanResult("CLEAN", None, 0.0)
        else:
            # Fallback: try JSON, then raw text
            try:
                body_json = json.loads(body_text)
                if isinstance(body_json, dict):
                    scan_result = scan_dict(body_json)
                else:
                    scan_result = scan_text(body_text)
            except (json.JSONDecodeError, ValueError):
                scan_result = scan_text(body_text)

        if scan_result.verdict == "SECRET_DETECTED":
            # Log redacted metadata only — never the payload
            audit = redact_for_logging(scan_result, request_id)
            logger.warning(
                "[REDACTED_SECRET_DETECTED] Secret detected at HTTP ingress, "
                "request rejected | %s",
                json.dumps(audit),
            )

            # Reject — do not persist, do not create workflow instance
            return JSONResponse(
                status_code=422,
                content={
                    "error": "secret_detected",
                    "message": "Request contains credential material and has been rejected. "
                               "Use a secret manager for credential storage.",
                    "request_id": request_id,
                    "detector_version": scan_result.detector_version,
                },
            )

        # Clean — proceed normally
        return await call_next(request)
