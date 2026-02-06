import React, { useState, useEffect, useCallback } from 'react';
import PromptTab from './PromptTab';
import { usePromptEditor } from '../../hooks/usePromptEditor';

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
 * Editor for standalone schemas.
 * Allows direct editing of JSON schema content.
 */
export default function SchemaEditor({
    workspaceId,
    schema,
    onArtifactSave,
}) {
    const [activeTab, setActiveTab] = useState('content');

    // Build artifact ID for schema content
    // Format: schema:{schema_id}:{version}:schema
    const schemaArtifactId = schema
        ? `schema:${schema.schema_id}:${schema.active_version || schema.version}:schema`
        : null;

    // Prompt editor hook for schema content
    const {
        content,
        loading,
        error,
        saving,
        isDirty,
        updateContent,
        lastSaveResult,
    } = usePromptEditor(workspaceId, schemaArtifactId, {
        onSave: (result) => {
            onArtifactSave?.(schemaArtifactId, result);
        },
    });

    if (!schema) {
        return (
            <div
                className="flex-1 flex items-center justify-center"
                style={{ background: 'var(--bg-canvas)' }}
            >
                <div
                    className="text-center p-8"
                    style={{ color: 'var(--text-muted)' }}
                >
                    <div className="text-lg mb-2">No Schema Selected</div>
                    <div className="text-sm">
                        Select a schema from the browser to edit its content.
                    </div>
                </div>
            </div>
        );
    }

    const displayName = schema.title || schema.schema_id?.replace(/_/g, ' ') || 'Schema';
    const version = schema.active_version || schema.version || '1.0.0';

    const tabs = [
        { id: 'content', label: 'Schema' },
        { id: 'info', label: 'Info' },
    ];

    // View-only mode when no workspace
    const isViewOnly = !workspaceId;

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
                                    background: '#8b5cf6',
                                    color: '#fff',
                                }}
                            >
                                Schema
                            </span>
                        </h2>
                        <div
                            className="text-xs mt-0.5 flex items-center gap-2"
                            style={{ color: 'var(--text-muted)' }}
                        >
                            <span>v{version}</span>
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
                    </button>
                ))}
            </div>

            {/* Content Tab - JSON Schema Editor */}
            {activeTab === 'content' && (
                <div className="flex-1 overflow-hidden">
                    <PromptTab
                        content={content}
                        onChange={updateContent}
                        loading={loading}
                        saving={saving}
                        isDirty={isDirty}
                        error={error}
                        placeholder="Enter JSON schema..."
                        readOnly={isViewOnly}
                        isJson={true}
                    />
                </div>
            )}

            {/* Info Tab */}
            {activeTab === 'info' && (
                <div className="flex-1 overflow-y-auto p-4">
                    <div className="max-w-xl space-y-4">
                        {/* Schema ID (read-only) */}
                        <div>
                            <label style={labelStyle}>Schema ID</label>
                            <div
                                className="px-3 py-2 rounded"
                                style={{
                                    background: 'var(--bg-canvas)',
                                    border: '1px solid var(--border-panel)',
                                    color: 'var(--text-primary)',
                                    fontSize: 13,
                                }}
                            >
                                {schema.schema_id}
                            </div>
                        </div>

                        {/* Version (read-only) */}
                        <div>
                            <label style={labelStyle}>Version</label>
                            <div
                                className="px-3 py-2 rounded"
                                style={{
                                    background: 'var(--bg-canvas)',
                                    border: '1px solid var(--border-panel)',
                                    color: 'var(--text-primary)',
                                    fontSize: 13,
                                }}
                            >
                                {version}
                            </div>
                        </div>

                        {/* Title */}
                        <div>
                            <label style={labelStyle}>Title (from JSON)</label>
                            <div
                                className="px-3 py-2 rounded"
                                style={{
                                    background: 'var(--bg-canvas)',
                                    border: '1px solid var(--border-panel)',
                                    color: 'var(--text-primary)',
                                    fontSize: 13,
                                }}
                            >
                                {schema.title || '-'}
                            </div>
                            <div
                                className="text-[10px] mt-1"
                                style={{ color: 'var(--text-muted)' }}
                            >
                                Edit in Schema tab via the "title" property
                            </div>
                        </div>

                        {/* File path hint */}
                        <div>
                            <label style={labelStyle}>File Path</label>
                            <div
                                className="px-3 py-2 rounded font-mono text-xs"
                                style={{
                                    background: 'var(--bg-canvas)',
                                    border: '1px solid var(--border-panel)',
                                    color: 'var(--text-muted)',
                                }}
                            >
                                combine-config/schemas/{schema.schema_id}/releases/{version}/schema.json
                            </div>
                        </div>

                        {/* Artifact ID hint */}
                        <div>
                            <label style={labelStyle}>Artifact ID</label>
                            <div
                                className="px-3 py-2 rounded font-mono text-xs"
                                style={{
                                    background: 'var(--bg-canvas)',
                                    border: '1px solid var(--border-panel)',
                                    color: 'var(--text-muted)',
                                }}
                            >
                                schema:{schema.schema_id}:{version}
                            </div>
                        </div>
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
