import React, { useState, useMemo, useEffect } from 'react';
import PromptTab from './PromptTab';
import ResolvedPreview from './ResolvedPreview';
import PackageEditor from './PackageEditor';
import WorkflowEditorContent from './workflow/WorkflowEditorContent';
import TabDropdown from './TabDropdown';
import { usePromptEditor } from '../../hooks/usePromptEditor';
import { adminApi } from '../../api/adminClient';

/**
 * Static tab button for the grouped tab bar (Package, Workflow, Schema).
 */
function StaticTab({ label, isSelected, onClick }) {
    return (
        <button
            onClick={onClick}
            className="px-4 py-2 text-sm font-medium transition-colors"
            style={{
                color: isSelected
                    ? 'var(--text-primary)'
                    : 'var(--text-muted)',
                background: isSelected
                    ? 'var(--bg-selected, rgba(255,255,255,0.1))'
                    : 'transparent',
                borderBottom: isSelected
                    ? '2px solid var(--action-primary)'
                    : '2px solid transparent',
                marginBottom: '-1px',
            }}
        >
            {label}
        </button>
    );
}

/**
 * Center panel - tabbed editor for document type prompts.
 * Shows grouped tabs: Package, Workflow, Generation, QA, PGC, Schema.
 */
export default function PromptEditor({
    workspaceId,
    docType,
    loading: detailsLoading = false,
    roles = [],
    onArtifactSave,
    initialTab = null,
    docTypeSource = null,
}) {
    // Which artifact type tab is selected
    const [selectedKind, setSelectedKind] = useState(initialTab || 'task_prompt');
    // When initialTab prop changes, switch to that tab
    useEffect(() => {
        if (initialTab) {
            setSelectedKind(initialTab);
        }
    }, [initialTab]);
    // View mode: 'source' (editable) or 'resolved' (read-only)
    const [viewMode, setViewMode] = useState('source');
    // Role prompt content (loaded separately for view-only display)
    const [roleContent, setRoleContent] = useState(null);
    const [roleLoading, setRoleLoading] = useState(false);
    const [roleError, setRoleError] = useState(null);

    // Template content (loaded separately for view-only display)
    const [templateContent, setTemplateContent] = useState(null);
    const [templateLoading, setTemplateLoading] = useState(false);
    const [templateError, setTemplateError] = useState(null);

    // QA Template content (loaded separately for view-only display)
    const [qaTemplateContent, setQaTemplateContent] = useState(null);
    const [qaTemplateLoading, setQaTemplateLoading] = useState(false);
    const [qaTemplateError, setQaTemplateError] = useState(null);

    // PGC Template content (loaded separately for view-only display)
    const [pgcTemplateContent, setPgcTemplateContent] = useState(null);
    const [pgcTemplateLoading, setPgcTemplateLoading] = useState(false);
    const [pgcTemplateError, setPgcTemplateError] = useState(null);

    // Parse role reference from docType.role_prompt_ref
    // Format: prompt:role:{role_id}:{version}
    const roleInfo = useMemo(() => {
        if (!docType?.role_prompt_ref) return null;
        const parts = docType.role_prompt_ref.split(':');
        if (parts.length !== 4 || parts[0] !== 'prompt' || parts[1] !== 'role') return null;
        return { roleId: parts[2], version: parts[3] };
    }, [docType?.role_prompt_ref]);

    // Parse template reference from docType.template_ref
    // Format: prompt:template:{template_id}:{version}
    const templateInfo = useMemo(() => {
        if (!docType?.template_ref) return null;
        const parts = docType.template_ref.split(':');
        if (parts.length !== 4 || parts[0] !== 'prompt' || parts[1] !== 'template') return null;
        return { templateId: parts[2], version: parts[3] };
    }, [docType?.template_ref]);

    // Parse QA template reference from docType.qa_template_ref
    const qaTemplateInfo = useMemo(() => {
        if (!docType?.qa_template_ref) return null;
        const parts = docType.qa_template_ref.split(':');
        if (parts.length !== 4 || parts[0] !== 'prompt' || parts[1] !== 'template') return null;
        return { templateId: parts[2], version: parts[3] };
    }, [docType?.qa_template_ref]);

    // Parse PGC template reference from docType.pgc_template_ref
    const pgcTemplateInfo = useMemo(() => {
        if (!docType?.pgc_template_ref) return null;
        const parts = docType.pgc_template_ref.split(':');
        if (parts.length !== 4 || parts[0] !== 'prompt' || parts[1] !== 'template') return null;
        return { templateId: parts[2], version: parts[3] };
    }, [docType?.pgc_template_ref]);

    // Fetch role content when docType changes and has a role reference
    useEffect(() => {
        if (!roleInfo) {
            setRoleContent(null);
            return;
        }

        setRoleLoading(true);
        setRoleError(null);

        adminApi.getRole(roleInfo.roleId, roleInfo.version)
            .then(data => {
                setRoleContent(data.content);
            })
            .catch(err => {
                console.error('Failed to load role:', err);
                setRoleError(err.message);
            })
            .finally(() => {
                setRoleLoading(false);
            });
    }, [roleInfo]);

    // Fetch template content when docType changes and has a template reference
    useEffect(() => {
        if (!templateInfo) {
            setTemplateContent(null);
            return;
        }

        setTemplateLoading(true);
        setTemplateError(null);

        adminApi.getTemplate(templateInfo.templateId, templateInfo.version)
            .then(data => {
                setTemplateContent(data.content);
            })
            .catch(err => {
                console.error('Failed to load template:', err);
                setTemplateError(err.message);
            })
            .finally(() => {
                setTemplateLoading(false);
            });
    }, [templateInfo]);

    // Fetch QA template content when docType changes and has a QA template reference
    useEffect(() => {
        if (!qaTemplateInfo) {
            setQaTemplateContent(null);
            return;
        }

        setQaTemplateLoading(true);
        setQaTemplateError(null);

        adminApi.getTemplate(qaTemplateInfo.templateId, qaTemplateInfo.version)
            .then(data => {
                setQaTemplateContent(data.content);
            })
            .catch(err => {
                console.error('Failed to load QA template:', err);
                setQaTemplateError(err.message);
            })
            .finally(() => {
                setQaTemplateLoading(false);
            });
    }, [qaTemplateInfo]);

    // Fetch PGC template content when docType changes and has a PGC template reference
    useEffect(() => {
        if (!pgcTemplateInfo) {
            setPgcTemplateContent(null);
            return;
        }

        setPgcTemplateLoading(true);
        setPgcTemplateError(null);

        adminApi.getTemplate(pgcTemplateInfo.templateId, pgcTemplateInfo.version)
            .then(data => {
                setPgcTemplateContent(data.content);
            })
            .catch(err => {
                console.error('Failed to load PGC template:', err);
                setPgcTemplateError(err.message);
            })
            .finally(() => {
                setPgcTemplateLoading(false);
            });
    }, [pgcTemplateInfo]);

    // Build artifact ID from doc type and selected kind (for non-role tabs)
    // Note: detail API returns "version", list API returns "active_version"
    const artifactId = useMemo(() => {
        if (!docType || selectedKind === 'role_prompt') return null;
        const version = docType.version || docType.active_version;
        return `doctype:${docType.doc_type_id}:${version}:${selectedKind}`;
    }, [docType, selectedKind]);

    // Prompt editor hook for the selected artifact (not used for role_prompt)
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

    // All possible prompt kinds (role_prompt is special - view only, package is form-based)
    const allPromptKinds = [
        { id: 'package', label: 'Package', isPackage: true },
        { id: 'role_prompt', label: 'Role Prompt', viewOnly: true },
        { id: 'template', label: 'Template', viewOnly: true },
        { id: 'task_prompt', label: 'Task Prompt' },
        { id: 'qa_prompt', label: 'QA Prompt' },
        { id: 'qa_template', label: 'QA Template', viewOnly: true },
        { id: 'reflection_prompt', label: 'Reflection' },
        { id: 'pgc_context', label: 'PGC Context' },
        { id: 'pgc_template', label: 'PGC Template', viewOnly: true },
        { id: 'schema', label: 'Schema', isJson: true },
        { id: 'workflow', label: 'Workflow', isWorkflow: true },
    ];

    // Filter to only show prompt kinds that exist for this document type
    const promptKinds = useMemo(() => {
        if (!docType) return [];

        return allPromptKinds.filter(kind => {
            // Package tab always shown
            if (kind.id === 'package') {
                return true;
            }
            // Role prompt shown if doc type has a role reference
            if (kind.id === 'role_prompt') {
                return !!docType.role_prompt_ref;
            }
            // Template shown if doc type has a template reference
            if (kind.id === 'template') {
                return !!docType.template_ref;
            }
            // QA Template shown if doc type has a QA template reference
            if (kind.id === 'qa_template') {
                return !!docType.qa_template_ref;
            }
            // PGC Template shown if doc type has a PGC template reference
            if (kind.id === 'pgc_template') {
                return !!docType.pgc_template_ref;
            }
            // Workflow tab shown if doc type has a workflow_ref
            if (kind.id === 'workflow') {
                return !!docType.workflow_ref;
            }
            // Other artifacts shown if they exist
            if (!docType.artifacts) return false;
            return docType.artifacts[kind.id] != null;
        });
    }, [docType]);

    // Reset to first available kind if current selection is not available
    useEffect(() => {
        if (promptKinds.length > 0 && !promptKinds.find(k => k.id === selectedKind)) {
            setSelectedKind(promptKinds[0].id);
        }
    }, [promptKinds, selectedKind]);

    // Check if current tab is view-only or form-based (no source/resolved toggle)
    const isViewOnly = selectedKind === 'role_prompt' || selectedKind === 'template' || selectedKind === 'qa_template' || selectedKind === 'pgc_template';
    const isPackage = selectedKind === 'package';
    const isSchema = selectedKind === 'schema';
    const isWorkflow = selectedKind === 'workflow';
    const showViewModeToggle = !isViewOnly && !isPackage && !isSchema && !isWorkflow;

    if (!docType && !detailsLoading) {
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

    if (detailsLoading) {
        return (
            <div
                className="flex-1 flex items-center justify-center"
                style={{ background: 'var(--bg-canvas)' }}
            >
                <div
                    className="text-center p-8"
                    style={{ color: 'var(--text-muted)' }}
                >
                    <div className="text-lg mb-2">Loading...</div>
                    <div className="text-sm">
                        Fetching document type details...
                    </div>
                </div>
            </div>
        );
    }

    // When opened from Building Blocks (task or schema), show focused view without tab bar
    const isFocusedView = docTypeSource === 'task' || docTypeSource === 'schema';
    const focusedLabel = docTypeSource === 'task' ? 'Interaction' : docTypeSource === 'schema' ? 'Schema' : null;
    // Building block artifacts (task_prompt, schema) are read-only when accessed from DCW tab bar
    const isDcwBuildingBlockView = !isFocusedView && (selectedKind === 'task_prompt' || selectedKind === 'schema');

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
                            {isFocusedView
                                ? focusedLabel
                                : <>v{docType.version || docType.active_version}{docType.authority_level && ` · ${docType.authority_level}`}</>
                            }
                        </div>
                    </div>
                </div>
            </div>

            {/* Single tab header for focused view (Building Blocks access) */}
            {isFocusedView && (
                <div
                    className="flex border-b"
                    style={{ borderColor: 'var(--border-panel)', background: 'var(--bg-panel)' }}
                >
                    <div
                        className="px-4 py-2 text-sm"
                        style={{
                            color: 'var(--text-primary)',
                            background: 'var(--bg-canvas)',
                            borderBottom: '2px solid var(--action-primary)',
                        }}
                    >
                        {docTypeSource === 'task' ? 'Task Prompt' : 'Schema'}
                    </div>
                </div>
            )}

            {/* Artifact kind tabs - grouped by Interaction Pass (hidden in focused view) */}
            {!isFocusedView && <div
                className="flex border-b"
                style={{ borderColor: 'var(--border-panel)', background: 'var(--bg-panel)' }}
            >
                {/* Package - static tab */}
                {promptKinds.find(k => k.id === 'package') && (
                    <StaticTab
                        label="Package"
                        isSelected={selectedKind === 'package'}
                        onClick={() => { setSelectedKind('package'); setViewMode('source'); }}
                    />
                )}

                {/* Workflow - static tab */}
                {promptKinds.find(k => k.id === 'workflow') && (
                    <StaticTab
                        label="Workflow"
                        isSelected={selectedKind === 'workflow'}
                        onClick={() => { setSelectedKind('workflow'); setViewMode('source'); }}
                    />
                )}

                {/* Generation - dropdown */}
                {(() => {
                    const genIds = ['role_prompt', 'task_prompt', 'template'];
                    const genItems = promptKinds
                        .filter(k => genIds.includes(k.id))
                        .map(k => ({
                            id: k.id,
                            label: k.id === 'role_prompt' ? 'Role' : k.id === 'task_prompt' ? 'Task' : 'Template',
                            viewOnly: k.viewOnly,
                        }));
                    if (genItems.length === 0) return null;
                    return (
                        <TabDropdown
                            label="Generation"
                            items={genItems}
                            selectedId={genIds.includes(selectedKind) ? selectedKind : null}
                            onSelect={(id) => { setSelectedKind(id); setViewMode('source'); }}
                            isGroupActive={genIds.includes(selectedKind)}
                        />
                    );
                })()}

                {/* QA - dropdown */}
                {(() => {
                    const qaIds = ['qa_prompt', 'qa_template'];
                    const qaItems = promptKinds
                        .filter(k => qaIds.includes(k.id))
                        .map(k => ({
                            id: k.id,
                            label: k.id === 'qa_prompt' ? 'Prompt' : 'Template',
                            viewOnly: k.viewOnly,
                        }));
                    if (qaItems.length === 0) return null;
                    return (
                        <TabDropdown
                            label="QA"
                            items={qaItems}
                            selectedId={qaIds.includes(selectedKind) ? selectedKind : null}
                            onSelect={(id) => { setSelectedKind(id); setViewMode('source'); }}
                            isGroupActive={qaIds.includes(selectedKind)}
                        />
                    );
                })()}

                {/* PGC - dropdown */}
                {(() => {
                    const pgcIds = ['pgc_context', 'pgc_template'];
                    const pgcItems = promptKinds
                        .filter(k => pgcIds.includes(k.id))
                        .map(k => ({
                            id: k.id,
                            label: k.id === 'pgc_context' ? 'Context' : 'Template',
                            viewOnly: k.viewOnly,
                        }));
                    if (pgcItems.length === 0) return null;
                    return (
                        <TabDropdown
                            label="PGC"
                            items={pgcItems}
                            selectedId={pgcIds.includes(selectedKind) ? selectedKind : null}
                            onSelect={(id) => { setSelectedKind(id); setViewMode('source'); }}
                            isGroupActive={pgcIds.includes(selectedKind)}
                        />
                    );
                })()}

                {/* Schema - static tab */}
                {promptKinds.find(k => k.id === 'schema') && (
                    <StaticTab
                        label="Schema"
                        isSelected={selectedKind === 'schema'}
                        onClick={() => { setSelectedKind('schema'); setViewMode('source'); }}
                    />
                )}
            </div>}

            {/* View mode tabs (Source / Resolved) - only for prompt tabs with content, hidden in focused view */}
            {!isFocusedView && showViewModeToggle && !isDcwBuildingBlockView && (
                <div
                    className="flex items-center justify-between px-3 py-2 border-b"
                    style={{ borderColor: 'var(--border-panel)', background: 'var(--bg-panel-alt, var(--bg-panel))' }}
                >
                    <div className="flex gap-1">
                        <button
                            onClick={() => setViewMode('source')}
                            className="px-3 py-1 text-xs font-medium rounded transition-colors"
                            style={{
                                background: viewMode === 'source'
                                    ? 'var(--action-primary)'
                                    : 'transparent',
                                color: viewMode === 'source'
                                    ? 'var(--bg-canvas, #000)'
                                    : 'var(--text-muted)',
                            }}
                        >
                            Source
                        </button>
                        <button
                            onClick={() => setViewMode('resolved')}
                            className="px-3 py-1 text-xs font-medium rounded transition-colors"
                            style={{
                                background: viewMode === 'resolved'
                                    ? 'var(--action-primary)'
                                    : 'transparent',
                                color: viewMode === 'resolved'
                                    ? 'var(--bg-canvas, #000)'
                                    : 'var(--text-muted)',
                            }}
                        >
                            Resolved
                        </button>
                    </div>
                    {/* File path display */}
                    {viewMode === 'source' && docType?.artifacts?.[selectedKind] && (
                        <span
                            className="text-xs font-mono truncate ml-4"
                            style={{ color: 'var(--text-muted)' }}
                            title={`combine-config/document_types/${docType.doc_type_id}/releases/${docType.version || docType.active_version}/${docType.artifacts[selectedKind]}`}
                        >
                            combine-config/document_types/{docType.doc_type_id}/releases/{docType.version || docType.active_version}/{docType.artifacts[selectedKind]}
                        </span>
                    )}
                </div>
            )}

            {/* View-only indicator for role prompt or template */}
            {isViewOnly && (
                <div
                    className="flex items-center gap-2 px-3 py-2 border-b"
                    style={{ borderColor: 'var(--border-panel)', background: 'var(--bg-panel-alt, var(--bg-panel))' }}
                >
                    <span
                        className="text-xs"
                        style={{ color: 'var(--text-muted)' }}
                    >
                        {selectedKind === 'role_prompt'
                            ? 'View Only - Edit roles in the Roles section'
                            : 'View Only - Shared template'}
                    </span>
                    {selectedKind === 'role_prompt' && roleInfo && (
                        <span
                            className="text-xs px-2 py-0.5 rounded"
                            style={{ background: 'var(--bg-selected)', color: 'var(--text-secondary)' }}
                        >
                            {roleInfo.roleId.replace(/_/g, ' ')} v{roleInfo.version}
                        </span>
                    )}
                    {selectedKind === 'template' && templateInfo && (
                        <span
                            className="text-xs px-2 py-0.5 rounded"
                            style={{ background: 'var(--bg-selected)', color: 'var(--text-secondary)' }}
                        >
                            {templateInfo.templateId.replace(/_/g, ' ')} v{templateInfo.version}
                        </span>
                    )}
                    {selectedKind === 'qa_template' && qaTemplateInfo && (
                        <span
                            className="text-xs px-2 py-0.5 rounded"
                            style={{ background: 'var(--bg-selected)', color: 'var(--text-secondary)' }}
                        >
                            {qaTemplateInfo.templateId.replace(/_/g, ' ')} v{qaTemplateInfo.version}
                        </span>
                    )}
                    {selectedKind === 'pgc_template' && pgcTemplateInfo && (
                        <span
                            className="text-xs px-2 py-0.5 rounded"
                            style={{ background: 'var(--bg-selected)', color: 'var(--text-secondary)' }}
                        >
                            {pgcTemplateInfo.templateId.replace(/_/g, ' ')} v{pgcTemplateInfo.version}
                        </span>
                    )}
                </div>
            )}
            {/* View-only indicator for building block artifacts accessed from DCW tab bar */}
            {isDcwBuildingBlockView && (
                <div
                    className="flex items-center gap-2 px-3 py-2 border-b"
                    style={{ borderColor: 'var(--border-panel)', background: 'var(--bg-panel-alt, var(--bg-panel))' }}
                >
                    <span
                        className="text-xs"
                        style={{ color: 'var(--text-muted)' }}
                    >
                        {selectedKind === 'task_prompt'
                            ? 'View Only \u2014 Edit from Building Blocks \u2192 Interactions'
                            : 'View Only \u2014 Edit from Building Blocks \u2192 Schemas'}
                    </span>
                </div>
            )}

            {/* File path indicator for Schema tab (no Source/Resolved toggle) */}
            {isSchema && docType?.artifacts?.schema && (
                <div
                    className="flex items-center justify-end px-3 py-2 border-b"
                    style={{ borderColor: 'var(--border-panel)', background: 'var(--bg-panel-alt, var(--bg-panel))' }}
                >
                    <span
                        className="text-xs font-mono truncate"
                        style={{ color: 'var(--text-muted)' }}
                        title={`combine-config/document_types/${docType.doc_type_id}/releases/${docType.version || docType.active_version}/${docType.artifacts.schema}`}
                    >
                        combine-config/document_types/{docType.doc_type_id}/releases/{docType.version || docType.active_version}/{docType.artifacts.schema}
                    </span>
                </div>
            )}

            {/* Content area */}
            <div className="flex-1 overflow-hidden flex flex-col">
                {isWorkflow ? (
                    // Document production workflow - React Flow canvas
                    <WorkflowEditorContent
                        workspaceId={workspaceId}
                        artifactId={docType.workflow_ref}
                        onArtifactSave={onArtifactSave}
                    />
                ) : selectedKind === 'package' ? (
                    // Package editor - form-based
                    <PackageEditor
                        workspaceId={workspaceId}
                        docType={docType}
                        roles={roles}
                        onSave={onArtifactSave}
                    />
                ) : selectedKind === 'role_prompt' ? (
                    // Role prompt - read only
                    <PromptTab
                        content={roleContent || ''}
                        onChange={() => {}} // No-op, read only
                        loading={roleLoading}
                        saving={false}
                        isDirty={false}
                        error={roleError}
                        readOnly={true}
                        placeholder="No role prompt configured for this document type"
                    />
                ) : selectedKind === 'template' ? (
                    // Template - read only
                    <PromptTab
                        content={templateContent || ''}
                        onChange={() => {}} // No-op, read only
                        loading={templateLoading}
                        saving={false}
                        isDirty={false}
                        error={templateError}
                        readOnly={true}
                        placeholder="No template configured for this document type"
                    />
                ) : selectedKind === 'qa_template' ? (
                    // QA Template - read only
                    <PromptTab
                        content={qaTemplateContent || ''}
                        onChange={() => {}} // No-op, read only
                        loading={qaTemplateLoading}
                        saving={false}
                        isDirty={false}
                        error={qaTemplateError}
                        readOnly={true}
                        placeholder="No QA template configured for this document type"
                    />
                ) : selectedKind === 'pgc_template' ? (
                    // PGC Template - read only
                    <PromptTab
                        content={pgcTemplateContent || ''}
                        onChange={() => {}} // No-op, read only
                        loading={pgcTemplateLoading}
                        saving={false}
                        isDirty={false}
                        error={pgcTemplateError}
                        readOnly={true}
                        placeholder="No PGC template configured for this document type"
                    />
                ) : viewMode === 'source' || isSchema ? (
                    <PromptTab
                        content={content}
                        onChange={isDcwBuildingBlockView ? () => {} : updateContent}
                        loading={loading}
                        saving={isDcwBuildingBlockView ? false : saving}
                        isDirty={isDcwBuildingBlockView ? false : isDirty}
                        error={error}
                        readOnly={isDcwBuildingBlockView}
                        placeholder={`Enter ${promptKinds.find(k => k.id === selectedKind)?.label || 'prompt'} content...`}
                        isJson={isSchema}
                    />
                ) : (
                    <ResolvedPreview
                        workspaceId={workspaceId}
                        artifactId={artifactId}
                    />
                )}
            </div>

            {/* Validation result from last save (compact) */}
            {showViewModeToggle && lastSaveResult?.tier1 && !lastSaveResult.tier1.passed && (
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