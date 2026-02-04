import React, { useState } from 'react';
import ValidationResults from './ValidationResults';
import CommitDialog from './CommitDialog';
import { adminApi } from '../../api/adminClient';

/**
 * Parse artifact ID into display components.
 * Format: {scope}:{name}:{version}:{kind}
 */
function parseArtifactId(artifactId) {
    const parts = artifactId.split(':');
    if (parts.length !== 4) return { display: artifactId };

    const [scope, name, version, kind] = parts;
    const displayName = name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    const kindLabel = kind.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

    return {
        scope,
        name,
        displayName,
        kind,
        kindLabel,
        version,
        display: `${displayName} - ${kindLabel}`,
    };
}

/**
 * Right panel - workspace git state, validation results, and commit actions.
 */
export default function GitStatusPanel({
    workspaceId,
    state,
    loading,
    onCommit,
    onDiscard,
    onClose,
    onRefresh,
}) {
    const [showCommitDialog, setShowCommitDialog] = useState(false);
    const [committing, setCommitting] = useState(false);
    const [discarding, setDiscarding] = useState(false);
    const [commitError, setCommitError] = useState(null);

    const isDirty = state?.is_dirty ?? false;
    const modifiedArtifacts = state?.modified_artifacts ?? [];
    const tier1Passed = state?.tier1?.passed ?? true;
    const tier1Results = state?.tier1?.results ?? [];
    const branch = state?.branch ?? '';
    const expiresAt = state?.expires_at ? new Date(state.expires_at) : null;

    // Handle commit
    const handleCommit = async (message) => {
        setCommitting(true);
        setCommitError(null);

        try {
            const result = await adminApi.commit(workspaceId, message);
            setShowCommitDialog(false);
            onCommit?.(result);
            onRefresh?.();
        } catch (err) {
            setCommitError(err.message);
        } finally {
            setCommitting(false);
        }
    };

    // Handle discard
    const handleDiscard = async () => {
        if (!confirm('Discard all uncommitted changes? This cannot be undone.')) {
            return;
        }

        setDiscarding(true);
        try {
            await adminApi.discard(workspaceId);
            onDiscard?.();
            onRefresh?.();
        } catch (err) {
            console.error('Discard failed:', err);
            alert('Failed to discard changes: ' + err.message);
        } finally {
            setDiscarding(false);
        }
    };

    // Handle close workspace
    const handleClose = async () => {
        if (isDirty) {
            alert('Cannot close workspace with uncommitted changes. Commit or discard first.');
            return;
        }

        if (!confirm('Close this workspace? You can open a new one later.')) {
            return;
        }

        try {
            await adminApi.closeWorkspace(workspaceId);
            onClose?.();
        } catch (err) {
            console.error('Close failed:', err);
            alert('Failed to close workspace: ' + err.message);
        }
    };

    // Format time remaining until expiry
    const formatTimeRemaining = (expiresAt) => {
        if (!expiresAt) return null;
        const now = new Date();
        const diff = expiresAt - now;
        if (diff <= 0) return 'Expired';

        const hours = Math.floor(diff / (1000 * 60 * 60));
        const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

        if (hours > 0) {
            return `${hours}h ${minutes}m remaining`;
        }
        return `${minutes}m remaining`;
    };

    return (
        <div
            className="w-80 flex flex-col border-l h-full"
            style={{
                borderColor: 'var(--border-panel)',
                background: 'var(--bg-panel)',
            }}
        >
            {/* Header */}
            <div
                className="px-4 py-3 border-b"
                style={{ borderColor: 'var(--border-panel)' }}
            >
                <h2
                    className="text-sm font-semibold uppercase tracking-wide"
                    style={{ color: 'var(--text-muted)' }}
                >
                    Workspace Status
                </h2>
            </div>

            {/* Loading state */}
            {loading ? (
                <div className="p-4 text-sm" style={{ color: 'var(--text-muted)' }}>
                    Loading...
                </div>
            ) : (
                <div className="flex-1 overflow-y-auto">
                    {/* Branch info */}
                    <div className="px-4 py-3 border-b" style={{ borderColor: 'var(--border-panel)' }}>
                        <div className="text-xs mb-1" style={{ color: 'var(--text-muted)' }}>
                            Branch
                        </div>
                        <div
                            className="text-sm font-mono truncate"
                            style={{ color: 'var(--text-primary)' }}
                            title={branch}
                        >
                            {branch || '-'}
                        </div>
                        {expiresAt && (
                            <div
                                className="text-xs mt-2"
                                style={{ color: 'var(--text-muted)' }}
                            >
                                {formatTimeRemaining(expiresAt)}
                            </div>
                        )}
                    </div>

                    {/* Dirty state */}
                    <div className="px-4 py-3 border-b" style={{ borderColor: 'var(--border-panel)' }}>
                        <div className="flex items-center justify-between mb-2">
                            <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
                                Status
                            </div>
                            <div
                                className="text-xs px-2 py-0.5 rounded"
                                style={{
                                    background: isDirty
                                        ? 'var(--state-warning-bg, rgba(245, 158, 11, 0.2))'
                                        : 'var(--state-success-bg)',
                                    color: isDirty
                                        ? 'var(--state-warning-text, #f59e0b)'
                                        : 'var(--state-success-text)',
                                }}
                            >
                                {isDirty ? 'Modified' : 'Clean'}
                            </div>
                        </div>

                        {/* Modified artifacts list */}
                        {modifiedArtifacts.length > 0 && (
                            <div className="mt-2">
                                <div className="text-xs mb-1" style={{ color: 'var(--text-muted)' }}>
                                    Changed ({modifiedArtifacts.length})
                                </div>
                                <div className="space-y-1">
                                    {modifiedArtifacts.map((artifact) => {
                                        const parsed = parseArtifactId(artifact);
                                        return (
                                            <div
                                                key={artifact}
                                                className="text-xs truncate"
                                                style={{ color: 'var(--text-secondary)' }}
                                                title={artifact}
                                            >
                                                <span style={{ color: 'var(--text-primary)' }}>
                                                    {parsed.displayName || artifact}
                                                </span>
                                                {parsed.kindLabel && (
                                                    <span style={{ color: 'var(--text-muted)' }}>
                                                        {' '}- {parsed.kindLabel}
                                                    </span>
                                                )}
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Tier 1 Validation */}
                    <div className="px-4 py-3 border-b" style={{ borderColor: 'var(--border-panel)' }}>
                        <div className="flex items-center justify-between mb-2">
                            <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
                                Tier 1 Validation
                            </div>
                            <ValidationResults results={tier1Results} compact />
                        </div>

                        {/* Expanded validation results */}
                        {tier1Results.length > 0 && !tier1Passed && (
                            <div className="mt-3">
                                <ValidationResults results={tier1Results} />
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Actions */}
            <div
                className="px-4 py-3 border-t space-y-2"
                style={{ borderColor: 'var(--border-panel)' }}
            >
                {/* Commit button */}
                <button
                    onClick={() => setShowCommitDialog(true)}
                    disabled={!isDirty || !tier1Passed || loading}
                    className="w-full px-4 py-2 rounded text-sm font-medium transition-opacity"
                    style={{
                        background: isDirty && tier1Passed
                            ? 'var(--action-success)'
                            : 'var(--border-panel)',
                        color: isDirty && tier1Passed
                            ? '#000'
                            : 'var(--text-muted)',
                        cursor: isDirty && tier1Passed && !loading
                            ? 'pointer'
                            : 'not-allowed',
                        opacity: loading ? 0.5 : 1,
                    }}
                >
                    Commit Changes
                </button>

                {/* Why commit is disabled */}
                {!tier1Passed && isDirty && (
                    <div
                        className="text-xs text-center"
                        style={{ color: 'var(--state-error-text)' }}
                    >
                        Fix validation errors to commit
                    </div>
                )}

                {/* Discard button */}
                {isDirty && (
                    <button
                        onClick={handleDiscard}
                        disabled={discarding || loading}
                        className="w-full px-4 py-2 rounded text-sm transition-opacity"
                        style={{
                            background: 'transparent',
                            border: '1px solid var(--border-panel)',
                            color: 'var(--text-muted)',
                            opacity: discarding || loading ? 0.5 : 1,
                        }}
                    >
                        {discarding ? 'Discarding...' : 'Discard Changes'}
                    </button>
                )}

                {/* Close workspace button */}
                {!isDirty && (
                    <button
                        onClick={handleClose}
                        disabled={loading}
                        className="w-full px-4 py-2 rounded text-sm transition-opacity"
                        style={{
                            background: 'transparent',
                            border: '1px solid var(--border-panel)',
                            color: 'var(--text-muted)',
                            opacity: loading ? 0.5 : 1,
                        }}
                    >
                        Close Workspace
                    </button>
                )}
            </div>

            {/* Commit Dialog */}
            {showCommitDialog && (
                <CommitDialog
                    workspaceId={workspaceId}
                    onCommit={handleCommit}
                    onCancel={() => {
                        setShowCommitDialog(false);
                        setCommitError(null);
                    }}
                    loading={committing}
                    modifiedArtifacts={modifiedArtifacts}
                    modifiedFiles={state?.modified_files ?? []}
                />
            )}

            {/* Commit error toast */}
            {commitError && (
                <div
                    className="absolute bottom-4 left-4 right-4 p-3 rounded text-sm"
                    style={{
                        background: 'rgba(239, 68, 68, 0.9)',
                        color: '#fff',
                    }}
                >
                    {commitError}
                </div>
            )}
        </div>
    );
}
