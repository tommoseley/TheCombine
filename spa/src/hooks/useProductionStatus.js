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
    const [notification, setNotification] = useState(null);

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

        // WS-EPIC-SPAWN-001 Phase 2: Handle children_updated event
        // Refresh floor when child documents are spawned/updated/superseded
        eventSource.addEventListener('children_updated', (event) => {
            try {
                const data = JSON.parse(event.data);
                console.log('Children updated:', data);
                fetchStatus();
            } catch (err) {
                console.error('Failed to parse children_updated:', err);
            }
        });

        // WS-STATION-DATA-001 Phase 3: Handle stations_declared event
        // Apply station list directly without refetching
        eventSource.addEventListener('stations_declared', (event) => {
            try {
                const eventData = JSON.parse(event.data);
                console.log('Stations declared:', eventData);
                const { document_type, stations } = eventData;
                
                setData(prev => {
                    const exists = prev.some(item => item.id === document_type);
                    console.log('stations_declared raw stations:', stations);
                    const stationData = stations.map(s => ({
                        id: s.id,
                        label: s.label,
                        state: s.state,
                        phases: s.phases || [],
                        phase: null,  // Current active phase (set by station_changed)
                    }));
                    console.log('stations_declared processed:', stationData);
                    
                    if (exists) {
                        // Update existing track - set state to in_production so stations render
                        return prev.map(item => 
                            item.id === document_type 
                                ? { ...item, state: 'in_production', stations: stationData }
                                : item
                        );
                    } else {
                        // Add new track with stations
                        return [...prev, {
                            id: document_type,
                            name: document_type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
                            state: 'in_production',
                            stations: stationData,
                        }];
                    }
                });
            } catch (err) {
                console.error('Failed to parse stations_declared:', err);
            }
        });

        // WS-STATION-DATA-001 Phase 3: Handle station_changed event
        // Update single station state without refetching
        eventSource.addEventListener('station_changed', (event) => {
            try {
                const eventData = JSON.parse(event.data);
                console.log('Station changed:', eventData);
                const { document_type, station_id, state: newState } = eventData;
                
                setData(prev => prev.map(item => {
                    if (item.id !== document_type) return item;
                    // Skip if no stations yet (will be populated by stations_declared or fetch)
                    if (!item.stations) return item;
                    return {
                        ...item,
                        stations: item.stations.map(s => 
                            s.id === station_id ? { ...s, state: newState } : s
                        ),
                    };
                }));
            } catch (err) {
                console.error('Failed to parse station_changed:', err);
            }
        });

        // Handle internal_step event - updates current phase within a station
        eventSource.addEventListener('internal_step', (event) => {
            try {
                const eventData = JSON.parse(event.data);
                console.log('Internal step:', eventData);
                const { document_type, station_id, step } = eventData;
                
                setData(prev => prev.map(item => {
                    if (item.id !== document_type) return item;
                    if (!item.stations) return item;
                    return {
                        ...item,
                        stations: item.stations.map(s => 
                            s.id === station_id 
                                ? { 
                                    ...s, 
                                    currentStep: step,  // { key, name, type, number, total }
                                  }
                                : s
                        ),
                    };
                }));
            } catch (err) {
                console.error('Failed to parse internal_step:', err);
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
            setNotification(null);
            await api.startProduction(projectId, documentType);
            setLineState('active');
            // Don't fetch immediately - SSE will provide updates as production progresses
        } catch (err) {
            console.error('Failed to start production:', err);
            // Show user-friendly notification
            const message = err.data?.message || err.message || 'Failed to start production';
            setNotification({ type: 'error', message });
            // Reset track state immediately - SSE events may have set stations
            // during the failed execution, creating a stale in_production state
            if (documentType) {
                setData(prev => prev.map(item =>
                    item.id === documentType
                        ? { ...item, state: 'ready_for_production', stations: null }
                        : item
                ));
            }
            setLineState('idle');
            // Also fetch full status for accuracy
            fetchStatus();
            throw err;
        }
    }, [projectId, fetchStatus]);

    // Dismiss notification
    const dismissNotification = useCallback(() => {
        setNotification(null);
    }, []);

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
        notification,
        dismissNotification,
        refresh: fetchStatus,
        resolveInterrupt,
        startProduction,
    };
}
