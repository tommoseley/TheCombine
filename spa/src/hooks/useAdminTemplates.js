import { useState, useEffect, useCallback } from 'react';
import { adminApi } from '../api/adminClient';

/**
 * Hook for fetching templates for Admin Workbench.
 *
 * Returns list of templates with their metadata
 * for display in the template browser.
 */
export function useAdminTemplates() {
    const [templates, setTemplates] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // Fetch templates
    const fetchTemplates = useCallback(async () => {
        setLoading(true);
        setError(null);

        try {
            const response = await adminApi.getTemplates();
            setTemplates(response.templates || []);
        } catch (err) {
            setError(err.message);
            console.error('Failed to fetch templates:', err);
        } finally {
            setLoading(false);
        }
    }, []);

    // Initial fetch
    useEffect(() => {
        fetchTemplates();
    }, [fetchTemplates]);

    return {
        templates,
        loading,
        error,
        refresh: fetchTemplates,
    };
}
