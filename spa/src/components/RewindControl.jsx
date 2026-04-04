/**
 * RewindControl — button to rewind pipeline from a stage (ADR-063, ADR-069).
 *
 * ADR-069: The reason field IS the correction brief — one living field that
 * serves as both narrative and binding authority. Pre-populated from authority
 * store on subsequent rewinds. Stage checkboxes control applies_to_stages.
 */
import { useState, useCallback } from 'react';
import { api } from '../api/client';

const PIPELINE_STAGES = ['CI', 'PD', 'IP', 'TA', 'WP', 'WS'];

// Map doc_type_id to canonical stage code (stageName prop may be either form)
const DOC_TYPE_TO_STAGE = {
    concierge_intake: 'CI',
    project_discovery: 'PD',
    implementation_plan: 'IP',
    technical_architecture: 'TA',
    work_package: 'WP',
    work_statement: 'WS',
};

function toCanonicalStage(name) {
    if (!name) return name;
    const upper = name.toUpperCase();
    if (PIPELINE_STAGES.includes(upper)) return upper;
    return DOC_TYPE_TO_STAGE[name] || DOC_TYPE_TO_STAGE[name.toLowerCase()] || upper;
}

export default function RewindControl({ projectId, stageName, displayName, onRewindComplete }) {
    const canonicalStage = toCanonicalStage(stageName);

    const [showConfirm, setShowConfirm] = useState(false);
    const [reason, setReason] = useState('');
    const [appliesTo, setAppliesTo] = useState([]);
    const [loading, setLoading] = useState(false);
    const [loadingPrev, setLoadingPrev] = useState(false);
    const [error, setError] = useState(null);

    // Fetch correction BEFORE opening dialog, then show with pre-populated text
    const handleOpenDialog = useCallback(async () => {
        setLoadingPrev(true);
        setShowConfirm(true);
        try {
            const data = await api.getCorrection(projectId, stageName);
            if (data && data.text) {
                setReason(data.text);
                setAppliesTo(data.applies_to_stages || [canonicalStage]);
            } else {
                setReason('');
                setAppliesTo([canonicalStage]);
            }
        } catch (err) {
            console.warn('Failed to load correction for pre-population:', err);
            setReason('');
            setAppliesTo([canonicalStage]);
        } finally {
            setLoadingPrev(false);
        }
    }, [projectId, stageName, canonicalStage]);

    const toggleStage = (stage) => {
        setAppliesTo(prev =>
            prev.includes(stage)
                ? prev.filter(s => s !== stage)
                : [...prev, stage]
        );
    };

    const handleRewind = async () => {
        if (!reason.trim()) return;
        setLoading(true);
        setError(null);
        try {
            const result = await api.rewindPipeline(projectId, stageName, reason, 'user', appliesTo);
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
                backgroundColor: 'var(--bg-panel, var(--bg-canvas, #1a1a2e))',
            }}>
                <p className="text-[11px] font-medium mb-1" style={{ color: 'var(--text-primary)' }}>
                    Rewind to {displayName}?
                </p>
                <p className="text-[10px] mb-2" style={{ color: 'var(--text-secondary)' }}>
                    All documents from this stage onward will be marked stale.
                    Describe what's wrong and what must change — this becomes a binding constraint for regeneration.
                </p>

                {loadingPrev ? (
                    <p className="text-[10px] mb-2" style={{ color: 'var(--text-secondary)' }}>Loading previous correction...</p>
                ) : (
                    <>
                        <textarea
                            placeholder="What's wrong and what must change before regeneration..."
                            value={reason}
                            onChange={(e) => setReason(e.target.value)}
                            rows={3}
                            className="w-full text-[11px] px-2 py-1 rounded border mb-1"
                            style={{
                                borderColor: 'var(--border-primary, #d1d5db)',
                                backgroundColor: 'var(--surface-secondary, var(--bg-canvas, #1a1a2e))',
                                color: 'var(--text-primary)',
                                resize: 'vertical',
                            }}
                            disabled={loading}
                        />
                        <div className="flex flex-wrap gap-1 mb-2">
                            <span className="text-[9px]" style={{ color: 'var(--text-secondary)' }}>Applies to:</span>
                            {PIPELINE_STAGES.map(s => (
                                <button
                                    key={s}
                                    type="button"
                                    onClick={() => toggleStage(s)}
                                    className="text-[9px] px-1.5 py-0.5 rounded border"
                                    style={{
                                        borderColor: appliesTo.includes(s)
                                            ? 'var(--accent-primary, #3b82f6)'
                                            : 'var(--border-primary, #d1d5db)',
                                        backgroundColor: appliesTo.includes(s)
                                            ? 'var(--accent-primary, #3b82f6)'
                                            : 'transparent',
                                        color: appliesTo.includes(s)
                                            ? '#fff'
                                            : 'var(--text-secondary)',
                                        cursor: 'pointer',
                                    }}
                                    disabled={loading}
                                >
                                    {s}
                                </button>
                            ))}
                        </div>
                    </>
                )}

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
                            backgroundColor: '#dc2626',
                            color: '#fff',
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
            onClick={handleOpenDialog}
            className="text-[9px] px-2 py-1 rounded font-medium transition-opacity hover:brightness-110"
            style={{
                backgroundColor: '#dc2626',
                color: '#fff',
            }}
            title={`Rewind pipeline to ${displayName}`}
        >
            ↩ Rewind
        </button>
    );
}
