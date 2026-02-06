import React, { useState, useEffect, useCallback, useMemo } from 'react';
import PromptTab from './PromptTab';
import { usePromptEditor } from '../../hooks/usePromptEditor';
import { adminApi } from '../../api/adminClient';
import yaml from 'js-yaml';

const PURPOSE_OPTIONS = [
    { value: '', label: '-- Select purpose --' },
    { value: 'document', label: 'Document' },
    { value: 'qa', label: 'QA' },
    { value: 'pgc', label: 'PGC' },
    { value: 'general', label: 'General' },
];

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
 * Editor for shared templates.
 * Allows direct editing of template content and metadata.
 */
export default function TemplateEditor({
    workspaceId,
    template,
    onArtifactSave,
}) {
    const [activeTab, setActiveTab] = useState('metadata');
    const [metadata, setMetadata] = useState({ name: '', purpose: '', use_case: '' });
    const [metadataDirty, setMetadataDirty] = useState(false);
    const [metadataSaving, setMetadataSaving] = useState(false);

    // Build artifact IDs
    const templateArtifactId = template
        ? `template:${template.template_id}:${template.active_version}:template`
        : null;
    const metadataArtifactId = template
        ? `template:${template.template_id}:${template.active_version}:meta`
        : null;

    // Prompt editor hook for template content
    const {
        content,
        loading,
        error,
        saving,
        isDirty,
        updateContent,
        lastSaveResult,
    } = usePromptEditor(workspaceId, templateArtifactId, {
        onSave: (result) => {
            onArtifactSave?.(templateArtifactId, result);
        },
    });

    // Load metadata from template prop
    useEffect(() => {
        if (template) {
            setMetadata({
                name: template.name || '',
                purpose: template.purpose || '',
                use_case: template.use_case || '',
            });
            setMetadataDirty(false);
        }
    }, [template?.template_id, template?.name, template?.purpose, template?.use_case]);

    // Update metadata field
    const updateMetadataField = useCallback((field, value) => {
        setMetadata(prev => ({ ...prev, [field]: value }));
        setMetadataDirty(true);
    }, []);

    // Save metadata
    const saveMetadata = useCallback(async () => {
        if (!workspaceId || !metadataArtifactId) return;

        setMetadataSaving(true);
        try {
            // Convert metadata to YAML
            const yamlContent = yaml.dump({
                name: metadata.name || null,
                purpose: metadata.purpose || null,
                use_case: metadata.use_case || null,
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
        if (metadataDirty) {
            saveMetadata();
        }
    }, [metadataDirty, saveMetadata]);

    if (!template) {
        return (
            <div
                className="flex-1 flex items-center justify-center"
                style={{ background: 'var(--bg-canvas)' }}
            >
                <div
                    className="text-center p-8"
                    style={{ color: 'var(--text-muted)' }}
                >
                    <div className="text-lg mb-2">No Template Selected</div>
                    <div className="text-sm">
                        Select a template from the browser to edit its content.
                    </div>
                </div>
            </div>
        );
    }

    const displayName = metadata.name || template.template_id
        .replace(/_/g, ' ')
        .replace(/\b\w/g, c => c.toUpperCase());

    const tabs = [
        { id: 'metadata', label: 'Metadata' },
        { id: 'template', label: 'Template' },
    ];

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
                            className="text-base font-semibold"
                            style={{ color: 'var(--text-primary)' }}
                        >
                            {displayName}
                        </h2>
                        <div
                            className="text-xs mt-0.5 flex items-center gap-2"
                            style={{ color: 'var(--text-muted)' }}
                        >
                            <span>v{template.active_version}</span>
                            <span>·</span>
                            <span>Shared Template</span>
                            {metadata.purpose && (
                                <>
                                    <span>·</span>
                                    <span
                                        className="px-1.5 py-0.5 rounded text-[10px] font-medium uppercase"
                                        style={{
                                            background: 'var(--action-primary)',
                                            color: '#000',
                                        }}
                                    >
                                        {metadata.purpose}
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
                        {tab.id === 'metadata' && metadataDirty && (
                            <span className="ml-1 text-[10px]" style={{ color: 'var(--action-primary)' }}>*</span>
                        )}
                        {tab.id === 'template' && isDirty && (
                            <span className="ml-1 text-[10px]" style={{ color: 'var(--action-primary)' }}>*</span>
                        )}
                    </button>
                ))}
            </div>

            {/* Metadata Tab */}
            {activeTab === 'metadata' && (
                <div className="flex-1 overflow-y-auto p-4">
                    <div className="max-w-xl space-y-4">
                        {/* Name */}
                        <div>
                            <label style={labelStyle}>Template Name</label>
                            <input
                                type="text"
                                value={metadata.name}
                                onChange={e => updateMetadataField('name', e.target.value)}
                                onBlur={handleMetadataBlur}
                                placeholder="e.g., Document Generator"
                                style={fieldStyle}
                            />
                            <div className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
                                Human-readable name for this template
                            </div>
                        </div>

                        {/* Purpose */}
                        <div>
                            <label style={labelStyle}>Template Purpose</label>
                            <select
                                value={metadata.purpose}
                                onChange={e => {
                                    updateMetadataField('purpose', e.target.value);
                                    // Save immediately on select change
                                    setTimeout(() => saveMetadata(), 0);
                                }}
                                style={fieldStyle}
                            >
                                {PURPOSE_OPTIONS.map(opt => (
                                    <option key={opt.value} value={opt.value}>
                                        {opt.label}
                                    </option>
                                ))}
                            </select>
                            <div className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
                                What type of interaction this template supports
                            </div>
                        </div>

                        {/* Use Case */}
                        <div>
                            <label style={labelStyle}>Use Case</label>
                            <textarea
                                value={metadata.use_case}
                                onChange={e => updateMetadataField('use_case', e.target.value)}
                                onBlur={handleMetadataBlur}
                                placeholder="Describe when and how this template should be used..."
                                rows={4}
                                style={{ ...fieldStyle, resize: 'vertical' }}
                            />
                            <div className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
                                Description of when and how this template should be used
                            </div>
                        </div>

                        {/* Save indicator */}
                        {metadataSaving && (
                            <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
                                Saving...
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Template Tab */}
            {activeTab === 'template' && (
                <>
                    {/* File path display */}
                    <div
                        className="flex items-center justify-end px-3 py-2 border-b"
                        style={{ borderColor: 'var(--border-panel)', background: 'var(--bg-panel-alt, var(--bg-panel))' }}
                    >
                        <span
                            className="text-xs font-mono truncate"
                            style={{ color: 'var(--text-muted)' }}
                        >
                            combine-config/prompts/templates/{template.template_id}/releases/{template.active_version}/template.txt
                        </span>
                    </div>

                    {/* Content area */}
                    <div className="flex-1 overflow-hidden">
                        <PromptTab
                            content={content}
                            onChange={updateContent}
                            loading={loading}
                            saving={saving}
                            isDirty={isDirty}
                            error={error}
                            placeholder="Enter template content..."
                        />
                    </div>
                </>
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
