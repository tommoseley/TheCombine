import { useState, useEffect, useCallback, useRef } from 'react';
import { adminApi } from '../api/adminClient';

/**
 * Hook for editing a workflow definition with debounced auto-save.
 *
 * Similar to usePromptEditor but handles JSON content.
 * Loads the workflow artifact, parses JSON, and auto-saves
 * the full definition on changes.
 *
 * @param {string} workspaceId - Workspace ID
 * @param {string} artifactId - Artifact ID (workflow:name:version:definition)
 * @param {object} options - { debounceMs, onSave }
 */
export function useWorkflowEditor(workspaceId, artifactId, { debounceMs = 1000, onSave } = {}) {
    const [workflowJson, setWorkflowJson] = useState(null);
    const [originalJson, setOriginalJson] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [saving, setSaving] = useState(false);
    const [lastSaveResult, setLastSaveResult] = useState(null);

    const debounceRef = useRef(null);
    const pendingJsonRef = useRef(null);

    // Load workflow content
    const loadContent = useCallback(async () => {
        if (!workspaceId || !artifactId) {
            setWorkflowJson(null);
            setOriginalJson(null);
            setLoading(false);
            return;
        }

        setLoading(true);
        setError(null);

        try {
            const result = await adminApi.getArtifact(workspaceId, artifactId);
            const parsed = JSON.parse(result.content);
            setWorkflowJson(parsed);
            setOriginalJson(parsed);
        } catch (err) {
            setError(err.message);
            console.error('Failed to load workflow artifact:', err);
        } finally {
            setLoading(false);
        }
    }, [workspaceId, artifactId]);

    // Save workflow content
    const saveContent = useCallback(async (jsonToSave) => {
        if (!workspaceId || !artifactId) return;

        setSaving(true);
        setError(null);

        try {
            const content = JSON.stringify(jsonToSave, null, 2);
            const result = await adminApi.writeArtifact(workspaceId, artifactId, content);
            setLastSaveResult(result);
            setOriginalJson(jsonToSave);

            if (onSave) {
                onSave(result);
            }
        } catch (err) {
            setError(err.message);
            console.error('Failed to save workflow:', err);
        } finally {
            setSaving(false);
        }
    }, [workspaceId, artifactId, onSave]);

    // Debounced save
    const debouncedSave = useCallback((newJson) => {
        pendingJsonRef.current = newJson;

        if (debounceRef.current) {
            clearTimeout(debounceRef.current);
        }

        debounceRef.current = setTimeout(() => {
            if (pendingJsonRef.current !== null) {
                saveContent(pendingJsonRef.current);
                pendingJsonRef.current = null;
            }
        }, debounceMs);
    }, [saveContent, debounceMs]);

    // Update workflow and trigger debounced save
    const updateWorkflow = useCallback((newJson) => {
        setWorkflowJson(newJson);
        debouncedSave(newJson);
    }, [debouncedSave]);

    // Force save immediately
    const saveNow = useCallback(() => {
        if (debounceRef.current) {
            clearTimeout(debounceRef.current);
        }
        if (workflowJson) {
            saveContent(workflowJson);
        }
    }, [workflowJson, saveContent]);

    // Load on artifact change
    useEffect(() => {
        loadContent();

        return () => {
            if (debounceRef.current) {
                clearTimeout(debounceRef.current);
            }
        };
    }, [loadContent]);

    return {
        workflowJson,
        originalJson,
        loading,
        error,
        saving,
        lastSaveResult,
        isDirty: workflowJson !== originalJson,
        updateWorkflow,
        saveNow,
        reload: loadContent,
    };
}
