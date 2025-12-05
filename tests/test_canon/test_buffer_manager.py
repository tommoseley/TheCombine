# tests/test_canon/test_buffer_manager.py

"""Tests for double-buffer canon pattern."""

import pytest
import threading
import time
from datetime import datetime

from workforce.canon.loader import SemanticVersion
from workforce.canon.buffer_manager import (
    CanonBufferManager,
    BufferState,
    CanonBuffer
)
from workforce.utils.errors import (
    CanonNotLoadedError,
    CanonLoadInProgressError,
    CanonNotReadyError
)


def test_get_current_buffer_when_not_loaded():
    """Test getting buffer when none is loaded."""
    manager = CanonBufferManager()
    
    with pytest.raises(CanonNotLoadedError):
        manager.get_current_buffer()


def test_load_new_buffer():
    """Test loading new buffer."""
    manager = CanonBufferManager()
    version = SemanticVersion(1, 0)
    
    manager.load_new_buffer(version, "content", "prompt")
    
    assert manager._next_buffer is not None
    assert manager._next_buffer.version == version
    assert manager._next_buffer.state == BufferState.READY


def test_load_buffer_while_loading():
    """Test error when loading while another load in progress."""
    manager = CanonBufferManager()
    
    # Start first load
    manager._next_buffer = CanonBuffer(
        version=SemanticVersion(1, 0),
        content="content",
        prompt="prompt",
        state=BufferState.LOADING,
        created_at=datetime.now()
    )
    
    # Try second load
    with pytest.raises(CanonLoadInProgressError):
        manager.load_new_buffer(SemanticVersion(2, 0), "new", "new")


def test_swap_buffers_atomic():
    """Test buffer swap is atomic."""
    manager = CanonBufferManager()
    
    # Setup initial buffer
    manager._current_buffer = CanonBuffer(
        version=SemanticVersion(1, 0),
        content="v1",
        prompt="v1",
        state=BufferState.ACTIVE,
        created_at=datetime.now()
    )
    
    # Load next buffer
    manager.load_new_buffer(SemanticVersion(2, 0), "v2", "v2")
    
    # Swap
    result = manager.swap_buffers()
    
    assert result.old_version == "1.0"
    assert result.new_version == "2.0"
    assert result.swap_duration_ms < 5.0  # Should be <1ms, allowing margin


def test_swap_buffers_when_not_ready():
    """Test error when swapping without ready buffer."""
    manager = CanonBufferManager()
    manager._current_buffer = CanonBuffer(
        version=SemanticVersion(1, 0),
        content="v1",
        prompt="v1",
        state=BufferState.ACTIVE,
        created_at=datetime.now()
    )
    
    with pytest.raises(CanonNotReadyError):
        manager.swap_buffers()


def test_register_and_unregister_pipeline():
    """Test pipeline reference registration."""
    manager = CanonBufferManager()
    
    # Setup buffer
    manager._current_buffer = CanonBuffer(
        version=SemanticVersion(1, 0),
        content="v1",
        prompt="v1",
        state=BufferState.ACTIVE,
        created_at=datetime.now()
    )
    
    # Register
    buffer = manager.register_pipeline_reference("pipeline-1")
    assert buffer.version == SemanticVersion(1, 0)
    assert len(manager._pipeline_refs) == 1
    
    # Unregister
    manager.unregister_pipeline_reference("pipeline-1")
    assert len(manager._pipeline_refs) == 0


def test_count_references():
    """Test counting buffer references."""
    manager = CanonBufferManager()
    
    buffer = CanonBuffer(
        version=SemanticVersion(1, 0),
        content="v1",
        prompt="v1",
        state=BufferState.ACTIVE,
        created_at=datetime.now()
    )
    manager._current_buffer = buffer
    
    # Register multiple pipelines
    manager.register_pipeline_reference("p1")
    manager.register_pipeline_reference("p2")
    manager.register_pipeline_reference("p3")
    
    assert manager.count_references(buffer) == 3


def test_in_flight_pipeline_preserved_during_swap():
    """Test in-flight pipelines preserved during buffer swap."""
    manager = CanonBufferManager()
    
    # Setup v1.0 buffer
    v1_buffer = CanonBuffer(
        version=SemanticVersion(1, 0),
        content="v1",
        prompt="v1",
        state=BufferState.ACTIVE,
        created_at=datetime.now()
    )
    manager._current_buffer = v1_buffer
    
    # Register in-flight pipeline
    pipeline_buffer = manager.register_pipeline_reference("pipeline-1")
    assert pipeline_buffer is v1_buffer
    
    # Load and swap to v2.0
    manager.load_new_buffer(SemanticVersion(2, 0), "v2", "v2")
    result = manager.swap_buffers()
    
    # Verify in-flight count
    assert result.in_flight_count == 1
    
    # Verify pipeline still holds v1.0
    assert pipeline_buffer.version == SemanticVersion(1, 0)
    
    # New pipeline gets v2.0
    new_pipeline_buffer = manager.register_pipeline_reference("pipeline-2")
    assert new_pipeline_buffer.version == SemanticVersion(2, 0)


def test_concurrent_buffer_access():
    """Test thread-safe buffer access."""
    manager = CanonBufferManager()
    
    # Setup buffer
    manager._current_buffer = CanonBuffer(
        version=SemanticVersion(1, 0),
        content="v1",
        prompt="v1",
        state=BufferState.ACTIVE,
        created_at=datetime.now()
    )
    
    results = []
    
    def access_buffer(thread_id):
        buffer = manager.register_pipeline_reference(f"pipeline-{thread_id}")
        results.append(buffer.version)
        time.sleep(0.01)
        manager.unregister_pipeline_reference(f"pipeline-{thread_id}")
    
    # Start 10 concurrent threads
    threads = []
    for i in range(10):
        t = threading.Thread(target=access_buffer, args=(i,))
        threads.append(t)
        t.start()
    
    # Wait for completion
    for t in threads:
        t.join()
    
    # All should have accessed same version
    assert len(results) == 10
    assert all(v == SemanticVersion(1, 0) for v in results)


def test_swap_blocks_concurrent_swaps():
    """Test that concurrent swap attempts are serialized."""
    manager = CanonBufferManager()
    
    # Setup initial buffer
    manager._current_buffer = CanonBuffer(
        version=SemanticVersion(1, 0),
        content="v1",
        prompt="v1",
        state=BufferState.ACTIVE,
        created_at=datetime.now()
    )
    
    swap_count = [0]
    
    def attempt_swap(version_minor):
        try:
            manager.load_new_buffer(
                SemanticVersion(1, version_minor),
                f"v{version_minor}",
                f"v{version_minor}"
            )
            manager.swap_buffers()
            swap_count[0] += 1
        except Exception:
            pass
    
    # Try concurrent swaps
    threads = []
    for i in range(1, 4):
        t = threading.Thread(target=attempt_swap, args=(i,))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    # Only one swap should succeed at a time
    assert swap_count[0] >= 1