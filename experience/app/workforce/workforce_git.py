# app/workforce/workforce_git.py

import os
import subprocess
from pathlib import Path

# --- Load .env explicitly from the experience root ---

try:
    from dotenv import load_dotenv
except ImportError:
    # Install if missing: pip install python-dotenv
    load_dotenv = None

# This file is: experience/app/workforce/workforce_git.py
# Root of the app (where .env lives) should be: experience/.env
BASE_DIR = Path(__file__).resolve().parents[2]  # .../experience
ENV_PATH = BASE_DIR / ".env"

if load_dotenv is not None:
    if ENV_PATH.exists():
        load_dotenv(ENV_PATH)
    else:
        # Fallback: try default search if .env is named differently
        load_dotenv()


REPO_ROOT = BASE_DIR / "workforce_repo"


def _run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, check=True)


def _get_config():
    """
    Read config fresh from the environment each time,
    so we don't cache None values at import time.
    """
    token = os.getenv("GITHUB_WORKFORCE_TOKEN")
    owner = os.getenv("GITHUB_WORKFORCE_REPO_OWNER")
    name = os.getenv("GITHUB_WORKFORCE_REPO_NAME")
    branch = os.getenv("GITHUB_WORKFORCE_BRANCH", "workforce-sandbox")

    missing = [
        env_name
        for env_name, value in {
            "GITHUB_WORKFORCE_TOKEN": token,
            "GITHUB_WORKFORCE_REPO_OWNER": owner,
            "GITHUB_WORKFORCE_REPO_NAME": name,
        }.items()
        if not value
    ]
    if missing:
        missing_str = ", ".join(missing)
        raise RuntimeError(
            f"Missing required env vars for Workforce git: {missing_str}. "
            f"Looked for .env at: {ENV_PATH}"
        )

    return token, owner, name, branch


def ensure_repo():
    token, owner, name, branch = _get_config()

    if not REPO_ROOT.exists():
        remote = (
            f"https://x-access-token:{token}"
            f"@github.com/{owner}/{name}.git"
        )
        _run(["git", "clone", remote, str(REPO_ROOT)])

    _run(["git", "fetch", "origin"], cwd=REPO_ROOT)
    _run(["git", "checkout", branch], cwd=REPO_ROOT)
    _run(["git", "pull", "origin", branch], cwd=REPO_ROOT)


def write_files(changes: list[dict[str, str]]):
    ensure_repo()
    for change in changes:
        path = REPO_ROOT / change["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(change["content"], encoding="utf-8")


def commit_and_push(message: str) -> str | None:
    token, owner, name, branch = _get_config()  # not strictly needed, but keeps pattern

    ensure_repo()

    _run(["git", "config", "user.name", "Workbench Workforce"], cwd=REPO_ROOT)
    _run(["git", "config", "user.email", "workforce@example.com"], cwd=REPO_ROOT)

    _run(["git", "add", "."], cwd=REPO_ROOT)

    # Commit (handle 'nothing to commit' gracefully)
    result = subprocess.run(
        ["git", "commit", "-m", message],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        # Likely "nothing to commit"
        return None

    # Get latest commit hash
    hash_result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    commit_hash = hash_result.stdout.strip()

    _run(["git", "push", "origin", branch], cwd=REPO_ROOT)
    return commit_hash
