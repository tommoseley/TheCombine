#!/usr/bin/env python3
"""
Check The Combine API health.

Usage:
    python scripts/check_health.py
"""

import sys
import requests
import json

def main():
    """Check server health."""
    url = "http://localhost:8000/health"
    
    print("🔍 Checking server health at", url)
    print()
    
    try:
        response = requests.get(url, timeout=5)
        health = response.json()
        
        print("="*60)
        print("HEALTH CHECK RESULTS")
        print("="*60)
        
        # Overall status
        status_emoji = "✅" if health["status"] == "healthy" else "❌"
        print(f"{status_emoji} Status: {health['status'].upper()}")
        print()
        
        # Individual components
        checks = [
            ("Orchestrator Ready", health.get("orchestrator_ready", False)),
            ("Canon Loaded", health.get("canon_loaded", False)),
            ("Database Connected", health.get("database_connected", False))
        ]
        
        for name, status in checks:
            emoji = "✅" if status else "❌"
            print(f"  {emoji} {name}: {status}")
        
        print()
        
        # Additional info
        if health.get("canon_version"):
            print(f"  📖 Canon Version: {health['canon_version']}")
        
        print(f"  ⏱️  Uptime: {health.get('uptime_seconds', 0)} seconds")
        
        print("="*60)
        print()
        
        if health["status"] == "healthy":
            print("🎉 All systems operational!")
            print()
            print("Next steps:")
            print("  • API docs: http://localhost:8000/docs")
            print("  • Create pipeline: POST /pipelines")
            print("  • Check database: sqlite3 data/workbench_ai.db")
            print()
            return 0
        else:
            print("⚠️  System is unhealthy. Check the issues above.")
            print()
            return 1
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server at", url)
        print()
        print("Is the server running? Try:")
        print("  python scripts/run.py")
        print("  ./run.sh")
        print()
        return 1
        
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        print()
        return 1

if __name__ == "__main__":
    sys.exit(main())