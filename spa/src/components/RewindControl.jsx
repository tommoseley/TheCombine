/**
 * RewindControl — button to rewind pipeline from a stage (ADR-063).
 *
 * WS-REWIND-016: Shows "Rewind to here" on pipeline nodes with
 * confirmation dialog before executing.
 */
import { useState } from 'react';
import { api } from '../api/client';

export default function RewindControl({ projectId, stageName, displayName, onRewindComplete }) {
    const [showConfirm, setShowConfirm] = useState(false);
    const [reason, setReason] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const handleRewind = async () => {
        if (!reason.trim()) return;
        setLoading(true);
        setError(null);
        try {
            const result = await api.rewindPipeline(projectId, stageName, reason);
            setShowConfirm(false);
            setReason('');
            if (onRewindComplete) onRewindComplete(result);
        } catch (err) {
            setError(err.message || 'Rewind failed');
        } finally {
            setLoading(false);
        }
    };

    if (showConfirm) {
        return (
            <div className="mt-2 p-2 rounded border" style={{
                borderColor: 'var(--state-blocked-bg, #fbbf24)',
                backgroundColor: 'var(--surface-secondary, #f9fafb)',
            }}>
                <p className="text-[11px] font-medium mb-1" style={{ color: 'var(--text-primary)' }}>
                    Rewind to {displayName}?
                </p>
                <p className="text-[10px] mb-2" style={{ color: 'var(--text-secondary)' }}>
                    All documents from this stage onward will be marked stale.
                </p>
                <input
                    type="text"
                    placeholder="Reason for rewind..."
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    className="w-full text-[11px] px-2 py-1 rounded border mb-2"
                    style={{
                        borderColor: 'var(--border-primary, #d1d5db)',
                        backgroundColor: 'var(--surface-primary, #fff)',
                        color: 'var(--text-primary)',
                    }}
                    disabled={loading}
                />
                {error && (
                    <p className="text-[10px] mb-1" style={{ color: 'var(--state-blocked-text, #dc2626)' }}>
                        {error}
                    </p>
                )}
                <div className="flex gap-2">
                    <button
                        onClick={handleRewind}
                        disabled={loading || !reason.trim()}
                        className="text-[10px] px-2 py-1 rounded font-medium"
                        style={{
                            backgroundColor: 'var(--state-blocked-bg, #fbbf24)',
                            color: 'var(--state-blocked-text, #92400e)',
                            opacity: loading || !reason.trim() ? 0.5 : 1,
                        }}
                    >
                        {loading ? 'Rewinding...' : 'Confirm Rewind'}
                    </button>
                    <button
                        onClick={() => { setShowConfirm(false); setError(null); }}
                        disabled={loading}
                        className="text-[10px] px-2 py-1 rounded"
                        style={{ color: 'var(--text-secondary)' }}
                    >
                        Cancel
                    </button>
                </div>
            </div>
        );
    }

    return (
        <button
            onClick={() => setShowConfirm(true)}
            className="text-[9px] px-1.5 py-0.5 rounded opacity-60 hover:opacity-100 transition-opacity"
            style={{
                color: 'var(--text-secondary)',
                border: '1px solid var(--border-primary, #d1d5db)',
            }}
            title={`Rewind pipeline to ${displayName}`}
        >
            ↩ Rewind
        </button>
    );
}
