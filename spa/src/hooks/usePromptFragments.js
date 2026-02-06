import { useState, useEffect, useMemo, useCallback } from 'react';
import { adminApi } from '../api/adminClient';

/**
 * Hook for fetching and managing prompt fragments.
 *
 * Per WS-ADR-044-002, provides:
 * - fragments: All loaded fragments
 * - loading/error state
 * - fragmentsByKind: Grouped by kind
 * - kindCounts: Count per kind
 * - filterByKind: Filter helper
 */
export default function usePromptFragments() {
    const [fragments, setFragments] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // Fetch all fragments on mount
    useEffect(() => {
        let mounted = true;

        async function fetchFragments() {
            setLoading(true);
            setError(null);
            try {
                const response = await adminApi.getPromptFragments();
                if (mounted) {
                    setFragments(response.fragments || []);
                }
            } catch (err) {
                console.error('Failed to fetch prompt fragments:', err);
                if (mounted) {
                    setError(err.message || 'Failed to load prompt fragments');
                }
            } finally {
                if (mounted) {
                    setLoading(false);
                }
            }
        }

        fetchFragments();

        return () => {
            mounted = false;
        };
    }, []);

    // Group fragments by kind
    const fragmentsByKind = useMemo(() => {
        const grouped = {
            all: fragments,
            role: [],
            task: [],
            qa: [],
            pgc: [],
            questions: [],
            reflection: [],
        };

        for (const fragment of fragments) {
            const kind = fragment.kind;
            if (grouped[kind]) {
                grouped[kind].push(fragment);
            }
        }

        return grouped;
    }, [fragments]);

    // Count per kind (for filter pills)
    const kindCounts = useMemo(() => ({
        all: fragments.length,
        role: fragmentsByKind.role.length,
        task: fragmentsByKind.task.length,
        qa: fragmentsByKind.qa.length,
        pgc: fragmentsByKind.pgc.length,
        questions: fragmentsByKind.questions.length,
        reflection: fragmentsByKind.reflection.length,
    }), [fragments, fragmentsByKind]);

    // Filter helper
    const filterByKind = useCallback((kind) => {
        if (!kind || kind === 'all') {
            return fragments;
        }
        return fragmentsByKind[kind] || [];
    }, [fragments, fragmentsByKind]);

    // Kind options for KindFilter component
    const kindOptions = useMemo(() => {
        const options = [
            { id: 'all', label: 'All', count: kindCounts.all },
            { id: 'role', label: 'Roles', count: kindCounts.role },
            { id: 'task', label: 'Tasks', count: kindCounts.task },
            { id: 'qa', label: 'QA', count: kindCounts.qa },
            { id: 'pgc', label: 'PGC', count: kindCounts.pgc },
        ];

        // Only show Questions/Reflection if they exist
        if (kindCounts.questions > 0) {
            options.push({ id: 'questions', label: 'Questions', count: kindCounts.questions });
        }
        if (kindCounts.reflection > 0) {
            options.push({ id: 'reflection', label: 'Reflection', count: kindCounts.reflection });
        }

        return options;
    }, [kindCounts]);

    // Refresh function
    const refresh = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await adminApi.getPromptFragments();
            setFragments(response.fragments || []);
        } catch (err) {
            console.error('Failed to refresh prompt fragments:', err);
            setError(err.message || 'Failed to refresh');
        } finally {
            setLoading(false);
        }
    }, []);

    return {
        fragments,
        loading,
        error,
        fragmentsByKind,
        kindCounts,
        kindOptions,
        filterByKind,
        refresh,
    };
}
