import { useState, useEffect, useCallback } from 'react';
import { adminApi } from '../api/adminClient';

/**
 * Hook for fetching roles for Admin Workbench.
 *
 * Returns list of roles with their metadata
 * for display in the role browser.
 */
export function useAdminRoles() {
    const [roles, setRoles] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // Fetch roles
    const fetchRoles = useCallback(async () => {
        setLoading(true);
        setError(null);

        try {
            const response = await adminApi.getRoles();
            setRoles(response.roles || []);
        } catch (err) {
            setError(err.message);
            console.error('Failed to fetch roles:', err);
        } finally {
            setLoading(false);
        }
    }, []);

    // Initial fetch
    useEffect(() => {
        fetchRoles();
    }, [fetchRoles]);

    return {
        roles,
        loading,
        error,
        refresh: fetchRoles,
    };
}
