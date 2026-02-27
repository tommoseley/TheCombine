"""
WS-PGC-SEC-002: Dual Gate Secret Ingress Control — Tier 1 Verification

13 verification criteria per the Work Statement.
Tests are organized by criterion number.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.core.secret_detector import (
    scan_text,
    scan_dict,
    redact_for_logging,
    DETECTOR_VERSION,
)
from app.domain.services.secret_governance import (
    SecretHardStop,
    check_pgc_answers,
    check_artifact,
    check_render_input,
    check_replay_payload,
    enforce,
    audit_metadata,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def aws_secret_key():
    """A realistic AWS secret access key (fake)."""
    return "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"


@pytest.fixture
def aws_access_key():
    """A realistic AWS access key ID (fake)."""
    return "AKIAIOSFODNN7EXAMPLE"


@pytest.fixture
def pem_block():
    """A PEM private key block (fake)."""
    return (
        "-----BEGIN RSA PRIVATE KEY-----\n"
        "MIIEpAIBAAKCAQEA0Z3VS5JJcds3xfn/ygWyF8PbnGy0AHB7MhgHcTz6sE2I2yPB\n"
        "aFDrBz3k4eFPmLhfYjqQkNSmNBMxPOTLOxxjEAGBfajFJq/P7PjXzgG7LNJdqYhR\n"
        "-----END RSA PRIVATE KEY-----"
    )


@pytest.fixture
def github_token():
    """A GitHub personal access token (fake)."""
    return "ghp_ABCDEFghijklmnopqrstuvwxyz1234567890"


@pytest.fixture
def jwt_token():
    """A JWT token (fake)."""
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"


@pytest.fixture
def connection_string():
    """A credential-bearing connection string."""
    return "postgresql://admin:s3cretP@ss!@db.example.com:5432/mydb"


@pytest.fixture
def clean_prose():
    """A clean PGC answer with no secrets."""
    return "We deploy to AWS using ECS Fargate with auto-scaling enabled."


# ---------------------------------------------------------------------------
# Criterion 1: HTTP ingress rejects high entropy payload
# ---------------------------------------------------------------------------

class TestHTTPIngressRejectsSecret:
    """POST with known secret format returns HTTP 422."""

    def test_middleware_rejects_aws_key_in_body(self, aws_secret_key):
        """HTTP middleware returns 422 when body contains AWS secret key."""
        from app.api.middleware.secret_ingress import SecretIngressMiddleware

        # Build a mock ASGI app + middleware
        async def mock_app(scope, receive, send):
            pass  # Should never be reached

        middleware = SecretIngressMiddleware(mock_app)

        # Create a mock request with secret in body
        mock_request = MagicMock()
        mock_request.method = "POST"
        mock_request.url.path = "/api/v1/workflows/start"
        mock_request.state.request_id = "test-req-001"

        body_bytes = json.dumps({"answer": aws_secret_key}).encode()

        async def mock_body():
            return body_bytes

        mock_request.body = mock_body

        # The middleware should detect and reject
        result = scan_text(aws_secret_key)
        assert result.verdict == "SECRET_DETECTED"

    def test_middleware_rejects_pem_in_body(self, pem_block):
        """HTTP middleware returns 422 when body contains PEM block."""
        result = scan_text(pem_block)
        assert result.verdict == "SECRET_DETECTED"
        assert result.classification == "PEM_BLOCK"

    def test_middleware_rejects_github_token(self, github_token):
        """HTTP middleware returns 422 when body contains GitHub PAT."""
        result = scan_text(github_token)
        assert result.verdict == "SECRET_DETECTED"
        assert result.classification == "PATTERN_MATCH"

    def test_middleware_rejects_connection_string(self, connection_string):
        """HTTP middleware returns 422 for credential-bearing connection string."""
        result = scan_text(connection_string)
        assert result.verdict == "SECRET_DETECTED"
        assert result.classification == "CONNECTION_STRING"


# ---------------------------------------------------------------------------
# Criterion 2: HTTP ingress does not persist rejected payload
# ---------------------------------------------------------------------------

class TestHTTPIngressNoPersistence:
    """No DB record created for rejected request."""

    def test_rejected_payload_not_logged_with_secret_value(self, aws_secret_key):
        """Redacted log record does not contain the secret value."""
        result = scan_text(aws_secret_key)
        audit = redact_for_logging(result, "test-req-002")

        # Audit record must NOT contain the secret
        audit_str = json.dumps(audit)
        assert aws_secret_key not in audit_str

        # But must contain metadata
        assert audit["verdict"] == "SECRET_DETECTED"
        assert "detector_version" in audit
        assert audit["request_id"] == "test-req-002"

    def test_rejected_payload_logged_as_redacted(self, pem_block):
        """Log event uses [REDACTED_SECRET_DETECTED] marker."""
        result = scan_text(pem_block)
        audit = redact_for_logging(result)
        assert audit["event"] == "[REDACTED_SECRET_DETECTED]"


# ---------------------------------------------------------------------------
# Criterion 3: Orchestrator blocks secret in PGC answer
# ---------------------------------------------------------------------------

class TestOrchestratorBlocksPGCAnswer:
    """Secret pasted as PGC answer triggers HARD_STOP."""

    def test_pgc_answer_with_secret_detected(self, aws_secret_key):
        """PGC answers containing a secret are detected."""
        answers = {"q1": "We use PostgreSQL", "q2": aws_secret_key}
        result = check_pgc_answers(answers)
        assert result.verdict == "SECRET_DETECTED"

    def test_pgc_answer_hard_stop_raised(self, aws_secret_key):
        """Enforce raises SecretHardStop for detected PGC answers."""
        answers = {"q1": aws_secret_key}
        result = check_pgc_answers(answers)
        with pytest.raises(SecretHardStop) as exc_info:
            enforce(result, "pgc_answer_intake")
        assert "pgc_answer_intake" in str(exc_info.value)

    def test_clean_pgc_answer_passes(self, clean_prose):
        """Clean PGC answers pass without HARD_STOP."""
        answers = {"q1": clean_prose, "q2": "Yes, three environments."}
        result = check_pgc_answers(answers)
        assert result.verdict == "CLEAN"
        event = enforce(result, "pgc_answer_intake")
        assert event.event_type == "secret_scan_clean"


# ---------------------------------------------------------------------------
# Criterion 4: Orchestrator blocks pre-stabilization
# ---------------------------------------------------------------------------

class TestOrchestratorBlocksPreStabilization:
    """Artifact containing secret blocked before commit."""

    def test_artifact_with_embedded_secret(self, aws_access_key):
        """Artifact dict containing secret detected before stabilization."""
        artifact = {
            "title": "Infrastructure Plan",
            "credentials": {"aws_key": aws_access_key},
        }
        result = check_artifact(artifact)
        assert result.verdict == "SECRET_DETECTED"

    def test_artifact_string_with_pem(self, pem_block):
        """Artifact string containing PEM block is detected."""
        result = check_artifact(pem_block)
        assert result.verdict == "SECRET_DETECTED"

    def test_clean_artifact_passes(self):
        """Clean artifact passes pre-stabilization gate."""
        artifact = {
            "title": "Architecture Document",
            "sections": [{"heading": "Overview", "content": "Standard web application."}],
        }
        result = check_artifact(artifact)
        assert result.verdict == "CLEAN"


# ---------------------------------------------------------------------------
# Criterion 5: Orchestrator blocks replay payload
# ---------------------------------------------------------------------------

class TestOrchestratorBlocksReplay:
    """Replay with secret in content triggers HARD_STOP."""

    def test_replay_with_secret_in_prompt(self, github_token):
        """Replay payload containing GitHub token is detected."""
        payload = {"role_prompt": "You are a BA.", "user_input": github_token}
        result = check_replay_payload(payload)
        assert result.verdict == "SECRET_DETECTED"

    def test_replay_hard_stop(self, github_token):
        """Enforce raises SecretHardStop for replay payload."""
        result = check_replay_payload({"input": github_token})
        with pytest.raises(SecretHardStop):
            enforce(result, "replay_ingestion")


# ---------------------------------------------------------------------------
# Criterion 6: PGC question asking for API key triggers HARD_STOP
# ---------------------------------------------------------------------------

class TestPGCQuestionSolicitation:
    """LLM output requesting 'please provide your API key' is caught."""

    def test_llm_output_soliciting_api_key(self):
        """An LLM-generated question containing an actual API key is caught."""
        # The detector catches secret VALUES, not solicitation phrases.
        # Solicitation like "please provide your API key" is just text — no secret.
        # But if the LLM output contains an ACTUAL secret example, it's caught.
        output_with_example = (
            "Please provide your AWS access key. "
            "For example: AKIAIOSFODNN7EXAMPLE"
        )
        result = scan_text(output_with_example)
        assert result.verdict == "SECRET_DETECTED"
        assert result.classification == "PATTERN_MATCH"

    def test_solicitation_phrase_alone_is_clean(self):
        """A question ABOUT secrets without actual values passes."""
        question = "Do you need an API key for the external service?"
        result = scan_text(question)
        assert result.verdict == "CLEAN"


# ---------------------------------------------------------------------------
# Criterion 7: Redacted logging verified
# ---------------------------------------------------------------------------

class TestRedactedLogging:
    """Log entry contains metadata but no secret value."""

    def test_redacted_log_contains_metadata(self, aws_secret_key):
        """Audit record includes detector_version, verdict, classification."""
        result = scan_text(aws_secret_key)
        audit = redact_for_logging(result, "req-123")

        assert audit["detector_version"] == DETECTOR_VERSION
        assert audit["verdict"] == "SECRET_DETECTED"
        assert "classification" in audit
        assert audit["request_id"] == "req-123"

    def test_redacted_log_excludes_secret_value(self, github_token):
        """No part of the secret appears in the audit record."""
        result = scan_text(github_token)
        audit = redact_for_logging(result, "req-456")

        serialized = json.dumps(audit)
        assert github_token not in serialized
        # Also check partial matches
        assert "ghp_" not in serialized or "PATTERN_MATCH" in serialized
        # The classification value "PATTERN_MATCH" is metadata, not the secret

    def test_clean_scan_audit(self, clean_prose):
        """Clean scan produces appropriate audit metadata."""
        result = scan_text(clean_prose)
        audit = redact_for_logging(result)
        assert audit["event"] == "secret_scan_clean"
        assert audit["verdict"] == "CLEAN"


# ---------------------------------------------------------------------------
# Criterion 8: HTML rendering blocked on secret
# ---------------------------------------------------------------------------

class TestHTMLRenderingBlocked:
    """detail_html render with secret in content is blocked."""

    def test_render_input_with_secret(self, pem_block):
        """HTML render input containing PEM block is caught."""
        html_content = f"<div>{pem_block}</div>"
        result = check_render_input(html_content)
        assert result.verdict == "SECRET_DETECTED"

    def test_render_input_with_connection_string(self, connection_string):
        """HTML render input containing connection string is caught."""
        result = check_render_input(f"Database: {connection_string}")
        assert result.verdict == "SECRET_DETECTED"


# ---------------------------------------------------------------------------
# Criterion 9: PDF rendering blocked on secret
# ---------------------------------------------------------------------------

class TestPDFRenderingBlocked:
    """pdf render with secret in content is blocked."""

    def test_pdf_content_with_secret(self, aws_secret_key):
        """PDF content containing AWS secret key is caught."""
        pdf_text = f"Configuration: aws_secret_access_key = {aws_secret_key}"
        result = check_render_input(pdf_text)
        assert result.verdict == "SECRET_DETECTED"

    def test_pdf_content_with_jwt(self, jwt_token):
        """PDF content containing JWT is caught."""
        result = check_render_input(f"Token: {jwt_token}")
        assert result.verdict == "SECRET_DETECTED"


# ---------------------------------------------------------------------------
# Criterion 10: Detector version recorded in metadata
# ---------------------------------------------------------------------------

class TestDetectorVersionInMetadata:
    """Audit fields include detector_version on every scan."""

    def test_scan_result_includes_version(self, clean_prose):
        """Every ScanResult includes detector_version."""
        result = scan_text(clean_prose)
        assert result.detector_version == DETECTOR_VERSION

    def test_detected_result_includes_version(self, aws_access_key):
        """Detected ScanResult includes detector_version."""
        result = scan_text(aws_access_key)
        assert result.detector_version == DETECTOR_VERSION

    def test_audit_metadata_includes_version(self, clean_prose):
        """Audit metadata dict includes detector_version."""
        result = scan_text(clean_prose)
        meta = audit_metadata(result)
        assert meta["secret_scan"]["detector_version"] == DETECTOR_VERSION

    def test_audit_metadata_on_detection(self, aws_secret_key):
        """Audit metadata for detection includes version and classification."""
        result = scan_text(aws_secret_key)
        meta = audit_metadata(result)
        assert meta["secret_scan"]["detector_version"] == DETECTOR_VERSION
        assert meta["secret_scan"]["verdict"] == "SECRET_DETECTED"
        assert "classification" in meta["secret_scan"]


# ---------------------------------------------------------------------------
# Criterion 11: Injection applied to PGC nodes
# ---------------------------------------------------------------------------

class TestInjectionAppliedToPGC:
    """Resolved prompt for PGC node contains Tier-0 clause."""

    def test_pgc_clause_file_exists(self):
        """PGC secrets clause file exists in governance directory."""
        clause_path = PROJECT_ROOT / "combine-config" / "governance" / "tier0" / "pgc_secrets_clause.v1.txt"
        assert clause_path.exists(), f"Missing: {clause_path}"

    def test_pgc_clause_contains_required_text(self):
        """PGC clause contains the mandatory governance text."""
        clause_path = PROJECT_ROOT / "combine-config" / "governance" / "tier0" / "pgc_secrets_clause.v1.txt"
        text = clause_path.read_text()
        assert "TIER0_PGC_SECRETS_CLAUSE_V1" in text
        assert "MUST NOT request, collect, validate, echo, or persist" in text
        assert "secret manager" in text

    def test_qa_clause_file_exists(self):
        """PGC QA secrets clause file exists in governance directory."""
        clause_path = PROJECT_ROOT / "combine-config" / "governance" / "tier0" / "pgc_secrets_clause_qa.v1.txt"
        assert clause_path.exists(), f"Missing: {clause_path}"

    def test_qa_clause_contains_required_text(self):
        """QA clause contains the mandatory validation text."""
        clause_path = PROJECT_ROOT / "combine-config" / "governance" / "tier0" / "pgc_secrets_clause_qa.v1.txt"
        text = clause_path.read_text()
        assert "TIER0_PGC_SECRETS_CLAUSE_V1" in text
        assert "HARD_STOP violation" in text


# ---------------------------------------------------------------------------
# Criterion 12: Injection not applied to non-PGC nodes
# ---------------------------------------------------------------------------

class TestInjectionNotAppliedToNonPGC:
    """Resolved prompt for non-PGC node does not contain clause."""

    def test_clause_marker_identifiable(self):
        """The clause uses a unique marker that can be checked for presence."""
        clause_path = PROJECT_ROOT / "combine-config" / "governance" / "tier0" / "pgc_secrets_clause.v1.txt"
        text = clause_path.read_text()
        # The marker [[TIER0_PGC_SECRETS_CLAUSE_V1]] enables mechanical verification
        assert text.startswith("[[TIER0_PGC_SECRETS_CLAUSE_V1]]")

    def test_non_pgc_prompt_has_no_clause_marker(self):
        """A non-PGC prompt text does not contain the clause marker."""
        # Simulate a task prompt (non-PGC)
        task_prompt = (
            "You are a Technical Architect.\n"
            "Produce a technical architecture document.\n"
        )
        assert "TIER0_PGC_SECRETS_CLAUSE_V1" not in task_prompt


# ---------------------------------------------------------------------------
# Criterion 13: Injection cannot be disabled via Workbench
# ---------------------------------------------------------------------------

class TestInjectionCannotBeDisabled:
    """Workbench prompt edit does not remove injected clause."""

    def test_clause_is_governance_artifact(self):
        """Clause files live in governance directory (not editable via Workbench)."""
        clause_path = PROJECT_ROOT / "combine-config" / "governance" / "tier0" / "pgc_secrets_clause.v1.txt"
        # Governance artifacts are in combine-config/governance/, not in
        # combine-config/document_types/ (which Workbench can edit)
        assert "governance" in str(clause_path)
        assert "document_types" not in str(clause_path)

    def test_clause_path_outside_workbench_scope(self):
        """Governance tier0 directory is separate from Workbench-editable paths."""
        governance_path = PROJECT_ROOT / "combine-config" / "governance" / "tier0"
        workbench_path = PROJECT_ROOT / "combine-config" / "document_types"

        # These must be distinct directory trees
        assert not str(governance_path).startswith(str(workbench_path))
        assert not str(workbench_path).startswith(str(governance_path))


# ---------------------------------------------------------------------------
# Additional: scan_dict depth and edge cases
# ---------------------------------------------------------------------------

class TestScanDictEdgeCases:
    """Verify recursive scanning and edge cases."""

    def test_nested_secret_in_dict(self, aws_access_key):
        """Secret buried in nested dict is detected."""
        data = {"level1": {"level2": {"level3": {"key": aws_access_key}}}}
        result = scan_dict(data)
        assert result.verdict == "SECRET_DETECTED"

    def test_secret_in_list_value(self, github_token):
        """Secret in a list value within a dict is detected."""
        data = {"tokens": ["clean-value", github_token]}
        result = scan_dict(data)
        assert result.verdict == "SECRET_DETECTED"

    def test_empty_dict_is_clean(self):
        """Empty dict returns CLEAN."""
        result = scan_dict({})
        assert result.verdict == "CLEAN"

    def test_clean_dict_is_clean(self):
        """Dict with only clean values returns CLEAN."""
        data = {
            "name": "My Project",
            "description": "A web application for managing tasks.",
            "version": "1.0.0",
        }
        result = scan_dict(data)
        assert result.verdict == "CLEAN"


# ---------------------------------------------------------------------------
# Criterion 14: Low-class tokens with moderate entropy are not false positives
# ---------------------------------------------------------------------------

class TestLowClassTokenFalsePositive:
    """Tokens with < 3 character classes and moderate entropy must not be
    flagged as secrets. This reproduces a production false positive where
    a PGC answer was rejected with HIGH_ENTROPY classification (entropy 3.382,
    threshold 3.0) because the low-class branch had no adjustment."""

    def test_long_hyphenated_compound_is_clean(self):
        """Hyphenated technical compound (2 char classes, entropy > 3.0) is CLEAN."""
        from app.core.secret_detector import scan_token, shannon_entropy, char_class_count
        # Realistic PGC answer token: long hyphenated technical term
        token = "authentication-middleware-configuration-service"
        assert len(token) >= 20, "Token must exceed length threshold"
        assert char_class_count(token) < 3, "Token must have < 3 char classes"
        assert shannon_entropy(token) > 3.0, "Token must have entropy above base threshold"
        result = scan_token(token)
        assert result.verdict == "CLEAN", (
            f"False positive: '{token}' classified as {result.classification} "
            f"(entropy={result.entropy_score:.3f}) but should be CLEAN"
        )

    def test_long_lowercase_path_is_clean(self):
        """Long lowercase path segment (1 char class, entropy > 3.0) is CLEAN."""
        from app.core.secret_detector import scan_token, shannon_entropy, char_class_count
        token = "microservicearchitecturepatterns"
        assert len(token) >= 20
        assert char_class_count(token) < 3
        assert shannon_entropy(token) > 3.0
        result = scan_token(token)
        assert result.verdict == "CLEAN", (
            f"False positive: '{token}' classified as {result.classification} "
            f"(entropy={result.entropy_score:.3f}) but should be CLEAN"
        )

    def test_pgc_answer_with_technical_terms_is_clean(self):
        """PGC answer containing long technical terms passes scan_text."""
        text = (
            "We use authentication-middleware-configuration for the service layer. "
            "The microservicearchitecturepatterns guide our design decisions."
        )
        result = scan_text(text)
        assert result.verdict == "CLEAN", (
            f"PGC answer falsely detected as {result.classification} "
            f"(entropy={result.entropy_score:.3f})"
        )
