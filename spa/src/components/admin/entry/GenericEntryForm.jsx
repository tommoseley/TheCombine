import React, { useState } from 'react';

/**
 * Generic Entry Form
 *
 * Fallback component for Entry operations without a specific implementation.
 * Renders a basic JSON editor for the response based on the captures schema.
 *
 * Props:
 * - operation: Full operation definition
 * - context: Data matching renders schema (what to display)
 * - onSubmit: Callback with response matching captures schema
 * - onCancel: Optional cancel callback
 */
export default function GenericEntryForm({ operation, context, onSubmit, onCancel }) {
    const [response, setResponse] = useState('{}');
    const [error, setError] = useState(null);

    const config = operation?.config || {};
    const entryPrompt = config.entry_prompt || 'Please provide your response.';

    const handleSubmit = () => {
        try {
            const parsed = JSON.parse(response);
            setError(null);
            onSubmit(parsed);
        } catch (err) {
            setError('Invalid JSON: ' + err.message);
        }
    };

    return (
        <div
            className="flex flex-col h-full"
            style={{ background: 'var(--bg-canvas)' }}
        >
            {/* Header */}
            <div
                className="px-4 py-3 border-b"
                style={{ borderColor: 'var(--border-panel)', background: 'var(--bg-panel)' }}
            >
                <div className="flex items-center gap-3">
                    <span
                        className="px-2 py-1 rounded font-semibold uppercase"
                        style={{
                            fontSize: 10,
                            background: 'var(--dot-orange, #f97316)',
                            color: '#fff',
                        }}
                    >
                        Entry
                    </span>
                    <div>
                        <div className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                            {operation?.name || 'Entry Form'}
                        </div>
                        <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
                            {operation?.id}
                        </div>
                    </div>
                </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-4">
                <div className="max-w-2xl space-y-4">
                    {/* Entry Prompt */}
                    <div
                        className="p-3 rounded"
                        style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-panel)' }}
                    >
                        <div className="text-sm" style={{ color: 'var(--text-primary)' }}>
                            {entryPrompt}
                        </div>
                    </div>

                    {/* Context Display */}
                    {context && (
                        <div>
                            <label
                                className="block text-xs font-semibold uppercase tracking-wide mb-2"
                                style={{ color: 'var(--text-muted)' }}
                            >
                                Context (renders: {config.renders})
                            </label>
                            <pre
                                className="p-3 rounded text-xs font-mono overflow-x-auto"
                                style={{
                                    background: 'var(--bg-panel)',
                                    border: '1px solid var(--border-panel)',
                                    color: 'var(--text-secondary)',
                                    maxHeight: 200,
                                }}
                            >
                                {JSON.stringify(context, null, 2)}
                            </pre>
                        </div>
                    )}

                    {/* Response Input */}
                    <div>
                        <label
                            className="block text-xs font-semibold uppercase tracking-wide mb-2"
                            style={{ color: 'var(--text-muted)' }}
                        >
                            Response (captures: {config.captures})
                        </label>
                        <textarea
                            value={response}
                            onChange={(e) => setResponse(e.target.value)}
                            className="w-full p-3 rounded font-mono text-xs"
                            style={{
                                background: 'var(--bg-input, var(--bg-canvas))',
                                border: '1px solid var(--border-panel)',
                                color: 'var(--text-primary)',
                                minHeight: 200,
                                resize: 'vertical',
                            }}
                            placeholder="Enter JSON response..."
                        />
                        {error && (
                            <div className="mt-2 text-xs" style={{ color: '#ef4444' }}>
                                {error}
                            </div>
                        )}
                    </div>

                    {/* Generic Form Note */}
                    <div
                        className="p-3 rounded text-xs"
                        style={{ background: 'var(--bg-panel)', color: 'var(--text-muted)' }}
                    >
                        <strong>Note:</strong> This is a generic entry form. For a better experience,
                        implement a specific component for this operation in EntryComponentRegistry.
                    </div>
                </div>
            </div>

            {/* Footer */}
            <div
                className="px-4 py-3 border-t flex justify-end gap-2"
                style={{ borderColor: 'var(--border-panel)', background: 'var(--bg-panel)' }}
            >
                {onCancel && (
                    <button
                        onClick={onCancel}
                        className="px-4 py-2 rounded text-sm"
                        style={{
                            background: 'var(--bg-canvas)',
                            border: '1px solid var(--border-panel)',
                            color: 'var(--text-secondary)',
                        }}
                    >
                        Cancel
                    </button>
                )}
                <button
                    onClick={handleSubmit}
                    className="px-4 py-2 rounded text-sm font-semibold"
                    style={{
                        background: 'var(--accent-primary, #3b82f6)',
                        color: '#fff',
                    }}
                >
                    Submit
                </button>
            </div>
        </div>
    );
}
