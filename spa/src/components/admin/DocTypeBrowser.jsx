import React, { useState } from 'react';

/**
 * Collapsible group section for the left rail.
 */
function CollapsibleGroup({ title, defaultOpen = true, children }) {
    const [open, setOpen] = useState(defaultOpen);

    return (
        <div>
            <button
                onClick={() => setOpen(!open)}
                className="w-full px-4 py-2.5 flex items-center justify-between text-left"
                style={{
                    background: 'var(--bg-panel)',
                    border: 'none',
                    borderBottom: '1px solid var(--border-panel)',
                    cursor: 'pointer',
                }}
            >
                <span
                    className="text-xs font-bold uppercase tracking-widest"
                    style={{ color: 'var(--text-muted)' }}
                >
                    {title}
                </span>
                <span
                    className="text-xs"
                    style={{
                        color: 'var(--text-muted)',
                        transform: open ? 'rotate(0deg)' : 'rotate(-90deg)',
                        transition: 'transform 150ms ease',
                        display: 'inline-block',
                    }}
                >
                    ▾
                </span>
            </button>
            {open && children}
        </div>
    );
}

/**
 * Collapsible sub-section within a group.
 */
function SubSection({ title, action, defaultOpen = true, children }) {
    const [open, setOpen] = useState(defaultOpen);

    return (
        <div>
            <div
                className="px-4 py-1.5 flex items-center justify-between"
                style={{ borderBottom: '1px solid var(--border-panel)' }}
            >
                <button
                    onClick={() => setOpen(!open)}
                    className="flex items-center gap-1.5"
                    style={{
                        background: 'transparent',
                        border: 'none',
                        cursor: 'pointer',
                        padding: 0,
                    }}
                >
                    <span
                        className="text-xs"
                        style={{
                            color: 'var(--text-muted)',
                            transform: open ? 'rotate(0deg)' : 'rotate(-90deg)',
                            transition: 'transform 150ms ease',
                            display: 'inline-block',
                        }}
                    >
                        ▾
                    </span>
                    <span
                        className="text-xs font-semibold uppercase tracking-wide"
                        style={{ color: 'var(--text-muted)' }}
                    >
                        {title}
                    </span>
                </button>
                {action}
            </div>
            {open && children}
        </div>
    );
}

/**
 * Reusable item button for the left rail.
 */
function ItemButton({ selected, onClick, label, sublabel }) {
    return (
        <button
            onClick={onClick}
            className="w-full px-4 py-2 text-left text-sm hover:opacity-80 transition-opacity"
            style={{
                background: selected ? 'var(--bg-selected)' : 'transparent',
                color: selected ? 'var(--text-primary)' : 'var(--text-secondary)',
                borderLeft: selected
                    ? '2px solid var(--action-primary)'
                    : '2px solid transparent',
            }}
        >
            <div className="font-medium truncate">{label}</div>
            {sublabel && (
                <div className="text-xs truncate" style={{ color: 'var(--text-muted)' }}>
                    {sublabel}
                </div>
            )}
        </button>
    );
}

/**
 * Loading / empty state for a section.
 */
function SectionState({ loading, empty, emptyMessage = 'None found' }) {
    if (loading) {
        return (
            <div className="px-4 py-3 text-sm" style={{ color: 'var(--text-muted)' }}>
                Loading...
            </div>
        );
    }
    if (empty) {
        return (
            <div className="px-4 py-3 text-sm" style={{ color: 'var(--text-muted)' }}>
                {emptyMessage}
            </div>
        );
    }
    return null;
}

/**
 * Left sidebar for the Admin Workbench, organized by abstraction level per ADR-045.
 *
 * Structure:
 *   Production Workflows
 *     > Project Workflows (POWs - step-based orchestration)
 *     > Document Workflows (DCWs - graph-based document production)
 *   Building Blocks
 *     > Roles
 *     > Tasks (derived from document types)
 *     > Schemas (derived from document types)
 *     > Templates
 *   Governance
 *     > Active Releases
 */
export default function DocTypeBrowser({
    documentTypes = [],
    roles = [],
    templates = [],
    workflows = [],
    loading = false,
    rolesLoading = false,
    templatesLoading = false,
    workflowsLoading = false,
    selectedDocType = null,
    selectedRole = null,
    selectedTemplate = null,
    selectedWorkflow = null,
    onSelectDocType,
    onSelectRole,
    onSelectTemplate,
    onSelectWorkflow,
    onCreateWorkflow,
    onSelectTask,
    onSelectSchema,
}) {
    const [showNewWorkflowForm, setShowNewWorkflowForm] = useState(false);
    const [newWorkflowId, setNewWorkflowId] = useState('');
    const [creating, setCreating] = useState(false);

    // Group doc types by category for Document Workflows section
    const grouped = documentTypes.reduce((acc, dt) => {
        const category = dt.category || 'other';
        if (!acc[category]) acc[category] = [];
        acc[category].push(dt);
        return acc;
    }, {});

    const categoryOrder = ['intake', 'architecture', 'planning', 'other'];
    const sortedCategories = Object.keys(grouped).sort((a, b) => {
        const aIdx = categoryOrder.indexOf(a);
        const bIdx = categoryOrder.indexOf(b);
        if (aIdx === -1 && bIdx === -1) return a.localeCompare(b);
        if (aIdx === -1) return 1;
        if (bIdx === -1) return -1;
        return aIdx - bIdx;
    });

    const handleCreateWorkflow = async () => {
        const id = newWorkflowId.trim().toLowerCase().replace(/\s+/g, '_');
        if (!id || !/^[a-z][a-z0-9_]*$/.test(id)) return;
        setCreating(true);
        try {
            await onCreateWorkflow?.({ workflow_id: id });
            setNewWorkflowId('');
            setShowNewWorkflowForm(false);
        } catch {
            // Error handled by parent
        } finally {
            setCreating(false);
        }
    };

    // Derive tasks and schemas from document types for Building Blocks
    const tasks = documentTypes.map(dt => ({
        doc_type_id: dt.doc_type_id,
        display_name: dt.display_name,
        active_version: dt.active_version,
    }));

    const schemas = documentTypes.map(dt => ({
        doc_type_id: dt.doc_type_id,
        display_name: dt.display_name,
        active_version: dt.active_version,
    }));

    // Count active releases for governance section
    const activeReleaseCount = documentTypes.filter(dt => dt.active_version).length
        + workflows.filter(wf => wf.active_version).length;

    return (
        <div
            className="w-60 flex flex-col border-r h-full"
            style={{
                borderColor: 'var(--border-panel)',
                background: 'var(--bg-panel)',
            }}
        >
            <div className="flex-1 overflow-y-auto">
                {/* ============================================================
                    PRODUCTION WORKFLOWS
                    ============================================================ */}
                <CollapsibleGroup title="Production Workflows" defaultOpen={true}>
                    {/* --- Project Workflows (POWs) --- */}
                    <SubSection
                        title="Project Workflows"
                        action={
                            onCreateWorkflow && (
                                <button
                                    onClick={() => setShowNewWorkflowForm(!showNewWorkflowForm)}
                                    className="text-xs hover:opacity-80"
                                    style={{
                                        color: 'var(--action-primary)',
                                        background: 'transparent',
                                        border: 'none',
                                        cursor: 'pointer',
                                        fontWeight: 600,
                                    }}
                                    title="Create new workflow"
                                >
                                    + New
                                </button>
                            )
                        }
                    >
                        {/* New Workflow Form */}
                        {showNewWorkflowForm && (
                            <div
                                className="px-4 py-2"
                                style={{ background: 'var(--bg-canvas)' }}
                            >
                                <input
                                    type="text"
                                    value={newWorkflowId}
                                    onChange={e => setNewWorkflowId(e.target.value)}
                                    onKeyDown={e => {
                                        if (e.key === 'Enter') handleCreateWorkflow();
                                        if (e.key === 'Escape') {
                                            setShowNewWorkflowForm(false);
                                            setNewWorkflowId('');
                                        }
                                    }}
                                    placeholder="workflow_id (snake_case)"
                                    autoFocus
                                    disabled={creating}
                                    className="w-full text-xs px-2 py-1.5 rounded mb-1.5"
                                    style={{
                                        background: 'var(--bg-input, var(--bg-panel))',
                                        border: '1px solid var(--border-panel)',
                                        color: 'var(--text-primary)',
                                        outline: 'none',
                                    }}
                                />
                                <div className="flex gap-1">
                                    <button
                                        onClick={handleCreateWorkflow}
                                        disabled={creating || !newWorkflowId.trim()}
                                        className="text-xs px-2 py-1 rounded hover:opacity-80"
                                        style={{
                                            background: 'var(--action-primary)',
                                            color: '#000',
                                            fontWeight: 600,
                                            border: 'none',
                                            cursor: creating ? 'wait' : 'pointer',
                                            opacity: (!newWorkflowId.trim() || creating) ? 0.5 : 1,
                                        }}
                                    >
                                        {creating ? 'Creating...' : 'Create'}
                                    </button>
                                    <button
                                        onClick={() => {
                                            setShowNewWorkflowForm(false);
                                            setNewWorkflowId('');
                                        }}
                                        className="text-xs px-2 py-1 rounded hover:opacity-80"
                                        style={{
                                            background: 'transparent',
                                            color: 'var(--text-muted)',
                                            border: 'none',
                                            cursor: 'pointer',
                                        }}
                                    >
                                        Cancel
                                    </button>
                                </div>
                            </div>
                        )}

                        <SectionState
                            loading={workflowsLoading}
                            empty={!workflowsLoading && workflows.length === 0}
                            emptyMessage="No project workflows"
                        />
                        {!workflowsLoading && workflows.length > 0 && (
                            <div className="py-1">
                                {workflows.map(wf => (
                                    <ItemButton
                                        key={wf.workflow_id}
                                        selected={selectedWorkflow?.workflow_id === wf.workflow_id}
                                        onClick={() => onSelectWorkflow?.(wf)}
                                        label={wf.workflow_id.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                                        sublabel={`v${wf.active_version}${wf.step_count != null ? ` \u00b7 ${wf.step_count} steps` : ''}`}
                                    />
                                ))}
                            </div>
                        )}
                    </SubSection>

                    {/* --- Document Workflows (DCWs) --- */}
                    <SubSection title="Document Workflows">
                        <SectionState
                            loading={loading}
                            empty={!loading && documentTypes.length === 0}
                            emptyMessage="No document workflows"
                        />
                        {!loading && documentTypes.length > 0 && (
                            <>
                                {sortedCategories.map(category => (
                                    <div key={category} className="py-1">
                                        <div
                                            className="px-4 py-1 text-xs font-medium uppercase tracking-wider"
                                            style={{ color: 'var(--text-muted)' }}
                                        >
                                            {category}
                                        </div>
                                        {grouped[category].map(dt => (
                                            <ItemButton
                                                key={dt.doc_type_id}
                                                selected={selectedDocType?.doc_type_id === dt.doc_type_id}
                                                onClick={() => onSelectDocType?.(dt)}
                                                label={dt.display_name}
                                                sublabel={`v${dt.active_version}${dt.authority_level ? ` \u00b7 ${dt.authority_level}` : ''}`}
                                            />
                                        ))}
                                    </div>
                                ))}
                            </>
                        )}
                    </SubSection>
                </CollapsibleGroup>

                {/* ============================================================
                    BUILDING BLOCKS
                    ============================================================ */}
                <CollapsibleGroup title="Building Blocks" defaultOpen={true}>
                    {/* --- Roles --- */}
                    <SubSection title="Roles">
                        <SectionState
                            loading={rolesLoading}
                            empty={!rolesLoading && roles.length === 0}
                            emptyMessage="No roles"
                        />
                        {!rolesLoading && roles.length > 0 && (
                            <div className="py-1">
                                {roles.map(role => (
                                    <ItemButton
                                        key={role.role_id}
                                        selected={selectedRole?.role_id === role.role_id}
                                        onClick={() => onSelectRole?.(role)}
                                        label={role.role_id.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                                        sublabel={`v${role.active_version}`}
                                    />
                                ))}
                            </div>
                        )}
                    </SubSection>

                    {/* --- Tasks (derived from document types) --- */}
                    <SubSection title="Tasks">
                        <SectionState
                            loading={loading}
                            empty={!loading && tasks.length === 0}
                            emptyMessage="No tasks"
                        />
                        {!loading && tasks.length > 0 && (
                            <div className="py-1">
                                {tasks.map(task => (
                                    <ItemButton
                                        key={`task-${task.doc_type_id}`}
                                        selected={selectedDocType?.doc_type_id === task.doc_type_id}
                                        onClick={() => (onSelectTask || onSelectDocType)?.({ doc_type_id: task.doc_type_id, display_name: task.display_name, active_version: task.active_version })}
                                        label={task.display_name}
                                        sublabel={`from ${task.doc_type_id}`}
                                    />
                                ))}
                            </div>
                        )}
                    </SubSection>

                    {/* --- Schemas (derived from document types, read-only for MVP) --- */}
                    <SubSection title="Schemas">
                        <SectionState
                            loading={loading}
                            empty={!loading && schemas.length === 0}
                            emptyMessage="No schemas"
                        />
                        {!loading && schemas.length > 0 && (
                            <div className="py-1">
                                {schemas.map(schema => (
                                    <ItemButton
                                        key={`schema-${schema.doc_type_id}`}
                                        selected={selectedDocType?.doc_type_id === schema.doc_type_id}
                                        onClick={() => (onSelectSchema || onSelectDocType)?.({ doc_type_id: schema.doc_type_id, display_name: schema.display_name, active_version: schema.active_version })}
                                        label={schema.display_name}
                                        sublabel={`from ${schema.doc_type_id}`}
                                    />
                                ))}
                            </div>
                        )}
                    </SubSection>

                    {/* --- Templates --- */}
                    <SubSection title="Templates">
                        <SectionState
                            loading={templatesLoading}
                            empty={!templatesLoading && templates.length === 0}
                            emptyMessage="No templates"
                        />
                        {!templatesLoading && templates.length > 0 && (
                            <div className="py-1">
                                {templates.map(template => (
                                    <ItemButton
                                        key={template.template_id}
                                        selected={selectedTemplate?.template_id === template.template_id}
                                        onClick={() => onSelectTemplate?.(template)}
                                        label={template.template_id.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                                        sublabel={`v${template.active_version}`}
                                    />
                                ))}
                            </div>
                        )}
                    </SubSection>
                </CollapsibleGroup>

                {/* ============================================================
                    GOVERNANCE
                    ============================================================ */}
                <CollapsibleGroup title="Governance" defaultOpen={false}>
                    <div className="px-4 py-3">
                        <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
                            <div className="font-semibold uppercase tracking-wide mb-1">Active Releases</div>
                            <div>
                                {activeReleaseCount} active {activeReleaseCount === 1 ? 'release' : 'releases'}
                            </div>
                        </div>
                    </div>
                </CollapsibleGroup>
            </div>
        </div>
    );
}
