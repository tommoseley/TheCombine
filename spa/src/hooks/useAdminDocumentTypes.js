import { useState, useEffect, useCallback } from 'react';
import { adminApi } from '../api/adminClient';

/**
 * Hook for fetching document types for Admin Workbench.
 *
 * Returns list of document types with their metadata
 * for display in the document type browser.
 */
export function useAdminDocumentTypes() {
    const [documentTypes, setDocumentTypes] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // Fetch document types
    const fetchDocumentTypes = useCallback(async () => {
        setLoading(true);
        setError(null);

        try {
            const response = await adminApi.getDocumentTypes();
            setDocumentTypes(response.document_types || []);
        } catch (err) {
            setError(err.message);
            console.error('Failed to fetch document types:', err);
        } finally {
            setLoading(false);
        }
    }, []);

    // Initial fetch
    useEffect(() => {
        fetchDocumentTypes();
    }, [fetchDocumentTypes]);

    return {
        documentTypes,
        loading,
        error,
        refresh: fetchDocumentTypes,
    };
}
