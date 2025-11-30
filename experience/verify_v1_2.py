#!/usr/bin/env python3
"""
Verification script for Canonical Architecture V1.2 compliance.

Checks that all required files exist and pytest configuration is correct.
"""

from pathlib import Path
import sys


def check_file_exists(path: Path, description: str) -> bool:
    """Check if a file exists and report result."""
    exists = path.exists()
    status = "✓" if exists else "✗"
    print(f"{status} {description}: {path}")
    return exists


def verify_v1_2_compliance():
    """Verify all V1.2 requirements are met."""
    print("=" * 60)
    print("Canonical Architecture V1.2 Compliance Check")
    print("=" * 60)
    print()
    
    # Assume we're running from experience/ directory
    base_dir = Path.cwd()
    
    all_checks_passed = True
    
    # Check package markers (__init__.py files)
    print("📦 Package Markers (__init__.py files):")
    print()
    
    required_init_files = [
        (base_dir / "app" / "__init__.py", "app/__init__.py"),
        (base_dir / "app" / "routers" / "__init__.py", "app/routers/__init__.py"),
        (base_dir / "app" / "schemas" / "__init__.py", "app/schemas/__init__.py"),
        (base_dir / "app" / "services" / "__init__.py", "app/services/__init__.py"),
        (base_dir / "app" / "models" / "__init__.py", "app/models/__init__.py"),
    ]
    
    for file_path, description in required_init_files:
        if not check_file_exists(file_path, description):
            all_checks_passed = False
    
    print()
    
    # Check pytest.ini
    print("⚙️  Pytest Configuration:")
    print()
    
    pytest_ini = base_dir / "pytest.ini"
    if not check_file_exists(pytest_ini, "pytest.ini"):
        all_checks_passed = False
    else:
        # Verify pythonpath setting
        content = pytest_ini.read_text()
        if "pythonpath = ." in content:
            print("  ✓ pythonpath = . setting found")
        else:
            print("  ✗ pythonpath = . setting NOT found")
            all_checks_passed = False
    
    print()
    
    # Check critical application files
    print("🔧 Application Files:")
    print()
    
    critical_files = [
        (base_dir / "app" / "main.py", "app/main.py (FastAPI entrypoint)"),
    ]
    
    for file_path, description in critical_files:
        if not check_file_exists(file_path, description):
            all_checks_passed = False
    
    print()
    print("=" * 60)
    
    if all_checks_passed:
        print("✅ All V1.2 compliance checks passed!")
        print()
        print("You can now run:")
        print("  cd experience")
        print("  pytest tests/ -v")
        return 0
    else:
        print("❌ Some V1.2 compliance checks failed.")
        print()
        print("Please ensure all required files are in place.")
        return 1


if __name__ == "__main__":
    sys.exit(verify_v1_2_compliance())