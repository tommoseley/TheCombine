import React, { useState, useEffect } from 'react';
import { adminApi } from '../../api/adminClient';

/**
 * Compute a simple line-by-line diff.
 * Returns an array of { type: 'same'|'added'|'removed', line, lineNum }
 */
function computeLineDiff(oldContent, newContent) {
    const oldLines = (oldContent || '').split('\n');
    const newLines = (newContent || '').split('\n');
    const result = [];

    // Simple approach: use longest common subsequence concept
    // For a quick implementation, we'll do a basic line-by-line comparison
    let oldIdx = 0;
    let newIdx = 0;

    while (oldIdx < oldLines.length || newIdx < newLines.length) {
        if (oldIdx >= oldLines.length) {
            // Rest are additions
            result.push({ type: 'added', line: newLines[newIdx], lineNum: newIdx + 1 });
            newIdx++;
        } else if (newIdx >= newLines.length) {
            // Rest are deletions
            result.push({ type: 'removed', line: oldLines[oldIdx], lineNum: oldIdx + 1 });
            oldIdx++;
        } else if (oldLines[oldIdx] === newLines[newIdx]) {
            // Same line
            result.push({ type: 'same', line: oldLines[oldIdx], oldLineNum: oldIdx + 1, newLineNum: newIdx + 1 });
            oldIdx++;
            newIdx++;
        } else {
            // Look ahead to see if we can find a match
            let foundOld = newLines.slice(newIdx, newIdx + 5).indexOf(oldLines[oldIdx]);
            let foundNew = oldLines.slice(oldIdx, oldIdx + 5).indexOf(newLines[newIdx]);

            if (foundOld !== -1 && (foundNew === -1 || foundOld <= foundNew)) {
                // Additions before the match
                for (let i = 0; i < foundOld; i++) {
                    result.push({ type: 'added', line: newLines[newIdx + i], lineNum: newIdx + i + 1 });
                }
                newIdx += foundOld;
            } else if (foundNew !== -1) {
                // Deletions before the match
                for (let i = 0; i < foundNew; i++) {
                    result.push({ type: 'removed', line: oldLines[oldIdx + i], lineNum: oldIdx + i + 1 });
                }
                oldIdx += foundNew;
            } else {
                // No match found nearby, treat as change
                result.push({ type: 'removed', line: oldLines[oldIdx], lineNum: oldIdx + 1 });
                result.push({ type: 'added', line: newLines[newIdx], lineNum: newIdx + 1 });
                oldIdx++;
                newIdx++;
            }
        }
    }

    return result;
}

/**
 * Single artifact diff display.
 */
function ArtifactDiff({ diff }) {
    const [expanded, setExpanded] = useState(true);

    const lines = computeLineDiff(diff.old_content, diff.new_content);

    const statusLabels = {
        M: 'Modified',
        A: 'Added',
        D: 'Deleted',
    };

    const statusColors = {
        M: { bg: 'rgba(245, 158, 11, 0.2)', color: '#f59e0b' },
        A: { bg: 'rgba(34, 197, 94, 0.2)', color: '#22c55e' },
        D: { bg: 'rgba(239, 68, 68, 0.2)', color: '#ef4444' },
    };

    return (
        <div
            className="border rounded mb-3"
            style={{ borderColor: 'var(--border-panel)' }}
        >
            {/* Header */}
            <div
                className="flex items-center justify-between px-3 py-2 cursor-pointer"
                style={{ background: 'var(--bg-panel)' }}
                onClick={() => setExpanded(!expanded)}
            >
                <div className="flex items-center gap-2">
                    <span
                        className="px-1.5 py-0.5 rounded text-xs font-medium"
                        style={statusColors[diff.status] || statusColors.M}
                    >
                        {diff.status}
                    </span>
                    <span
                        className="text-sm font-mono truncate"
                        style={{ color: 'var(--text-primary)' }}
                    >
                        {diff.file_path}
                    </span>
                </div>
                <div className="flex items-center gap-3">
                    <span className="text-xs" style={{ color: 'var(--action-success)' }}>
                        +{diff.additions}
                    </span>
                    <span className="text-xs" style={{ color: 'var(--state-error-text)' }}>
                        -{diff.deletions}
                    </span>
                    <span
                        className="text-xs"
                        style={{ color: 'var(--text-muted)' }}
                    >
                        {expanded ? '−' : '+'}
                    </span>
                </div>
            </div>

            {/* Diff content */}
            {expanded && (
                <div
                    className="overflow-x-auto"
                    style={{ background: 'var(--bg-canvas)' }}
                >
                    <pre className="text-xs font-mono m-0 p-0">
                        {lines.map((item, idx) => (
                            <div
                                key={idx}
                                className="flex"
                                style={{
                                    background: item.type === 'added'
                                        ? 'rgba(34, 197, 94, 0.1)'
                                        : item.type === 'removed'
                                            ? 'rgba(239, 68, 68, 0.1)'
                                            : 'transparent',
                                    borderLeft: item.type === 'added'
                                        ? '3px solid #22c55e'
                                        : item.type === 'removed'
                                            ? '3px solid #ef4444'
                                            : '3px solid transparent',
                                }}
                            >
                                <span
                                    className="select-none px-2 text-right"
                                    style={{
                                        color: 'var(--text-muted)',
                                        minWidth: '40px',
                                        background: 'rgba(0,0,0,0.1)',
                                    }}
                                >
                                    {item.type === 'same' ? item.oldLineNum : item.lineNum || ''}
                                </span>
                                <span
                                    className="select-none px-1"
                                    style={{
                                        color: item.type === 'added'
                                            ? '#22c55e'
                                            : item.type === 'removed'
                                                ? '#ef4444'
                                                : 'var(--text-muted)',
                                        minWidth: '16px',
                                    }}
                                >
                                    {item.type === 'added' ? '+' : item.type === 'removed' ? '-' : ' '}
                                </span>
                                <span
                                    className="flex-1 px-2 whitespace-pre"
                                    style={{ color: 'var(--text-primary)' }}
                                >
                                    {item.line}
                                </span>
                            </div>
                        ))}
                    </pre>
                </div>
            )}
        </div>
    );
}

/**
 * Modal dialog showing diff for workspace changes.
 */
export default function DiffView({
    workspaceId,
    artifactId = null,
    onClose,
}) {
    const [diffs, setDiffs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (!workspaceId) return;

        setLoading(true);
        setError(null);

        adminApi.getDiff(workspaceId, artifactId)
            .then(response => {
                setDiffs(response.diffs || []);
            })
            .catch(err => {
                setError(err.message);
            })
            .finally(() => {
                setLoading(false);
            });
    }, [workspaceId, artifactId]);

    // Handle Escape key
    const handleKeyDown = (e) => {
        if (e.key === 'Escape') {
            onClose?.();
        }
    };

    return (
        <div
            className="fixed inset-0 flex items-center justify-center z-50"
            style={{ background: 'rgba(0, 0, 0, 0.7)' }}
            onClick={(e) => e.target === e.currentTarget && onClose?.()}
            onKeyDown={handleKeyDown}
            tabIndex={0}
        >
            <div
                className="w-full max-w-4xl max-h-[80vh] flex flex-col rounded-lg shadow-xl"
                style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-panel)' }}
            >
                {/* Header */}
                <div
                    className="flex items-center justify-between px-4 py-3 border-b"
                    style={{ borderColor: 'var(--border-panel)' }}
                >
                    <h2
                        className="text-lg font-semibold"
                        style={{ color: 'var(--text-primary)' }}
                    >
                        {artifactId ? 'Artifact Changes' : 'All Changes'}
                    </h2>
                    <button
                        onClick={onClose}
                        className="p-1 rounded hover:opacity-80"
                        style={{ color: 'var(--text-muted)' }}
                    >
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M18 6L6 18M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-4">
                    {loading ? (
                        <div
                            className="text-center py-8"
                            style={{ color: 'var(--text-muted)' }}
                        >
                            Loading diff...
                        </div>
                    ) : error ? (
                        <div
                            className="text-center py-8"
                            style={{ color: 'var(--state-error-text)' }}
                        >
                            Error: {error}
                        </div>
                    ) : diffs.length === 0 ? (
                        <div
                            className="text-center py-8"
                            style={{ color: 'var(--text-muted)' }}
                        >
                            No changes to display
                        </div>
                    ) : (
                        diffs.map((diff, idx) => (
                            <ArtifactDiff key={diff.artifact_id || idx} diff={diff} />
                        ))
                    )}
                </div>

                {/* Footer */}
                <div
                    className="flex justify-end px-4 py-3 border-t"
                    style={{ borderColor: 'var(--border-panel)' }}
                >
                    <button
                        onClick={onClose}
                        className="px-4 py-2 rounded text-sm"
                        style={{
                            background: 'transparent',
                            border: '1px solid var(--border-panel)',
                            color: 'var(--text-muted)',
                        }}
                    >
                        Close
                    </button>
                </div>
            </div>
        </div>
    );
}
