import { useState, useEffect, useCallback } from 'react';
import { adminApi } from '../api/adminClient';

/**
 * Hook for managing Admin Workbench workspace lifecycle.
 *
 * Handles get-or-create pattern: retrieves existing workspace
 * or creates a new one if none exists.
 */
export function useWorkspace() {
    const [workspaceId, setWorkspaceId] = useState(null);
    const [branch, setBranch] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // Initialize workspace (get or create)
    const initWorkspace = useCallback(async () => {
        setLoading(true);
        setError(null);

        try {
            // Try to get existing workspace
            let workspace = await adminApi.getCurrentWorkspace();

            // If none exists, create one
            if (!workspace) {
                workspace = await adminApi.createWorkspace();
            }

            setWorkspaceId(workspace.workspace_id);
            setBranch(workspace.branch);
        } catch (err) {
            setError(err.message);
            console.error('Failed to initialize workspace:', err);
        } finally {
            setLoading(false);
        }
    }, []);

    // Close workspace
    const closeWorkspace = useCallback(async (force = false) => {
        if (!workspaceId) return;

        try {
            await adminApi.closeWorkspace(workspaceId, force);
            setWorkspaceId(null);
            setBranch(null);
        } catch (err) {
            // Re-throw for caller to handle
            throw err;
        }
    }, [workspaceId]);

    // Initialize on mount
    useEffect(() => {
        initWorkspace();
    }, [initWorkspace]);

    return {
        workspaceId,
        branch,
        loading,
        error,
        closeWorkspace,
        reinitialize: initWorkspace,
    };
}
