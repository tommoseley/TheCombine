import React, { useState } from 'react';

/**
 * Left sidebar for browsing and selecting document types, roles, templates, and workflows.
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
}) {
    const [showNewWorkflowForm, setShowNewWorkflowForm] = useState(false);
    const [newWorkflowId, setNewWorkflowId] = useState('');
    const [creating, setCreating] = useState(false);

    // Group doc types by category
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

    return (
        <div
            className="w-60 flex flex-col border-r h-full"
            style={{
                borderColor: 'var(--border-panel)',
                background: 'var(--bg-panel)',
            }}
        >
            {/* Document Types Section */}
            <div
                className="px-4 py-3 border-b"
                style={{ borderColor: 'var(--border-panel)' }}
            >
                <h2
                    className="text-sm font-semibold uppercase tracking-wide"
                    style={{ color: 'var(--text-muted)' }}
                >
                    Document Types
                </h2>
            </div>

            {/* Document Types List */}
            <div className="flex-1 overflow-y-auto">
                {loading ? (
                    <div className="p-4 text-sm" style={{ color: 'var(--text-muted)' }}>
                        Loading...
                    </div>
                ) : documentTypes.length === 0 ? (
                    <div className="p-4 text-sm" style={{ color: 'var(--text-muted)' }}>
                        No document types found
                    </div>
                ) : (
                    sortedCategories.map(category => (
                        <div key={category} className="py-2">
                            <div
                                className="px-4 py-1 text-xs font-medium uppercase tracking-wider"
                                style={{ color: 'var(--text-muted)' }}
                            >
                                {category}
                            </div>
                            {grouped[category].map(dt => (
                                <button
                                    key={dt.doc_type_id}
                                    onClick={() => {
                                        onSelectDocType?.(dt);
                                    }}
                                    className="w-full px-4 py-2 text-left text-sm hover:opacity-80 transition-opacity"
                                    style={{
                                        background: selectedDocType?.doc_type_id === dt.doc_type_id
                                            ? 'var(--bg-selected)'
                                            : 'transparent',
                                        color: selectedDocType?.doc_type_id === dt.doc_type_id
                                            ? 'var(--text-primary)'
                                            : 'var(--text-secondary)',
                                        borderLeft: selectedDocType?.doc_type_id === dt.doc_type_id
                                            ? '2px solid var(--action-primary)'
                                            : '2px solid transparent',
                                    }}
                                >
                                    <div className="font-medium truncate">{dt.display_name}</div>
                                    <div
                                        className="text-xs truncate"
                                        style={{ color: 'var(--text-muted)' }}
                                    >
                                        v{dt.active_version}
                                        {dt.authority_level && ` \u00b7 ${dt.authority_level}`}
                                    </div>
                                </button>
                            ))}
                        </div>
                    ))
                )}
            </div>

            {/* Roles Section */}
            <div
                className="px-4 py-3 border-t border-b"
                style={{ borderColor: 'var(--border-panel)' }}
            >
                <h2
                    className="text-sm font-semibold uppercase tracking-wide"
                    style={{ color: 'var(--text-muted)' }}
                >
                    Roles
                </h2>
            </div>

            {/* Roles List */}
            <div className="overflow-y-auto" style={{ maxHeight: '150px' }}>
                {rolesLoading ? (
                    <div className="p-4 text-sm" style={{ color: 'var(--text-muted)' }}>
                        Loading...
                    </div>
                ) : roles.length === 0 ? (
                    <div className="p-4 text-sm" style={{ color: 'var(--text-muted)' }}>
                        No roles found
                    </div>
                ) : (
                    <div className="py-2">
                        {roles.map(role => (
                            <button
                                key={role.role_id}
                                onClick={() => {
                                    onSelectRole?.(role);
                                }}
                                className="w-full px-4 py-2 text-left text-sm hover:opacity-80 transition-opacity"
                                style={{
                                    background: selectedRole?.role_id === role.role_id
                                        ? 'var(--bg-selected)'
                                        : 'transparent',
                                    color: selectedRole?.role_id === role.role_id
                                        ? 'var(--text-primary)'
                                        : 'var(--text-secondary)',
                                    borderLeft: selectedRole?.role_id === role.role_id
                                        ? '2px solid var(--action-primary)'
                                        : '2px solid transparent',
                                }}
                            >
                                <div className="font-medium truncate">
                                    {role.role_id.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                                </div>
                                <div
                                    className="text-xs truncate"
                                    style={{ color: 'var(--text-muted)' }}
                                >
                                    v{role.active_version}
                                </div>
                            </button>
                        ))}
                    </div>
                )}
            </div>

            {/* Templates Section */}
            <div
                className="px-4 py-3 border-t border-b"
                style={{ borderColor: 'var(--border-panel)' }}
            >
                <h2
                    className="text-sm font-semibold uppercase tracking-wide"
                    style={{ color: 'var(--text-muted)' }}
                >
                    Templates
                </h2>
            </div>

            {/* Templates List */}
            <div className="overflow-y-auto" style={{ maxHeight: '150px' }}>
                {templatesLoading ? (
                    <div className="p-4 text-sm" style={{ color: 'var(--text-muted)' }}>
                        Loading...
                    </div>
                ) : templates.length === 0 ? (
                    <div className="p-4 text-sm" style={{ color: 'var(--text-muted)' }}>
                        No templates found
                    </div>
                ) : (
                    <div className="py-2">
                        {templates.map(template => (
                            <button
                                key={template.template_id}
                                onClick={() => {
                                    onSelectTemplate?.(template);
                                }}
                                className="w-full px-4 py-2 text-left text-sm hover:opacity-80 transition-opacity"
                                style={{
                                    background: selectedTemplate?.template_id === template.template_id
                                        ? 'var(--bg-selected)'
                                        : 'transparent',
                                    color: selectedTemplate?.template_id === template.template_id
                                        ? 'var(--text-primary)'
                                        : 'var(--text-secondary)',
                                    borderLeft: selectedTemplate?.template_id === template.template_id
                                        ? '2px solid var(--action-primary)'
                                        : '2px solid transparent',
                                }}
                            >
                                <div className="font-medium truncate">
                                    {template.template_id.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                                </div>
                                <div
                                    className="text-xs truncate"
                                    style={{ color: 'var(--text-muted)' }}
                                >
                                    v{template.active_version}
                                </div>
                            </button>
                        ))}
                    </div>
                )}
            </div>

            {/* Workflows Section */}
            <div
                className="px-4 py-3 border-t border-b flex items-center justify-between"
                style={{ borderColor: 'var(--border-panel)' }}
            >
                <h2
                    className="text-sm font-semibold uppercase tracking-wide"
                    style={{ color: 'var(--text-muted)' }}
                >
                    Workflows
                </h2>
                {onCreateWorkflow && (
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
                )}
            </div>

            {/* New Workflow Form */}
            {showNewWorkflowForm && (
                <div
                    className="px-4 py-2 border-b"
                    style={{ borderColor: 'var(--border-panel)', background: 'var(--bg-canvas)' }}
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

            {/* Workflows List */}
            <div className="overflow-y-auto" style={{ maxHeight: '150px' }}>
                {workflowsLoading ? (
                    <div className="p-4 text-sm" style={{ color: 'var(--text-muted)' }}>
                        Loading...
                    </div>
                ) : workflows.length === 0 ? (
                    <div className="p-4 text-sm" style={{ color: 'var(--text-muted)' }}>
                        No workflows found
                    </div>
                ) : (
                    <div className="py-2">
                        {workflows.map(wf => (
                            <button
                                key={wf.workflow_id}
                                onClick={() => {
                                    onSelectWorkflow?.(wf);
                                }}
                                className="w-full px-4 py-2 text-left text-sm hover:opacity-80 transition-opacity"
                                style={{
                                    background: selectedWorkflow?.workflow_id === wf.workflow_id
                                        ? 'var(--bg-selected)'
                                        : 'transparent',
                                    color: selectedWorkflow?.workflow_id === wf.workflow_id
                                        ? 'var(--text-primary)'
                                        : 'var(--text-secondary)',
                                    borderLeft: selectedWorkflow?.workflow_id === wf.workflow_id
                                        ? '2px solid var(--action-primary)'
                                        : '2px solid transparent',
                                }}
                            >
                                <div className="font-medium truncate">
                                    {wf.workflow_id.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                                </div>
                                <div
                                    className="text-xs truncate"
                                    style={{ color: 'var(--text-muted)' }}
                                >
                                    v{wf.active_version}
                                    {wf.step_count != null && ` \u00b7 ${wf.step_count} steps`}
                                </div>
                            </button>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
