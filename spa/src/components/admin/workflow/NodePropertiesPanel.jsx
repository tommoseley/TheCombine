import React, { useState, useEffect } from 'react';

const NODE_TYPES = [
    { value: 'intake_gate', label: 'Intake Gate' },
    { value: 'task', label: 'Task' },
    { value: 'qa', label: 'QA' },
    { value: 'pgc', label: 'PGC' },
    { value: 'gate', label: 'Gate' },
    { value: 'end', label: 'End' },
];

const QA_MODES = ['semantic', 'structural', 'hybrid'];
const TERMINAL_OUTCOMES = ['stabilized', 'blocked', 'abandoned'];

const fieldStyle = {
    width: '100%',
    padding: '6px 8px',
    borderRadius: 4,
    fontSize: 12,
    background: 'var(--bg-input, var(--bg-canvas))',
    border: '1px solid var(--border-panel)',
    color: 'var(--text-primary)',
};

const labelStyle = {
    display: 'block',
    fontSize: 10,
    fontWeight: 600,
    color: 'var(--text-muted)',
    marginBottom: 2,
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
};

/**
 * Side panel for editing selected workflow node properties.
 */
export default function NodePropertiesPanel({ node, onChange, onDelete }) {
    const [localData, setLocalData] = useState(node);

    useEffect(() => {
        setLocalData(node);
    }, [node]);

    const updateField = (field, value) => {
        const updated = { ...localData, [field]: value };
        setLocalData(updated);
        onChange(updated);
    };

    const updateInclude = (key, value) => {
        const includes = { ...localData.includes, [key]: value };
        const updated = { ...localData, includes };
        setLocalData(updated);
        onChange(updated);
    };

    const removeInclude = (key) => {
        const includes = { ...localData.includes };
        delete includes[key];
        const updated = { ...localData, includes };
        setLocalData(updated);
        onChange(updated);
    };

    const addInclude = () => {
        const includes = { ...localData.includes, NEW_KEY: '' };
        const updated = { ...localData, includes };
        setLocalData(updated);
        onChange(updated);
    };

    if (!localData) return null;

    return (
        <div
            className="w-64 border-l overflow-y-auto flex-shrink-0"
            style={{
                borderColor: 'var(--border-panel)',
                background: 'var(--bg-panel)',
            }}
        >
            {/* Header */}
            <div
                className="px-3 py-2 border-b flex items-center justify-between"
                style={{ borderColor: 'var(--border-panel)' }}
            >
                <span
                    className="text-xs font-semibold uppercase tracking-wide"
                    style={{ color: 'var(--text-muted)' }}
                >
                    Node Properties
                </span>
                <button
                    onClick={() => onDelete(localData.node_id)}
                    className="p-1 rounded hover:bg-red-500/20 transition-colors"
                    style={{ color: '#ef4444' }}
                    title="Delete node"
                >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" />
                    </svg>
                </button>
            </div>

            <div className="p-3 space-y-3">
                {/* Node ID */}
                <div>
                    <label style={labelStyle}>Node ID</label>
                    <input
                        type="text"
                        value={localData.node_id || ''}
                        onChange={e => updateField('node_id', e.target.value)}
                        style={fieldStyle}
                    />
                </div>

                {/* Type */}
                <div>
                    <label style={labelStyle}>Type</label>
                    <select
                        value={localData.type || 'task'}
                        onChange={e => updateField('type', e.target.value)}
                        style={fieldStyle}
                    >
                        {NODE_TYPES.map(t => (
                            <option key={t.value} value={t.value}>{t.label}</option>
                        ))}
                    </select>
                </div>

                {/* Description */}
                <div>
                    <label style={labelStyle}>Description</label>
                    <textarea
                        value={localData.description || ''}
                        onChange={e => updateField('description', e.target.value)}
                        rows={3}
                        style={{ ...fieldStyle, resize: 'vertical' }}
                    />
                </div>

                {/* Task Ref - for task, qa, pgc */}
                {['task', 'qa', 'pgc', 'intake_gate'].includes(localData.type) && (
                    <div>
                        <label style={labelStyle}>Task Ref</label>
                        <input
                            type="text"
                            value={localData.task_ref || ''}
                            onChange={e => updateField('task_ref', e.target.value)}
                            placeholder="tasks/Name v1.0"
                            style={fieldStyle}
                        />
                    </div>
                )}

                {/* Produces - for task nodes */}
                {['task', 'intake_gate'].includes(localData.type) && (
                    <div>
                        <label style={labelStyle}>Produces</label>
                        <input
                            type="text"
                            value={localData.produces || ''}
                            onChange={e => updateField('produces', e.target.value)}
                            placeholder="document_type"
                            style={fieldStyle}
                        />
                    </div>
                )}

                {/* QA Mode */}
                {localData.type === 'qa' && (
                    <div>
                        <label style={labelStyle}>QA Mode</label>
                        <select
                            value={localData.qa_mode || 'semantic'}
                            onChange={e => updateField('qa_mode', e.target.value)}
                            style={fieldStyle}
                        >
                            {QA_MODES.map(m => (
                                <option key={m} value={m}>{m}</option>
                            ))}
                        </select>
                    </div>
                )}

                {/* Terminal Outcome - for end nodes */}
                {localData.type === 'end' && (
                    <>
                        <div>
                            <label style={labelStyle}>Terminal Outcome</label>
                            <select
                                value={localData.terminal_outcome || 'stabilized'}
                                onChange={e => updateField('terminal_outcome', e.target.value)}
                                style={fieldStyle}
                            >
                                {TERMINAL_OUTCOMES.map(o => (
                                    <option key={o} value={o}>{o}</option>
                                ))}
                            </select>
                        </div>
                        <div>
                            <label style={labelStyle}>Gate Outcome</label>
                            <input
                                type="text"
                                value={localData.gate_outcome || ''}
                                onChange={e => updateField('gate_outcome', e.target.value)}
                                placeholder="e.g., complete, failed"
                                style={fieldStyle}
                            />
                        </div>
                    </>
                )}

                {/* Flags */}
                <div className="flex gap-4">
                    {localData.type === 'qa' && (
                        <label className="flex items-center gap-1.5 text-xs" style={{ color: 'var(--text-muted)' }}>
                            <input
                                type="checkbox"
                                checked={localData.requires_qa || false}
                                onChange={e => updateField('requires_qa', e.target.checked)}
                            />
                            Requires QA
                        </label>
                    )}
                    <label className="flex items-center gap-1.5 text-xs" style={{ color: 'var(--text-muted)' }}>
                        <input
                            type="checkbox"
                            checked={localData.non_advancing || false}
                            onChange={e => updateField('non_advancing', e.target.checked)}
                        />
                        Non-advancing
                    </label>
                </div>

                {/* Includes (for task, pgc nodes) */}
                {['task', 'pgc'].includes(localData.type) && (
                    <div>
                        <div className="flex items-center justify-between mb-1">
                            <label style={labelStyle}>Includes</label>
                            <button
                                onClick={addInclude}
                                className="text-xs px-1.5 py-0.5 rounded hover:opacity-80"
                                style={{ color: 'var(--action-primary)', background: 'transparent' }}
                            >
                                + Add
                            </button>
                        </div>
                        <div className="space-y-2">
                            {Object.entries(localData.includes || {}).map(([key, value]) => (
                                <div key={key} className="flex gap-1">
                                    <input
                                        type="text"
                                        value={key}
                                        onChange={e => {
                                            const newIncludes = { ...localData.includes };
                                            delete newIncludes[key];
                                            newIncludes[e.target.value] = value;
                                            const updated = { ...localData, includes: newIncludes };
                                            setLocalData(updated);
                                            onChange(updated);
                                        }}
                                        style={{ ...fieldStyle, width: '35%', fontSize: 10 }}
                                        placeholder="KEY"
                                    />
                                    <input
                                        type="text"
                                        value={value}
                                        onChange={e => updateInclude(key, e.target.value)}
                                        style={{ ...fieldStyle, flex: 1, fontSize: 10 }}
                                        placeholder="path/to/file"
                                    />
                                    <button
                                        onClick={() => removeInclude(key)}
                                        className="text-xs px-1"
                                        style={{ color: '#ef4444' }}
                                    >
                                        x
                                    </button>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
