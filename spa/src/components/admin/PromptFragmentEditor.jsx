import React, { useState, useEffect, useCallback } from 'react';
import PromptTab from './PromptTab';
import { usePromptEditor } from '../../hooks/usePromptEditor';
import { adminApi } from '../../api/adminClient';
import yaml from 'js-yaml';

const KIND_LABELS = {
    role: 'Role',
    task: 'Task',
    qa: 'QA',
    pgc: 'PGC',
    questions: 'Questions',
    reflection: 'Reflection',
};

const KIND_COLORS = {
    role: 'var(--dot-purple)',
    task: 'var(--action-primary)',
    qa: '#10b981',
    pgc: '#8b5cf6',
    questions: '#f59e0b',
    reflection: '#ec4899',
};

const fieldStyle = {
    width: '100%',
    padding: '8px 12px',
    borderRadius: 6,
    fontSize: 13,
    background: 'var(--bg-input, var(--bg-canvas))',
    border: '1px solid var(--border-panel)',
    color: 'var(--text-primary)',
};

const labelStyle = {
    display: 'block',
    fontSize: 11,
    fontWeight: 600,
    color: 'var(--text-muted)',
    marginBottom: 4,
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
};

/**
 * Editor for prompt fragments (roles, tasks, QA, PGC prompts).
 *
 * Per WS-ADR-044-002:
 * - Two tabs: Metadata and Content
 * - Metadata: name, intent, tags[], kind (read-only badge)
 * - Content: CodeMirror editor with prompt text
 * - Auto-save with debounce
 */
export default function PromptFragmentEditor({
    workspaceId,
    fragment,
    onArtifactSave,
}) {
    const [activeTab, setActiveTab] = useState('content');
    const [metadata, setMetadata] = useState({ name: '', intent: '', tags: [] });
    const [metadataDirty, setMetadataDirty] = useState(false);
    const [metadataSaving, setMetadataSaving] = useState(false);
    const [tagInput, setTagInput] = useState('');

    // Parse fragment ID to get kind and name
    // fragment_id format: {kind}:{name} e.g., "role:technical_architect" or "task:project_discovery"
    const [fragmentKind, fragmentName] = fragment?.fragment_id?.split(':') || [null, null];

    // Build artifact IDs based on fragment type
    // Role fragments: fragment:role:{id}:{version}:content
    // DCW-derived fragments use doctype scope
    const contentArtifactId = fragment
        ? fragmentKind === 'role'
            ? `fragment:role:${fragmentName}:${fragment.version}:content`
            : `doctype:${fragment.source_doc_type}:${fragment.version}:${fragmentKind}_prompt`
        : null;

    const metadataArtifactId = fragment
        ? fragmentKind === 'role'
            ? `fragment:role:${fragmentName}:${fragment.version}:meta`
            : null  // DCW-derived fragments don't have separate meta yet
        : null;

    // Prompt editor hook for content
    const {
        content,
        loading,
        error,
        saving,
        isDirty,
        updateContent,
        lastSaveResult,
    } = usePromptEditor(workspaceId, contentArtifactId, {
        onSave: (result) => {
            onArtifactSave?.(contentArtifactId, result);
        },
    });

    // Load metadata from fragment prop
    useEffect(() => {
        if (fragment) {
            setMetadata({
                name: fragment.name || '',
                intent: fragment.intent || '',
                tags: fragment.tags || [],
            });
            setMetadataDirty(false);
        }
    }, [fragment?.fragment_id, fragment?.name, fragment?.intent, fragment?.tags]);

    // Update metadata field
    const updateMetadataField = useCallback((field, value) => {
        setMetadata(prev => ({ ...prev, [field]: value }));
        setMetadataDirty(true);
    }, []);

    // Save metadata (only for role fragments currently)
    const saveMetadata = useCallback(async () => {
        if (!workspaceId || !metadataArtifactId) return;

        setMetadataSaving(true);
        try {
            const yamlContent = yaml.dump({
                name: metadata.name || null,
                intent: metadata.intent || null,
                tags: metadata.tags.length > 0 ? metadata.tags : null,
            }, { lineWidth: -1 });

            await adminApi.writeArtifact(workspaceId, metadataArtifactId, yamlContent);
            setMetadataDirty(false);
            onArtifactSave?.(metadataArtifactId, { success: true });
        } catch (err) {
            console.error('Failed to save metadata:', err);
            alert(`Failed to save metadata: ${err.message}`);
        } finally {
            setMetadataSaving(false);
        }
    }, [workspaceId, metadataArtifactId, metadata, onArtifactSave]);

    // Auto-save metadata on blur if dirty
    const handleMetadataBlur = useCallback(() => {
        if (metadataDirty && metadataArtifactId) {
            saveMetadata();
        }
    }, [metadataDirty, metadataArtifactId, saveMetadata]);

    // Handle tag addition
    const handleAddTag = useCallback(() => {
        const tag = tagInput.trim().toLowerCase();
        if (tag && !metadata.tags.includes(tag)) {
            updateMetadataField('tags', [...metadata.tags, tag]);
            setTagInput('');
        }
    }, [tagInput, metadata.tags, updateMetadataField]);

    // Handle tag removal
    const handleRemoveTag = useCallback((tagToRemove) => {
        updateMetadataField('tags', metadata.tags.filter(t => t !== tagToRemove));
    }, [metadata.tags, updateMetadataField]);

    // Handle Enter key in tag input
    const handleTagKeyDown = useCallback((e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            handleAddTag();
        }
    }, [handleAddTag]);

    if (!fragment) {
        return (
            <div
                className="flex-1 flex items-center justify-center"
                style={{ background: 'var(--bg-canvas)' }}
            >
                <div
                    className="text-center p-8"
                    style={{ color: 'var(--text-muted)' }}
                >
                    <div className="text-lg mb-2">No Fragment Selected</div>
                    <div className="text-sm">
                        Select a prompt fragment from the browser to edit its content.
                    </div>
                </div>
            </div>
        );
    }

    const displayName = metadata.name || fragment.name || fragment.fragment_id;
    const kindLabel = KIND_LABELS[fragmentKind] || fragmentKind;
    const kindColor = KIND_COLORS[fragmentKind] || 'var(--text-muted)';

    const tabs = [
        { id: 'content', label: 'Content' },
        { id: 'metadata', label: 'Metadata' },
    ];

    // View-only mode when no workspace or DCW-derived without meta support
    const isViewOnly = !workspaceId;
    const canEditMetadata = metadataArtifactId && !isViewOnly;

    return (
        <div className="flex-1 flex flex-col h-full" style={{ background: 'var(--bg-canvas)' }}>
            {/* Header */}
            <div
                className="px-4 py-3 border-b"
                style={{ borderColor: 'var(--border-panel)', background: 'var(--bg-panel)' }}
            >
                <div className="flex items-center justify-between">
                    <div>
                        <h2
                            className="text-base font-semibold flex items-center gap-2"
                            style={{ color: 'var(--text-primary)' }}
                        >
                            {displayName}
                            <span
                                className="px-2 py-0.5 rounded text-[10px] font-medium uppercase"
                                style={{
                                    background: kindColor,
                                    color: '#fff',
                                }}
                            >
                                {kindLabel}
                            </span>
                        </h2>
                        <div
                            className="text-xs mt-0.5 flex items-center gap-2"
                            style={{ color: 'var(--text-muted)' }}
                        >
                            <span>v{fragment.version}</span>
                            {fragment.source_doc_type && (
                                <>
                                    <span>·</span>
                                    <span>from {fragment.source_doc_type}</span>
                                </>
                            )}
                            {isViewOnly && (
                                <>
                                    <span>·</span>
                                    <span
                                        className="px-1.5 py-0.5 rounded text-[10px]"
                                        style={{
                                            background: 'var(--bg-canvas)',
                                            border: '1px solid var(--border-panel)',
                                        }}
                                    >
                                        View Only
                                    </span>
                                </>
                            )}
                        </div>
                    </div>
                </div>
            </div>

            {/* Tab bar */}
            <div
                className="flex border-b"
                style={{ borderColor: 'var(--border-panel)', background: 'var(--bg-panel)' }}
            >
                {tabs.map(tab => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id)}
                        className="px-4 py-2 text-sm transition-colors"
                        style={{
                            color: activeTab === tab.id ? 'var(--text-primary)' : 'var(--text-muted)',
                            background: activeTab === tab.id ? 'var(--bg-canvas)' : 'transparent',
                            borderBottom: activeTab === tab.id ? '2px solid var(--action-primary)' : '2px solid transparent',
                        }}
                    >
                        {tab.label}
                        {tab.id === 'content' && isDirty && (
                            <span className="ml-1 text-[10px]" style={{ color: 'var(--action-primary)' }}>*</span>
                        )}
                        {tab.id === 'metadata' && metadataDirty && (
                            <span className="ml-1 text-[10px]" style={{ color: 'var(--action-primary)' }}>*</span>
                        )}
                    </button>
                ))}
            </div>

            {/* Content Tab */}
            {activeTab === 'content' && (
                <div className="flex-1 overflow-hidden">
                    <PromptTab
                        content={content}
                        onChange={updateContent}
                        loading={loading}
                        saving={saving}
                        isDirty={isDirty}
                        error={error}
                        placeholder="Enter prompt content..."
                        readOnly={isViewOnly}
                    />
                </div>
            )}

            {/* Metadata Tab */}
            {activeTab === 'metadata' && (
                <div className="flex-1 overflow-y-auto p-4">
                    <div className="max-w-xl space-y-4">
                        {/* Kind (read-only) */}
                        <div>
                            <label style={labelStyle}>Kind</label>
                            <div
                                className="px-3 py-2 rounded flex items-center gap-2"
                                style={{
                                    background: 'var(--bg-canvas)',
                                    border: '1px solid var(--border-panel)',
                                }}
                            >
                                <span
                                    style={{
                                        width: 8,
                                        height: 8,
                                        borderRadius: '50%',
                                        background: kindColor,
                                    }}
                                />
                                <span style={{ color: 'var(--text-primary)', fontSize: 13 }}>
                                    {kindLabel}
                                </span>
                            </div>
                            <div className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
                                Fragment kind determines how it's used in prompt assembly
                            </div>
                        </div>

                        {/* Name */}
                        <div>
                            <label style={labelStyle}>Name</label>
                            <input
                                type="text"
                                value={metadata.name}
                                onChange={e => updateMetadataField('name', e.target.value)}
                                onBlur={handleMetadataBlur}
                                placeholder="e.g., Technical Architect Role"
                                style={fieldStyle}
                                disabled={!canEditMetadata}
                            />
                            <div className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
                                Human-readable name for this fragment
                            </div>
                        </div>

                        {/* Intent */}
                        <div>
                            <label style={labelStyle}>Intent</label>
                            <textarea
                                value={metadata.intent}
                                onChange={e => updateMetadataField('intent', e.target.value)}
                                onBlur={handleMetadataBlur}
                                placeholder="Describe the purpose and intent of this prompt fragment..."
                                rows={4}
                                style={{ ...fieldStyle, resize: 'vertical' }}
                                disabled={!canEditMetadata}
                            />
                            <div className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
                                Description of what this fragment is meant to accomplish
                            </div>
                        </div>

                        {/* Tags */}
                        <div>
                            <label style={labelStyle}>Tags</label>
                            <div className="flex flex-wrap gap-1.5 mb-2">
                                {metadata.tags.map(tag => (
                                    <span
                                        key={tag}
                                        className="px-2 py-0.5 rounded text-xs flex items-center gap-1"
                                        style={{
                                            background: 'var(--bg-panel)',
                                            border: '1px solid var(--border-panel)',
                                            color: 'var(--text-secondary)',
                                        }}
                                    >
                                        {tag}
                                        {canEditMetadata && (
                                            <button
                                                onClick={() => handleRemoveTag(tag)}
                                                className="ml-0.5 hover:opacity-70"
                                                style={{ color: 'var(--text-muted)' }}
                                            >
                                                ×
                                            </button>
                                        )}
                                    </span>
                                ))}
                            </div>
                            {canEditMetadata && (
                                <div className="flex gap-2">
                                    <input
                                        type="text"
                                        value={tagInput}
                                        onChange={e => setTagInput(e.target.value)}
                                        onKeyDown={handleTagKeyDown}
                                        placeholder="Add tag..."
                                        style={{ ...fieldStyle, flex: 1 }}
                                    />
                                    <button
                                        onClick={handleAddTag}
                                        disabled={!tagInput.trim()}
                                        className="px-3 py-2 rounded text-sm"
                                        style={{
                                            background: 'var(--action-primary)',
                                            color: '#000',
                                            opacity: tagInput.trim() ? 1 : 0.5,
                                            cursor: tagInput.trim() ? 'pointer' : 'not-allowed',
                                        }}
                                    >
                                        Add
                                    </button>
                                </div>
                            )}
                            <div className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
                                Free-form tags for classification and filtering
                            </div>
                        </div>

                        {/* Source info for DCW-derived fragments */}
                        {fragment.source_doc_type && (
                            <div>
                                <label style={labelStyle}>Source</label>
                                <div
                                    className="px-3 py-2 rounded text-sm"
                                    style={{
                                        background: 'var(--bg-canvas)',
                                        border: '1px solid var(--border-panel)',
                                        color: 'var(--text-secondary)',
                                    }}
                                >
                                    Derived from document type: <strong>{fragment.source_doc_type}</strong>
                                </div>
                                <div className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
                                    This fragment is defined within a DCW package. Edit it from the document type's tab bar.
                                </div>
                            </div>
                        )}

                        {/* Save indicator */}
                        {metadataSaving && (
                            <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
                                Saving...
                            </div>
                        )}

                        {!canEditMetadata && !fragment.source_doc_type && (
                            <div
                                className="text-xs p-2 rounded"
                                style={{
                                    background: 'rgba(251, 191, 36, 0.1)',
                                    color: 'var(--text-muted)',
                                }}
                            >
                                Metadata editing requires an active workspace.
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Validation result from last save */}
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
