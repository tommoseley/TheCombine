import React from 'react';

const TAB_STYLE = {
    padding: '6px 14px',
    fontSize: 12,
    fontWeight: 600,
    border: 'none',
    cursor: 'pointer',
    transition: 'opacity 0.15s',
    background: 'transparent',
};

const TABS = [
    { id: 'steps', label: 'Steps' },
    { id: 'json', label: 'JSON' },
    { id: 'metadata', label: 'Metadata' },
];

/**
 * Header bar + tab strip for the StepWorkflowEditor.
 * Displays workflow name, version, pow_class badge, saving/error indicators,
 * delete button, and the steps/json/metadata tab bar.
 */
export default function EditorToolbar({
    workflow,
    workflowJson,
    activeTab,
    onTabChange,
    saving,
    error,
    onDelete,
    onDeleteWorkflow,
}) {
    return (
        <>
            {/* Header */}
            <div
                className="px-4 py-3 border-b"
                style={{ borderColor: 'var(--border-panel)', background: 'var(--bg-panel)' }}
            >
                <div className="flex items-center justify-between">
                    <div>
                        <div className="flex items-center gap-2">
                            <span className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                                {workflowJson?.name || workflow.workflow_id.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                            </span>
                            {(workflowJson?.pow_class || workflow.pow_class) && (
                                <span
                                    className="text-xs px-1.5 py-0.5 rounded font-semibold uppercase"
                                    style={{
                                        fontSize: 9,
                                        letterSpacing: '0.05em',
                                        background: (workflowJson?.pow_class || workflow.pow_class) === 'reference'
                                            ? 'var(--action-primary)'
                                            : 'var(--bg-selected, #334155)',
                                        color: (workflowJson?.pow_class || workflow.pow_class) === 'reference'
                                            ? '#000'
                                            : 'var(--text-primary)',
                                    }}
                                >
                                    {workflowJson?.pow_class || workflow.pow_class}
                                </span>
                            )}
                        </div>
                        <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
                            v{workflow.active_version}
                            {workflowJson?.description && ` \u2014 ${workflowJson.description}`}
                        </div>
                    </div>
                    <div className="flex items-center gap-3">
                        {saving && (
                            <span className="text-xs" style={{ color: 'var(--action-primary)' }}>
                                Saving...
                            </span>
                        )}
                        {error && (
                            <span className="text-xs" style={{ color: '#ef4444' }}>
                                {error}
                            </span>
                        )}
                        {onDelete && (
                            <button
                                onClick={onDeleteWorkflow}
                                className="p-1 rounded hover:bg-red-500/20 transition-colors"
                                style={{ color: '#ef4444' }}
                                title="Delete workflow"
                            >
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                    <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" />
                                </svg>
                            </button>
                        )}
                    </div>
                </div>
            </div>

            {/* Tab bar */}
            <div
                className="flex items-center border-b px-2"
                style={{ borderColor: 'var(--border-panel)', background: 'var(--bg-panel)' }}
            >
                {TABS.map(tab => (
                    <button
                        key={tab.id}
                        onClick={() => onTabChange(tab.id)}
                        style={{
                            ...TAB_STYLE,
                            color: activeTab === tab.id ? 'var(--text-primary)' : 'var(--text-muted)',
                            borderBottom: activeTab === tab.id
                                ? '2px solid var(--action-primary)'
                                : '2px solid transparent',
                        }}
                    >
                        {tab.label}
                    </button>
                ))}
            </div>
        </>
    );
}
