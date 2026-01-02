#!/usr/bin/env python3
"""Environment setup script for The Combine."""
import sys
import subprocess
import venv
from pathlib import Path
import os

ROOT = Path(__file__).parent.parent
VENV_PATH = ROOT / "venv"


def main():
    print("Setting up The Combine environment...")

    if not create_venv():
        return 1

    if not install_dependencies():
        return 1

    if not initialize_database():
        return 1

    if not run_tests():
        return 1

    print("Setup complete!")
    print("Run: ./run.sh (or run.ps1 on Windows) to start server")
    return 0


def create_venv():
    print("Creating virtual environment...")
    try:
        venv.create(VENV_PATH, with_pip=True)
        print("Virtual environment created")
        return True
    except Exception as e:
        print(f"Failed to create venv: {e}", file=sys.stderr)
        return False


def install_dependencies():
    print("Installing dependencies...")
    pip_path = (
        VENV_PATH / "bin" / "pip"
        if sys.platform != "win32"
        else VENV_PATH / "Scripts" / "pip.exe"
    )
    requirements = ROOT / "requirements.txt"

    try:
        subprocess.run(
            [str(pip_path), "install", "-r", str(requirements)],
            check=True,
            capture_output=True,
        )
        print("Dependencies installed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to install dependencies: {e.stderr.decode()}", file=sys.stderr)
        return False


def initialize_database():
    print("Initializing database...")
    python_path = VENV_PATH / "bin" / "python" if sys.platform != "win32" else VENV_PATH / "Scripts" / "python.exe"
    init_script = ROOT / "scripts" / "init_db.py"
    
    # Set PYTHONPATH to include project root
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    
    try:
        subprocess.run(
            [str(python_path), str(init_script)],
            check=True,
            capture_output=True,
            cwd=ROOT,
            env=env  # Pass the modified environment
        )
        print("Database initialized")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to initialize database: {e.stderr.decode()}", file=sys.stderr)
        return False

def run_tests():
    print("Running tests...")
    python_path = (
        VENV_PATH / "bin" / "python"
        if sys.platform != "win32"
        else VENV_PATH / "Scripts" / "python.exe"
    )

    try:
        subprocess.run(
            [str(python_path), "-m", "pytest", "tests/", "-v"],
            check=True,
            capture_output=True,
            cwd=ROOT,
        )
        print("All tests passed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Tests failed: {e.stderr.decode()}", file=sys.stderr)
        return False


if __name__ == "__main__":
    sys.exit(main())
