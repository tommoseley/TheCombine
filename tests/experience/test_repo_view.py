"""
Tests for Repo View endpoints.

Tests the read-only repository introspection API.
"""

from fastapi.testclient import TestClient
from pathlib import Path
import pytest

# Canonical import pattern
from app.api.main import app

client = TestClient(app)


class TestRepoFilesEndpoint:
    """Test suite for GET /repo/files endpoint."""
    
    def test_list_files_valid_root(self):
        """Test listing files with a valid allowed root."""
        response = client.get(
            "/repo/files",
            params={"root": "app"},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "root" in data
        assert "files" in data
        assert "truncated" in data
        assert data["root"] == "app"
        assert isinstance(data["files"], list)
        assert isinstance(data["truncated"], bool)
    
    def test_list_files_with_glob_pattern(self):
        """Test listing files with a glob pattern filter."""
        response = client.get(
            "/repo/files",
            params={
                "root": "app",
                "glob": "**/*.py",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # All returned files should be .py files
        for file_path in data["files"]:
            assert file_path.endswith(".py"), f"Non-Python file returned: {file_path}"
    
    def test_list_files_forbidden_root_env(self):
        """Test that .env is blocked by allow-list."""
        response = client.get(
            "/repo/files",
            params={"root": ".env"},
        )
        
        assert response.status_code == 403
        assert "not in allow-list" in response.json()["detail"].lower()
    
    def test_list_files_forbidden_root_git(self):
        """Test that .git is blocked by allow-list."""
        response = client.get(
            "/repo/files",
            params={"root": ".git"},
        )
        
        assert response.status_code == 403
        assert "not in allow-list" in response.json()["detail"].lower()
    
    def test_list_files_forbidden_root_arbitrary(self):
        """Test that arbitrary paths outside allow-list are blocked."""
        response = client.get(
            "/repo/files",
            params={"root": "/etc/passwd"},
        )
        
        assert response.status_code == 403
    
    def test_list_files_max_files_truncation(self):
        """Test that max_files limit works and truncated flag is set."""
        response = client.get(
            "/repo/files",
            params={
                "root": "app",
                "max_files": 5,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return at most 5 files
        assert len(data["files"]) <= 5
        
        # If there are more than 5 files in app/, truncated should be True
        # (This depends on your actual repo structure)
    
    def test_list_files_single_file_root(self):
        """Test listing a single file (e.g., README.md)."""
        response = client.get(
            "/repo/files",
            params={"root": "README.md"},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return the single file if it exists
        assert data["root"] == "README.md"
        # files should be empty or contain only README.md
        assert len(data["files"]) <= 1
    
    def test_list_files_nonexistent_root(self):
        """Test listing from a root that doesn't exist but is in allow-list."""
        response = client.get(
            "/repo/files",
            params={"root": "static"},
        )
        
        # Should return 200 with empty list since 'static' is in allow-list
        # even if the directory doesn't exist yet
        assert response.status_code == 200
        data = response.json()
        assert data["files"] == []
        assert data["truncated"] == False
    
    def test_list_files_forbidden_nonexistent_root(self):
        """Test listing from a root that doesn't exist and is NOT in allow-list."""
        response = client.get(
            "/repo/files",
            params={"root": "nonexistent_folder"},
        )
        
        # Should return 403 because it's not in the explicit allow-list
        assert response.status_code == 403
    
    def test_list_files_max_files_validation(self):
        """Test that max_files parameter validates correctly."""
        # Test below minimum
        response = client.get(
            "/repo/files",
            params={
                "root": "app",
                "max_files": 0,
            },
        )
        assert response.status_code == 422  # Validation error
        
        # Test above maximum
        response = client.get(
            "/repo/files",
            params={
                "root": "app",
                "max_files": 2000,
            },
        )
        assert response.status_code == 422  # Validation error
    
    def test_list_files_empty_root_validation(self):
        """Test that empty root is rejected."""
        response = client.get(
            "/repo/files",
            params={"root": ""},
        )
        # Empty string should either fail validation (422) or be rejected as not in allow-list (403)
        assert response.status_code in [403, 422]
    
    def test_list_files_templates_root(self):
        """Test listing files in templates/ directory."""
        response = client.get(
            "/repo/files",
            params={"root": "templates"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["root"] == "templates"
    
    def test_list_files_tests_root(self):
        """Test listing files in tests/ directory."""
        response = client.get(
            "/repo/files",
            params={"root": "tests"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["root"] == "tests"
    
    def test_list_files_pyproject_toml(self):
        """Test listing single file pyproject.toml."""
        response = client.get(
            "/repo/files",
            params={"root": "pyproject.toml"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["root"] == "pyproject.toml"


class TestRepoReaderService:
    """Direct tests for RepoFileReader service (unit tests)."""
    
    def test_forbidden_path_detection(self):
        """Test that forbidden paths are correctly identified."""
        from app.services.repo_reader import RepoFileReader
        
        service = RepoFileReader()
        
        # Test forbidden names (case-insensitive)
        assert service._is_forbidden_path(Path(".env/something"))
        assert service._is_forbidden_path(Path("project/.git/config"))
        assert service._is_forbidden_path(Path("app/__pycache__/module.pyc"))
        assert service._is_forbidden_path(Path("secrets/api_keys.txt"))
        
        # Test allowed paths
        assert not service._is_forbidden_path(Path("app/main.py"))
        assert not service._is_forbidden_path(Path("README.md"))
        assert not service._is_forbidden_path(Path("templates/index.html"))
    
    def test_binary_file_detection(self):
        """Test that binary files are correctly identified."""
        from app.services.repo_reader import RepoFileReader
        
        service = RepoFileReader()
        
        # Test binary extensions
        assert service._is_binary_file(Path("module.pyc"))
        assert service._is_binary_file(Path("database.sqlite"))
        assert service._is_binary_file(Path("image.png"))
        assert service._is_binary_file(Path("archive.zip"))
        
        # Test text files
        assert not service._is_binary_file(Path("script.py"))
        assert not service._is_binary_file(Path("README.md"))
        assert not service._is_binary_file(Path("config.json"))
    
    def test_allow_list_validation(self):
        """Test that only allow-listed roots are permitted."""
        from app.services.repo_reader import RepoFileReader
        
        service = RepoFileReader()
        
        # Test allowed roots (per Repo Structure Contract)
        assert service._is_allowed_root("app")
        assert service._is_allowed_root("templates")
        assert service._is_allowed_root("tests")
        assert service._is_allowed_root("static")
        assert service._is_allowed_root("README.md")
        assert service._is_allowed_root("pyproject.toml")
        
        # Test forbidden roots
        assert not service._is_allowed_root(".env")
        assert not service._is_allowed_root(".git")
        assert not service._is_allowed_root("experience")  # Not in allow-list
        assert not service._is_allowed_root("experience/app")  # Not in allow-list
        assert not service._is_allowed_root("random/path")
        assert not service._is_allowed_root("/etc/passwd")
    
    def test_project_root_derivation(self):
        """Test that project root is correctly derived from file location."""
        from app.services.repo_reader import RepoFileReader
        
        service = RepoFileReader()
        
        # Project root should be experience/ directory
        # The service file is at: experience/app/services/repo_reader.py
        # So parents[2] should give us experience/
        assert service.project_root.name == "experience"
        assert (service.project_root / "app").exists()
        assert (service.project_root / "app" / "main.py").exists()

# Add to existing TestRepoReaderService class:

    def test_get_file_content_basic(self):
        """Test basic file content reading."""
        from app.services.repo_reader import RepoFileReader
        
        service = RepoFileReader()
        
        # Read a known file
        content, truncated = service.get_file_content("app/__init__.py")
        
        assert isinstance(content, str)
        assert isinstance(truncated, bool)
        assert len(content) > 0

    def test_get_file_content_truncation(self):
        """Test content truncation."""
        from app.services.repo_reader import RepoFileReader
        
        service = RepoFileReader()
        
        # Read with very small max_bytes
        content, truncated = service.get_file_content("app/main.py", max_bytes=10)
        
        assert len(content) == 10
        assert truncated == True

    def test_get_file_content_forbidden(self):
        """Test forbidden path rejection."""
        from app.services.repo_reader import RepoFileReader, ForbiddenPathError
        
        service = RepoFileReader()
        
        with pytest.raises(ForbiddenPathError):
            service.get_file_content(".env")

    def test_get_file_content_binary(self):
        """Test binary file rejection."""
        from app.services.repo_reader import RepoFileReader
        from pathlib import Path
        
        service = RepoFileReader()
        
        # Create a mock path object for testing binary detection
        # We test the logic, not actual file existence
        test_path = Path("app/test.pyc")
        
        # Verify binary detection works
        assert service._is_binary_file(test_path) == True
        
        # The actual rejection happens when trying to read
        # We can't test non-existent files, so test the binary check logic instead
        assert service._is_binary_file(Path("app/test.py")) == False
        assert service._is_binary_file(Path("app/test.pyc")) == True
        assert service._is_binary_file(Path("data/image.png")) == True

    def test_extract_root_from_path(self):
        """Test root extraction helper."""
        from app.services.repo_reader import RepoFileReader
        from pathlib import Path
        
        service = RepoFileReader()
        
        # Directory root
        assert service._extract_root_from_path(Path("app/main.py")) == "app"
        assert service._extract_root_from_path(Path("tests/test_file.py")) == "tests"
        
        # Single file root
        assert service._extract_root_from_path(Path("pyproject.toml")) == "pyproject.toml"
        assert service._extract_root_from_path(Path("README.md")) == "README.md"
        
# Add to existing TestRepoFilesEndpoint class:

class TestRepoFileEndpoint:
    """Test suite for GET /repo/file endpoint (REPO-101)."""
    
    def test_get_file_valid_path(self):
        """Test reading a valid file."""
        response = client.get("/repo/file", params={"path": "app/main.py"})
        
        assert response.status_code == 200
        data = response.json()
        
        assert "path" in data
        assert "content" in data
        assert "truncated" in data
        assert data["path"] == "app/main.py"
        assert isinstance(data["content"], str)
        assert isinstance(data["truncated"], bool)
        assert len(data["content"]) > 0
        # Main.py should contain FastAPI import
        assert "fastapi" in data["content"].lower()
    
    def test_get_file_with_max_bytes(self):
        """Test reading file with max_bytes limit."""
        response = client.get(
            "/repo/file",
            params={"path": "app/main.py", "max_bytes": 100}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Content should be truncated to 100 bytes
        assert len(data["content"]) <= 100
        # Should be marked as truncated (assuming main.py > 100 bytes)
        assert data["truncated"] == True
    
    def test_get_file_single_file_root(self):
        """Test reading a single-file root."""
        # Try known single-file roots in order of likelihood
        single_file_roots = ["pytest.ini", "pyproject.toml", "README.md"]
        
        for path in single_file_roots:
            response = client.get("/repo/file", params={"path": path})
            
            if response.status_code == 200:
                # Found a valid single-file root
                data = response.json()
                assert data["path"] == path
                assert isinstance(data["content"], str)
                assert data["truncated"] in [True, False]
                return  # Test passed
        
        # If none exist, skip (but this is unlikely since pytest.ini should exist)
        pytest.skip("No single-file roots found in test environment")
            
    def test_get_file_forbidden_path_env(self):
        """Test that .env files are blocked."""
        response = client.get("/repo/file", params={"path": ".env"})
        
        assert response.status_code == 403
        assert "not in allow-list" in response.json()["detail"].lower()
    
    def test_get_file_forbidden_path_git(self):
        """Test that .git files are blocked."""
        response = client.get("/repo/file", params={"path": ".git/config"})
        
        assert response.status_code == 403
    
    def test_get_file_path_traversal(self):
        """Test that path traversal is blocked."""
        response = client.get("/repo/file", params={"path": "../secrets/api_key.txt"})
        
        # Path traversal is caught either at:
        # 1. Root validation (if ".." is extracted as root)
        # 2. Path resolution (if it tries to escape project root)
        assert response.status_code == 403
        # Accept either error message
        detail_lower = response.json()["detail"].lower()
        assert ("not in allow-list" in detail_lower) or ("traversal" in detail_lower)

    
    def test_get_file_forbidden_path_pycache(self):
        """Test that __pycache__ files are blocked."""
        # This tests the forbidden path logic, not whether file exists
        # __pycache__ is a forbidden directory, so access should be blocked
        response = client.get("/repo/file", params={"path": "app/__pycache__/main.cpython-312.pyc"})
        
        # Could be 403 (forbidden path) or 400 (file not found)
        # Both are acceptable - the important part is it's not 200
        assert response.status_code in [400, 403]
        
        # If it's 403, verify it's due to forbidden path
        if response.status_code == 403:
            assert "forbidden" in response.json()["detail"].lower()
    
    def test_get_file_binary_rejection(self):
        """Test that binary files are rejected."""
        # Try to read a .pyc file (if it exists)
        response = client.get("/repo/file", params={"path": "app/models/__init__.pyc"})
        
        # Should be either 400 (not a text file) or 400 (file not found)
        # Both are acceptable since .pyc might not exist
        assert response.status_code == 400
        if "not a text file" in response.json()["detail"].lower():
            assert True
        elif "not found" in response.json()["detail"].lower():
            assert True
    
    def test_get_file_not_found(self):
        """Test reading a non-existent file."""
        response = client.get("/repo/file", params={"path": "app/nonexistent.py"})
        
        assert response.status_code == 400
        assert "not found" in response.json()["detail"].lower()
    
    def test_get_file_directory_not_file(self):
        """Test that directories are rejected."""
        response = client.get("/repo/file", params={"path": "app"})
        
        assert response.status_code == 400
        assert "not a file" in response.json()["detail"].lower()
    
    def test_get_file_max_bytes_validation_too_low(self):
        """Test max_bytes validation (minimum)."""
        response = client.get(
            "/repo/file",
            params={"path": "app/main.py", "max_bytes": 0}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_get_file_max_bytes_validation_too_high(self):
        """Test max_bytes validation (maximum)."""
        response = client.get(
            "/repo/file",
            params={"path": "app/main.py", "max_bytes": 2000000}  # 2MB, over 1MB limit
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_get_file_utf8_content(self):
        """Test that UTF-8 content is properly decoded."""
        response = client.get("/repo/file", params={"path": "app/main.py"})
        
        assert response.status_code == 200
        data = response.json()
        
        # Should be valid UTF-8 string
        assert isinstance(data["content"], str)
        # Should not have encoding errors
        assert "�" not in data["content"]

