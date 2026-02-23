"""
WS-PGC-SEC-002-A: Secret Detector Calibration Spike — Tier 1 Verification

Criteria:
1. Prose corpus meets minimum size (>= 5,000 non-secret samples)
2. Secret corpus covers all required types (AWS, PEM, OAuth, random, short, Base64, JWT)
3. Threshold sweep complete (all length x entropy combinations tested)
4. TPR meets target (>= 99% on secret corpus)
5. FPR meets target (<= 1% on prose corpus)
6. Short API keys caught (selected threshold detects 20-40 char API keys)
7. Calibration artifact valid (output JSON matches schema with all required fields)
8. Corpus hash recorded (calibration artifact contains SHA-256 of corpus)
"""

import json
from pathlib import Path

import pytest

# Import the calibration module
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "ops" / "scripts"))
from calibrate_secret_detector import (
    generate_prose_corpus,
    generate_secret_corpus,
    scan_text,
    sweep,
    LENGTH_THRESHOLDS,
    ENTROPY_THRESHOLDS,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ARTIFACT_PATH = PROJECT_ROOT / "combine-config" / "governance" / "secrets" / "detector_calibration.v1.json"

REQUIRED_SECRET_FAMILIES = {
    "aws": "aws_",
    "pem": "pem_",
    "oauth": "oauth_",
    "random_key": "random_key_",
    "short_api_key": "short_api_key_",
    "base64_secret": "base64_secret_",
    "jwt": "jwt",
}


@pytest.fixture(scope="module")
def prose_corpus():
    return generate_prose_corpus(5500)


@pytest.fixture(scope="module")
def secret_corpus():
    return generate_secret_corpus()


@pytest.fixture(scope="module")
def calibration_artifact():
    assert ARTIFACT_PATH.exists(), f"Calibration artifact not found at {ARTIFACT_PATH}"
    return json.loads(ARTIFACT_PATH.read_text())


# --- Criterion 1: Prose corpus meets minimum size ---

def test_prose_corpus_minimum_size(prose_corpus):
    """Prose corpus contains >= 5,000 non-secret samples."""
    assert len(prose_corpus) >= 5000, (
        f"Prose corpus has {len(prose_corpus)} samples, need >= 5,000"
    )


# --- Criterion 2: Secret corpus covers all required types ---

@pytest.mark.parametrize("family,prefix", REQUIRED_SECRET_FAMILIES.items())
def test_secret_corpus_covers_type(secret_corpus, family, prefix):
    """Secret corpus includes samples for each required secret family."""
    matching = [s for s in secret_corpus if s["type"].startswith(prefix)]
    assert len(matching) > 0, (
        f"Secret corpus missing {family} samples (prefix: {prefix})"
    )


# --- Criterion 3: Threshold sweep complete ---

def test_threshold_sweep_complete(prose_corpus, secret_corpus):
    """All length x entropy threshold combinations are tested."""
    results = sweep(prose_corpus, secret_corpus)
    expected_count = len(LENGTH_THRESHOLDS) * len(ENTROPY_THRESHOLDS)
    assert len(results) == expected_count, (
        f"Sweep produced {len(results)} results, expected {expected_count}"
    )

    # Verify all combinations present
    combos = {(r["length_threshold"], r["entropy_threshold"]) for r in results}
    for lt in LENGTH_THRESHOLDS:
        for et in ENTROPY_THRESHOLDS:
            assert (lt, et) in combos, f"Missing combination: length={lt}, entropy={et}"


# --- Criterion 4: TPR meets target ---

def test_tpr_meets_target(calibration_artifact):
    """Selected threshold achieves >= 99% TPR on secret corpus."""
    tpr = calibration_artifact["expected_tpr"]
    assert tpr >= 0.99, f"TPR is {tpr:.4f}, must be >= 0.99"


# --- Criterion 5: FPR meets target ---

def test_fpr_meets_target(calibration_artifact):
    """Selected threshold achieves <= 1% FPR on prose corpus."""
    fpr = calibration_artifact["expected_fpr"]
    assert fpr <= 0.01, f"FPR is {fpr:.4f}, must be <= 0.01"


# --- Criterion 6: Short API keys caught ---

def test_short_api_keys_detected(secret_corpus, calibration_artifact):
    """Selected threshold detects 20-40 char API keys."""
    lt = calibration_artifact["length_threshold"]
    et = calibration_artifact["entropy_threshold"]

    short_keys = [s for s in secret_corpus if "short_api_key" in s["type"]]
    assert len(short_keys) > 0, "No short API keys in corpus"

    detected = sum(
        1 for s in short_keys
        if scan_text(s["value"], lt, et)["verdict"] == "SECRET_DETECTED"
    )
    detection_rate = detected / len(short_keys)
    assert detection_rate >= 0.95, (
        f"Short API key detection rate is {detection_rate:.4f}, must be >= 0.95"
    )


# --- Criterion 7: Calibration artifact valid ---

REQUIRED_ARTIFACT_FIELDS = [
    "detector_version",
    "length_threshold",
    "entropy_threshold",
    "expected_tpr",
    "expected_fpr",
    "calibration_corpus_hash",
    "date",
]


def test_calibration_artifact_exists():
    """Calibration artifact file exists on disk."""
    assert ARTIFACT_PATH.exists(), f"Missing: {ARTIFACT_PATH}"


def test_calibration_artifact_valid_json():
    """Calibration artifact is valid JSON."""
    content = ARTIFACT_PATH.read_text()
    artifact = json.loads(content)
    assert isinstance(artifact, dict)


@pytest.mark.parametrize("field", REQUIRED_ARTIFACT_FIELDS)
def test_calibration_artifact_has_field(calibration_artifact, field):
    """Calibration artifact contains all required fields."""
    assert field in calibration_artifact, f"Missing field: {field}"


def test_calibration_artifact_detector_version(calibration_artifact):
    """Detector version is v1."""
    assert calibration_artifact["detector_version"] == "v1"


def test_calibration_artifact_thresholds_numeric(calibration_artifact):
    """Thresholds are numeric values."""
    assert isinstance(calibration_artifact["length_threshold"], int)
    assert isinstance(calibration_artifact["entropy_threshold"], (int, float))


# --- Criterion 8: Corpus hash recorded ---

def test_corpus_hash_recorded(calibration_artifact):
    """Calibration artifact contains SHA-256 hash of the corpus used."""
    corpus_hash = calibration_artifact.get("calibration_corpus_hash")
    assert corpus_hash is not None, "Missing calibration_corpus_hash"
    assert isinstance(corpus_hash, str), "corpus_hash must be a string"
    assert len(corpus_hash) == 64, f"corpus_hash length is {len(corpus_hash)}, expected 64 (SHA-256)"
    assert all(c in "0123456789abcdef" for c in corpus_hash), "corpus_hash must be lowercase hex"
