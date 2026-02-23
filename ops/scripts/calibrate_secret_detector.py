#!/usr/bin/env python3
"""
WS-PGC-SEC-002-A: Secret Detector Calibration Spike

Generates prose and secret corpora, sweeps entropy x length thresholds,
measures TPR/FPR, and produces a versioned calibration artifact.

Detection uses three layers:
  1. Structural detection (PEM blocks)
  2. Known prefix patterns (AKIA, ghp_, sk_live_, etc.)
  3. Entropy + character distribution analysis

Usage:
    python ops/scripts/calibrate_secret_detector.py
"""

import base64
import hashlib
import json
import math
import random
import re
import secrets
import string
import uuid
from datetime import date
from pathlib import Path

# ---------------------------------------------------------------------------
# Corpus generators
# ---------------------------------------------------------------------------

PROSE_TEMPLATES = [
    # Infrastructure descriptions
    "We deploy to {cloud} using {service} with {region} region configuration.",
    "The database runs on {db} version {ver} with {replicas} read replicas.",
    "Our load balancer terminates TLS and forwards to port {port}.",
    "CI/CD pipeline triggers on push to {branch} and deploys via {tool}.",
    "Container images are stored in {registry} and pulled at deploy time.",
    "DNS is managed through {dns} with a {ttl} second TTL.",
    "Monitoring uses {monitor} with alerts routed to {channel}.",
    "Backups run every {hours} hours and are retained for {days} days.",
    "The application uses {framework} with {orm} for data access.",
    "Authentication is handled via {auth} with {session} session management.",
    "We use {queue} for async task processing with {workers} workers.",
    "Log aggregation flows through {logger} to {store} for retention.",
    "The API rate limit is set to {rpm} requests per minute per client.",
    "Static assets are served from {cdn} with cache TTL of {cache_ttl} seconds.",
    "Health checks run every {interval} seconds on the {path} endpoint.",
    # PGC-style answers
    "Yes, the project requires a PostgreSQL database for persistent storage.",
    "We need three environments: development, staging, and production.",
    "The team consists of {count} developers and {qa} QA engineers.",
    "We plan to use microservices architecture with REST APIs between services.",
    "The expected load is approximately {rps} requests per second at peak.",
    "Data retention policy requires keeping records for {years} years.",
    "The application should support {users} concurrent users.",
    "We need OAuth 2.0 integration with Google and GitHub providers.",
    "The secret manager will be AWS Secrets Manager for all credentials.",
    "Runtime resolution should happen at container startup, not build time.",
    "We use Terraform for infrastructure provisioning across all environments.",
    "The deployment target is ECS Fargate with auto-scaling enabled.",
    "We need a Redis cache layer for session management and rate limiting.",
    "The frontend is a React SPA served from CloudFront.",
    "Database migrations are managed through Alembic with version control.",
    "We want blue-green deployments with automatic rollback on failure.",
    "The API follows OpenAPI 3.0 specification with generated documentation.",
    "Error tracking uses Sentry with PII scrubbing enabled.",
    "The batch processing job runs nightly and processes about {records} records.",
    "We need CORS configured to allow requests from {domain} only.",
    # Natural conversation
    "I think we should prioritize the authentication flow first.",
    "The current architecture won't scale beyond {threshold} users.",
    "Can we discuss the caching strategy for the product catalog?",
    "The mobile app needs offline support with eventual consistency.",
    "We should implement circuit breakers for all external service calls.",
    "The search feature should use Elasticsearch with fuzzy matching.",
    "Let me know if you need any additional context about the requirements.",
    "The compliance team requires audit logging for all data access.",
    "We're migrating from a monolith to microservices incrementally.",
    "The webhook system should support retry with exponential backoff.",
    # Technical descriptions
    "The service mesh uses Istio for traffic management and observability.",
    "gRPC is preferred for inter-service communication due to performance.",
    "The event sourcing pattern is used for the order management domain.",
    "Feature flags are managed through LaunchDarkly with gradual rollouts.",
    "The GraphQL gateway aggregates data from {count} backend services.",
    "We implement CQRS for the inventory management bounded context.",
    "The notification service supports email, SMS, and push channels.",
    "Database sharding is planned when we exceed {size} GB of data.",
    "The API gateway handles authentication, rate limiting, and routing.",
    "We use structured logging with correlation IDs across all services.",
    # Longer technical answers with mixed content
    "The deployment pipeline has four stages: build, test, stage, and production. "
    "Each stage runs in its own VPC with separate security groups.",
    "We use a multi-region active-passive setup. The primary region is us-east-1 "
    "with failover to eu-west-1. RTO target is under 15 minutes.",
    "Our data pipeline processes events from Kafka topics, transforms them using "
    "Apache Flink, and loads results into a Redshift data warehouse.",
    "The microservices communicate through an event bus pattern. Each service "
    "publishes domain events that other services can subscribe to.",
    "Testing strategy includes unit tests, integration tests with testcontainers, "
    "contract tests using Pact, and end-to-end tests with Playwright.",
]

FILL_VALUES = {
    "cloud": ["AWS", "GCP", "Azure", "DigitalOcean"],
    "service": ["ECS", "EKS", "Lambda", "App Engine", "Cloud Run"],
    "region": ["us-east-1", "eu-west-1", "ap-southeast-1", "us-west-2"],
    "db": ["PostgreSQL", "MySQL", "MongoDB", "DynamoDB"],
    "ver": ["14.2", "15.1", "8.0", "6.0", "16.1"],
    "replicas": ["2", "3", "4", "5"],
    "port": ["8080", "3000", "8000", "5000", "443"],
    "branch": ["main", "master", "develop", "release"],
    "tool": ["GitHub Actions", "Jenkins", "GitLab CI", "CircleCI"],
    "registry": ["ECR", "GCR", "Docker Hub", "GitHub Packages"],
    "dns": ["Route 53", "CloudFlare", "Cloud DNS"],
    "ttl": ["60", "300", "600", "3600"],
    "monitor": ["Datadog", "CloudWatch", "Prometheus", "New Relic"],
    "channel": ["Slack", "PagerDuty", "OpsGenie", "email"],
    "hours": ["6", "12", "24"],
    "days": ["7", "30", "90", "365"],
    "framework": ["FastAPI", "Django", "Flask", "Express", "Spring Boot"],
    "orm": ["SQLAlchemy", "Django ORM", "Prisma", "Hibernate"],
    "auth": ["OAuth 2.0", "SAML", "OpenID Connect", "JWT"],
    "session": ["Redis-backed", "cookie-based", "token-based"],
    "queue": ["SQS", "RabbitMQ", "Kafka", "Celery"],
    "workers": ["4", "8", "16", "32"],
    "logger": ["Fluentd", "Logstash", "CloudWatch Logs"],
    "store": ["Elasticsearch", "S3", "CloudWatch", "Loki"],
    "rpm": ["100", "500", "1000", "5000"],
    "cdn": ["CloudFront", "Cloudflare", "Fastly"],
    "cache_ttl": ["60", "300", "3600", "86400"],
    "interval": ["10", "30", "60"],
    "path": ["/health", "/healthz", "/status", "/ping"],
    "count": ["5", "8", "12", "20"],
    "qa": ["2", "3", "4"],
    "rps": ["100", "500", "1000", "5000", "10000"],
    "years": ["1", "3", "5", "7"],
    "users": ["100", "1000", "10000", "50000"],
    "records": ["10000", "50000", "100000", "1000000"],
    "domain": ["example.com", "app.example.com", "*.example.com"],
    "threshold": ["10000", "50000", "100000"],
    "size": ["100", "500", "1000"],
}

# JSON payloads without credentials
JSON_TEMPLATES = [
    '{"name": "{name}", "type": "{type}", "version": "{ver}", "enabled": true}',
    '{"database": {"host": "db.internal", "port": 5432, "name": "{name}", "pool_size": {pool}}}',
    '{"deployment": {"strategy": "{strategy}", "replicas": {replicas}, "region": "{region}"}}',
    '{"logging": {"level": "{level}", "format": "json", "destination": "{dest}"}}',
    '{"cache": {"provider": "{provider}", "ttl": {ttl}, "max_size": {size}}}',
    '{"features": {"dark_mode": true, "beta_access": false, "analytics": true}}',
    '{"notification": {"channels": ["email", "slack"], "throttle_seconds": {throttle}}}',
    '{"cors": {"origins": ["https://app.example.com"], "methods": ["GET", "POST"]}}',
    '{"rateLimit": {"window": "1m", "max": {max}, "strategy": "sliding_window"}}',
    '{"healthCheck": {"path": "/health", "interval": {interval}, "timeout": {timeout}}}',
]

JSON_FILL = {
    "name": ["myapp", "service-a", "worker", "gateway", "auth-service"],
    "type": ["web", "worker", "cron", "api"],
    "ver": ["1.0.0", "2.3.1", "0.9.0"],
    "pool": ["5", "10", "20"],
    "strategy": ["rolling", "blue-green", "canary"],
    "replicas": ["2", "3", "4"],
    "region": ["us-east-1", "eu-west-1"],
    "level": ["info", "debug", "warning"],
    "dest": ["stdout", "file", "cloudwatch"],
    "provider": ["redis", "memcached", "in-memory"],
    "ttl": ["60", "300", "3600"],
    "size": ["1000", "5000", "10000"],
    "throttle": ["60", "300"],
    "max": ["100", "500", "1000"],
    "interval": ["10", "30"],
    "timeout": ["5", "10"],
}


def _fill_template(template: str, values: dict) -> str:
    """Fill template placeholders with random values."""
    result = template
    for key, options in values.items():
        placeholder = "{" + key + "}"
        if placeholder in result:
            result = result.replace(placeholder, random.choice(options), 1)
    return result


def generate_prose_corpus(n: int = 5500) -> list[str]:
    """Generate n prose samples from templates with random fills."""
    rng = random.Random(42)
    corpus = []

    # Template-based samples (bulk)
    for _ in range(n - 550):
        template = rng.choice(PROSE_TEMPLATES)
        sample = _fill_template(template, FILL_VALUES)
        corpus.append(sample)

    # JSON samples (non-credential)
    for _ in range(200):
        template = rng.choice(JSON_TEMPLATES)
        sample = _fill_template(template, JSON_FILL)
        corpus.append(sample)

    # UUIDs — common in technical answers (8-4-4-4-12 format)
    for _ in range(100):
        corpus.append(str(uuid.uuid4()))

    # Hex references embedded in context (realistic PGC answers)
    # Short git hashes (7-10 chars)
    for _ in range(50):
        short_hash = secrets.token_hex(rng.randint(4, 5))[:rng.randint(7, 10)]
        corpus.append(f"The fix is in commit {short_hash}")

    # Full git hashes (40 chars, hex) — in context
    for _ in range(30):
        full_hash = secrets.token_hex(20)
        corpus.append(f"git revert {full_hash}")

    # SHA-256 hashes with labels
    for _ in range(30):
        sha = secrets.token_hex(32)
        label = rng.choice(["sha256", "checksum", "digest", "content-hash"])
        corpus.append(f"{label}: {sha}")

    # Docker image digests
    for _ in range(20):
        digest = secrets.token_hex(32)
        corpus.append(f"myapp@sha256:{digest}")

    # Base64-encoded non-secret data (config values, file names, etc.)
    b64_words = [
        "hello world", "test data", "configuration value",
        "deployment metadata", "build artifact name",
        "my-application", "service-config", "health-check",
        "default-settings", "production-east",
    ]
    for _ in range(50):
        word = rng.choice(b64_words)
        corpus.append(base64.b64encode(word.encode()).decode())

    # Version strings, semver, etc.
    for _ in range(20):
        corpus.append(f"v{rng.randint(1,9)}.{rng.randint(0,20)}.{rng.randint(0,50)}")

    # URLs with path segments
    for _ in range(30):
        path_id = secrets.token_hex(8)
        corpus.append(f"https://api.example.com/v1/resources/{path_id}")

    # Long prose answers (realistic multi-sentence PGC)
    long_answers = [
        "We currently have a monolithic application built with Django. The plan is to "
        "extract the user management, billing, and notification modules into separate "
        "microservices over the next two quarters. Each service will have its own "
        "PostgreSQL database to ensure data isolation.",
        "The authentication flow works as follows: user submits credentials, the auth "
        "service validates against the identity provider, issues a JWT with a 15-minute "
        "expiry, and stores a refresh token in Redis with a 7-day TTL.",
        "For the migration, we need to maintain backward compatibility with the existing "
        "REST API while introducing GraphQL for new clients. The gateway will route "
        "requests based on the Accept header and API version prefix.",
    ]
    for _ in range(20):
        corpus.append(rng.choice(long_answers))

    rng.shuffle(corpus)
    return corpus[:n]


# ---------------------------------------------------------------------------
# Secret corpus
# ---------------------------------------------------------------------------

def _generate_aws_key() -> str:
    suffix = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(16))
    return f"AKIA{suffix}"


def _generate_aws_secret() -> str:
    charset = string.ascii_letters + string.digits + "+/"
    return "".join(secrets.choice(charset) for _ in range(40))


def _generate_pem_block(key_type: str = "RSA") -> str:
    body_lines = []
    for _ in range(random.randint(4, 8)):
        body_lines.append(base64.b64encode(secrets.token_bytes(48)).decode())
    body = "\n".join(body_lines)
    headers = {
        "RSA": ("-----BEGIN RSA PRIVATE KEY-----", "-----END RSA PRIVATE KEY-----"),
        "EC": ("-----BEGIN EC PRIVATE KEY-----", "-----END EC PRIVATE KEY-----"),
    }
    begin, end = headers.get(key_type, ("-----BEGIN PRIVATE KEY-----", "-----END PRIVATE KEY-----"))
    return f"{begin}\n{body}\n{end}"


def _generate_oauth_token() -> str:
    return "ya29." + "".join(secrets.choice(string.ascii_letters + string.digits + "-_")
                             for _ in range(120))


def _generate_random_key(bits: int) -> str:
    return secrets.token_hex(bits // 8)


def _generate_short_api_key(length: int) -> str:
    charset = string.ascii_letters + string.digits
    return "".join(secrets.choice(charset) for _ in range(length))


def _generate_base64_secret(byte_len: int = 32) -> str:
    return base64.b64encode(secrets.token_bytes(byte_len)).decode()


def _generate_jwt() -> str:
    header = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').decode().rstrip("=")
    payload_data = f'{{"sub":"user123","iat":{random.randint(1700000000, 1800000000)}}}'
    payload = base64.urlsafe_b64encode(payload_data.encode()).decode().rstrip("=")
    sig = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")
    return f"{header}.{payload}.{sig}"


def _generate_github_token() -> str:
    return "ghp_" + "".join(secrets.choice(string.ascii_letters + string.digits)
                            for _ in range(36))


def _generate_slack_token() -> str:
    return "xoxb-" + "-".join(
        "".join(secrets.choice(string.digits) for _ in range(random.randint(10, 13)))
        for _ in range(3)
    )


def _generate_stripe_key() -> str:
    return "sk_live_" + "".join(secrets.choice(string.ascii_letters + string.digits)
                                for _ in range(24))


def _generate_connection_string() -> str:
    """Generate a credential-bearing connection string."""
    user = "admin"
    pw = "".join(secrets.choice(string.ascii_letters + string.digits + "!@#$%") for _ in range(16))
    return f"postgresql://{user}:{pw}@db.example.com:5432/mydb"


def generate_secret_corpus() -> list[dict]:
    """Generate labeled secret samples."""
    corpus = []

    # AWS access keys (AKIA prefix, 20 chars total)
    for _ in range(50):
        corpus.append({"value": _generate_aws_key(), "type": "aws_access_key"})

    # AWS secret keys (40 chars, mixed charset)
    for _ in range(50):
        corpus.append({"value": _generate_aws_secret(), "type": "aws_secret_key"})

    # PEM blocks
    for key_type in ["RSA", "EC", "GENERIC"]:
        for _ in range(20):
            corpus.append({"value": _generate_pem_block(key_type), "type": f"pem_{key_type.lower()}"})

    # OAuth tokens
    for _ in range(50):
        corpus.append({"value": _generate_oauth_token(), "type": "oauth_token"})

    # Random hex keys (128-512 bit) — hardest for entropy-only detection
    for bits in [128, 192, 256, 384, 512]:
        for _ in range(20):
            corpus.append({"value": _generate_random_key(bits), "type": f"random_key_{bits}bit"})

    # Short API keys (20-40 chars, alphanumeric) — hardest to catch
    for length in range(20, 41, 5):
        for _ in range(30):
            corpus.append({"value": _generate_short_api_key(length), "type": f"short_api_key_{length}ch"})

    # Base64-encoded secrets
    for byte_len in [16, 24, 32, 48, 64]:
        for _ in range(15):
            corpus.append({"value": _generate_base64_secret(byte_len), "type": f"base64_secret_{byte_len}B"})

    # JWTs
    for _ in range(50):
        corpus.append({"value": _generate_jwt(), "type": "jwt"})

    # GitHub tokens
    for _ in range(30):
        corpus.append({"value": _generate_github_token(), "type": "github_pat"})

    # Slack tokens
    for _ in range(20):
        corpus.append({"value": _generate_slack_token(), "type": "slack_token"})

    # Stripe keys
    for _ in range(20):
        corpus.append({"value": _generate_stripe_key(), "type": "stripe_key"})

    # Connection strings with embedded passwords
    for _ in range(20):
        corpus.append({"value": _generate_connection_string(), "type": "connection_string"})

    return corpus


# ---------------------------------------------------------------------------
# Entropy and detection logic
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
    """Count how many character classes are present (lowercase, uppercase, digit, special)."""
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
    """Check if a string is composed entirely of hexadecimal characters."""
    return bool(s) and all(c in "0123456789abcdefABCDEF" for c in s)


def is_uuid(s: str) -> bool:
    """Check if a string matches UUID format (8-4-4-4-12)."""
    return bool(re.match(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$', s))


def detect_pem(text: str) -> bool:
    """Check if text contains a PEM block header."""
    return "-----BEGIN " in text and "PRIVATE KEY-----" in text


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


def has_known_prefix(text: str) -> bool:
    """Check if text starts with a known credential prefix."""
    for prefix in KNOWN_PREFIXES:
        if text.startswith(prefix):
            return True
    return False


def detect_connection_string(text: str) -> bool:
    """Detect credential-bearing connection strings."""
    return bool(re.search(r'://[^:]+:[^@]+@', text))


_TOKENIZER = re.compile(r'[\s,;:="\'`\{\}\[\]\(\)<>]+')

# Patterns for non-secret hex/base64 in context
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


def _extract_context_excluded_tokens(text: str) -> set[str]:
    """Find hex tokens that appear in known non-secret contexts."""
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
        # Re-pad if tokenizer stripped trailing '='
        padded = token + "=" * (-len(token) % 4)
        decoded = base64.b64decode(padded)
        text = decoded.decode('ascii')
        # If mostly printable and contains spaces or common text chars, it's prose
        printable_ratio = sum(1 for c in text if c.isprintable()) / len(text) if text else 0
        return printable_ratio > 0.9 and len(text) >= 4
    except Exception:
        return False


def scan_token(token: str, length_threshold: int, entropy_threshold: float,
               excluded_tokens: set[str] | None = None) -> dict:
    """Scan a single token for secret characteristics.

    Uses multi-factor detection:
      1. PEM structure
      2. Known prefix patterns
      3. Entropy + character distribution analysis
    """
    # Skip UUIDs — common non-secret format
    if is_uuid(token):
        return {"verdict": "CLEAN", "classification": None, "entropy_score": 0.0}

    # Skip tokens identified as non-secret by context analysis
    if excluded_tokens and token in excluded_tokens:
        return {"verdict": "CLEAN", "classification": None, "entropy_score": 0.0}

    # Skip benign base64 (decodes to readable ASCII text)
    if _is_benign_base64(token):
        return {"verdict": "CLEAN", "classification": None, "entropy_score": 0.0}

    # PEM block detection (structural)
    if detect_pem(token):
        return {
            "verdict": "SECRET_DETECTED",
            "classification": "PEM_BLOCK",
            "entropy_score": shannon_entropy(token),
        }

    # Known prefix detection (accelerator)
    if has_known_prefix(token):
        return {
            "verdict": "SECRET_DETECTED",
            "classification": "PATTERN_MATCH",
            "entropy_score": shannon_entropy(token),
        }

    # Connection string detection
    if detect_connection_string(token):
        return {
            "verdict": "SECRET_DETECTED",
            "classification": "CONNECTION_STRING",
            "entropy_score": shannon_entropy(token),
        }

    # Length gate — tokens below threshold are not analyzed for entropy
    if len(token) < length_threshold:
        return {"verdict": "CLEAN", "classification": None, "entropy_score": 0.0}

    entropy = shannon_entropy(token)
    classes = char_class_count(token)

    # Character distribution analysis:
    # Tokens with 3+ character classes (lower + upper + digit) at moderate entropy
    # are very likely to be secrets (API keys, passwords, etc.)
    # Hex-only tokens need higher entropy to trigger (they're often hashes)
    if is_hex_only(token):
        # Hex tokens: require higher entropy threshold to reduce hash false positives.
        # Random hex maxes at ~4.0 bits/char. Structured hex (repeated patterns,
        # sequential values) scores lower. We use entropy_threshold directly —
        # if set to 4.0, catches most random hex; if higher, misses more.
        if entropy >= entropy_threshold:
            return {
                "verdict": "SECRET_DETECTED",
                "classification": "HIGH_ENTROPY_HEX",
                "entropy_score": entropy,
            }
    elif classes >= 3:
        # Mixed-charset tokens (lower + upper + digit or + special):
        # High diversity with moderate entropy strongly indicates a secret.
        # Use a reduced entropy threshold for these.
        adjusted_threshold = entropy_threshold * 0.85
        if entropy >= adjusted_threshold:
            return {
                "verdict": "SECRET_DETECTED",
                "classification": "HIGH_ENTROPY_MIXED",
                "entropy_score": entropy,
            }
    else:
        # Other tokens (single-case alphanumeric, etc.)
        if entropy >= entropy_threshold:
            return {
                "verdict": "SECRET_DETECTED",
                "classification": "HIGH_ENTROPY",
                "entropy_score": entropy,
            }

    return {"verdict": "CLEAN", "classification": None, "entropy_score": entropy}


def scan_text(text: str, length_threshold: int, entropy_threshold: float) -> dict:
    """Scan text by splitting into tokens and checking each.

    Also checks full text for PEM blocks and connection strings.
    """
    # Full-text structural checks
    if detect_pem(text):
        return {
            "verdict": "SECRET_DETECTED",
            "classification": "PEM_BLOCK",
            "entropy_score": shannon_entropy(text),
        }

    if detect_connection_string(text):
        return {
            "verdict": "SECRET_DETECTED",
            "classification": "CONNECTION_STRING",
            "entropy_score": shannon_entropy(text),
        }

    # Extract context-excluded tokens (labeled hashes, git refs, URL paths)
    excluded = _extract_context_excluded_tokens(text)

    # Strip non-credential URLs before tokenization to prevent URL fragments
    # from being flagged. Connection strings (://user:pass@host) are already
    # caught above, so we only strip clean URLs here.
    sanitized = re.sub(r'https?://[^\s]+', '', text)

    # Tokenize and check each token
    tokens = _TOKENIZER.split(sanitized)

    for token in tokens:
        if not token:
            continue
        result = scan_token(token, length_threshold, entropy_threshold, excluded)
        if result["verdict"] == "SECRET_DETECTED":
            return result

    return {"verdict": "CLEAN", "classification": None, "entropy_score": 0.0}


# ---------------------------------------------------------------------------
# Threshold sweep
# ---------------------------------------------------------------------------

LENGTH_THRESHOLDS = [16, 20, 24, 28, 32]
ENTROPY_THRESHOLDS = [3.0, 3.5, 3.8, 4.0, 4.2, 4.5, 5.0]


def sweep(prose_corpus: list[str], secret_corpus: list[dict]) -> list[dict]:
    """Sweep all threshold combinations, measuring TPR and FPR."""
    results = []

    for length_t in LENGTH_THRESHOLDS:
        for entropy_t in ENTROPY_THRESHOLDS:
            # Measure TPR (true positive rate on secrets)
            tp = 0
            fn = 0
            missed_types: set[str] = set()
            for item in secret_corpus:
                result = scan_text(item["value"], length_t, entropy_t)
                if result["verdict"] == "SECRET_DETECTED":
                    tp += 1
                else:
                    fn += 1
                    missed_types.add(item["type"])

            # Measure FPR (false positive rate on prose)
            fp = 0
            fp_samples: list[str] = []
            for sample in prose_corpus:
                result = scan_text(sample, length_t, entropy_t)
                if result["verdict"] == "SECRET_DETECTED":
                    fp += 1
                    if len(fp_samples) < 5:
                        fp_samples.append(sample[:100])

            tpr = tp / len(secret_corpus) if secret_corpus else 0.0
            fpr = fp / len(prose_corpus) if prose_corpus else 0.0

            # Check short API key detection specifically
            short_keys = [s for s in secret_corpus if "short_api_key" in s["type"]]
            short_tp = sum(
                1 for s in short_keys
                if scan_text(s["value"], length_t, entropy_t)["verdict"] == "SECRET_DETECTED"
            )
            short_tpr = short_tp / len(short_keys) if short_keys else 0.0

            results.append({
                "length_threshold": length_t,
                "entropy_threshold": entropy_t,
                "tpr": round(tpr, 5),
                "fpr": round(fpr, 5),
                "tp": tp,
                "fn": fn,
                "fp": fp,
                "total_secrets": len(secret_corpus),
                "total_prose": len(prose_corpus),
                "missed_types": sorted(missed_types),
                "fp_examples": fp_samples,
                "short_api_key_tpr": round(short_tpr, 5),
            })

    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    random.seed(42)
    project_root = Path(__file__).resolve().parent.parent.parent

    print("=== WS-PGC-SEC-002-A: Secret Detector Calibration Spike ===\n")

    # Phase 1: Build corpora
    print("Phase 1: Building corpora...")
    prose_corpus = generate_prose_corpus(5500)
    secret_corpus = generate_secret_corpus()

    print(f"  Prose corpus: {len(prose_corpus)} samples")
    print(f"  Secret corpus: {len(secret_corpus)} samples")

    # Secret type breakdown
    types: dict[str, int] = {}
    for s in secret_corpus:
        types[s["type"]] = types.get(s["type"], 0) + 1
    print(f"  Secret types: {len(types)}")
    for t, count in sorted(types.items()):
        print(f"    {t}: {count}")

    # Compute corpus hash
    corpus_content = json.dumps({
        "prose": prose_corpus,
        "secrets": [s["value"] for s in secret_corpus],
    }, sort_keys=True)
    corpus_hash = hashlib.sha256(corpus_content.encode()).hexdigest()
    print(f"  Corpus hash: {corpus_hash[:16]}...")

    # Phase 2: Sweep
    print("\nPhase 2: Threshold sweep...")
    results = sweep(prose_corpus, secret_corpus)

    print(f"\n{'Length':>6} {'Entropy':>8} {'TPR':>8} {'FPR':>8} "
          f"{'FN':>5} {'FP':>5} {'ShortTPR':>9} {'Status':>10}")
    print("-" * 75)

    best = None
    for r in results:
        meets_tpr = r["tpr"] >= 0.99
        meets_fpr = r["fpr"] <= 0.01
        status = "PASS" if (meets_tpr and meets_fpr) else "FAIL"

        print(f"{r['length_threshold']:>6} {r['entropy_threshold']:>8.1f} "
              f"{r['tpr']:>8.4f} {r['fpr']:>8.4f} "
              f"{r['fn']:>5} {r['fp']:>5} "
              f"{r['short_api_key_tpr']:>9.4f} {status:>10}")

        if status == "PASS":
            if best is None or r["tpr"] > best["tpr"] or (
                r["tpr"] == best["tpr"] and r["fpr"] < best["fpr"]
            ):
                best = r

    # Phase 3: Select and document
    print("\n" + "=" * 75)

    if best is None:
        print("WARNING: No threshold combination met both TPR >= 99% and FPR <= 1%.")
        print("Selecting best tradeoff (highest TPR with FPR <= 1%)...")
        candidates = [r for r in results if r["fpr"] <= 0.01]
        if candidates:
            best = max(candidates, key=lambda r: (r["tpr"], -r["fpr"]))
        else:
            print("No combination has FPR <= 1%. Selecting lowest FPR with highest TPR...")
            best = min(results, key=lambda r: (r["fpr"], -r["tpr"]))
        print(f"  Best available: length={best['length_threshold']}, "
              f"entropy={best['entropy_threshold']}, "
              f"TPR={best['tpr']:.4f}, FPR={best['fpr']:.4f}")
    else:
        print(f"SELECTED: length={best['length_threshold']}, "
              f"entropy={best['entropy_threshold']}")
        print(f"  TPR: {best['tpr']:.4f} (target >= 0.99)")
        print(f"  FPR: {best['fpr']:.4f} (target <= 0.01)")
        print(f"  Short API key TPR: {best['short_api_key_tpr']:.4f}")

    if best["missed_types"]:
        print(f"  Missed types: {', '.join(best['missed_types'])}")
    if best["fp_examples"]:
        print(f"  FP examples ({best['fp']} total):")
        for ex in best["fp_examples"]:
            print(f"    - {ex}")

    # Produce calibration artifact
    artifact = {
        "detector_version": "v1",
        "length_threshold": best["length_threshold"],
        "entropy_threshold": best["entropy_threshold"],
        "char_class_adjustment": 0.85,
        "expected_tpr": best["tpr"],
        "expected_fpr": best["fpr"],
        "short_api_key_tpr": best["short_api_key_tpr"],
        "calibration_corpus_hash": corpus_hash,
        "prose_corpus_size": len(prose_corpus),
        "secret_corpus_size": len(secret_corpus),
        "date": date.today().isoformat(),
    }

    artifact_path = (project_root / "combine-config" / "governance" / "secrets"
                     / "detector_calibration.v1.json")
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(json.dumps(artifact, indent=2) + "\n")
    print(f"\nCalibration artifact written to: {artifact_path.relative_to(project_root)}")

    # Write full sweep results for documentation
    sweep_path = (project_root / "combine-config" / "governance" / "secrets"
                  / "calibration_sweep_results.json")
    sweep_path.write_text(json.dumps(results, indent=2) + "\n")
    print(f"Full sweep results written to: {sweep_path.relative_to(project_root)}")

    print("\nDone.")
    return artifact


if __name__ == "__main__":
    main()
