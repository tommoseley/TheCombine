import { useState, useEffect, useCallback } from 'react';
import { adminApi } from '../api/adminClient';

/**
 * Hook for fetching orchestration workflows for Admin Workbench sidebar.
 *
 * Returns step-based project orchestration workflows
 * (e.g., software_product_development) for display in the workflow browser.
 * Document production workflows (graph-based) are now shown as tabs
 * on their associated document types.
 */
export function useAdminWorkflows() {
    const [workflows, setWorkflows] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const fetchWorkflows = useCallback(async () => {
        setLoading(true);
        setError(null);

        try {
            const response = await adminApi.getOrchestrationWorkflows();
            setWorkflows(response.workflows || []);
        } catch (err) {
            setError(err.message);
            console.error('Failed to fetch orchestration workflows:', err);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchWorkflows();
    }, [fetchWorkflows]);

    return {
        workflows,
        loading,
        error,
        refresh: fetchWorkflows,
    };
}
