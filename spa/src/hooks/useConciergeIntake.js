import { useState, useCallback, useRef, useEffect } from 'react';
import { api, createIntakeSSE } from '../api/client';

/**
 * Hook for managing concierge intake workflow.
 *
 * Encapsulates all intake workflow logic:
 * - Starting intake
 * - Submitting messages
 * - Updating interpretation fields
 * - Locking and generating
 * - Polling during generation
 */
export function useConciergeIntake() {
    const [executionId, setExecutionId] = useState(null);
    const [phase, setPhase] = useState('idle'); // idle, describe, review, generating, complete
    const [messages, setMessages] = useState([]);
    const [pendingPrompt, setPendingPrompt] = useState(null);
    const [pendingChoices, setPendingChoices] = useState(null);
    const [interpretation, setInterpretation] = useState({});
    const [confidence, setConfidence] = useState(0);
    const [missingFields, setMissingFields] = useState([]);
    const [canInitialize, setCanInitialize] = useState(false);
    const [gateOutcome, setGateOutcome] = useState(null);
    const [project, setProject] = useState(null);
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(false);
    const [submitting, setSubmitting] = useState(false);
    // Gate Profile fields (ADR-047)
    const [intakeClassification, setIntakeClassification] = useState(null);
    const [intakeGatePhase, setIntakeGatePhase] = useState(null);

    const sseRef = useRef(null);
    const mountedRef = useRef(true);

    // Cleanup on unmount
    useEffect(() => {
        mountedRef.current = true;
        return () => {
            mountedRef.current = false;
            if (sseRef.current) {
                sseRef.current.close();
            }
        };
    }, []);

    /**
     * Update state from API response
     */
    const updateFromState = useCallback((state) => {
        if (!mountedRef.current) return;

        setPhase(state.phase);
        setMessages(state.messages || []);
        setPendingPrompt(state.pending_prompt);
        setPendingChoices(state.pending_choices);
        setInterpretation(state.interpretation || {});
        setConfidence(state.confidence || 0);
        setMissingFields(state.missing_fields || []);
        setCanInitialize(state.can_initialize || false);
        setGateOutcome(state.gate_outcome);
        setProject(state.project);
        // Gate Profile fields (ADR-047)
        setIntakeClassification(state.intake_classification);
        setIntakeGatePhase(state.intake_gate_phase);
    }, []);

    /**
     * Start a new intake workflow
     */
    const startIntake = useCallback(async () => {
        setError(null);
        setLoading(true);

        try {
            const response = await api.startIntake();
            if (!mountedRef.current) return;

            setExecutionId(response.execution_id);
            setPhase(response.phase || 'describe');
            setPendingPrompt(response.pending_prompt);
            setMessages([]);
            setInterpretation({});
            setProject(null);
            setGateOutcome(null);
        } catch (err) {
            if (!mountedRef.current) return;
            setError(err.message || 'Failed to start intake');
        } finally {
            if (mountedRef.current) {
                setLoading(false);
            }
        }
    }, []);

    /**
     * Submit a user message
     */
    const submitMessage = useCallback(async (content) => {
        if (!executionId || !content.trim()) return;

        setError(null);
        setSubmitting(true);

        // Optimistically add user message
        const userMessage = { role: 'user', content };
        setMessages(prev => [...prev, userMessage]);

        try {
            const state = await api.submitIntakeMessage(executionId, content);
            if (!mountedRef.current) return;

            updateFromState(state);
        } catch (err) {
            if (!mountedRef.current) return;
            // Remove optimistic message on error
            setMessages(prev => prev.filter(m => m !== userMessage));
            setError(err.message || 'Failed to submit message');
        } finally {
            if (mountedRef.current) {
                setSubmitting(false);
            }
        }
    }, [executionId, updateFromState]);

    /**
     * Update an interpretation field
     */
    const updateField = useCallback(async (fieldKey, value) => {
        if (!executionId) return;

        setError(null);

        // Optimistic update
        setInterpretation(prev => ({
            ...prev,
            [fieldKey]: { value, source: 'user', locked: true },
        }));

        try {
            const state = await api.updateIntakeField(executionId, fieldKey, value);
            if (!mountedRef.current) return;

            updateFromState(state);
        } catch (err) {
            if (!mountedRef.current) return;
            setError(err.message || 'Failed to update field');
            // Reload state on error
            const state = await api.getIntakeState(executionId);
            if (mountedRef.current) {
                updateFromState(state);
            }
        }
    }, [executionId, updateFromState]);

    /**
     * Lock interpretation and start generation via SSE
     */
    const lockAndGenerate = useCallback(async () => {
        if (!executionId || !canInitialize) return;

        setError(null);
        setLoading(true);

        try {
            const state = await api.initializeIntake(executionId);
            if (!mountedRef.current) return;

            updateFromState(state);

            // Start SSE for generation progress
            if (state.phase === 'generating') {
                startSSE();
            }
        } catch (err) {
            if (!mountedRef.current) return;
            setError(err.message || 'Failed to initialize project');
            setLoading(false);
        }
    }, [executionId, canInitialize, updateFromState]);

    /**
     * Start SSE connection for generation progress
     */
    const startSSE = useCallback(() => {
        if (sseRef.current) {
            sseRef.current.close();
        }

        const eventSource = createIntakeSSE(executionId);
        sseRef.current = eventSource;

        eventSource.addEventListener('started', (e) => {
            if (!mountedRef.current) return;
            const data = JSON.parse(e.data);
            console.log('Intake started:', data);
        });

        eventSource.addEventListener('progress', (e) => {
            if (!mountedRef.current) return;
            const data = JSON.parse(e.data);
            console.log('Intake progress:', data.current_node);
        });

        eventSource.addEventListener('complete', async (e) => {
            if (!mountedRef.current) return;
            const data = JSON.parse(e.data);
            console.log('Intake complete:', data);

            eventSource.close();
            sseRef.current = null;

            // Update state with completion data
            setPhase('complete');
            setGateOutcome(data.gate_outcome);
            setProject(data.project);
            setLoading(false);
        });

        eventSource.addEventListener('error', (e) => {
            if (!mountedRef.current) return;

            // Check if it's a real error or just connection closed
            if (eventSource.readyState === EventSource.CLOSED) {
                return;
            }

            try {
                const data = JSON.parse(e.data);
                setError(data.message || 'Generation failed');
            } catch {
                setError('Connection lost during generation');
            }

            eventSource.close();
            sseRef.current = null;
            setLoading(false);
        });

        eventSource.onerror = () => {
            if (!mountedRef.current) return;
            // EventSource will auto-reconnect, but if closed we clean up
            if (eventSource.readyState === EventSource.CLOSED) {
                sseRef.current = null;
                setLoading(false);
            }
        };
    }, [executionId]);

    /**
     * Reset intake state
     */
    const reset = useCallback(() => {
        if (sseRef.current) {
            sseRef.current.close();
            sseRef.current = null;
        }
        setExecutionId(null);
        setPhase('idle');
        setMessages([]);
        setPendingPrompt(null);
        setPendingChoices(null);
        setInterpretation({});
        setConfidence(0);
        setMissingFields([]);
        setCanInitialize(false);
        setGateOutcome(null);
        setProject(null);
        setError(null);
        setLoading(false);
        setSubmitting(false);
    }, []);

    return {
        // State
        executionId,
        phase,
        messages,
        pendingPrompt,
        pendingChoices,
        interpretation,
        confidence,
        missingFields,
        canInitialize,
        gateOutcome,
        project,
        error,
        loading,
        submitting,
        // Gate Profile fields (ADR-047)
        intakeClassification,
        intakeGatePhase,

        // Actions
        startIntake,
        submitMessage,
        updateField,
        lockAndGenerate,
        reset,
    };
}
