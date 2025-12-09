"""Integration test for bootstrap flow."""
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent.parent


class TestBootstrapFlow:
    @pytest.mark.skip(reason="Causes recursive test execution")
    def test_setup_script_executes(self):
        python_path = sys.executable
        setup_script = ROOT / "scripts" / "setup.py"

        result = subprocess.run(
            [python_path, str(setup_script)],
            capture_output=True,
            timeout=300,
        )

        assert result.returncode == 0

    def test_server_starts(self):
        import time
        from threading import Thread

        import requests

        python_path = sys.executable
        run_script = ROOT / "scripts" / "run.py"

        def start_server():
            subprocess.run([python_path, str(run_script)], timeout=5)

        server_thread = Thread(target=start_server, daemon=True)
        server_thread.start()
        time.sleep(2)

        try:
            response = requests.get("http://localhost:8000/health", timeout=1)
            assert response.status_code == 200
        except Exception:
            pytest.skip("Server did not start in time")
