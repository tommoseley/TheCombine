import { useState, useEffect, useCallback, useRef } from 'react';
import { api, createProductionSSE } from '../api/client';
import { transformProductionStatus } from '../api/transformers';

/**
 * Hook for production line status with SSE updates
 *
 * Fetches initial status from API and subscribes to SSE for real-time updates.
 */
export function useProductionStatus(projectId) {
    const [data, setData] = useState([]);
    const [lineState, setLineState] = useState('idle');
    const [interrupts, setInterrupts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [connected, setConnected] = useState(false);

    const eventSourceRef = useRef(null);
    const reconnectTimeoutRef = useRef(null);

    // Fetch current status
    const fetchStatus = useCallback(async () => {
        if (!projectId) return;

        try {
            setLoading(true);
            setError(null);

            // Fetch status and interrupts in parallel
            const [status, projectInterrupts] = await Promise.all([
                api.getProductionStatus(projectId),
                api.getProjectInterrupts(projectId).catch(() => []),
            ]);

            setInterrupts(projectInterrupts);
            setLineState(status.line_state);
            setData(transformProductionStatus(status, projectInterrupts));
        } catch (err) {
            setError(err.message);
            console.error('Failed to fetch production status:', err);
        } finally {
            setLoading(false);
        }
    }, [projectId]);

    // Connect to SSE
    const connectSSE = useCallback(() => {
        if (!projectId) return;

        // Clean up existing connection
        if (eventSourceRef.current) {
            eventSourceRef.current.close();
        }

        const eventSource = createProductionSSE(projectId);
        eventSourceRef.current = eventSource;

        eventSource.addEventListener('connected', () => {
            setConnected(true);
            setError(null);
            console.log(`SSE connected for project ${projectId}`);
        });

        eventSource.addEventListener('station_transition', (event) => {
            try {
                const data = JSON.parse(event.data);
                console.log('Station transition:', data);
                // Refresh status on state changes
                fetchStatus();
            } catch (err) {
                console.error('Failed to parse station_transition:', err);
            }
        });

        eventSource.addEventListener('line_stopped', (event) => {
            try {
                const data = JSON.parse(event.data);
                console.log('Line stopped:', data);
                setLineState('stopped');
                fetchStatus();
            } catch (err) {
                console.error('Failed to parse line_stopped:', err);
            }
        });

        eventSource.addEventListener('production_complete', (event) => {
            try {
                const data = JSON.parse(event.data);
                console.log('Production complete:', data);
                setLineState('complete');
                fetchStatus();
            } catch (err) {
                console.error('Failed to parse production_complete:', err);
            }
        });

        eventSource.addEventListener('interrupt_resolved', (event) => {
            try {
                const data = JSON.parse(event.data);
                console.log('Interrupt resolved:', data);
                fetchStatus();
            } catch (err) {
                console.error('Failed to parse interrupt_resolved:', err);
            }
        });

        eventSource.addEventListener('track_started', (event) => {
            try {
                const data = JSON.parse(event.data);
                console.log('Track started:', data);
                setLineState('active');
                fetchStatus();
            } catch (err) {
                console.error('Failed to parse track_started:', err);
            }
        });

        eventSource.addEventListener('track_stabilized', (event) => {
            try {
                const data = JSON.parse(event.data);
                console.log('Track stabilized:', data);
                // Refresh to get the final state
                fetchStatus();
            } catch (err) {
                console.error('Failed to parse track_stabilized:', err);
            }
        });

        eventSource.onerror = (err) => {
            console.error('SSE error:', err);
            setConnected(false);
            setError('Connection lost');
            eventSource.close();

            // Auto-reconnect after 3 seconds
            reconnectTimeoutRef.current = setTimeout(() => {
                console.log('Attempting SSE reconnect...');
                connectSSE();
            }, 3000);
        };
    }, [projectId, fetchStatus]);

    // Disconnect SSE
    const disconnect = useCallback(() => {
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
        }
        if (eventSourceRef.current) {
            eventSourceRef.current.close();
            eventSourceRef.current = null;
        }
        setConnected(false);
    }, []);

    // Resolve an interrupt (submit answers)
    // NOTE: Don't fetchStatus immediately - let SSE events update the UI
    // This allows optimistic updates in the component to persist until real data arrives
    const resolveInterrupt = useCallback(async (interruptId, answers) => {
        try {
            await api.resolveInterrupt(interruptId, { answers });
            // Don't fetch immediately - SSE will provide updates as production continues
        } catch (err) {
            console.error('Failed to resolve interrupt:', err);
            throw err;
        }
    }, []);

    // Start production for a document type
    // NOTE: Don't fetchStatus immediately - let SSE events update the UI
    // This allows optimistic updates in the component to persist until real data arrives
    const startProduction = useCallback(async (documentType = null) => {
        try {
            await api.startProduction(projectId, documentType);
            setLineState('active');
            // Don't fetch immediately - SSE will provide updates as production progresses
        } catch (err) {
            console.error('Failed to start production:', err);
            throw err;
        }
    }, [projectId]);

    // Initial fetch and SSE connection
    useEffect(() => {
        fetchStatus();
        connectSSE();
        return () => disconnect();
    }, [fetchStatus, connectSSE, disconnect]);

    return {
        data,
        lineState,
        interrupts,
        loading,
        error,
        connected,
        refresh: fetchStatus,
        resolveInterrupt,
        startProduction,
    };
}
