# workforce/canon/buffer_manager.py

"""Double-buffer canon pattern for concurrency safety."""

import threading
import time
from enum import Enum
from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime

from workforce.canon.loader import SemanticVersion
from workforce.utils.errors import (
    CanonNotLoadedError,
    CanonLoadInProgressError,
    CanonNotReadyError
)
from workforce.utils.logging import log_info, log_warning, log_debug


class BufferState(Enum):
    """Canon buffer lifecycle states."""
    EMPTY = "empty"
    LOADING = "loading"
    READY = "ready"
    ACTIVE = "active"
    DRAINING = "draining"
    RETIRED = "retired"


@dataclass
class CanonBuffer:
    """Immutable canon buffer."""
    version: SemanticVersion
    content: str
    prompt: str
    state: BufferState
    created_at: datetime
    
    def __hash__(self):
        return id(self)


@dataclass
class SwapResult:
    """Result of buffer swap operation."""
    old_version: str
    new_version: str
    in_flight_count: int
    swap_duration_ms: float


class CanonBufferManager:
    """
    Manages double-buffer canon pattern for concurrency safety.
    
    CRITICAL: Prevents mid-flight version changes by maintaining
    separate buffers for in-flight vs. new pipelines.
    """
    
    def __init__(self):
        self._current_buffer: Optional[CanonBuffer] = None
        self._next_buffer: Optional[CanonBuffer] = None
        self._lock = threading.Lock()
        self._pipeline_refs: Dict[str, CanonBuffer] = {}
    
    def get_current_buffer(self) -> CanonBuffer:
        """
        Get current canon buffer (thread-safe read).
        
        Returns immutable reference to current buffer.
        Pipelines hold this reference for their entire lifetime.
        
        Returns:
            Current active buffer
            
        Raises:
            CanonNotLoadedError: If no buffer is loaded
        """
        with self._lock:
            if self._current_buffer is None:
                raise CanonNotLoadedError("No canon buffer loaded")
            return self._current_buffer
    
    def load_new_buffer(self, version: SemanticVersion, content: str, prompt: str) -> None:
        """
        Load new canon into next buffer (background operation).
        
        Does not affect in-flight pipelines using current buffer.
        
        Args:
            version: Semantic version
            content: Canon content
            prompt: System prompt with canon
            
        Raises:
            CanonLoadInProgressError: If load already in progress
        """
        with self._lock:
            if self._next_buffer is not None and self._next_buffer.state == BufferState.LOADING:
                raise CanonLoadInProgressError("Canon load already in progress")
            
            self._next_buffer = CanonBuffer(
                version=version,
                content=content,
                prompt=prompt,
                state=BufferState.LOADING,
                created_at=datetime.now()
            )
        
        # Mark as ready
        with self._lock:
            if self._next_buffer:
                self._next_buffer.state = BufferState.READY
    
    def swap_buffers(self) -> SwapResult:
        """
        Atomically swap current buffer (thread-safe write).
        
        CRITICAL: Must complete in <1ms.
        New pipelines immediately see new buffer.
        In-flight pipelines continue with old buffer.
        
        Returns:
            SwapResult with old/new versions and in-flight count
            
        Raises:
            CanonNotReadyError: If next buffer not ready
        """
        swap_start = time.perf_counter()
        
        with self._lock:
            if self._next_buffer is None or self._next_buffer.state != BufferState.READY:
                raise CanonNotReadyError("Next buffer not ready for swap")
            
            old_buffer = self._current_buffer
            new_buffer = self._next_buffer
            
            # Atomic pointer swap
            self._current_buffer = new_buffer
            self._next_buffer = None
            
            # Update states
            new_buffer.state = BufferState.ACTIVE
            if old_buffer:
                old_buffer.state = BufferState.DRAINING
            
            in_flight_count = len(self._pipeline_refs)
        
        swap_duration = (time.perf_counter() - swap_start) * 1000  # Convert to ms
        
        result = SwapResult(
            old_version=str(old_buffer.version) if old_buffer else "none",
            new_version=str(new_buffer.version),
            in_flight_count=in_flight_count,
            swap_duration_ms=swap_duration
        )
        
        log_info(f"Canon buffer swapped: {result.old_version} → {result.new_version}")
        log_info(f"In-flight pipelines preserved: {in_flight_count}")
        log_info(f"Swap duration: {swap_duration:.3f}ms")
        
        # Verify swap was atomic (<1ms requirement)
        if swap_duration > 1.0:
            log_warning(f"Buffer swap exceeded 1ms: {swap_duration:.3f}ms")
        
        # Schedule cleanup of old buffer
        if old_buffer:
            self._schedule_cleanup(old_buffer)
        
        return result
    
    def register_pipeline_reference(self, pipeline_id: str) -> CanonBuffer:
        """
        Register pipeline's reference to current buffer.
        
        Pipeline holds immutable reference for entire lifetime.
        
        Args:
            pipeline_id: Unique pipeline identifier
            
        Returns:
            Canon buffer for this pipeline
        """
        with self._lock:
            buffer = self._current_buffer
            if buffer is None:
                raise CanonNotLoadedError("No canon buffer loaded")
            self._pipeline_refs[pipeline_id] = buffer
            log_debug(f"Pipeline {pipeline_id} registered with buffer {buffer.version}")
            return buffer
    
    def unregister_pipeline_reference(self, pipeline_id: str) -> None:
        """
        Unregister pipeline reference when complete.
        
        Allows old buffer cleanup when last reference released.
        
        Args:
            pipeline_id: Unique pipeline identifier
        """
        with self._lock:
            if pipeline_id in self._pipeline_refs:
                buffer = self._pipeline_refs[pipeline_id]
                del self._pipeline_refs[pipeline_id]
                log_debug(f"Pipeline {pipeline_id} unregistered from buffer {buffer.version}")
    
    def count_references(self, buffer: CanonBuffer) -> int:
        """
        Count pipelines referencing a specific buffer.
        
        Args:
            buffer: Buffer to count references for
            
        Returns:
            Number of active references
        """
        with self._lock:
            return sum(1 for b in self._pipeline_refs.values() if b is buffer)
    
    def _schedule_cleanup(self, buffer: CanonBuffer) -> None:
        """Schedule cleanup of old buffer after references released."""
        def cleanup():
            # Wait for all references to be released
            max_wait = 300  # 5 minutes
            start_time = time.time()
            
            while self.count_references(buffer) > 0:
                if time.time() - start_time > max_wait:
                    log_warning(f"Buffer cleanup timeout: {buffer.version} still has references")
                    break
                time.sleep(0.1)
            
            # Mark as retired
            buffer.state = BufferState.RETIRED
            
            log_info(f"Canon buffer retired: {buffer.version}")
        
        # Run cleanup in background thread
        threading.Thread(target=cleanup, daemon=True).start()