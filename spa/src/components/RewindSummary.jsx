/**
 * RewindSummary — shows what changed after rewind (ADR-063).
 *
 * WS-REWIND-018: Displays rewind result, stale documents, and
 * a regenerate action button. Also shows a persistent warning
 * banner when the project has stale documents.
 */
import { useState } from 'react';
import { api } from '../api/client';

/**
 * Banner shown when pipeline has stale documents.
 */
export function StaleBanner({ projectId, earliestStaleStage, onRegenerateClick }) {
    if (!earliestStaleStage) return null;

    return (
        <div
            className="px-3 py-2 rounded-md mb-3 flex items-center justify-between"
            style={{
                backgroundColor: 'var(--state-blocked-bg, #fef3c7)',
                border: '1px solid var(--state-blocked-text, #d97706)',
            }}
        >
            <div>
                <span className="text-[11px] font-semibold" style={{ color: 'var(--state-blocked-text, #92400e)' }}>
                    Pipeline has stale documents
                </span>
                <span className="text-[10px] ml-2" style={{ color: 'var(--text-secondary)' }}>
                    from {earliestStaleStage} stage. Regeneration required.
                </span>
            </div>
            {onRegenerateClick && (
                <button
                    onClick={() => onRegenerateClick(earliestStaleStage)}
                    className="text-[10px] px-2 py-1 rounded font-medium"
                    style={{
                        backgroundColor: 'var(--accent, #7c3aed)',
                        color: '#fff',
                    }}
                >
                    Regenerate from {earliestStaleStage}
                </button>
            )}
        </div>
    );
}

/**
 * Rewind result panel shown after a rewind completes.
 */
export default function RewindSummary({ result, onDismiss, onRegenerate }) {
    if (!result) return null;

    return (
        <div
            className="p-3 rounded-md mb-3 border"
            style={{
                backgroundColor: 'var(--surface-secondary, #f9fafb)',
                borderColor: 'var(--state-blocked-bg, #fbbf24)',
            }}
        >
            <div className="flex items-center justify-between mb-2">
                <span className="text-[11px] font-semibold" style={{ color: 'var(--text-primary)' }}>
                    Pipeline Rewound to {result.rewind_to_stage}
                </span>
                {onDismiss && (
                    <button
                        onClick={onDismiss}
                        className="text-[10px]"
                        style={{ color: 'var(--text-secondary)' }}
                    >
                        ✕
                    </button>
                )}
            </div>

            <div className="text-[10px] space-y-1" style={{ color: 'var(--text-secondary)' }}>
                <p><strong>Affected stages:</strong> {result.affected_stages?.join(' → ')}</p>
                <p><strong>Documents marked stale:</strong> {result.affected_document_count}</p>
            </div>

            {onRegenerate && result.rewind_to_stage && (
                <button
                    onClick={() => onRegenerate(result.rewind_to_stage)}
                    className="mt-2 text-[10px] px-2 py-1 rounded font-medium"
                    style={{
                        backgroundColor: 'var(--accent, #7c3aed)',
                        color: '#fff',
                    }}
                >
                    Regenerate from {result.rewind_to_stage}
                </button>
            )}
        </div>
    );
}
