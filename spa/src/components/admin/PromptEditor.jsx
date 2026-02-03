import React, { useState, useMemo } from 'react';
import PromptTab from './PromptTab';
import ResolvedPreview from './ResolvedPreview';
import { usePromptEditor } from '../../hooks/usePromptEditor';

/**
 * Center panel - tabbed editor for document type prompts.
 * Shows tabs for Task/QA/PGC artifacts, each with Source/Resolved sub-tabs.
 */
export default function PromptEditor({
    workspaceId,
    docType,
    onArtifactSave,
}) {
    // Which artifact type tab is selected (task_prompt, qa_prompt, pgc_context)
    const [selectedKind, setSelectedKind] = useState('task_prompt');
    // View mode: 'source' (editable) or 'resolved' (read-only)
    const [viewMode, setViewMode] = useState('source');

    // Build artifact ID from doc type and selected kind
    const artifactId = useMemo(() => {
        if (!docType) return null;
        return `doctype:${docType.doc_type_id}:${docType.active_version}:${selectedKind}`;
    }, [docType, selectedKind]);

    // Prompt editor hook for the selected artifact
    const {
        content,
        loading,
        error,
        saving,
        isDirty,
        updateContent,
        lastSaveResult,
    } = usePromptEditor(workspaceId, artifactId, {
        onSave: (result) => {
            onArtifactSave?.(artifactId, result);
        },
    });

    // All possible prompt kinds
    const allPromptKinds = [
        { id: 'task_prompt', label: 'Task Prompt' },
        { id: 'qa_prompt', label: 'QA Prompt' },
        { id: 'reflection_prompt', label: 'Reflection' },
        { id: 'pgc_context', label: 'PGC Context' },
    ];

    // Filter to only show prompt kinds that exist for this document type
    // The docType.artifacts object maps artifact kinds to their status/path
    const promptKinds = useMemo(() => {
        if (!docType?.artifacts) {
            // If no artifacts info, show all (will show error when loading)
            return allPromptKinds;
        }
        return allPromptKinds.filter(kind => {
            // Show tab if artifact exists (has a non-null value)
            return docType.artifacts[kind.id] != null;
        });
    }, [docType?.artifacts]);

    // Reset to first available kind if current selection is not available
    React.useEffect(() => {
        if (promptKinds.length > 0 && !promptKinds.find(k => k.id === selectedKind)) {
            setSelectedKind(promptKinds[0].id);
        }
    }, [promptKinds, selectedKind]);

    if (!docType) {
        return (
            <div
                className="flex-1 flex items-center justify-center"
                style={{ background: 'var(--bg-canvas)' }}
            >
                <div
                    className="text-center p-8"
                    style={{ color: 'var(--text-muted)' }}
                >
                    <div className="text-lg mb-2">No Document Type Selected</div>
                    <div className="text-sm">
                        Select a document type from the browser to edit its prompts.
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="flex-1 flex flex-col h-full" style={{ background: 'var(--bg-canvas)' }}>
            {/* Header with doc type info */}
            <div
                className="px-4 py-3 border-b"
                style={{ borderColor: 'var(--border-panel)', background: 'var(--bg-panel)' }}
            >
                <div className="flex items-center justify-between">
                    <div>
                        <h2
                            className="text-base font-semibold"
                            style={{ color: 'var(--text-primary)' }}
                        >
                            {docType.display_name}
                        </h2>
                        <div
                            className="text-xs mt-0.5"
                            style={{ color: 'var(--text-muted)' }}
                        >
                            v{docType.active_version}
                            {docType.authority_level && ` - ${docType.authority_level}`}
                        </div>
                    </div>
                </div>
            </div>

            {/* Artifact kind tabs */}
            <div
                className="flex border-b"
                style={{ borderColor: 'var(--border-panel)', background: 'var(--bg-panel)' }}
            >
                {promptKinds.map((kind) => (
                    <button
                        key={kind.id}
                        onClick={() => {
                            setSelectedKind(kind.id);
                            setViewMode('source'); // Reset to source when switching
                        }}
                        className="px-4 py-2 text-sm transition-colors"
                        style={{
                            color: selectedKind === kind.id
                                ? 'var(--text-primary)'
                                : 'var(--text-muted)',
                            background: selectedKind === kind.id
                                ? 'var(--bg-canvas)'
                                : 'transparent',
                            borderBottom: selectedKind === kind.id
                                ? '2px solid var(--action-primary)'
                                : '2px solid transparent',
                        }}
                    >
                        {kind.label}
                    </button>
                ))}
            </div>

            {/* View mode tabs (Source / Resolved) */}
            <div
                className="flex gap-1 px-3 py-2 border-b"
                style={{ borderColor: 'var(--border-panel)', background: 'var(--bg-panel-alt, var(--bg-panel))' }}
            >
                <button
                    onClick={() => setViewMode('source')}
                    className="px-3 py-1 text-xs rounded transition-colors"
                    style={{
                        background: viewMode === 'source'
                            ? 'var(--bg-selected)'
                            : 'transparent',
                        color: viewMode === 'source'
                            ? 'var(--text-primary)'
                            : 'var(--text-muted)',
                    }}
                >
                    Source
                </button>
                <button
                    onClick={() => setViewMode('resolved')}
                    className="px-3 py-1 text-xs rounded transition-colors"
                    style={{
                        background: viewMode === 'resolved'
                            ? 'var(--bg-selected)'
                            : 'transparent',
                        color: viewMode === 'resolved'
                            ? 'var(--text-primary)'
                            : 'var(--text-muted)',
                    }}
                >
                    Resolved
                </button>
            </div>

            {/* Content area */}
            <div className="flex-1 overflow-hidden">
                {viewMode === 'source' ? (
                    <PromptTab
                        content={content}
                        onChange={updateContent}
                        loading={loading}
                        saving={saving}
                        isDirty={isDirty}
                        error={error}
                        placeholder={`Enter ${promptKinds.find(k => k.id === selectedKind)?.label || 'prompt'} content...`}
                    />
                ) : (
                    <ResolvedPreview
                        workspaceId={workspaceId}
                        artifactId={artifactId}
                    />
                )}
            </div>

            {/* Validation result from last save (compact) */}
            {lastSaveResult?.tier1 && !lastSaveResult.tier1.passed && (
                <div
                    className="px-4 py-2 border-t"
                    style={{
                        borderColor: 'var(--border-panel)',
                        background: 'rgba(239, 68, 68, 0.1)',
                    }}
                >
                    <div
                        className="text-xs"
                        style={{ color: 'var(--state-error-text)' }}
                    >
                        Validation issues found - see status panel for details
                    </div>
                </div>
            )}
        </div>
    );
}
