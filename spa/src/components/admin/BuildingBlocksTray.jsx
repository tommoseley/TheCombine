import React, { useState, useCallback, useEffect } from 'react';
import KindFilter from './KindFilter';

/**
 * Collapsible section within the tray.
 */
function TraySection({ title, count, dotColor, defaultOpen = false, action, children }) {
    const [open, setOpen] = useState(defaultOpen);

    return (
        <div style={{ borderBottom: '1px solid var(--border-panel)' }}>
            <div
                className="flex items-center"
                style={{ background: 'var(--bg-subsection-header)' }}
            >
                <button
                    onClick={() => setOpen(!open)}
                    className="flex-1 px-4 py-2.5 flex items-center justify-between text-sm hover:opacity-80 transition-opacity"
                    style={{
                        background: 'transparent',
                        border: 'none',
                        color: 'var(--text-secondary)',
                        cursor: 'pointer',
                        textAlign: 'left',
                    }}
                >
                    <span className="flex items-center gap-2">
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
                        <span style={{ color: dotColor, fontSize: 10 }}>&#9679;</span>
                        <span className="font-semibold">{title}</span>
                    </span>
                    <span
                        style={{
                            fontSize: 9,
                            fontFamily: 'monospace',
                            color: 'var(--text-muted)',
                        }}
                    >
                        {count}
                    </span>
                </button>
                {action && <div className="pr-3">{action}</div>}
            </div>
            {open && (
                <div style={{ background: 'var(--bg-panel)' }}>
                    {children}
                </div>
            )}
        </div>
    );
}

/**
 * Item button within a tray section.
 */
function TrayItem({ onClick, label, sublabel, badge, isSelected }) {
    return (
        <button
            onClick={onClick}
            className="w-full px-4 py-2 text-left text-sm hover:opacity-80 transition-opacity"
            style={{
                background: isSelected ? 'var(--bg-selected, rgba(99, 102, 241, 0.15))' : 'transparent',
                border: 'none',
                borderLeft: isSelected ? '3px solid var(--action-primary)' : '3px solid transparent',
                color: isSelected ? 'var(--text-primary)' : 'var(--text-secondary)',
                cursor: 'pointer',
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
 * Loading / empty state.
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
 * BuildingBlocksTray - Slide-out drawer for Building Blocks.
 *
 * Per WS-ADR-044-003, Building Blocks (Prompt Fragments, Templates, Schemas) are
 * moved from the left rail to this secondary tray. The tray is:
 * - Collapsed by default on page load
 * - Never auto-opens
 * - Only opened intentionally by user
 * - Click item -> opens editor (tray stays open)
 * - Close button or click-outside -> closes tray
 *
 * Per ADR-047, Mechanical Operations are added as a new Building Block type.
 */
export default function BuildingBlocksTray({
    isOpen,
    onClose,
    // Data
    promptFragments = [],
    promptFragmentKindOptions = [],
    templates = [],
    schemas = [],
    documentTypes = [], // Fallback for DCW-derived schemas
    mechanicalOpTypes = [],
    mechanicalOps = [],
    // Loading states
    promptFragmentsLoading = false,
    templatesLoading = false,
    schemasLoading = false,
    mechanicalOpsLoading = false,
    // Selected items (for highlighting)
    selectedFragment = null,
    selectedTemplate = null,
    selectedSchema = null,
    selectedMechanicalOp = null,
    // Handlers
    onSelectFragment,
    onSelectTemplate,
    onSelectSchema,
    onSelectStandaloneSchema,
    onSelectMechanicalOp,
    onCreateFragment,
    onCreateTemplate,
    onCreateSchema,
}) {
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

    // Filter prompt fragments by selected kind
    const filteredFragments = fragmentKindFilter === 'all'
        ? promptFragments
        : promptFragments.filter(f => f.kind === fragmentKindFilter);

    // Reset forms when tray closes
    useEffect(() => {
        if (!isOpen) {
            setCreateFragmentMode(false);
            setCreateTemplateMode(false);
            setCreateSchemaMode(false);
            setNewFragmentId('');
            setNewTemplateId('');
            setNewSchemaId('');
        }
    }, [isOpen]);

    // Select item without closing tray (user requested behavior)
    const handleSelect = useCallback((handler, item) => {
        handler?.(item);
    }, []);

    const handleCreateFragment = async () => {
        const id = newFragmentId.trim().toLowerCase().replace(/\s+/g, '_');
        if (!id || !/^[a-z][a-z0-9_]*$/.test(id)) return;
        setCreatingFragment(true);
        try {
            await onCreateFragment?.({ role_id: id, kind: newFragmentKind });
            setCreateFragmentMode(false);
            setNewFragmentId('');
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
            setCreateTemplateMode(false);
            setNewTemplateId('');
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
            setCreateSchemaMode(false);
            setNewSchemaId('');
        } catch {
            // Error handled by parent
        } finally {
            setCreatingSchema(false);
        }
    };

    if (!isOpen) return null;

    return (
        <>
            {/* Backdrop overlay - visual only, close via X button */}
            <div
                style={{
                    position: 'fixed',
                    inset: 0,
                    background: 'rgba(0, 0, 0, 0.15)',
                    zIndex: 40,
                    pointerEvents: 'none',
                }}
            />

            {/* Tray panel */}
            <div
                className="fixed right-0 top-0 h-full flex flex-col"
                style={{
                    width: 320,
                    background: 'var(--bg-panel)',
                    borderLeft: '1px solid var(--border-panel)',
                    boxShadow: '-4px 0 20px rgba(0, 0, 0, 0.2)',
                    zIndex: 50,
                    animation: 'slideInFromRight 200ms ease-out',
                }}
            >
                {/* Header */}
                <div
                    className="flex items-center justify-between px-4 py-3"
                    style={{
                        background: 'var(--bg-group-header)',
                        borderBottom: '1px solid var(--border-panel)',
                    }}
                >
                    <span
                        className="font-bold uppercase tracking-widest"
                        style={{ color: 'var(--text-primary)', fontSize: 11 }}
                    >
                        Building Blocks
                    </span>
                    <button
                        onClick={onClose}
                        className="text-lg hover:opacity-80"
                        style={{
                            background: 'transparent',
                            border: 'none',
                            color: 'var(--text-muted)',
                            cursor: 'pointer',
                            lineHeight: 1,
                            padding: '2px 6px',
                        }}
                        title="Close"
                    >
                        &times;
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto">
                    {/* --- Prompt Fragments --- */}
                    <TraySection
                        title="Prompt Fragments"
                        count={promptFragments.length}
                        dotColor="#f59e0b"
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
                                        if (e.key === 'Escape') setCreateFragmentMode(false);
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
                                        onClick={() => setCreateFragmentMode(false)}
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
                                    <TrayItem
                                        key={fragment.fragment_id}
                                        onClick={() => handleSelect(onSelectFragment, fragment)}
                                        label={fragment.name || fragment.fragment_id}
                                        sublabel={`${fragment.kind} · v${fragment.version}`}
                                        badge={fragment.kind}
                                        isSelected={selectedFragment?.fragment_id === fragment.fragment_id}
                                    />
                                ))}
                            </div>
                        )}
                    </TraySection>

                    {/* --- Templates --- */}
                    <TraySection
                        title="Templates"
                        count={templates.length}
                        dotColor="var(--dot-green)"
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
                                        if (e.key === 'Escape') setCreateTemplateMode(false);
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
                                        onClick={() => setCreateTemplateMode(false)}
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
                                    <TrayItem
                                        key={template.template_id}
                                        onClick={() => handleSelect(onSelectTemplate, template)}
                                        label={template.name || template.template_id.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                                        sublabel={`v${template.active_version}`}
                                        isSelected={selectedTemplate?.template_id === template.template_id}
                                    />
                                ))}
                            </div>
                        )}
                    </TraySection>

                    {/* --- Schemas --- */}
                    <TraySection
                        title="Schemas"
                        count={schemas.length || documentTypes.length}
                        dotColor="var(--dot-blue)"
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
                                        if (e.key === 'Escape') setCreateSchemaMode(false);
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
                                        onClick={() => setCreateSchemaMode(false)}
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
                            loading={schemasLoading}
                            empty={!schemasLoading && schemas.length === 0 && documentTypes.length === 0}
                            emptyMessage="No schemas"
                        />

                        {/* Standalone schemas */}
                        {!schemasLoading && schemas.length > 0 && (
                            <div className="py-1">
                                {schemas.map(schema => (
                                    <TrayItem
                                        key={`standalone-${schema.schema_id}`}
                                        onClick={() => handleSelect(onSelectStandaloneSchema, schema)}
                                        label={schema.title || schema.schema_id}
                                        sublabel={`v${schema.active_version}`}
                                        isSelected={selectedSchema?.schema_id === schema.schema_id}
                                    />
                                ))}
                            </div>
                        )}

                        {/* DCW-derived schemas fallback */}
                        {schemas.length === 0 && documentTypes.length > 0 && (
                            <div className="py-1">
                                {documentTypes.map(dt => (
                                    <TrayItem
                                        key={`schema-${dt.doc_type_id}`}
                                        onClick={() => handleSelect(onSelectSchema, {
                                            doc_type_id: dt.doc_type_id,
                                            display_name: dt.display_name,
                                            active_version: dt.active_version,
                                        })}
                                        label={dt.display_name}
                                        sublabel={`from ${dt.doc_type_id}`}
                                    />
                                ))}
                            </div>
                        )}
                    </TraySection>

                    {/* --- Mechanical Operations (ADR-047) --- */}
                    <TraySection
                        title="Mechanical Ops"
                        count={mechanicalOps.length}
                        dotColor="var(--dot-purple, #a855f7)"
                    >
                        <SectionState
                            loading={mechanicalOpsLoading}
                            empty={!mechanicalOpsLoading && mechanicalOps.length === 0 && mechanicalOpTypes.length === 0}
                            emptyMessage="No mechanical operations"
                        />

                        {/* Group operations by type */}
                        {!mechanicalOpsLoading && mechanicalOpTypes.length > 0 && (
                            <div className="py-1">
                                {mechanicalOpTypes.map(opType => {
                                    const opsOfType = mechanicalOps.filter(op => op.type === opType.type_id);
                                    return (
                                        <div key={opType.type_id}>
                                            {/* Type header */}
                                            <div
                                                className="px-4 py-1.5 text-xs font-semibold flex items-center gap-2"
                                                style={{ color: 'var(--text-muted)' }}
                                            >
                                                <span style={{ fontSize: 10 }}>⚙</span>
                                                <span>{opType.name}</span>
                                                <span style={{ fontFamily: 'monospace', fontSize: 9 }}>
                                                    ({opsOfType.length})
                                                </span>
                                            </div>
                                            {/* Operations of this type */}
                                            {opsOfType.length > 0 ? (
                                                opsOfType.map(op => (
                                                    <TrayItem
                                                        key={op.op_id}
                                                        onClick={() => handleSelect(onSelectMechanicalOp, op)}
                                                        label={op.name}
                                                        sublabel={`v${op.active_version}`}
                                                        badge={op.type}
                                                        isSelected={selectedMechanicalOp?.op_id === op.op_id}
                                                    />
                                                ))
                                            ) : (
                                                <div
                                                    className="px-6 py-1 text-xs italic"
                                                    style={{ color: 'var(--text-muted)' }}
                                                >
                                                    No instances
                                                </div>
                                            )}
                                        </div>
                                    );
                                })}
                            </div>
                        )}

                        {/* Show types even if no instances, when ops not loading but types loaded */}
                        {!mechanicalOpsLoading && mechanicalOpTypes.length === 0 && mechanicalOps.length === 0 && (
                            <div
                                className="px-4 py-2 text-xs"
                                style={{ color: 'var(--text-muted)' }}
                            >
                                Operation types not loaded
                            </div>
                        )}
                    </TraySection>
                </div>
            </div>

            {/* Slide-in animation */}
            <style>{`
                @keyframes slideInFromRight {
                    from {
                        transform: translateX(100%);
                    }
                    to {
                        transform: translateX(0);
                    }
                }
            `}</style>
        </>
    );
}
