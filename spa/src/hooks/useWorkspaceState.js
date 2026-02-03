import { useState, useEffect, useCallback, useRef } from 'react';
import { adminApi } from '../api/adminClient';

/**
 * Hook for managing workspace state.
 *
 * Provides git status, tier1 validation, and TTL info.
 * Refreshes on demand and polls as a safety net.
 *
 * @param {string} workspaceId - Workspace to track
 * @param {number} pollInterval - Background poll interval in ms (default: 10000)
 */
export function useWorkspaceState(workspaceId, pollInterval = 10000) {
    const [state, setState] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const pollRef = useRef(null);

    // Fetch state
    const refresh = useCallback(async () => {
        if (!workspaceId) {
            setState(null);
            setLoading(false);
            return;
        }

        try {
            const newState = await adminApi.getWorkspaceState(workspaceId);
            setState(newState);
            setError(null);
        } catch (err) {
            setError(err.message);
            console.error('Failed to fetch workspace state:', err);
        } finally {
            setLoading(false);
        }
    }, [workspaceId]);

    // Initial fetch
    useEffect(() => {
        if (workspaceId) {
            setLoading(true);
            refresh();
        }
    }, [workspaceId, refresh]);

    // Background polling
    useEffect(() => {
        if (!workspaceId || !pollInterval) return;

        pollRef.current = setInterval(refresh, pollInterval);

        return () => {
            if (pollRef.current) {
                clearInterval(pollRef.current);
            }
        };
    }, [workspaceId, pollInterval, refresh]);

    return {
        state,
        loading,
        error,
        refresh,
        // Derived state for convenience
        isDirty: state?.is_dirty ?? false,
        modifiedArtifacts: state?.modified_artifacts ?? [],
        tier1Passed: state?.tier1?.passed ?? true,
        tier1Results: state?.tier1?.results ?? [],
        expiresAt: state?.expires_at ? new Date(state.expires_at) : null,
    };
}
