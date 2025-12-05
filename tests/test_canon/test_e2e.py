# tests/test_canon/test_e2e.py

"""End-to-end tests for canon version management."""

import pytest
import threading
import time
from pathlib import Path

from workforce.canon_version_manager import CanonVersionManager
from workforce.canon.loader import SemanticVersion


def create_canon_content(version_minor, tmp_path):
    """Helper to create canon file with specific version."""
    canon_file = tmp_path / "canon.md"
    content = f"""PIPELINE_FLOW_VERSION=1.{version_minor}
# Pipeline Flow - Version 1.{version_minor} (Canonical)

## 1. Overview
Test overview content for version 1.{version_minor}.

## 2. Phase Sequence (Strict Order)
Test phase sequence.

## 3. Phase Definitions
Test phase definitions.

### 3.1 PM Phase
Test PM phase.

### 3.2 Architect Phase
Test architect phase.

### 3.3 BA Phase
Test BA phase.

### 3.4 Developer Phase
Test developer phase.

### 3.5 QA Phase
Test QA phase.

### 3.6 Commit Phase
Test commit phase.

## 4. Error Handling & Recovery
Test error handling.

## 5. Behavioral Rules (Binding)
Test behavioral rules.

## 6. Canonical Summary Diagram
Test canonical summary diagram.

## 7. Canon Enforcement
Test canon enforcement.
"""
    canon_file.write_text(content, encoding='utf-8')
    return canon_file


def test_e2e_11_concurrency_safety(tmp_path, monkeypatch):
    """
    E2E-11 (CRITICAL): Concurrency Safety Test
    
    Verifies that canon version changes do not affect in-flight pipelines.
    
    Scenario:
    1. Start 10 parallel pipelines with canon v1.0
    2. Update canon to v1.1 while pipelines in-flight
    3. Trigger version check and reload
    4. Verify all 10 pipelines complete with v1.0
    5. Verify next pipeline uses v1.1
    """
    canon_file = create_canon_content(0, tmp_path)
    monkeypatch.setenv("COMBINE_CANON_PATH", str(canon_file))
    
    manager = CanonVersionManager()
    manager.load_canon()
    
    # Register 10 pipelines with v1.0
    pipeline_buffers = []
    for i in range(10):
        buffer = manager.buffer_manager.register_pipeline_reference(f"pipeline-{i}")
        pipeline_buffers.append(buffer)
        assert buffer.version == SemanticVersion(1, 0)
    
    # Update canon to v1.1
    create_canon_content(1, tmp_path)
    
    # Reload canon (triggers buffer swap)
    manager.reload_canon_with_buffer_swap()
    
    # Verify all original pipelines still have v1.0
    for i, buffer in enumerate(pipeline_buffers):
        assert buffer.version == SemanticVersion(1, 0), \
            f"Pipeline {i} experienced mid-flight version change"
    
    # New pipeline gets v1.1
    new_buffer = manager.buffer_manager.register_pipeline_reference("pipeline-11")
    assert new_buffer.version == SemanticVersion(1, 1)
    
    # Cleanup pipelines
    for i in range(10):
        manager.buffer_manager.unregister_pipeline_reference(f"pipeline-{i}")


def test_e2e_concurrent_pipeline_starts(tmp_path, monkeypatch):
    """Test multiple pipelines starting concurrently."""
    canon_file = create_canon_content(0, tmp_path)
    monkeypatch.setenv("COMBINE_CANON_PATH", str(canon_file))
    
    manager = CanonVersionManager()
    manager.load_canon()
    
    results = []
    
    def start_pipeline(pipeline_id):
        buffer = manager.buffer_manager.register_pipeline_reference(pipeline_id)
        results.append((pipeline_id, buffer.version))
        time.sleep(0.01)
        manager.buffer_manager.unregister_pipeline_reference(pipeline_id)
    
    threads = []
    for i in range(20):
        t = threading.Thread(target=start_pipeline, args=(f"p{i}",))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    # All should get v1.0
    assert len(results) == 20
    assert all(v == SemanticVersion(1, 0) for _, v in results)


def test_e2e_version_change_during_execution(tmp_path, monkeypatch):
    """Test version change while pipelines are executing."""
    canon_file = create_canon_content(0, tmp_path)
    monkeypatch.setenv("COMBINE_CANON_PATH", str(canon_file))
    
    manager = CanonVersionManager()
    manager.load_canon()
    
    execution_results = []
    
    def execute_pipeline(pipeline_id, delay):
        buffer = manager.buffer_manager.register_pipeline_reference(pipeline_id)
        start_version = buffer.version
        
        # Simulate execution
        time.sleep(delay)
        
        end_version = buffer.version
        execution_results.append({
            'pipeline': pipeline_id,
            'start_version': start_version,
            'end_version': end_version,
            'stable': start_version == end_version
        })
        
        manager.buffer_manager.unregister_pipeline_reference(pipeline_id)
    
    # Start 5 long-running pipelines
    threads = []
    for i in range(5):
        t = threading.Thread(target=execute_pipeline, args=(f"long-{i}", 0.2))
        threads.append(t)
        t.start()
    
    # Let them start
    time.sleep(0.05)
    
    # Update canon
    create_canon_content(1, tmp_path)
    manager.reload_canon_with_buffer_swap()
    
    # Start new pipeline
    t = threading.Thread(target=execute_pipeline, args=("new", 0.1))
    t.start()
    threads.append(t)
    
    # Wait for all
    for t in threads:
        t.join()
    
    # Verify old pipelines kept v1.0
    long_running = [r for r in execution_results if r['pipeline'].startswith('long')]
    assert all(r['start_version'] == SemanticVersion(1, 0) for r in long_running)
    assert all(r['end_version'] == SemanticVersion(1, 0) for r in long_running)
    assert all(r['stable'] for r in long_running)
    
    # Verify new pipeline got v1.1
    new = [r for r in execution_results if r['pipeline'] == 'new'][0]
    assert new['start_version'] == SemanticVersion(1, 1)
    assert new['end_version'] == SemanticVersion(1, 1)


def test_e2e_rapid_version_changes(tmp_path, monkeypatch):
    """Test handling of rapid canon version changes."""
    canon_file = create_canon_content(0, tmp_path)
    monkeypatch.setenv("COMBINE_CANON_PATH", str(canon_file))
    
    manager = CanonVersionManager()
    manager.load_canon()
    
    # Perform rapid version updates
    for v in range(1, 6):
        create_canon_content(v, tmp_path)
        manager.reload_canon_with_buffer_swap()
        time.sleep(0.01)
    
    # Final version should be v1.5
    current = manager.version_store.get_current_version()
    assert current == SemanticVersion(1, 5)
    
    buffer = manager.buffer_manager.get_current_buffer()
    assert buffer.version == SemanticVersion(1, 5)


def test_e2e_buffer_cleanup_after_pipelines_complete(tmp_path, monkeypatch):
    """Test old buffer cleanup after all pipelines complete."""
    canon_file = create_canon_content(0, tmp_path)
    monkeypatch.setenv("COMBINE_CANON_PATH", str(canon_file))
    
    manager = CanonVersionManager()
    manager.load_canon()
    
    # Register pipeline
    buffer_v1 = manager.buffer_manager.register_pipeline_reference("p1")
    
    # Swap to v1.1
    create_canon_content(1, tmp_path)
    manager.reload_canon_with_buffer_swap()
    
    # Old buffer should be draining
    from workforce.canon.buffer_manager import BufferState
    assert buffer_v1.state == BufferState.DRAINING
    
    # Unregister pipeline
    manager.buffer_manager.unregister_pipeline_reference("p1")
    
    # Give cleanup thread time to run
    time.sleep(0.2)
    
    # Old buffer should be retired
    assert buffer_v1.state == BufferState.RETIRED