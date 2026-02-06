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
 * Build a template reference string for the task_ref field.
 * Format: prompt:template:{template_id}:{version}
 */
function buildTemplateRef(template) {
    if (!template) return '';
    return `prompt:template:${template.template_id}:${template.active_version || template.version || '1.0.0'}`;
}

/**
 * Parse a template reference to extract template_id.
 * Format: prompt:template:{template_id}:{version}
 */
function parseTemplateRef(ref) {
    if (!ref) return null;
    const parts = ref.split(':');
    if (parts.length >= 3 && parts[0] === 'prompt' && parts[1] === 'template') {
        return parts[2];
    }
    // Legacy format: tasks/Name v1.0 or just the template_id
    return ref;
}

/**
 * Build a fragment reference string for includes.
 * Format: prompt:{kind}:{fragment_id}:{version}
 */
function buildFragmentRef(fragment) {
    if (!fragment) return '';
    const kind = fragment.kind || 'role';
    const id = fragment.fragment_id?.replace(`${kind}:`, '') || fragment.id || '';
    const version = fragment.version || fragment.active_version || '1.0.0';
    return `prompt:${kind}:${id}:${version}`;
}

/**
 * Parse a fragment reference to extract the ID.
 * Format: prompt:{kind}:{id}:{version}
 */
function parseFragmentRef(ref) {
    if (!ref) return null;
    const parts = ref.split(':');
    if (parts.length >= 3 && parts[0] === 'prompt') {
        return parts[2]; // Return the ID part
    }
    return ref;
}

/**
 * Build a schema reference string for includes.
 * Format: schema:{schema_id}:{version}
 */
function buildSchemaRef(schema) {
    if (!schema) return '';
    const version = schema.active_version || schema.version || '1.0.0';
    return `schema:${schema.schema_id}:${version}`;
}

/**
 * Parse a schema reference to extract the ID.
 * Format: schema:{schema_id}:{version}
 */
function parseSchemaRef(ref) {
    if (!ref) return null;
    const parts = ref.split(':');
    if (parts.length >= 2 && parts[0] === 'schema') {
        return parts[1]; // Return the ID part
    }
    return ref;
}

/**
 * Side panel for editing selected workflow node properties.
 */
export default function NodePropertiesPanel({
    node,
    onChange,
    onDelete,
    templates = [],
    schemas = [],
    roleFragments = [],
    taskFragments = [],
    pgcFragments = [],
}) {
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

    const addCustomInclude = () => {
        const includes = { ...localData.includes, NEW_KEY: '' };
        const updated = { ...localData, includes };
        setLocalData(updated);
        onChange(updated);
    };

    if (!localData) return null;

    // Get current template_id from task_ref
    const currentTemplateId = parseTemplateRef(localData.task_ref);

    // Get current includes
    const includes = localData.includes || {};
    const currentRoleRef = includes.ROLE_PROMPT || '';
    const currentTaskRef = includes.TASK_PROMPT || '';
    const currentSchemaRef = includes.OUTPUT_SCHEMA || '';
    const currentPgcRef = includes.PGC_CONTEXT || '';
    const currentRoleId = parseFragmentRef(currentRoleRef);
    const currentTaskId = parseFragmentRef(currentTaskRef);
    const currentSchemaId = parseSchemaRef(currentSchemaRef);
    const currentPgcId = parseFragmentRef(currentPgcRef);

    // Get custom includes (not the predefined ones)
    const customIncludes = Object.entries(includes).filter(
        ([key]) => !['ROLE_PROMPT', 'TASK_PROMPT', 'OUTPUT_SCHEMA', 'PGC_CONTEXT'].includes(key)
    );

    // Handle template selection
    const handleTemplateChange = (e) => {
        const templateId = e.target.value;
        if (!templateId) {
            updateField('task_ref', '');
            return;
        }
        const template = templates.find(t => t.template_id === templateId);
        if (template) {
            updateField('task_ref', buildTemplateRef(template));
        }
    };

    // Handle role fragment selection
    const handleRoleChange = (e) => {
        const fragmentId = e.target.value;
        if (!fragmentId) {
            removeInclude('ROLE_PROMPT');
            return;
        }
        const fragment = roleFragments.find(f =>
            f.fragment_id === `role:${fragmentId}` || f.id === fragmentId
        );
        if (fragment) {
            updateInclude('ROLE_PROMPT', buildFragmentRef(fragment));
        }
    };

    // Handle task fragment selection
    const handleTaskChange = (e) => {
        const fragmentId = e.target.value;
        if (!fragmentId) {
            removeInclude('TASK_PROMPT');
            return;
        }
        const fragment = taskFragments.find(f =>
            f.fragment_id === `task:${fragmentId}` || f.id === fragmentId
        );
        if (fragment) {
            updateInclude('TASK_PROMPT', buildFragmentRef(fragment));
        }
    };

    // Handle schema selection
    const handleSchemaChange = (e) => {
        const schemaId = e.target.value;
        if (!schemaId) {
            removeInclude('OUTPUT_SCHEMA');
            return;
        }
        const schema = schemas.find(s => s.schema_id === schemaId);
        if (schema) {
            updateInclude('OUTPUT_SCHEMA', buildSchemaRef(schema));
        }
    };

    // Handle PGC context selection
    const handlePgcChange = (e) => {
        const fragmentId = e.target.value;
        if (!fragmentId) {
            removeInclude('PGC_CONTEXT');
            return;
        }
        const fragment = pgcFragments.find(f =>
            f.fragment_id === `pgc:${fragmentId}` || f.id === fragmentId
        );
        if (fragment) {
            updateInclude('PGC_CONTEXT', buildFragmentRef(fragment));
        }
    };

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

                {/* Interaction Template - for task, qa, pgc, intake_gate */}
                {['task', 'qa', 'pgc', 'intake_gate'].includes(localData.type) && (
                    <div>
                        <label style={labelStyle}>Interaction Template</label>
                        <select
                            value={currentTemplateId || ''}
                            onChange={handleTemplateChange}
                            style={fieldStyle}
                        >
                            <option value="">-- Select Template --</option>
                            {templates.map(t => (
                                <option key={t.template_id} value={t.template_id}>
                                    {t.name || t.template_id.replace(/_/g, ' ')}
                                </option>
                            ))}
                        </select>
                        {localData.task_ref && (
                            <div
                                className="mt-1 text-xs font-mono truncate"
                                style={{ color: 'var(--text-muted)' }}
                                title={localData.task_ref}
                            >
                                {localData.task_ref}
                            </div>
                        )}
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
                        <div className="flex items-center justify-between mb-2">
                            <label style={labelStyle}>Includes</label>
                        </div>

                        {/* ROLE_PROMPT - dropdown from role fragments */}
                        <div className="mb-2">
                            <label
                                className="text-xs mb-1 block"
                                style={{ color: 'var(--text-muted)' }}
                            >
                                ROLE_PROMPT
                            </label>
                            <select
                                value={currentRoleId || ''}
                                onChange={handleRoleChange}
                                style={{ ...fieldStyle, fontSize: 11 }}
                            >
                                <option value="">-- Select Role --</option>
                                {roleFragments.map(f => {
                                    const id = f.fragment_id?.replace('role:', '') || f.id;
                                    return (
                                        <option key={f.fragment_id || f.id} value={id}>
                                            {f.name || id?.replace(/_/g, ' ')}
                                        </option>
                                    );
                                })}
                            </select>
                        </div>

                        {/* TASK_PROMPT - dropdown from task fragments */}
                        <div className="mb-2">
                            <label
                                className="text-xs mb-1 block"
                                style={{ color: 'var(--text-muted)' }}
                            >
                                TASK_PROMPT
                            </label>
                            <select
                                value={currentTaskId || ''}
                                onChange={handleTaskChange}
                                style={{ ...fieldStyle, fontSize: 11 }}
                            >
                                <option value="">-- Select Task --</option>
                                {taskFragments.map(f => {
                                    const id = f.fragment_id?.replace('task:', '') || f.id;
                                    return (
                                        <option key={f.fragment_id || f.id} value={id}>
                                            {f.name || id?.replace(/_/g, ' ')}
                                        </option>
                                    );
                                })}
                            </select>
                        </div>

                        {/* OUTPUT_SCHEMA - dropdown from schemas */}
                        <div className="mb-2">
                            <label
                                className="text-xs mb-1 block"
                                style={{ color: 'var(--text-muted)' }}
                            >
                                OUTPUT_SCHEMA
                            </label>
                            <select
                                value={currentSchemaId || ''}
                                onChange={handleSchemaChange}
                                style={{ ...fieldStyle, fontSize: 11 }}
                            >
                                <option value="">-- Select Schema --</option>
                                {schemas.map(s => (
                                    <option key={s.schema_id} value={s.schema_id}>
                                        {s.title || s.schema_id.replace(/_/g, ' ')}
                                    </option>
                                ))}
                            </select>
                        </div>

                        {/* PGC_CONTEXT - dropdown from PGC fragments */}
                        <div className="mb-2">
                            <label
                                className="text-xs mb-1 block"
                                style={{ color: 'var(--text-muted)' }}
                            >
                                PGC_CONTEXT
                            </label>
                            <select
                                value={currentPgcId || ''}
                                onChange={handlePgcChange}
                                style={{ ...fieldStyle, fontSize: 11 }}
                            >
                                <option value="">-- Select PGC Context --</option>
                                {pgcFragments.map(f => {
                                    const id = f.fragment_id?.replace('pgc:', '') || f.id;
                                    return (
                                        <option key={f.fragment_id || f.id} value={id}>
                                            {f.name || id?.replace(/_/g, ' ')}
                                        </option>
                                    );
                                })}
                            </select>
                        </div>

                        {/* Custom includes */}
                        {customIncludes.length > 0 && (
                            <div className="mt-3 pt-2 border-t" style={{ borderColor: 'var(--border-panel)' }}>
                                <label
                                    className="text-xs mb-1 block"
                                    style={{ color: 'var(--text-muted)' }}
                                >
                                    Custom Includes
                                </label>
                                <div className="space-y-2">
                                    {customIncludes.map(([key, value]) => (
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

                        {/* Add custom include button */}
                        <button
                            onClick={addCustomInclude}
                            className="mt-2 text-xs px-2 py-1 rounded hover:opacity-80 w-full"
                            style={{
                                color: 'var(--action-primary)',
                                background: 'transparent',
                                border: '1px dashed var(--border-panel)',
                            }}
                        >
                            + Add Custom Include
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}
