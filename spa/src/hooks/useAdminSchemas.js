import { useState, useEffect, useCallback } from 'react';
import { adminApi } from '../api/adminClient';

/**
 * Hook for fetching standalone schemas for Admin Workbench.
 *
 * Per ADR-045, schemas are extracted to combine-config/schemas/
 * and listed via /admin/workbench/schemas endpoint.
 */
export function useAdminSchemas() {
    const [schemas, setSchemas] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // Fetch schemas
    const fetchSchemas = useCallback(async () => {
        setLoading(true);
        setError(null);

        try {
            const response = await adminApi.getSchemas();
            setSchemas(response.schemas || []);
        } catch (err) {
            setError(err.message);
            console.error('Failed to fetch schemas:', err);
        } finally {
            setLoading(false);
        }
    }, []);

    // Initial fetch
    useEffect(() => {
        fetchSchemas();
    }, [fetchSchemas]);

    return {
        schemas,
        loading,
        error,
        refresh: fetchSchemas,
    };
}
