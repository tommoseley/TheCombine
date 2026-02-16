import { useState } from 'react';
import { api } from '../api/client';

/**
 * IntentIntakeDialog - Minimal intake form for creating IntentPackets.
 *
 * Per WS-BCP-001 Phase 2: textarea + submit, no editing, no versioning.
 * IntentPackets are immutable once created.
 */
export default function IntentIntakeDialog({ projectId, onClose, onCreated }) {
    const [rawIntent, setRawIntent] = useState('');
    const [constraints, setConstraints] = useState('');
    const [successCriteria, setSuccessCriteria] = useState('');
    const [context, setContext] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState(null);
    const [result, setResult] = useState(null);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!rawIntent.trim()) return;

        setSubmitting(true);
        setError(null);

        try {
            const response = await api.createIntent(projectId, {
                raw_intent: rawIntent.trim(),
                constraints: constraints.trim() || null,
                success_criteria: successCriteria.trim() || null,
                context: context.trim() || null,
            });
            setResult(response);
            if (onCreated) onCreated(response);
        } catch (err) {
            setError(err.message || 'Failed to create intent');
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center"
            style={{ background: 'rgba(0,0,0,0.4)' }}
            onClick={(e) => e.target === e.currentTarget && onClose()}
        >
            <div
                className="w-full max-w-xl mx-4 rounded-lg shadow-2xl flex flex-col"
                style={{ background: 'var(--bg-panel)', maxHeight: '90vh' }}
            >
                {/* Header */}
                <div
                    className="flex items-center justify-between px-5 py-3 border-b"
                    style={{ borderColor: 'var(--border-panel)' }}
                >
                    <div>
                        <h3 className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>
                            New Intent
                        </h3>
                        <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                            Describe what you want to build. This becomes an immutable input.
                        </p>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-1.5 rounded hover:bg-white/10 transition-colors"
                        style={{ color: 'var(--text-muted)' }}
                    >
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M18 6L6 18M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                {/* Content */}
                {result ? (
                    <div className="p-5 text-center">
                        <div
                            className="inline-flex items-center gap-2 px-3 py-1.5 rounded text-sm font-medium mb-3"
                            style={{ background: 'var(--color-emerald-bg)', color: 'var(--color-emerald-text, #065f46)' }}
                        >
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <path d="M20 6L9 17l-5-5" />
                            </svg>
                            Intent Saved
                        </div>
                        <p className="text-sm mb-1" style={{ color: 'var(--text-primary)' }}>
                            Intent ID:
                        </p>
                        <p className="text-xs font-mono mb-4" style={{ color: 'var(--text-muted)' }}>
                            {result.intent_id}
                        </p>
                        <button
                            onClick={onClose}
                            className="px-4 py-2 rounded text-sm font-medium text-white"
                            style={{ background: 'var(--color-action, #3b82f6)' }}
                        >
                            Done
                        </button>
                    </div>
                ) : (
                    <form onSubmit={handleSubmit} className="p-5 space-y-4 overflow-auto">
                        {/* Raw Intent (required) */}
                        <div>
                            <label
                                className="block text-sm font-medium mb-1"
                                style={{ color: 'var(--text-primary)' }}
                            >
                                What do you want to build? *
                            </label>
                            <textarea
                                value={rawIntent}
                                onChange={(e) => setRawIntent(e.target.value)}
                                placeholder="Describe your intent clearly. This text is stored exactly as written."
                                rows={4}
                                required
                                className="w-full px-3 py-2 text-sm rounded border resize-y"
                                style={{
                                    background: 'var(--bg-canvas)',
                                    borderColor: 'var(--border-panel)',
                                    color: 'var(--text-primary)',
                                }}
                            />
                        </div>

                        {/* Constraints (optional) */}
                        <div>
                            <label
                                className="block text-sm font-medium mb-1"
                                style={{ color: 'var(--text-primary)' }}
                            >
                                Constraints
                            </label>
                            <textarea
                                value={constraints}
                                onChange={(e) => setConstraints(e.target.value)}
                                placeholder="Technical, timeline, resource, or other constraints (optional)"
                                rows={2}
                                className="w-full px-3 py-2 text-sm rounded border resize-y"
                                style={{
                                    background: 'var(--bg-canvas)',
                                    borderColor: 'var(--border-panel)',
                                    color: 'var(--text-primary)',
                                }}
                            />
                        </div>

                        {/* Success Criteria (optional) */}
                        <div>
                            <label
                                className="block text-sm font-medium mb-1"
                                style={{ color: 'var(--text-primary)' }}
                            >
                                Success Criteria
                            </label>
                            <textarea
                                value={successCriteria}
                                onChange={(e) => setSuccessCriteria(e.target.value)}
                                placeholder="What does success look like? (optional)"
                                rows={2}
                                className="w-full px-3 py-2 text-sm rounded border resize-y"
                                style={{
                                    background: 'var(--bg-canvas)',
                                    borderColor: 'var(--border-panel)',
                                    color: 'var(--text-primary)',
                                }}
                            />
                        </div>

                        {/* Context (optional) */}
                        <div>
                            <label
                                className="block text-sm font-medium mb-1"
                                style={{ color: 'var(--text-primary)' }}
                            >
                                Context
                            </label>
                            <textarea
                                value={context}
                                onChange={(e) => setContext(e.target.value)}
                                placeholder="Project background, domain notes, etc. (optional)"
                                rows={2}
                                className="w-full px-3 py-2 text-sm rounded border resize-y"
                                style={{
                                    background: 'var(--bg-canvas)',
                                    borderColor: 'var(--border-panel)',
                                    color: 'var(--text-primary)',
                                }}
                            />
                        </div>

                        {error && (
                            <p className="text-sm text-red-500">{error}</p>
                        )}

                        {/* Submit */}
                        <div className="flex justify-end gap-2 pt-2">
                            <button
                                type="button"
                                onClick={onClose}
                                className="px-4 py-2 rounded text-sm"
                                style={{ color: 'var(--text-muted)' }}
                            >
                                Cancel
                            </button>
                            <button
                                type="submit"
                                disabled={!rawIntent.trim() || submitting}
                                className="px-4 py-2 rounded text-sm font-medium text-white disabled:opacity-50"
                                style={{ background: 'var(--color-action, #3b82f6)' }}
                            >
                                {submitting ? 'Saving...' : 'Save Intent'}
                            </button>
                        </div>
                    </form>
                )}
            </div>
        </div>
    );
}
