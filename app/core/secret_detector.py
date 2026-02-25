"""
Canonical secret detector module (detector.v1).

Per GOV-SEC-T0-002: Single authoritative detector invoked by both
the HTTP ingress gate and the orchestrator Tier-0 governance boundary.

Thresholds loaded from:
  combine-config/governance/secrets/detector_calibration.v1.json

Detection layers:
  1. Structural (PEM blocks)
  2. Known prefix patterns (AKIA, ghp_, sk_live_, etc.)
  3. Connection string patterns (://user:pass@host)
  4. Entropy + character distribution analysis
"""

import base64
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class ScanResult:
    """Deterministic output from the secret detector."""
    verdict: str  # "CLEAN" or "SECRET_DETECTED"
    classification: Optional[str]  # HIGH_ENTROPY, PEM_BLOCK, PATTERN_MATCH, etc.
    entropy_score: float
    detector_version: str = "v1"


# ---------------------------------------------------------------------------
# Calibration loading
# ---------------------------------------------------------------------------

_DEFAULT_CALIBRATION = {
    "detector_version": "v1",
    "length_threshold": 20,
    "entropy_threshold": 3.0,
    "char_class_adjustment": 0.85,
}


def _find_calibration_path() -> Optional[Path]:
    """Find the calibration artifact relative to the project root."""
    # Try common locations
    candidates = [
        Path("combine-config/governance/secrets/detector_calibration.v1.json"),
        Path(__file__).resolve().parent.parent.parent
        / "combine-config/governance/secrets/detector_calibration.v1.json",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def load_calibration(path: Optional[Path] = None) -> dict:
    """Load calibration thresholds from artifact file."""
    if path is None:
        path = _find_calibration_path()
    if path and path.exists():
        return json.loads(path.read_text())
    return dict(_DEFAULT_CALIBRATION)


# ---------------------------------------------------------------------------
# Module-level calibration (loaded once)
# ---------------------------------------------------------------------------

_calibration = load_calibration()
LENGTH_THRESHOLD: int = _calibration.get("length_threshold", 20)
ENTROPY_THRESHOLD: float = _calibration.get("entropy_threshold", 3.0)
CHAR_CLASS_ADJUSTMENT: float = _calibration.get("char_class_adjustment", 0.85)
LOW_CLASS_ADJUSTMENT: float = _calibration.get("low_class_adjustment", 1.5)
DETECTOR_VERSION: str = _calibration.get("detector_version", "v1")


def reconfigure(calibration: dict) -> None:
    """Reconfigure thresholds (for testing)."""
    global LENGTH_THRESHOLD, ENTROPY_THRESHOLD, CHAR_CLASS_ADJUSTMENT, LOW_CLASS_ADJUSTMENT, DETECTOR_VERSION
    LENGTH_THRESHOLD = calibration.get("length_threshold", LENGTH_THRESHOLD)
    ENTROPY_THRESHOLD = calibration.get("entropy_threshold", ENTROPY_THRESHOLD)
    CHAR_CLASS_ADJUSTMENT = calibration.get("char_class_adjustment", CHAR_CLASS_ADJUSTMENT)
    LOW_CLASS_ADJUSTMENT = calibration.get("low_class_adjustment", LOW_CLASS_ADJUSTMENT)
    DETECTOR_VERSION = calibration.get("detector_version", DETECTOR_VERSION)


# ---------------------------------------------------------------------------
# Detection primitives
# ---------------------------------------------------------------------------

def shannon_entropy(s: str) -> float:
    """Calculate Shannon entropy of a string in bits per character."""
    if not s:
        return 0.0
    freq: dict[str, int] = {}
    for c in s:
        freq[c] = freq.get(c, 0) + 1
    length = len(s)
    return -sum((count / length) * math.log2(count / length) for count in freq.values())


def char_class_count(s: str) -> int:
    """Count character classes present (lowercase, uppercase, digit, special)."""
    has_lower = has_upper = has_digit = has_special = False
    for c in s:
        if c.islower():
            has_lower = True
        elif c.isupper():
            has_upper = True
        elif c.isdigit():
            has_digit = True
        else:
            has_special = True
    return sum([has_lower, has_upper, has_digit, has_special])


def is_hex_only(s: str) -> bool:
    """Check if string is composed entirely of hexadecimal characters."""
    return bool(s) and all(c in "0123456789abcdefABCDEF" for c in s)


_UUID_RE = re.compile(
    r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
)

KNOWN_PREFIXES = [
    "AKIA",           # AWS access key
    "ASIA",           # AWS STS key
    "ya29.",          # Google OAuth
    "ghp_",           # GitHub PAT
    "gho_",           # GitHub OAuth
    "ghs_",           # GitHub App
    "ghu_",           # GitHub user-to-server
    "github_pat_",    # GitHub fine-grained PAT
    "xoxb-",          # Slack bot
    "xoxp-",          # Slack user
    "xoxa-",          # Slack app
    "sk_live_",       # Stripe live
    "sk_test_",       # Stripe test
    "rk_live_",       # Stripe restricted
    "pk_live_",       # Stripe publishable
    "sq0csp-",        # Square
]

_TOKENIZER = re.compile(r'[\s,;:="\'`\{\}\[\]\(\)<>]+')

# Context patterns for non-secret hex values
_LABELED_HEX = re.compile(
    r'(?:sha256|sha512|sha384|sha1|md5|checksum|digest|content-hash|etag|commit|hash|build-id|trace-id)'
    r'\s*[:=]\s*([0-9a-fA-F]+)',
    re.IGNORECASE,
)
_DOCKER_DIGEST = re.compile(r'@sha256:([0-9a-fA-F]+)')
_GIT_CMD = re.compile(
    r'(?:git\s+(?:revert|cherry-pick|show|log|diff|checkout|reset|bisect))\s+([0-9a-fA-F]{7,40})',
    re.IGNORECASE,
)
_URL_HEX_PATH = re.compile(r'https?://[^\s]+/([0-9a-fA-F]{8,64})(?:\s|$)')
_CONNECTION_STRING = re.compile(r'://[^:]+:[^@]+@')


def _extract_excluded_tokens(text: str) -> set[str]:
    """Find hex tokens in known non-secret contexts."""
    excluded: set[str] = set()
    for pattern in [_LABELED_HEX, _DOCKER_DIGEST, _GIT_CMD, _URL_HEX_PATH]:
        for m in pattern.finditer(text):
            excluded.add(m.group(1))
    return excluded


def _is_benign_base64(token: str) -> bool:
    """Check if a base64 token decodes to printable ASCII text."""
    if not re.match(r'^[A-Za-z0-9+/]+={0,2}$', token):
        return False
    try:
        padded = token + "=" * (-len(token) % 4)
        decoded = base64.b64decode(padded)
        text = decoded.decode('ascii')
        printable_ratio = sum(1 for c in text if c.isprintable()) / len(text) if text else 0
        return printable_ratio > 0.9 and len(text) >= 4
    except Exception:
        return False


def _detect_pem(text: str) -> bool:
    """Check if text contains a PEM private key block."""
    return "-----BEGIN " in text and "PRIVATE KEY-----" in text


def _has_known_prefix(text: str) -> bool:
    """Check if text starts with a known credential prefix."""
    return any(text.startswith(p) for p in KNOWN_PREFIXES)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def scan_token(token: str, excluded: set[str] | None = None) -> ScanResult:
    """Scan a single token for secret characteristics."""
    clean = ScanResult("CLEAN", None, 0.0, DETECTOR_VERSION)

    if _UUID_RE.match(token):
        return clean

    if excluded and token in excluded:
        return clean

    if _is_benign_base64(token):
        return clean

    if _detect_pem(token):
        return ScanResult("SECRET_DETECTED", "PEM_BLOCK", shannon_entropy(token), DETECTOR_VERSION)

    if _has_known_prefix(token):
        return ScanResult("SECRET_DETECTED", "PATTERN_MATCH", shannon_entropy(token), DETECTOR_VERSION)

    if _CONNECTION_STRING.search(token):
        return ScanResult("SECRET_DETECTED", "CONNECTION_STRING", shannon_entropy(token), DETECTOR_VERSION)

    if len(token) < LENGTH_THRESHOLD:
        return clean

    entropy = shannon_entropy(token)
    classes = char_class_count(token)

    if is_hex_only(token):
        if entropy >= ENTROPY_THRESHOLD:
            return ScanResult("SECRET_DETECTED", "HIGH_ENTROPY_HEX", entropy, DETECTOR_VERSION)
    elif classes >= 3:
        adjusted = ENTROPY_THRESHOLD * CHAR_CLASS_ADJUSTMENT
        if entropy >= adjusted:
            return ScanResult("SECRET_DETECTED", "HIGH_ENTROPY_MIXED", entropy, DETECTOR_VERSION)
    else:
        adjusted = ENTROPY_THRESHOLD * LOW_CLASS_ADJUSTMENT
        if entropy >= adjusted:
            return ScanResult("SECRET_DETECTED", "HIGH_ENTROPY", entropy, DETECTOR_VERSION)

    return ScanResult("CLEAN", None, entropy, DETECTOR_VERSION)


def scan_text(text: str) -> ScanResult:
    """Scan arbitrary text for secret material.

    This is the canonical entry point for both the HTTP ingress gate
    and the orchestrator Tier-0 governance boundary.
    """
    if not text or not text.strip():
        return ScanResult("CLEAN", None, 0.0, DETECTOR_VERSION)

    # Full-text structural checks
    if _detect_pem(text):
        return ScanResult("SECRET_DETECTED", "PEM_BLOCK", shannon_entropy(text), DETECTOR_VERSION)

    if _CONNECTION_STRING.search(text):
        return ScanResult("SECRET_DETECTED", "CONNECTION_STRING", shannon_entropy(text), DETECTOR_VERSION)

    # Extract context-excluded tokens
    excluded = _extract_excluded_tokens(text)

    # Strip non-credential URLs before tokenization
    sanitized = re.sub(r'https?://[^\s]+', '', text)

    # Tokenize and check each token
    tokens = _TOKENIZER.split(sanitized)
    for token in tokens:
        if not token:
            continue
        result = scan_token(token, excluded)
        if result.verdict == "SECRET_DETECTED":
            return result

    return ScanResult("CLEAN", None, 0.0, DETECTOR_VERSION)


def scan_dict(data: dict, max_depth: int = 5) -> ScanResult:
    """Recursively scan dictionary values for secrets.

    Useful for scanning JSON request bodies, PGC answers, and
    workflow context_state.
    """
    if max_depth <= 0:
        return ScanResult("CLEAN", None, 0.0, DETECTOR_VERSION)

    for value in data.values():
        if isinstance(value, str):
            result = scan_text(value)
            if result.verdict == "SECRET_DETECTED":
                return result
        elif isinstance(value, dict):
            result = scan_dict(value, max_depth - 1)
            if result.verdict == "SECRET_DETECTED":
                return result
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    result = scan_text(item)
                    if result.verdict == "SECRET_DETECTED":
                        return result
                elif isinstance(item, dict):
                    result = scan_dict(item, max_depth - 1)
                    if result.verdict == "SECRET_DETECTED":
                        return result

    return ScanResult("CLEAN", None, 0.0, DETECTOR_VERSION)


def redact_for_logging(scan_result: ScanResult, request_id: str = "") -> dict:
    """Produce a redacted audit record suitable for logging.

    Per GOV-SEC-T0-002 Section 9: logging may record detection metadata
    but MUST NOT store secret material.
    """
    record = {
        "event": "[REDACTED_SECRET_DETECTED]" if scan_result.verdict == "SECRET_DETECTED" else "secret_scan_clean",
        "detector_version": scan_result.detector_version,
        "verdict": scan_result.verdict,
    }
    if request_id:
        record["request_id"] = request_id
    if scan_result.classification:
        record["classification"] = scan_result.classification
    if scan_result.entropy_score > 0:
        record["entropy_score"] = round(scan_result.entropy_score, 3)
    return record
