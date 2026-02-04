import React, { useState } from 'react';
import DiffView from './DiffView';

/**
 * Parse artifact ID into human-readable components.
 * Format: {scope}:{name}:{version}:{kind}
 */
function parseArtifactId(artifactId) {
    const parts = artifactId.split(':');
    if (parts.length !== 4) return { display: artifactId, scope: 'unknown' };

    const [scope, name, version, kind] = parts;
    const displayName = name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    const kindLabel = kind.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

    return {
        scope,
        name,
        version,
        kind,
        displayName,
        kindLabel,
        display: `${displayName} - ${kindLabel}`,
    };
}

/**
 * Group artifacts by scope for display.
 */
function groupArtifactsByScope(artifacts) {
    const groups = {
        doctype: { label: 'Document Types', items: [] },
        role: { label: 'Roles', items: [] },
        template: { label: 'Templates', items: [] },
    };

    artifacts.forEach(artifactId => {
        const parsed = parseArtifactId(artifactId);
        if (groups[parsed.scope]) {
            groups[parsed.scope].items.push(parsed);
        }
    });

    return Object.entries(groups)
        .filter(([_, group]) => group.items.length > 0)
        .map(([scope, group]) => ({ scope, ...group }));
}

/**
 * Modal dialog for entering commit message and reviewing changes.
 */
export default function CommitDialog({
    workspaceId,
    onCommit,
    onCancel,
    loading = false,
    modifiedArtifacts = [],
    modifiedFiles = [],
}) {
    // workspaceId is required for DiffView
    const [message, setMessage] = useState('');
    const [showDiff, setShowDiff] = useState(false);

    const groupedArtifacts = groupArtifactsByScope(modifiedArtifacts);
    const totalChanges = modifiedArtifacts.length;

    const handleSubmit = (e) => {
        e.preventDefault();
        if (message.trim() && !loading) {
            onCommit(message.trim());
        }
    };

    // Handle Escape key
    const handleKeyDown = (e) => {
        if (e.key === 'Escape' && !loading) {
            onCancel();
        }
    };

    return (
        <div
            className="fixed inset-0 flex items-center justify-center z-50"
            style={{ background: 'rgba(0, 0, 0, 0.7)' }}
            onClick={(e) => e.target === e.currentTarget && !loading && onCancel()}
            onKeyDown={handleKeyDown}
        >
            <div
                className="w-full max-w-lg p-6 rounded-lg shadow-xl"
                style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-panel)' }}
            >
                <h2
                    className="text-lg font-semibold mb-4"
                    style={{ color: 'var(--text-primary)' }}
                >
                    Commit Changes
                </h2>

                {/* Changes summary */}
                {totalChanges > 0 && (
                    <div
                        className="mb-4 p-3 rounded"
                        style={{ background: 'var(--bg-canvas)', border: '1px solid var(--border-panel)' }}
                    >
                        <div
                            className="text-xs font-medium mb-2"
                            style={{ color: 'var(--text-muted)' }}
                        >
                            {totalChanges} {totalChanges === 1 ? 'change' : 'changes'} to be committed
                        </div>

                        <div className="space-y-3 max-h-40 overflow-y-auto">
                            {groupedArtifacts.map(group => (
                                <div key={group.scope}>
                                    <div
                                        className="text-xs font-medium mb-1"
                                        style={{ color: 'var(--text-secondary)' }}
                                    >
                                        {group.label}
                                    </div>
                                    <div className="space-y-1">
                                        {group.items.map((item, idx) => (
                                            <div
                                                key={idx}
                                                className="flex items-center gap-2 text-xs"
                                            >
                                                <span
                                                    className="px-1.5 py-0.5 rounded"
                                                    style={{
                                                        background: 'var(--state-warning-bg, rgba(245, 158, 11, 0.2))',
                                                        color: 'var(--state-warning-text, #f59e0b)',
                                                    }}
                                                >
                                                    M
                                                </span>
                                                <span style={{ color: 'var(--text-primary)' }}>
                                                    {item.displayName}
                                                </span>
                                                <span style={{ color: 'var(--text-muted)' }}>
                                                    {item.kindLabel}
                                                </span>
                                                <span
                                                    className="text-[10px]"
                                                    style={{ color: 'var(--text-muted)' }}
                                                >
                                                    v{item.version}
                                                </span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            ))}
                        </div>

                        {/* View Changes button */}
                        <button
                            type="button"
                            onClick={() => setShowDiff(true)}
                            className="mt-3 text-xs hover:underline"
                            style={{ color: 'var(--action-primary)' }}
                        >
                            View detailed changes...
                        </button>
                    </div>
                )}

                <form onSubmit={handleSubmit}>
                    <div className="mb-4">
                        <label
                            className="block text-sm mb-2"
                            style={{ color: 'var(--text-muted)' }}
                        >
                            Commit Message
                        </label>
                        <textarea
                            value={message}
                            onChange={(e) => setMessage(e.target.value)}
                            placeholder="Describe your changes..."
                            className="w-full p-3 rounded text-sm resize-none"
                            style={{
                                background: 'var(--bg-input, var(--bg-canvas))',
                                border: '1px solid var(--border-panel)',
                                color: 'var(--text-primary)',
                                minHeight: '80px',
                            }}
                            autoFocus
                            disabled={loading}
                        />
                        <div
                            className="text-xs mt-1"
                            style={{ color: 'var(--text-muted)' }}
                        >
                            Keep it concise - describe the "why" not the "what"
                        </div>
                    </div>

                    <div className="flex justify-end gap-3">
                        <button
                            type="button"
                            onClick={onCancel}
                            disabled={loading}
                            className="px-4 py-2 rounded text-sm"
                            style={{
                                background: 'transparent',
                                border: '1px solid var(--border-panel)',
                                color: 'var(--text-muted)',
                            }}
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            disabled={!message.trim() || loading}
                            className="px-4 py-2 rounded text-sm font-medium"
                            style={{
                                background: message.trim() && !loading
                                    ? 'var(--action-success)'
                                    : 'var(--border-panel)',
                                color: message.trim() && !loading
                                    ? '#000'
                                    : 'var(--text-muted)',
                                cursor: message.trim() && !loading ? 'pointer' : 'not-allowed',
                            }}
                        >
                            {loading ? 'Committing...' : 'Commit'}
                        </button>
                    </div>
                </form>
            </div>

            {/* Diff View Modal */}
            {showDiff && workspaceId && (
                <DiffView
                    workspaceId={workspaceId}
                    onClose={() => setShowDiff(false)}
                />
            )}
        </div>
    );
}
