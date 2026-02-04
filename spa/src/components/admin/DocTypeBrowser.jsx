import React, { useState, useCallback } from 'react';

const STORAGE_KEY = 'doctype-browser-collapsed';

function usePersistedOpen(key, defaultOpen) {
    const [open, setOpenRaw] = useState(() => {
        try {
            const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
            return key in stored ? stored[key] : defaultOpen;
        } catch {
            return defaultOpen;
        }
    });
    const setOpen = useCallback((next) => {
        const val = typeof next === 'function' ? next(open) : next;
        setOpenRaw(val);
        try {
            const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
            stored[key] = val;
            localStorage.setItem(STORAGE_KEY, JSON.stringify(stored));
        } catch { /* ignore */ }
    }, [key, open]);
    return [open, setOpen];
}

/**
 * Collapsible group section for the left rail.
 */
function CollapsibleGroup({ title, defaultOpen = true, children }) {
    const [open, setOpen] = usePersistedOpen(`group:${title}`, defaultOpen);

    return (
        <div>
            <button
                onClick={() => setOpen(!open)}
                className="w-full px-4 py-2.5 flex items-center justify-between text-left"
                style={{
                    background: 'var(--bg-group-header)',
                    border: 'none',
                    borderBottom: '1px solid var(--border-panel)',
                    cursor: 'pointer',
                }}
            >
                <span
                    className="font-bold uppercase tracking-widest"
                    style={{ color: 'var(--text-primary)', fontSize: 11 }}
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
                    &#9662;
                </span>
            </button>
            {open && children}
        </div>
    );
}

/**
 * Collapsible sub-section within a group. Supports optional colored dot indicator.
 */
function SubSection({ title, action, defaultOpen = true, dotColor, children }) {
    const [open, setOpen] = usePersistedOpen(`sub:${title}`, defaultOpen);

    return (
        <div>
            <div
                className="px-4 py-1.5 flex items-center justify-between"
                style={{
                    background: 'var(--bg-subsection-header)',
                    borderBottom: '1px solid var(--border-panel)',
                    paddingLeft: '1.25rem',
                }}
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
                        style={{
                            color: 'var(--text-muted)',
                            transform: open ? 'rotate(0deg)' : 'rotate(-90deg)',
                            transition: 'transform 150ms ease',
                            display: 'inline-block',
                            fontSize: 9,
                        }}
                    >
                        &#9662;
                    </span>
                    {dotColor && (
                        <span style={{ color: dotColor, fontSize: 8 }}>&#9679;</span>
                    )}
                    <span
                        style={{ color: 'var(--text-muted)', fontSize: 10, fontWeight: 500 }}
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
 * Reusable item button for the left rail. Supports optional right-aligned badge.
 */
function ItemButton({ selected, onClick, label, sublabel, badge }) {
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
            <div className="flex items-center justify-between">
                <div className="font-medium truncate">{label}</div>
                {badge && (
                    <span
                        style={{
                            fontSize: 9,
                            fontFamily: 'monospace',
                            color: 'var(--text-muted)',
                            flexShrink: 0,
                            marginLeft: 8,
                        }}
                    >
                        {badge}
                    </span>
                )}
            </div>
            {sublabel && (
                <div className="text-xs truncate" style={{ color: 'var(--text-muted)' }}>
                    {sublabel}
                </div>
            )}
        </button>
    );
}

/**
 * Collapsible Building Blocks item with colored dot and count badge.
 * Header shows dot, label, and count. Expands to show child items.
 */
function BuildingBlockItem({ label, count, dotColor, active, defaultOpen = false, children }) {
    const [open, setOpen] = usePersistedOpen(`bb:${label}`, defaultOpen);

    return (
        <div>
            <button
                onClick={() => setOpen(!open)}
                className="w-full px-4 py-2 flex items-center justify-between text-sm hover:opacity-80 transition-opacity"
                style={{
                    background: active ? 'var(--bg-selected)' : 'transparent',
                    color: active ? 'var(--text-primary)' : 'var(--text-secondary)',
                    borderLeft: active
                        ? '2px solid var(--action-primary)'
                        : '2px solid transparent',
                    cursor: 'pointer',
                }}
            >
                <span className="flex items-center gap-2">
                    <span style={{ color: dotColor, fontSize: 10 }}>&#9679;</span>
                    <span className="font-medium">{label}</span>
                </span>
                <span className="flex items-center gap-2">
                    <span
                        style={{
                            fontSize: 9,
                            fontFamily: 'monospace',
                            color: 'var(--text-muted)',
                        }}
                    >
                        {count}
                    </span>
                    <span
                        style={{
                            color: 'var(--text-muted)',
                            transform: open ? 'rotate(0deg)' : 'rotate(-90deg)',
                            transition: 'transform 150ms ease',
                            display: 'inline-block',
                            fontSize: 9,
                        }}
                    >
                        &#9662;
                    </span>
                </span>
            </button>
            {open && children}
        </div>
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
 * Left sidebar for the Admin Workbench, organized by composition hierarchy per ADR-045.
 *
 * Structure:
 *   Production Workflows
 *     > Project Orchestration (POWs) - flat list with pow_class badge
 *     > Document Creation (DCWs) - flat alphabetical list with version badge
 *   Building Blocks
 *     > Roles (count badge)
 *     > Interactions (count badge)
 *     > Schemas (count badge)
 *     > Templates (count badge)
 *   Governance
 *     > Active Releases
 *     > Git Status
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
    docTypeSource = null,
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
    workspaceState = null,
}) {
    // Create workflow state: null | 'choose' | 'from_reference' | 'blank'
    const [createMode, setCreateMode] = useState(null);
    const [selectedReference, setSelectedReference] = useState(null);
    const [newWorkflowId, setNewWorkflowId] = useState('');
    const [creating, setCreating] = useState(false);

    // Sort doc types alphabetically for DCW section
    const sortedDocTypes = [...documentTypes].sort((a, b) =>
        (a.display_name || '').localeCompare(b.display_name || '')
    );

    // Reference workflows needed for create-from-reference flow
    const referenceWorkflows = workflows.filter(wf => (wf.pow_class || 'reference') === 'reference');

    // POW class badge abbreviation
    const powClassBadge = (wf) => {
        const cls = wf.pow_class || 'reference';
        return cls === 'reference' ? 'ref' : cls === 'template' ? 'tpl' : 'inst';
    };

    // Count active releases for governance section
    const activeReleaseCount = documentTypes.filter(dt => dt.active_version).length
        + workflows.filter(wf => wf.active_version).length;

    // Dirty file info for governance section
    const dirtyCount = workspaceState?.modified_artifacts?.length ?? 0;
    const isDirty = workspaceState?.is_dirty ?? false;

    const resetCreateForm = () => {
        setCreateMode(null);
        setSelectedReference(null);
        setNewWorkflowId('');
    };

    const handleCreateWorkflow = async () => {
        const id = newWorkflowId.trim().toLowerCase().replace(/\s+/g, '_');
        if (!id || !/^[a-z][a-z0-9_]*$/.test(id)) return;
        setCreating(true);
        try {
            const data = { workflow_id: id, pow_class: 'template' };
            if (selectedReference) {
                data.derived_from = {
                    workflow_id: selectedReference.workflow_id,
                    version: selectedReference.active_version,
                };
                data.source_version = selectedReference.active_version;
            }
            await onCreateWorkflow?.(data);
            resetCreateForm();
        } catch {
            // Error handled by parent
        } finally {
            setCreating(false);
        }
    };

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
                    {/* --- Project Orchestration (POWs) --- */}
                    <SubSection
                        title="Project Orchestration (POWs)"
                        dotColor="var(--dot-green)"
                        action={
                            onCreateWorkflow && (
                                <button
                                    onClick={() => setCreateMode(createMode ? null : 'choose')}
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
                        {/* Create Workflow: Step 1 - Choose mode */}
                        {createMode === 'choose' && (
                            <div
                                className="px-4 py-2"
                                style={{ background: 'var(--bg-canvas)' }}
                            >
                                <button
                                    onClick={() => setCreateMode('from_reference')}
                                    className="w-full text-left text-xs px-2 py-1.5 rounded mb-1 hover:opacity-80"
                                    style={{
                                        background: 'var(--action-primary)',
                                        color: '#000',
                                        fontWeight: 600,
                                        border: 'none',
                                        cursor: 'pointer',
                                    }}
                                    disabled={referenceWorkflows.length === 0}
                                >
                                    From Reference{referenceWorkflows.length === 0 ? ' (none available)' : ''}
                                </button>
                                <button
                                    onClick={() => setCreateMode('blank')}
                                    className="w-full text-left text-xs px-2 py-1.5 rounded hover:opacity-80"
                                    style={{
                                        background: 'transparent',
                                        color: 'var(--text-muted)',
                                        border: '1px solid var(--border-panel)',
                                        cursor: 'pointer',
                                    }}
                                >
                                    Blank Workflow
                                </button>
                                <button
                                    onClick={resetCreateForm}
                                    className="w-full text-center text-xs px-2 py-1 mt-1 hover:opacity-80"
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
                        )}

                        {/* Create Workflow: Step 2a - Pick reference to fork */}
                        {createMode === 'from_reference' && !selectedReference && (
                            <div
                                className="px-4 py-2"
                                style={{ background: 'var(--bg-canvas)' }}
                            >
                                <div
                                    className="text-xs font-semibold mb-1"
                                    style={{ color: 'var(--text-muted)' }}
                                >
                                    Select reference to fork:
                                </div>
                                {referenceWorkflows.map(wf => (
                                    <button
                                        key={wf.workflow_id}
                                        onClick={() => setSelectedReference(wf)}
                                        className="w-full text-left text-xs px-2 py-1.5 rounded mb-0.5 hover:opacity-80"
                                        style={{
                                            background: 'transparent',
                                            color: 'var(--text-secondary)',
                                            border: '1px solid var(--border-panel)',
                                            cursor: 'pointer',
                                        }}
                                    >
                                        <div className="font-medium">
                                            {wf.name || wf.workflow_id.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                                        </div>
                                        <div style={{ color: 'var(--text-muted)' }}>v{wf.active_version}</div>
                                    </button>
                                ))}
                                <button
                                    onClick={() => setCreateMode('choose')}
                                    className="w-full text-center text-xs px-2 py-1 mt-1 hover:opacity-80"
                                    style={{
                                        background: 'transparent',
                                        color: 'var(--text-muted)',
                                        border: 'none',
                                        cursor: 'pointer',
                                    }}
                                >
                                    Back
                                </button>
                            </div>
                        )}

                        {/* Create Workflow: Step 2b/3 - Enter workflow ID (from_reference with selection, or blank) */}
                        {(createMode === 'blank' || (createMode === 'from_reference' && selectedReference)) && (
                            <div
                                className="px-4 py-2"
                                style={{ background: 'var(--bg-canvas)' }}
                            >
                                {selectedReference && (
                                    <div
                                        className="text-xs mb-1.5 px-2 py-1 rounded"
                                        style={{
                                            background: 'var(--bg-panel)',
                                            border: '1px solid var(--border-panel)',
                                            color: 'var(--text-muted)',
                                        }}
                                    >
                                        Forking: {selectedReference.name || selectedReference.workflow_id} v{selectedReference.active_version}
                                    </div>
                                )}
                                <input
                                    type="text"
                                    value={newWorkflowId}
                                    onChange={e => setNewWorkflowId(e.target.value)}
                                    onKeyDown={e => {
                                        if (e.key === 'Enter') handleCreateWorkflow();
                                        if (e.key === 'Escape') resetCreateForm();
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
                                        onClick={resetCreateForm}
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
                            emptyMessage="No workflows"
                        />
                        {!workflowsLoading && workflows.length > 0 && (
                            <div className="py-1">
                                {workflows.map(wf => (
                                    <ItemButton
                                        key={wf.workflow_id}
                                        selected={selectedWorkflow?.workflow_id === wf.workflow_id}
                                        onClick={() => onSelectWorkflow?.(wf)}
                                        label={wf.name || wf.workflow_id.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                                        sublabel={`v${wf.active_version}`}
                                        badge={powClassBadge(wf)}
                                    />
                                ))}
                            </div>
                        )}
                    </SubSection>

                    {/* --- Document Creation (DCWs) --- */}
                    <SubSection title="Document Creation (DCWs)" dotColor="var(--dot-blue)">
                        <SectionState
                            loading={loading}
                            empty={!loading && documentTypes.length === 0}
                            emptyMessage="No document workflows"
                        />
                        {!loading && sortedDocTypes.length > 0 && (
                            <div className="py-1">
                                {sortedDocTypes.map(dt => (
                                    <ItemButton
                                        key={dt.doc_type_id}
                                        selected={docTypeSource === 'docworkflow' && selectedDocType?.doc_type_id === dt.doc_type_id}
                                        onClick={() => onSelectDocType?.(dt)}
                                        label={dt.display_name}
                                        badge={`v${dt.active_version}`}
                                    />
                                ))}
                            </div>
                        )}
                    </SubSection>
                </CollapsibleGroup>

                {/* ============================================================
                    BUILDING BLOCKS
                    ============================================================ */}
                <CollapsibleGroup title="Building Blocks" defaultOpen={true}>
                    <BuildingBlockItem
                        label="Roles"
                        count={roles.length}
                        dotColor="var(--dot-purple)"
                        active={!!selectedRole}
                    >
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
                    </BuildingBlockItem>
                    <BuildingBlockItem
                        label="Interactions"
                        count={documentTypes.length}
                        dotColor="var(--action-primary)"
                        active={docTypeSource === 'task'}
                    >
                        <SectionState
                            loading={loading}
                            empty={!loading && documentTypes.length === 0}
                            emptyMessage="No interactions"
                        />
                        {!loading && documentTypes.length > 0 && (
                            <div className="py-1">
                                {documentTypes.map(dt => (
                                    <ItemButton
                                        key={`task-${dt.doc_type_id}`}
                                        selected={docTypeSource === 'task' && selectedDocType?.doc_type_id === dt.doc_type_id}
                                        onClick={() => (onSelectTask || onSelectDocType)?.({ doc_type_id: dt.doc_type_id, display_name: dt.display_name, active_version: dt.active_version })}
                                        label={dt.display_name}
                                        sublabel={`from ${dt.doc_type_id}`}
                                    />
                                ))}
                            </div>
                        )}
                    </BuildingBlockItem>
                    <BuildingBlockItem
                        label="Schemas"
                        count={documentTypes.length}
                        dotColor="var(--dot-blue)"
                        active={docTypeSource === 'schema'}
                    >
                        <SectionState
                            loading={loading}
                            empty={!loading && documentTypes.length === 0}
                            emptyMessage="No schemas"
                        />
                        {!loading && documentTypes.length > 0 && (
                            <div className="py-1">
                                {documentTypes.map(dt => (
                                    <ItemButton
                                        key={`schema-${dt.doc_type_id}`}
                                        selected={docTypeSource === 'schema' && selectedDocType?.doc_type_id === dt.doc_type_id}
                                        onClick={() => (onSelectSchema || onSelectDocType)?.({ doc_type_id: dt.doc_type_id, display_name: dt.display_name, active_version: dt.active_version })}
                                        label={dt.display_name}
                                        sublabel={`from ${dt.doc_type_id}`}
                                    />
                                ))}
                            </div>
                        )}
                    </BuildingBlockItem>
                    <BuildingBlockItem
                        label="Templates"
                        count={templates.length}
                        dotColor="var(--dot-green)"
                        active={!!selectedTemplate}
                    >
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
                    </BuildingBlockItem>
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
                    {workspaceState && (
                        <div className="px-4 py-2 flex items-center justify-between">
                            <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                                Git Status
                            </span>
                            {isDirty && (
                                <span
                                    style={{
                                        fontSize: 9,
                                        fontFamily: 'monospace',
                                        color: 'var(--action-primary)',
                                    }}
                                >
                                    {dirtyCount} dirty
                                </span>
                            )}
                        </div>
                    )}
                </CollapsibleGroup>
            </div>
        </div>
    );
}
