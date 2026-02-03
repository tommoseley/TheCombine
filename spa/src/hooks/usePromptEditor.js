import { useState, useEffect, useCallback, useRef } from 'react';
import { adminApi } from '../api/adminClient';

/**
 * Hook for editing a single prompt artifact with debounced auto-save.
 *
 * Handles loading content, tracking edits, and auto-saving with debounce.
 * Returns tier1 validation results after each save.
 *
 * @param {string} workspaceId - Workspace ID
 * @param {string} artifactId - Artifact ID (format: scope:name:version:kind)
 * @param {number} debounceMs - Debounce delay for auto-save (default: 500)
 * @param {function} onSave - Optional callback after successful save
 */
export function usePromptEditor(workspaceId, artifactId, { debounceMs = 500, onSave } = {}) {
    const [content, setContent] = useState('');
    const [originalContent, setOriginalContent] = useState('');
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [saving, setSaving] = useState(false);
    const [lastSaveResult, setLastSaveResult] = useState(null);

    const debounceRef = useRef(null);
    const pendingContentRef = useRef(null);

    // Load content
    const loadContent = useCallback(async () => {
        if (!workspaceId || !artifactId) {
            setContent('');
            setOriginalContent('');
            setLoading(false);
            return;
        }

        setLoading(true);
        setError(null);

        try {
            const result = await adminApi.getArtifact(workspaceId, artifactId);
            setContent(result.content);
            setOriginalContent(result.content);
        } catch (err) {
            setError(err.message);
            console.error('Failed to load artifact:', err);
        } finally {
            setLoading(false);
        }
    }, [workspaceId, artifactId]);

    // Save content
    const saveContent = useCallback(async (contentToSave) => {
        if (!workspaceId || !artifactId) return;

        setSaving(true);
        setError(null);

        try {
            const result = await adminApi.writeArtifact(workspaceId, artifactId, contentToSave);
            setLastSaveResult(result);
            setOriginalContent(contentToSave);

            if (onSave) {
                onSave(result);
            }
        } catch (err) {
            setError(err.message);
            console.error('Failed to save artifact:', err);
        } finally {
            setSaving(false);
        }
    }, [workspaceId, artifactId, onSave]);

    // Debounced save
    const debouncedSave = useCallback((newContent) => {
        pendingContentRef.current = newContent;

        if (debounceRef.current) {
            clearTimeout(debounceRef.current);
        }

        debounceRef.current = setTimeout(() => {
            if (pendingContentRef.current !== null) {
                saveContent(pendingContentRef.current);
                pendingContentRef.current = null;
            }
        }, debounceMs);
    }, [saveContent, debounceMs]);

    // Update content and trigger debounced save
    const updateContent = useCallback((newContent) => {
        setContent(newContent);

        // Only trigger save if content changed from original
        if (newContent !== originalContent) {
            debouncedSave(newContent);
        }
    }, [originalContent, debouncedSave]);

    // Reset to original content
    const reset = useCallback(() => {
        if (debounceRef.current) {
            clearTimeout(debounceRef.current);
        }
        pendingContentRef.current = null;
        setContent(originalContent);
    }, [originalContent]);

    // Force save immediately (bypass debounce)
    const saveNow = useCallback(() => {
        if (debounceRef.current) {
            clearTimeout(debounceRef.current);
        }
        if (content !== originalContent) {
            saveContent(content);
        }
    }, [content, originalContent, saveContent]);

    // Load on artifact change
    useEffect(() => {
        loadContent();

        // Cleanup debounce on unmount or artifact change
        return () => {
            if (debounceRef.current) {
                clearTimeout(debounceRef.current);
            }
        };
    }, [loadContent]);

    return {
        content,
        originalContent,
        loading,
        error,
        saving,
        lastSaveResult,
        // Derived
        isDirty: content !== originalContent,
        // Actions
        updateContent,
        reset,
        saveNow,
        reload: loadContent,
    };
}
