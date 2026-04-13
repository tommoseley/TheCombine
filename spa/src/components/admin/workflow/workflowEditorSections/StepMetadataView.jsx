import React, { useState } from 'react';

export function StepMetadataView({ workflow, onUpdateWorkflow, onNavigateToWorkflow }) {
    const [newTag, setNewTag] = useState('');

    const metaFieldStyle = {
        fontSize: 12,
        color: 'var(--text-primary)',
        padding: '6px 8px',
        borderRadius: 4,
        background: 'var(--bg-input, var(--bg-canvas))',
        border: '1px solid var(--border-panel)',
        width: '100%',
    };

    const metaLabelStyle = {
        display: 'block',
        fontSize: 10,
        fontWeight: 600,
        color: 'var(--text-muted)',
        marginBottom: 2,
        textTransform: 'uppercase',
        letterSpacing: '0.05em',
    };

    const fields = [
        { key: 'workflow_id', label: 'Workflow ID' },
        { key: 'name', label: 'Name' },
        { key: 'schema_version', label: 'Schema Version' },
        { key: 'revision', label: 'Revision' },
        { key: 'effective_date', label: 'Effective Date' },
        { key: 'description', label: 'Description' },
    ];

    const scopes = workflow.scopes || {};
    const scopeEntries = Object.entries(scopes);
    const docTypes = workflow.document_types || {};
    const docTypeEntries = Object.entries(docTypes);

    const powClass = workflow.pow_class || 'reference';
    const derivedFrom = workflow.derived_from;
    const sourceVersion = workflow.source_version;
    const tags = workflow.tags || [];

    const handleAddTag = () => {
        const tag = newTag.trim().toLowerCase().replace(/\s+/g, '_');
        if (!tag || tags.includes(tag)) return;
        onUpdateWorkflow?.({ ...workflow, tags: [...tags, tag] });
        setNewTag('');
    };

    const handleRemoveTag = (tagToRemove) => {
        onUpdateWorkflow?.({ ...workflow, tags: tags.filter(t => t !== tagToRemove) });
    };

    const handleNavigateToDerived = () => {
        if (derivedFrom?.workflow_id && onNavigateToWorkflow) {
            onNavigateToWorkflow(derivedFrom.workflow_id);
        }
    };

    return (
        <div className="space-y-4 max-w-lg">
            {/* Classification */}
            <h3
                className="text-xs font-semibold uppercase tracking-wide"
                style={{ color: 'var(--text-muted)' }}
            >
                Classification
            </h3>

            <div>
                <label style={metaLabelStyle}>POW Class</label>
                <div className="flex items-center gap-2">
                    <span
                        className="text-xs px-2 py-1 rounded font-semibold uppercase"
                        style={{
                            fontSize: 10,
                            letterSpacing: '0.05em',
                            background: powClass === 'reference'
                                ? 'var(--action-primary)'
                                : 'var(--bg-selected, #334155)',
                            color: powClass === 'reference' ? '#000' : 'var(--text-primary)',
                        }}
                    >
                        {powClass}
                    </span>
                </div>
            </div>

            {derivedFrom && (
                <div>
                    <label style={metaLabelStyle}>Derived From</label>
                    <div style={metaFieldStyle}>
                        {onNavigateToWorkflow ? (
                            <button
                                onClick={handleNavigateToDerived}
                                className="hover:opacity-80"
                                style={{
                                    background: 'transparent',
                                    border: 'none',
                                    padding: 0,
                                    cursor: 'pointer',
                                    color: 'var(--action-primary)',
                                    textDecoration: 'underline',
                                    fontSize: 12,
                                }}
                            >
                                {derivedFrom.workflow_id} v{derivedFrom.version}
                            </button>
                        ) : (
                            <span>{derivedFrom.workflow_id} v{derivedFrom.version}</span>
                        )}
                    </div>
                </div>
            )}

            {sourceVersion && (
                <div>
                    <label style={metaLabelStyle}>Source Version</label>
                    <div style={metaFieldStyle}>{sourceVersion}</div>
                </div>
            )}

            <div>
                <label style={metaLabelStyle}>Tags</label>
                <div className="flex flex-wrap gap-1 mb-1.5">
                    {tags.length === 0 && (
                        <span className="text-xs" style={{ color: 'var(--text-muted)' }}>No tags</span>
                    )}
                    {tags.map(tag => (
                        <span
                            key={tag}
                            className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded"
                            style={{
                                background: 'var(--bg-selected, #334155)',
                                color: 'var(--text-primary)',
                                fontSize: 11,
                            }}
                        >
                            {tag}
                            {onUpdateWorkflow && (
                                <button
                                    onClick={() => handleRemoveTag(tag)}
                                    className="hover:opacity-80"
                                    style={{
                                        background: 'transparent',
                                        border: 'none',
                                        padding: 0,
                                        cursor: 'pointer',
                                        color: 'var(--text-muted)',
                                        fontSize: 11,
                                        lineHeight: 1,
                                    }}
                                    title={`Remove tag "${tag}"`}
                                >
                                    x
                                </button>
                            )}
                        </span>
                    ))}
                </div>
                {onUpdateWorkflow && (
                    <div className="flex gap-1">
                        <input
                            type="text"
                            value={newTag}
                            onChange={e => setNewTag(e.target.value)}
                            onKeyDown={e => {
                                if (e.key === 'Enter') { e.preventDefault(); handleAddTag(); }
                            }}
                            placeholder="Add tag..."
                            className="text-xs px-2 py-1 rounded"
                            style={{
                                background: 'var(--bg-input, var(--bg-canvas))',
                                border: '1px solid var(--border-panel)',
                                color: 'var(--text-primary)',
                                outline: 'none',
                                flex: 1,
                            }}
                        />
                        <button
                            onClick={handleAddTag}
                            disabled={!newTag.trim()}
                            className="text-xs px-2 py-1 rounded hover:opacity-80"
                            style={{
                                background: 'var(--action-primary)',
                                color: '#000',
                                fontWeight: 600,
                                border: 'none',
                                cursor: !newTag.trim() ? 'default' : 'pointer',
                                opacity: !newTag.trim() ? 0.5 : 1,
                            }}
                        >
                            Add
                        </button>
                    </div>
                )}
            </div>

            {/* Core Metadata */}
            <h3
                className="text-xs font-semibold uppercase tracking-wide pt-2"
                style={{ color: 'var(--text-muted)' }}
            >
                Workflow Metadata
            </h3>

            {fields.map(f => (
                <div key={f.key}>
                    <label style={metaLabelStyle}>{f.label}</label>
                    <div style={metaFieldStyle}>{workflow[f.key] || '-'}</div>
                </div>
            ))}

            {scopeEntries.length > 0 && (
                <>
                    <h3
                        className="text-xs font-semibold uppercase tracking-wide pt-2"
                        style={{ color: 'var(--text-muted)' }}
                    >
                        Scopes
                    </h3>
                    {scopeEntries.map(([scopeId, config]) => (
                        <div key={scopeId}>
                            <label style={metaLabelStyle}>{scopeId}</label>
                            <div style={metaFieldStyle}>
                                parent: {config.parent || 'none'}
                            </div>
                        </div>
                    ))}
                </>
            )}

            {docTypeEntries.length > 0 && (
                <>
                    <h3
                        className="text-xs font-semibold uppercase tracking-wide pt-2"
                        style={{ color: 'var(--text-muted)' }}
                    >
                        Document Types
                    </h3>
                    {docTypeEntries.map(([dtId, config]) => (
                        <div key={dtId}>
                            <label style={metaLabelStyle}>{dtId}</label>
                            <div style={metaFieldStyle}>
                                {config.name}
                                {config.scope && ` (${config.scope})`}
                                {config.acceptance_required && ' [acceptance required]'}
                            </div>
                        </div>
                    ))}
                </>
            )}
        </div>
    );
}
