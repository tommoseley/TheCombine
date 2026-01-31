import { useState, useEffect, useCallback, useRef } from 'react';

/**
 * Hook for SSE connection to production floor updates
 * Automatically reconnects on disconnect
 */
export function useFloorSSE(projectId, onUpdate) {
    const [connected, setConnected] = useState(false);
    const [error, setError] = useState(null);
    const eventSourceRef = useRef(null);
    const reconnectTimeoutRef = useRef(null);

    const connect = useCallback(() => {
        if (!projectId) return;

        // Clean up existing connection
        if (eventSourceRef.current) {
            eventSourceRef.current.close();
        }

        const url = `/api/v1/projects/${projectId}/sse`;
        const eventSource = new EventSource(url);
        eventSourceRef.current = eventSource;

        eventSource.onopen = () => {
            setConnected(true);
            setError(null);
            console.log(`SSE connected for project ${projectId}`);
        };

        eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                onUpdate?.(data);
            } catch (err) {
                console.error('Failed to parse SSE message:', err);
            }
        };

        eventSource.addEventListener('node_update', (event) => {
            try {
                const data = JSON.parse(event.data);
                onUpdate?.({ type: 'node_update', ...data });
            } catch (err) {
                console.error('Failed to parse node_update:', err);
            }
        });

        eventSource.addEventListener('state_change', (event) => {
            try {
                const data = JSON.parse(event.data);
                onUpdate?.({ type: 'state_change', ...data });
            } catch (err) {
                console.error('Failed to parse state_change:', err);
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
                connect();
            }, 3000);
        };
    }, [projectId, onUpdate]);

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

    useEffect(() => {
        connect();
        return () => disconnect();
    }, [connect, disconnect]);

    return { connected, error, reconnect: connect };
}
