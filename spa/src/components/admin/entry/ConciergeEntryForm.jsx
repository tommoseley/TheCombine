import React, { useState } from 'react';

/**
 * Concierge Entry Form
 *
 * Specific Entry component for concierge_entry operation.
 * Displays intake classification and allows operator to confirm or correct.
 *
 * Context (renders: intake_classification.v1):
 * - classification: string ('qualified', 'needs_clarification', 'out_of_scope')
 * - project_type: string ('greenfield', 'enhancement', 'migration', etc.)
 * - artifact_type: string (e.g., 'web_application', 'api', 'mobile_application')
 * - audience: string
 * - intake_summary: string
 * - confidence: number (0-1)
 * - missing_information: string[]
 * - classification_rationale: string
 *
 * Response (captures: intake_confirmation.v1):
 * - confirmed: boolean
 * - corrected_project_type?: string
 * - notes?: string
 */
export default function ConciergeEntryForm({ operation, context, onSubmit, onCancel }) {
    const [mode, setMode] = useState('confirm'); // 'confirm' or 'correct'
    const [correctedProjectType, setCorrectedProjectType] = useState(context?.project_type || '');
    const [notes, setNotes] = useState('');

    const config = operation?.config || {};
    const entryPrompt = config.entry_prompt || 'Review the intake classification.';

    const projectTypes = [
        { value: 'greenfield', label: 'Greenfield (New Project)' },
        { value: 'enhancement', label: 'Enhancement (Existing Project)' },
        { value: 'migration', label: 'Migration' },
        { value: 'integration', label: 'Integration' },
        { value: 'unknown', label: 'Unknown / Other' },
    ];

    const handleSubmit = () => {
        const response = {
            confirmed: mode === 'confirm',
            timestamp: new Date().toISOString(),
        };

        if (mode === 'correct') {
            response.corrected_project_type = correctedProjectType;
        }

        if (notes.trim()) {
            response.notes = notes.trim();
        }

        onSubmit(response);
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
                            background: 'var(--dot-green, #22c55e)',
                            color: '#fff',
                        }}
                    >
                        Intake
                    </span>
                    <div>
                        <div className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                            Concierge Entry
                        </div>
                        <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
                            Confirm or correct the intake classification
                        </div>
                    </div>
                </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-4">
                <div className="max-w-2xl space-y-6">
                    {/* Entry Prompt */}
                    <div
                        className="p-3 rounded"
                        style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-panel)' }}
                    >
                        <div className="text-sm" style={{ color: 'var(--text-primary)' }}>
                            {entryPrompt}
                        </div>
                    </div>

                    {/* Confirmation Notice */}
                    <div
                        className="text-xs"
                        style={{ color: 'var(--text-muted)' }}
                    >
                        Confirmation requested
                    </div>

                    {/* Classification Summary */}
                    <div>
                        <h3
                            className="text-xs font-semibold uppercase tracking-wide mb-3"
                            style={{ color: 'var(--text-muted)' }}
                        >
                            Classification Result
                        </h3>

                        <div
                            className="p-4 rounded space-y-3"
                            style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-panel)' }}
                        >
                            {/* Intent Classification */}
                            <div className="flex items-center justify-between">
                                <span className="text-sm" style={{ color: 'var(--text-muted)' }}>
                                    Intent Classification
                                </span>
                                <span
                                    className="px-3 py-1 rounded font-semibold"
                                    style={{
                                        background: 'var(--accent-primary, #3b82f6)',
                                        color: '#fff',
                                        fontSize: 12,
                                    }}
                                >
                                    {context?.project_type?.replace(/_/g, ' ').toUpperCase() || 'Unknown'}
                                </span>
                            </div>

                            {/* Artifact Type */}
                            {context?.artifact_type && (
                                <div className="flex items-center justify-between">
                                    <span className="text-sm" style={{ color: 'var(--text-muted)' }}>
                                        Artifact Type
                                    </span>
                                    <span className="text-sm" style={{ color: 'var(--text-primary)' }}>
                                        {context.artifact_type.replace(/_/g, ' ')}
                                    </span>
                                </div>
                            )}

                            {/* Audience */}
                            {context?.audience && (
                                <div className="flex items-center justify-between">
                                    <span className="text-sm" style={{ color: 'var(--text-muted)' }}>
                                        Audience
                                    </span>
                                    <span className="text-sm" style={{ color: 'var(--text-primary)' }}>
                                        {context.audience}
                                    </span>
                                </div>
                            )}

                            {/* Summary */}
                            {context?.intake_summary && (
                                <div>
                                    <span className="text-sm block mb-1" style={{ color: 'var(--text-muted)' }}>
                                        Summary
                                    </span>
                                    <p className="text-sm" style={{ color: 'var(--text-primary)' }}>
                                        {context.intake_summary}
                                    </p>
                                </div>
                            )}

                            {/* Classification Rationale */}
                            {context?.classification_rationale && (
                                <div>
                                    <span className="text-sm block mb-1" style={{ color: 'var(--text-muted)' }}>
                                        Rationale
                                    </span>
                                    <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                                        {context.classification_rationale}
                                    </p>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Mode Selection */}
                    <div>
                        <h3
                            className="text-xs font-semibold uppercase tracking-wide mb-3"
                            style={{ color: 'var(--text-muted)' }}
                        >
                            Your Decision
                        </h3>

                        <div className="flex gap-3">
                            <button
                                onClick={() => setMode('confirm')}
                                className="flex-1 p-4 rounded text-left"
                                style={{
                                    background: mode === 'confirm'
                                        ? 'rgba(34, 197, 94, 0.1)'
                                        : 'var(--bg-panel)',
                                    border: mode === 'confirm'
                                        ? '2px solid #22c55e'
                                        : '1px solid var(--border-panel)',
                                }}
                            >
                                <div className="font-semibold mb-1" style={{ color: 'var(--text-primary)' }}>
                                    Confirm
                                </div>
                                <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
                                    The classification is correct
                                </div>
                            </button>

                            <button
                                onClick={() => setMode('correct')}
                                className="flex-1 p-4 rounded text-left"
                                style={{
                                    background: mode === 'correct'
                                        ? 'rgba(249, 115, 22, 0.1)'
                                        : 'var(--bg-panel)',
                                    border: mode === 'correct'
                                        ? '2px solid #f97316'
                                        : '1px solid var(--border-panel)',
                                }}
                            >
                                <div className="font-semibold mb-1" style={{ color: 'var(--text-primary)' }}>
                                    Correct
                                </div>
                                <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
                                    I need to change the classification before proceeding
                                </div>
                            </button>
                        </div>
                    </div>

                    {/* Correction Fields */}
                    {mode === 'correct' && (
                        <div>
                            <h3
                                className="text-xs font-semibold uppercase tracking-wide mb-3"
                                style={{ color: 'var(--text-muted)' }}
                            >
                                Correct Intent Classification
                            </h3>

                            <select
                                value={correctedProjectType}
                                onChange={(e) => setCorrectedProjectType(e.target.value)}
                                className="w-full p-3 rounded"
                                style={{
                                    background: 'var(--bg-input, var(--bg-canvas))',
                                    border: '1px solid var(--border-panel)',
                                    color: 'var(--text-primary)',
                                }}
                            >
                                <option value="">Select intent classification...</option>
                                {projectTypes.map((pt) => (
                                    <option key={pt.value} value={pt.value}>
                                        {pt.label}
                                    </option>
                                ))}
                            </select>
                        </div>
                    )}

                    {/* Notes */}
                    <div>
                        <h3
                            className="text-xs font-semibold uppercase tracking-wide mb-3"
                            style={{ color: 'var(--text-muted)' }}
                        >
                            Notes (Optional)
                        </h3>

                        <textarea
                            value={notes}
                            onChange={(e) => setNotes(e.target.value)}
                            placeholder="Add any additional context or notes..."
                            className="w-full p-3 rounded text-sm"
                            style={{
                                background: 'var(--bg-input, var(--bg-canvas))',
                                border: '1px solid var(--border-panel)',
                                color: 'var(--text-primary)',
                                minHeight: 80,
                                resize: 'vertical',
                            }}
                        />
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
                    disabled={mode === 'correct' && !correctedProjectType}
                    className="px-4 py-2 rounded text-sm font-semibold"
                    style={{
                        background: mode === 'confirm' ? '#22c55e' : '#f97316',
                        color: '#fff',
                        opacity: mode === 'correct' && !correctedProjectType ? 0.5 : 1,
                    }}
                >
                    {mode === 'confirm' ? 'Confirm Classification' : 'Submit Correction'}
                </button>
            </div>
        </div>
    );
}
