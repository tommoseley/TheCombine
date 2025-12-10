"""
Database Connection Test for The Combine

Run this to verify PostgreSQL setup.

Usage:
    python test_database.py
"""

import os
from dotenv import load_dotenv

# Debug: Force load and print
load_dotenv()
print(f"DEBUG: DATABASE_URL = {os.getenv('DATABASE_URL')}")

import sys
from database import (
    check_database_connection,
    test_postgres_extensions,
    verify_database_ready
)


def main():
    print("=" * 70)
    print("  THE COMBINE - DATABASE CONNECTION TEST")
    print("=" * 70)
    
    # Test 1: Basic connection
    print("\n1. Testing basic connection...")
    if check_database_connection():
        print("   ✅ Connected to PostgreSQL!")
    else:
        print("   ❌ Connection failed!")
        print("   Check your DATABASE_URL in .env")
        return False
    
    # Test 2: Extensions
    print("\n2. Testing PostgreSQL extensions...")
    if test_postgres_extensions():
        print("   ✅ Extensions installed!")
    else:
        print("   ❌ Missing extensions!")
        print("   Run: CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";")
        return False
    
    # Test 3: Full readiness
    print("\n3. Running full readiness check...")
    try:
        verify_database_ready()
        print("   ✅ Database fully ready!")
    except Exception as e:
        print(f"   ❌ Readiness check failed: {e}")
        return False
    
    print("\n" + "=" * 70)
    print("✅ ALL TESTS PASSED - DATABASE READY!")
    print("=" * 70)
    print("\nYou can now start your application")
    print("=" * 70)
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)