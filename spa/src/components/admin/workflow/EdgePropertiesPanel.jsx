import React, { useState, useEffect } from 'react';

const EDGE_KINDS = ['auto', 'user_choice'];
const CONDITION_OPERATORS = ['eq', 'ne', 'lt', 'lte', 'gt', 'gte'];

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
 * Side panel for editing selected workflow edge properties.
 */
export default function EdgePropertiesPanel({ edge, nodeIds, onChange, onDelete }) {
    const [localData, setLocalData] = useState(edge);

    useEffect(() => {
        setLocalData(edge);
    }, [edge]);

    const updateField = (field, value) => {
        const updated = { ...localData, [field]: value };
        setLocalData(updated);
        onChange(updated);
    };

    const addCondition = () => {
        const conditions = [...(localData.conditions || []), { type: 'retry_count', operator: 'lt', value: 2 }];
        updateField('conditions', conditions);
    };

    const updateCondition = (idx, field, value) => {
        const conditions = [...(localData.conditions || [])];
        conditions[idx] = { ...conditions[idx], [field]: value };
        updateField('conditions', conditions);
    };

    const removeCondition = (idx) => {
        const conditions = (localData.conditions || []).filter((_, i) => i !== idx);
        updateField('conditions', conditions);
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
                    Edge Properties
                </span>
                <button
                    onClick={() => onDelete(localData.edge_id)}
                    className="p-1 rounded hover:bg-red-500/20 transition-colors"
                    style={{ color: '#ef4444' }}
                    title="Delete edge"
                >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" />
                    </svg>
                </button>
            </div>

            <div className="p-3 space-y-3">
                {/* Edge ID */}
                <div>
                    <label style={labelStyle}>Edge ID</label>
                    <input
                        type="text"
                        value={localData.edge_id || ''}
                        onChange={e => updateField('edge_id', e.target.value)}
                        style={fieldStyle}
                    />
                </div>

                {/* From Node */}
                <div>
                    <label style={labelStyle}>From Node</label>
                    <select
                        value={localData.from_node_id || ''}
                        onChange={e => updateField('from_node_id', e.target.value)}
                        style={fieldStyle}
                    >
                        {nodeIds.map(id => (
                            <option key={id} value={id}>{id}</option>
                        ))}
                    </select>
                </div>

                {/* To Node */}
                <div>
                    <label style={labelStyle}>To Node</label>
                    <select
                        value={localData.to_node_id || ''}
                        onChange={e => updateField('to_node_id', e.target.value || null)}
                        style={fieldStyle}
                    >
                        <option value="">(none - non-advancing)</option>
                        {nodeIds.map(id => (
                            <option key={id} value={id}>{id}</option>
                        ))}
                    </select>
                </div>

                {/* Outcome */}
                <div>
                    <label style={labelStyle}>Outcome</label>
                    <input
                        type="text"
                        value={localData.outcome || ''}
                        onChange={e => updateField('outcome', e.target.value)}
                        placeholder="success, failed, etc."
                        style={fieldStyle}
                    />
                </div>

                {/* Label */}
                <div>
                    <label style={labelStyle}>Label</label>
                    <input
                        type="text"
                        value={localData.label || ''}
                        onChange={e => updateField('label', e.target.value)}
                        placeholder="Human-readable label"
                        style={fieldStyle}
                    />
                </div>

                {/* Kind */}
                <div>
                    <label style={labelStyle}>Kind</label>
                    <select
                        value={localData.kind || 'auto'}
                        onChange={e => updateField('kind', e.target.value)}
                        style={fieldStyle}
                    >
                        {EDGE_KINDS.map(k => (
                            <option key={k} value={k}>{k}</option>
                        ))}
                    </select>
                </div>

                {/* Non-advancing */}
                <label className="flex items-center gap-1.5 text-xs" style={{ color: 'var(--text-muted)' }}>
                    <input
                        type="checkbox"
                        checked={localData.non_advancing || false}
                        onChange={e => updateField('non_advancing', e.target.checked)}
                    />
                    Non-advancing
                </label>

                {/* Conditions */}
                <div>
                    <div className="flex items-center justify-between mb-1">
                        <label style={labelStyle}>Conditions</label>
                        <button
                            onClick={addCondition}
                            className="text-xs px-1.5 py-0.5 rounded hover:opacity-80"
                            style={{ color: 'var(--action-primary)', background: 'transparent' }}
                        >
                            + Add
                        </button>
                    </div>
                    <div className="space-y-2">
                        {(localData.conditions || []).map((cond, idx) => (
                            <div
                                key={idx}
                                className="p-2 rounded space-y-1"
                                style={{ background: 'var(--bg-canvas)', border: '1px solid var(--border-panel)' }}
                            >
                                <div className="flex gap-1 items-center">
                                    <input
                                        type="text"
                                        value={cond.type || ''}
                                        onChange={e => updateCondition(idx, 'type', e.target.value)}
                                        placeholder="retry_count"
                                        style={{ ...fieldStyle, flex: 1, fontSize: 10 }}
                                    />
                                    <select
                                        value={cond.operator || 'lt'}
                                        onChange={e => updateCondition(idx, 'operator', e.target.value)}
                                        style={{ ...fieldStyle, width: 'auto', fontSize: 10 }}
                                    >
                                        {CONDITION_OPERATORS.map(op => (
                                            <option key={op} value={op}>{op}</option>
                                        ))}
                                    </select>
                                    <input
                                        type="text"
                                        value={cond.value ?? ''}
                                        onChange={e => {
                                            const val = isNaN(e.target.value) ? e.target.value : Number(e.target.value);
                                            updateCondition(idx, 'value', val);
                                        }}
                                        placeholder="value"
                                        style={{ ...fieldStyle, width: 50, fontSize: 10 }}
                                    />
                                    <button
                                        onClick={() => removeCondition(idx)}
                                        className="text-xs px-1"
                                        style={{ color: '#ef4444' }}
                                    >
                                        x
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}
