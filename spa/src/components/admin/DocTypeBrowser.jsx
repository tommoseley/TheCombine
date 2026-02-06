import React, { useState, useCallback } from 'react';
import KindFilter from './KindFilter';

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
                        style={{ color: 'var(--text-secondary)', fontSize: 12, fontWeight: 600, letterSpacing: '0.02em' }}
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
 * Supports optional action button (e.g., "+ New").
 */
function BuildingBlockItem({ label, count, dotColor, active, defaultOpen = false, action, children }) {
    const [open, setOpen] = usePersistedOpen(`bb:${label}`, defaultOpen);

    return (
        <div>
            <div
                className="flex items-center"
                style={{
                    background: active ? 'var(--bg-selected)' : 'transparent',
                    borderLeft: active
                        ? '2px solid var(--action-primary)'
                        : '2px solid transparent',
                }}
            >
                <button
                    onClick={() => setOpen(!open)}
                    className="flex-1 px-4 py-2 flex items-center justify-between text-sm hover:opacity-80 transition-opacity"
                    style={{
                        background: 'transparent',
                        border: 'none',
                        color: active ? 'var(--text-primary)' : 'var(--text-secondary)',
                        cursor: 'pointer',
                        textAlign: 'left',
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
                {action && <div className="pr-2">{action}</div>}
            </div>
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
 *     > Prompt Fragments (count badge)
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
    promptFragments = [],
    promptFragmentKindOptions = [],
    schemas = [],
    loading = false,
    rolesLoading = false,
    templatesLoading = false,
    workflowsLoading = false,
    promptFragmentsLoading = false,
    schemasLoading = false,
    selectedDocType = null,
    docTypeSource = null,
    selectedRole = null,
    selectedTemplate = null,
    selectedWorkflow = null,
    selectedFragment = null,
    selectedSchema = null,
    onSelectDocType,
    onSelectRole,
    onSelectTemplate,
    onSelectWorkflow,
    onSelectFragment,
    onSelectStandaloneSchema,
    onCreateWorkflow,
    onCreateDocType,
    onCreateFragment,
    onCreateTemplate,
    onCreateSchema,
    onSelectTask,
    onSelectSchema,
    workspaceState = null,
}) {
    // Create workflow state: null | 'choose' | 'from_reference' | 'blank'
    const [createMode, setCreateMode] = useState(null);
    const [selectedReference, setSelectedReference] = useState(null);
    const [newWorkflowId, setNewWorkflowId] = useState('');
    const [creating, setCreating] = useState(false);

    // Create document type state
    const [dcwCreateMode, setDcwCreateMode] = useState(false);
    const [newDocTypeId, setNewDocTypeId] = useState('');
    const [creatingDocType, setCreatingDocType] = useState(false);

    // Prompt fragment filter state
    const [fragmentKindFilter, setFragmentKindFilter] = useState('all');

    // Creation dialog states
    const [createFragmentMode, setCreateFragmentMode] = useState(false);
    const [newFragmentKind, setNewFragmentKind] = useState('role');
    const [newFragmentId, setNewFragmentId] = useState('');
    const [creatingFragment, setCreatingFragment] = useState(false);

    const [createTemplateMode, setCreateTemplateMode] = useState(false);
    const [newTemplateId, setNewTemplateId] = useState('');
    const [creatingTemplate, setCreatingTemplate] = useState(false);

    const [createSchemaMode, setCreateSchemaMode] = useState(false);
    const [newSchemaId, setNewSchemaId] = useState('');
    const [creatingSchema, setCreatingSchema] = useState(false);

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

    // Filter prompt fragments by selected kind
    const filteredFragments = fragmentKindFilter === 'all'
        ? promptFragments
        : promptFragments.filter(f => f.kind === fragmentKindFilter);

    const resetCreateForm = () => {
        setCreateMode(null);
        setSelectedReference(null);
        setNewWorkflowId('');
    };

    const resetDcwCreateForm = () => {
        setDcwCreateMode(false);
        setNewDocTypeId('');
    };

    const resetFragmentCreateForm = () => {
        setCreateFragmentMode(false);
        setNewFragmentKind('role');
        setNewFragmentId('');
    };

    const resetTemplateCreateForm = () => {
        setCreateTemplateMode(false);
        setNewTemplateId('');
    };

    const resetSchemaCreateForm = () => {
        setCreateSchemaMode(false);
        setNewSchemaId('');
    };

    const handleCreateDocType = async () => {
        const id = newDocTypeId.trim().toLowerCase().replace(/\s+/g, '_');
        if (!id || !/^[a-z][a-z0-9_]*$/.test(id)) return;
        setCreatingDocType(true);
        try {
            await onCreateDocType?.({ doc_type_id: id });
            resetDcwCreateForm();
        } catch {
            // Error handled by parent
        } finally {
            setCreatingDocType(false);
        }
    };

    const handleCreateFragment = async () => {
        const id = newFragmentId.trim().toLowerCase().replace(/\s+/g, '_');
        if (!id || !/^[a-z][a-z0-9_]*$/.test(id)) return;
        setCreatingFragment(true);
        try {
            // For role fragments, pass role_id; API expects role_id for createRolePrompt
            await onCreateFragment?.({ role_id: id, kind: newFragmentKind });
            resetFragmentCreateForm();
        } catch {
            // Error handled by parent
        } finally {
            setCreatingFragment(false);
        }
    };

    const handleCreateTemplate = async () => {
        const id = newTemplateId.trim().toLowerCase().replace(/\s+/g, '_');
        if (!id || !/^[a-z][a-z0-9_]*$/.test(id)) return;
        setCreatingTemplate(true);
        try {
            await onCreateTemplate?.({ template_id: id });
            resetTemplateCreateForm();
        } catch {
            // Error handled by parent
        } finally {
            setCreatingTemplate(false);
        }
    };

    const handleCreateSchema = async () => {
        const id = newSchemaId.trim().toLowerCase().replace(/\s+/g, '_');
        if (!id || !/^[a-z][a-z0-9_]*$/.test(id)) return;
        setCreatingSchema(true);
        try {
            await onCreateSchema?.({ schema_id: id });
            resetSchemaCreateForm();
        } catch {
            // Error handled by parent
        } finally {
            setCreatingSchema(false);
        }
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
                    <SubSection
                        title="Document Creation (DCWs)"
                        dotColor="var(--dot-blue)"
                        action={
                            onCreateDocType && (
                                <button
                                    onClick={() => setDcwCreateMode(!dcwCreateMode)}
                                    className="text-xs hover:opacity-80"
                                    style={{
                                        color: 'var(--action-primary)',
                                        background: 'transparent',
                                        border: 'none',
                                        cursor: 'pointer',
                                        fontWeight: 600,
                                    }}
                                    title="Create new document type"
                                >
                                    + New
                                </button>
                            )
                        }
                    >
                        {/* Create Document Type Form */}
                        {dcwCreateMode && (
                            <div
                                className="px-4 py-2"
                                style={{ background: 'var(--bg-canvas)' }}
                            >
                                <input
                                    type="text"
                                    value={newDocTypeId}
                                    onChange={e => setNewDocTypeId(e.target.value)}
                                    onKeyDown={e => {
                                        if (e.key === 'Enter') handleCreateDocType();
                                        if (e.key === 'Escape') resetDcwCreateForm();
                                    }}
                                    placeholder="doc_type_id (snake_case)"
                                    autoFocus
                                    disabled={creatingDocType}
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
                                        onClick={handleCreateDocType}
                                        disabled={creatingDocType || !newDocTypeId.trim()}
                                        className="text-xs px-2 py-1 rounded hover:opacity-80"
                                        style={{
                                            background: 'var(--action-primary)',
                                            color: '#000',
                                            fontWeight: 600,
                                            border: 'none',
                                            cursor: creatingDocType ? 'wait' : 'pointer',
                                            opacity: (!newDocTypeId.trim() || creatingDocType) ? 0.5 : 1,
                                        }}
                                    >
                                        {creatingDocType ? 'Creating...' : 'Create'}
                                    </button>
                                    <button
                                        onClick={resetDcwCreateForm}
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
                    BUILDING BLOCKS (Per WS-ADR-044-002)
                    - Prompt Fragments: unified view with kind filter
                    - Templates: separate (composition with $$TOKEN slots)
                    - Schemas: separate (JSON editor)
                    ============================================================ */}
                <CollapsibleGroup title="Building Blocks" defaultOpen={true}>
                    {/* --- Prompt Fragments (unified) --- */}
                    <BuildingBlockItem
                        label="Prompt Fragments"
                        count={promptFragments.length}
                        dotColor="#f59e0b"
                        active={!!selectedFragment}
                        defaultOpen={true}
                        action={
                            onCreateFragment && (
                                <button
                                    onClick={() => setCreateFragmentMode(!createFragmentMode)}
                                    className="text-xs hover:opacity-80"
                                    style={{
                                        color: 'var(--action-primary)',
                                        background: 'transparent',
                                        border: 'none',
                                        cursor: 'pointer',
                                        fontWeight: 600,
                                    }}
                                    title="Create new prompt fragment"
                                >
                                    + New
                                </button>
                            )
                        }
                    >
                        {/* Create Fragment Form */}
                        {createFragmentMode && (
                            <div
                                className="px-4 py-2"
                                style={{ background: 'var(--bg-canvas)' }}
                            >
                                <div className="mb-2">
                                    <label className="block text-xs mb-1" style={{ color: 'var(--text-muted)' }}>
                                        Kind
                                    </label>
                                    <select
                                        value={newFragmentKind}
                                        onChange={e => setNewFragmentKind(e.target.value)}
                                        className="w-full text-xs px-2 py-1.5 rounded"
                                        style={{
                                            background: 'var(--bg-input, var(--bg-panel))',
                                            border: '1px solid var(--border-panel)',
                                            color: 'var(--text-primary)',
                                        }}
                                    >
                                        <option value="role">Role</option>
                                    </select>
                                </div>
                                <input
                                    type="text"
                                    value={newFragmentId}
                                    onChange={e => setNewFragmentId(e.target.value)}
                                    onKeyDown={e => {
                                        if (e.key === 'Enter') handleCreateFragment();
                                        if (e.key === 'Escape') resetFragmentCreateForm();
                                    }}
                                    placeholder="fragment_id (snake_case)"
                                    autoFocus
                                    disabled={creatingFragment}
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
                                        onClick={handleCreateFragment}
                                        disabled={creatingFragment || !newFragmentId.trim()}
                                        className="text-xs px-2 py-1 rounded hover:opacity-80"
                                        style={{
                                            background: 'var(--action-primary)',
                                            color: '#000',
                                            fontWeight: 600,
                                            border: 'none',
                                            cursor: creatingFragment ? 'wait' : 'pointer',
                                            opacity: (!newFragmentId.trim() || creatingFragment) ? 0.5 : 1,
                                        }}
                                    >
                                        {creatingFragment ? 'Creating...' : 'Create'}
                                    </button>
                                    <button
                                        onClick={resetFragmentCreateForm}
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
                        {/* Kind filter pills */}
                        {promptFragmentKindOptions.length > 0 && (
                            <KindFilter
                                kinds={promptFragmentKindOptions}
                                selectedKind={fragmentKindFilter}
                                onSelect={setFragmentKindFilter}
                            />
                        )}
                        <SectionState
                            loading={promptFragmentsLoading}
                            empty={!promptFragmentsLoading && filteredFragments.length === 0}
                            emptyMessage={fragmentKindFilter === 'all' ? 'No prompt fragments' : `No ${fragmentKindFilter} fragments`}
                        />
                        {!promptFragmentsLoading && filteredFragments.length > 0 && (
                            <div className="py-1">
                                {filteredFragments.map(fragment => (
                                    <ItemButton
                                        key={fragment.fragment_id}
                                        selected={selectedFragment?.fragment_id === fragment.fragment_id}
                                        onClick={() => onSelectFragment?.(fragment)}
                                        label={fragment.name || fragment.fragment_id}
                                        sublabel={`${fragment.kind} · v${fragment.version}`}
                                        badge={fragment.kind}
                                    />
                                ))}
                            </div>
                        )}
                    </BuildingBlockItem>

                    {/* --- Templates (separate - composition structure) --- */}
                    <BuildingBlockItem
                        label="Templates"
                        count={templates.length}
                        dotColor="var(--dot-green)"
                        active={!!selectedTemplate}
                        action={
                            onCreateTemplate && (
                                <button
                                    onClick={() => setCreateTemplateMode(!createTemplateMode)}
                                    className="text-xs hover:opacity-80"
                                    style={{
                                        color: 'var(--action-primary)',
                                        background: 'transparent',
                                        border: 'none',
                                        cursor: 'pointer',
                                        fontWeight: 600,
                                    }}
                                    title="Create new template"
                                >
                                    + New
                                </button>
                            )
                        }
                    >
                        {/* Create Template Form */}
                        {createTemplateMode && (
                            <div
                                className="px-4 py-2"
                                style={{ background: 'var(--bg-canvas)' }}
                            >
                                <input
                                    type="text"
                                    value={newTemplateId}
                                    onChange={e => setNewTemplateId(e.target.value)}
                                    onKeyDown={e => {
                                        if (e.key === 'Enter') handleCreateTemplate();
                                        if (e.key === 'Escape') resetTemplateCreateForm();
                                    }}
                                    placeholder="template_id (snake_case)"
                                    autoFocus
                                    disabled={creatingTemplate}
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
                                        onClick={handleCreateTemplate}
                                        disabled={creatingTemplate || !newTemplateId.trim()}
                                        className="text-xs px-2 py-1 rounded hover:opacity-80"
                                        style={{
                                            background: 'var(--action-primary)',
                                            color: '#000',
                                            fontWeight: 600,
                                            border: 'none',
                                            cursor: creatingTemplate ? 'wait' : 'pointer',
                                            opacity: (!newTemplateId.trim() || creatingTemplate) ? 0.5 : 1,
                                        }}
                                    >
                                        {creatingTemplate ? 'Creating...' : 'Create'}
                                    </button>
                                    <button
                                        onClick={resetTemplateCreateForm}
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
                                        label={template.name || template.template_id.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                                        sublabel={`v${template.active_version}`}
                                    />
                                ))}
                            </div>
                        )}
                    </BuildingBlockItem>

                    {/* --- Schemas (separate - JSON editor) --- */}
                    <BuildingBlockItem
                        label="Schemas"
                        count={schemas.length || documentTypes.length}
                        dotColor="var(--dot-blue)"
                        active={docTypeSource === 'schema' || !!selectedSchema}
                        action={
                            onCreateSchema && (
                                <button
                                    onClick={() => setCreateSchemaMode(!createSchemaMode)}
                                    className="text-xs hover:opacity-80"
                                    style={{
                                        color: 'var(--action-primary)',
                                        background: 'transparent',
                                        border: 'none',
                                        cursor: 'pointer',
                                        fontWeight: 600,
                                    }}
                                    title="Create new schema"
                                >
                                    + New
                                </button>
                            )
                        }
                    >
                        {/* Create Schema Form */}
                        {createSchemaMode && (
                            <div
                                className="px-4 py-2"
                                style={{ background: 'var(--bg-canvas)' }}
                            >
                                <input
                                    type="text"
                                    value={newSchemaId}
                                    onChange={e => setNewSchemaId(e.target.value)}
                                    onKeyDown={e => {
                                        if (e.key === 'Enter') handleCreateSchema();
                                        if (e.key === 'Escape') resetSchemaCreateForm();
                                    }}
                                    placeholder="schema_id (snake_case)"
                                    autoFocus
                                    disabled={creatingSchema}
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
                                        onClick={handleCreateSchema}
                                        disabled={creatingSchema || !newSchemaId.trim()}
                                        className="text-xs px-2 py-1 rounded hover:opacity-80"
                                        style={{
                                            background: 'var(--action-primary)',
                                            color: '#000',
                                            fontWeight: 600,
                                            border: 'none',
                                            cursor: creatingSchema ? 'wait' : 'pointer',
                                            opacity: (!newSchemaId.trim() || creatingSchema) ? 0.5 : 1,
                                        }}
                                    >
                                        {creatingSchema ? 'Creating...' : 'Create'}
                                    </button>
                                    <button
                                        onClick={resetSchemaCreateForm}
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
                            loading={schemasLoading || loading}
                            empty={!schemasLoading && !loading && (schemas.length === 0 && documentTypes.length === 0)}
                            emptyMessage="No schemas"
                        />
                        {/* Standalone schemas first */}
                        {!schemasLoading && schemas.length > 0 && (
                            <div className="py-1">
                                {schemas.map(schema => (
                                    <ItemButton
                                        key={`standalone-${schema.schema_id}`}
                                        selected={selectedSchema?.schema_id === schema.schema_id}
                                        onClick={() => onSelectStandaloneSchema?.(schema)}
                                        label={schema.title || schema.schema_id}
                                        sublabel={`v${schema.active_version}`}
                                    />
                                ))}
                            </div>
                        )}
                        {/* DCW-derived schemas fallback */}
                        {!loading && schemas.length === 0 && documentTypes.length > 0 && (
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
