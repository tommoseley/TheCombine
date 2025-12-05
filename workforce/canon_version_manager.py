# workforce/canon_version_manager.py

"""Canon version management coordinator."""

from pathlib import Path

from workforce.canon import (
    CanonLoader,
    VersionValidator,
    VersionStore,
    PromptBuilder,
    DriftDetector,
    CanonBufferManager,
    resolve_canon_path,
    VersionComparison
)
from workforce.utils.logging import log_info, log_warning


class CanonVersionManager:
    """
    Manages canon versioning with double-buffer pattern.
    
    Coordinates CanonLoader, VersionValidator, VersionStore,
    PromptBuilder, DriftDetector, and CanonBufferManager.
    """
    
    def __init__(self):
        self.loader = CanonLoader()
        self.validator = VersionValidator()
        self.version_store = VersionStore()
        self.prompt_builder = PromptBuilder()
        self.drift_detector = DriftDetector()
        self.buffer_manager = CanonBufferManager()
    
    def load_canon(self) -> None:
        """
        Load canon on startup.
        
        Creates initial buffer and stores in buffer_manager.
        """
        canon_path = resolve_canon_path()
        canon_doc = self.loader.load_canon(canon_path)
        
        # Build system prompt
        prompt = self.prompt_builder.build_orchestrator_prompt(canon_doc)
        
        # Store in version store (for version checking)
        self.version_store.update_version(canon_doc.version, canon_doc.content)
        
        # Load into buffer manager as initial active buffer
        self.buffer_manager._current_buffer = self.buffer_manager._lock.__enter__()
        try:
            from workforce.canon.buffer_manager import CanonBuffer, BufferState
            from datetime import datetime
            
            initial_buffer = CanonBuffer(
                version=canon_doc.version,
                content=canon_doc.content,
                prompt=prompt,
                state=BufferState.ACTIVE,
                created_at=datetime.now()
            )
            self.buffer_manager._current_buffer = initial_buffer
        finally:
            self.buffer_manager._lock.__exit__(None, None, None)
        
        log_info(f"Canon loaded: PIPELINE_FLOW_VERSION={canon_doc.version}")
    
    def reload_canon_with_buffer_swap(self) -> None:
        """
        Reload canon with double-buffer pattern.
        
        CRITICAL: This method performs atomic buffer swap to ensure
        in-flight pipelines continue with old canon.
        
        Steps:
        1. Load new canon into next buffer (background)
        2. Build system prompt
        3. Atomically swap buffers
        4. Schedule cleanup of old buffer
        """
        log_info("Reloading canon with buffer swap...")
        
        # STEP 1: Load new canon
        canon_path = resolve_canon_path()
        new_canon_doc = self.loader.load_canon(canon_path)
        
        # Check if version actually changed
        old_version = self.version_store.get_current_version()
        if old_version:
            comparison = self.validator.compare_versions(old_version, new_canon_doc.version)
            
            if comparison == VersionComparison.SAME:
                log_info("Canon version unchanged, skipping reload")
                return
            
            log_info(f"Canon version changed: {old_version} → {new_canon_doc.version}")
        
        # STEP 2: Build system prompt
        new_prompt = self.prompt_builder.build_orchestrator_prompt(new_canon_doc)
        
        # STEP 3: Load into next buffer
        self.buffer_manager.load_new_buffer(
            new_canon_doc.version,
            new_canon_doc.content,
            new_prompt
        )
        
        # STEP 4: Atomically swap buffers (CRITICAL)
        swap_result = self.buffer_manager.swap_buffers()
        
        # STEP 5: Update version store
        self.version_store.update_version(new_canon_doc.version, new_canon_doc.content)
        
        log_info(
            f"Canon buffer swapped: {swap_result.old_version} → {swap_result.new_version}, "
            f"in-flight preserved: {swap_result.in_flight_count}, "
            f"swap duration: {swap_result.swap_duration_ms:.3f}ms"
        )
        
        # STEP 6: Verify swap performance (<1ms requirement)
        if swap_result.swap_duration_ms > 1.0:
            log_warning(
                f"Buffer swap exceeded 1ms requirement: {swap_result.swap_duration_ms:.3f}ms"
            )
    
    def version_changed(self) -> bool:
        """
        Check if canon file version changed on disk.
        
        Returns:
            True if version on disk differs from in-memory version
        """
        current_version = self.version_store.get_current_version()
        if not current_version:
            return False
        
        new_version = self.drift_detector.check_for_drift(current_version)
        return new_version is not None