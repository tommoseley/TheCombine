import React, { useState, useEffect } from 'react';

const NODE_TYPES = [
    { value: 'intake_gate', label: 'Intake Gate' },
    { value: 'task', label: 'Task' },
    { value: 'qa', label: 'QA' },
    { value: 'pgc', label: 'PGC Gate' },
    { value: 'gate', label: 'Gate' },
    { value: 'end', label: 'End' },
];

// ADR-047: Node internal types
const INTERNAL_TYPES = [
    { value: 'LLM', label: 'LLM', description: 'AI-powered interaction' },
    { value: 'MECH', label: 'Mechanical', description: 'Deterministic operation' },
    { value: 'UI', label: 'UI', description: 'Operator entry' },
];

const PGC_GATE_KINDS = [
    { value: 'intake', label: 'Intake Gate', produces: 'pgc_clarifications.intake' },
    { value: 'discovery', label: 'Discovery Gate', produces: 'pgc_clarifications.discovery' },
    { value: 'plan', label: 'Plan Gate', produces: 'pgc_clarifications.plan' },
    { value: 'architecture', label: 'Architecture Gate', produces: 'pgc_clarifications.architecture' },
    { value: 'epic', label: 'Epic Gate', produces: 'pgc_clarifications.epic' },
    { value: 'remediation', label: 'Remediation Gate', produces: 'pgc_clarifications.remediation' },
    { value: 'compliance', label: 'Compliance Gate', produces: 'pgc_clarifications.compliance' },
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

const sectionHeaderStyle = {
    fontSize: 10,
    fontWeight: 700,
    color: 'var(--text-primary)',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    padding: '6px 0',
    borderBottom: '1px solid var(--border-panel)',
    marginBottom: 8,
};

const passHeaderStyle = {
    fontSize: 10,
    fontWeight: 600,
    color: 'var(--action-primary)',
    marginBottom: 4,
    display: 'flex',
    alignItems: 'center',
    gap: 6,
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
 * Collapsible section component.
 * Supports both uncontrolled (defaultOpen) and controlled (isOpen + onToggle) modes.
 */
function CollapsibleSection({ title, defaultOpen = false, isOpen: controlledOpen, onToggle, children, badge }) {
    const [internalOpen, setInternalOpen] = useState(defaultOpen);

    // Use controlled mode if isOpen prop is provided
    const isControlled = controlledOpen !== undefined;
    const isOpen = isControlled ? controlledOpen : internalOpen;

    const handleToggle = () => {
        if (isControlled && onToggle) {
            onToggle();
        } else {
            setInternalOpen(!internalOpen);
        }
    };

    return (
        <div className="border rounded" style={{ borderColor: 'var(--border-panel)' }}>
            <button
                onClick={handleToggle}
                className="w-full px-2 py-1.5 flex items-center justify-between text-left hover:bg-white/5 transition-colors"
                style={{ background: 'var(--bg-canvas)' }}
            >
                <div className="flex items-center gap-2">
                    <svg
                        width="10"
                        height="10"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        style={{
                            color: 'var(--text-muted)',
                            transform: isOpen ? 'rotate(90deg)' : 'rotate(0deg)',
                            transition: 'transform 0.15s ease',
                        }}
                    >
                        <path d="M9 18l6-6-6-6" />
                    </svg>
                    <span style={{ ...labelStyle, marginBottom: 0 }}>{title}</span>
                </div>
                {badge && (
                    <span
                        className="text-[9px] px-1.5 py-0.5 rounded"
                        style={{ background: 'var(--action-primary)', color: '#fff' }}
                    >
                        {badge}
                    </span>
                )}
            </button>
            {isOpen && (
                <div className="p-2 border-t" style={{ borderColor: 'var(--border-panel)' }}>
                    {children}
                </div>
            )}
        </div>
    );
}

/**
 * Build a mechanical operation reference string.
 * Format: mech:{type}:{op_id}:{version}
 */
function buildMechOpRef(op) {
    if (!op) return '';
    return `mech:${op.type}:${op.op_id}:${op.active_version || op.version || '1.0.0'}`;
}

/**
 * Parse a mechanical operation reference to extract op_id.
 * Format: mech:{type}:{op_id}:{version}
 */
function parseMechOpRef(ref) {
    if (!ref) return null;
    const parts = ref.split(':');
    if (parts.length >= 3 && parts[0] === 'mech') {
        return parts[2]; // Return the op_id
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
    // ADR-047: Mechanical operations
    mechanicalOpTypes = [],
    mechanicalOps = [],
}) {
    const [localData, setLocalData] = useState(node);
    // Single-expansion for PGC LLM passes: 'A' | 'B' | null (WS-ADR-044-003 Phase 4)
    const [expandedPass, setExpandedPass] = useState('A');

    useEffect(() => {
        setLocalData(node);
        // Reset expanded pass when node changes
        setExpandedPass('A');
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

    // PGC internals update helpers
    const updateInternals = (internals) => {
        const updated = { ...localData, internals };
        setLocalData(updated);
        onChange(updated);
    };

    const updateQuestionGeneration = (field, value) => {
        const internals = localData.internals || getDefaultPgcInternals();
        const questionGeneration = { ...internals.question_generation, [field]: value };
        updateInternals({ ...internals, question_generation: questionGeneration });
    };

    const updateQuestionGenIncludes = (key, value) => {
        const internals = localData.internals || getDefaultPgcInternals();
        const includes = { ...internals.question_generation.includes, [key]: value };
        const questionGeneration = { ...internals.question_generation, includes };
        updateInternals({ ...internals, question_generation: questionGeneration });
    };

    const updateClarificationMerge = (field, value) => {
        const internals = localData.internals || getDefaultPgcInternals();
        const clarificationMerge = { ...internals.clarification_merge, [field]: value };
        updateInternals({ ...internals, clarification_merge: clarificationMerge });
    };

    // Get default PGC internals structure
    const getDefaultPgcInternals = () => ({
        question_generation: {
            template_ref: '',
            includes: {
                ROLE_PROMPT: '',
                TASK_PROMPT: '',
                PGC_CONTEXT: '',
            },
            output_schema_ref: 'schema:clarification_question_set:2.0.0',
        },
        operator_entry: {
            renders: 'question_set',
            captures: 'pgc_answers',
        },
        clarification_merge: {
            template_ref: '',
            output_schema_ref: 'schema:pgc_clarifications:1.0.0',
        },
    });

    if (!localData) return null;

    const isPgcNode = localData.type === 'pgc';

    // For non-PGC nodes: Get current template_id from task_ref
    const currentTemplateId = parseTemplateRef(localData.task_ref);

    // For non-PGC nodes: Get current includes
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

    // For PGC nodes: Get internals
    const internals = localData.internals || getDefaultPgcInternals();
    const qgTemplateId = parseTemplateRef(internals.question_generation?.template_ref);
    const qgRoleId = parseFragmentRef(internals.question_generation?.includes?.ROLE_PROMPT);
    const qgTaskId = parseFragmentRef(internals.question_generation?.includes?.TASK_PROMPT);
    const qgPgcId = parseFragmentRef(internals.question_generation?.includes?.PGC_CONTEXT);
    const qgSchemaId = parseSchemaRef(internals.question_generation?.output_schema_ref);
    const cmTemplateId = parseTemplateRef(internals.clarification_merge?.template_ref);
    const cmSchemaId = parseSchemaRef(internals.clarification_merge?.output_schema_ref);

    // Handle template selection (for non-PGC nodes)
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

    // Handle role fragment selection (for non-PGC nodes)
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

    // Handle task fragment selection (for non-PGC nodes)
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

    // Handle schema selection (for non-PGC nodes)
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

    // Handle PGC context selection (for non-PGC nodes)
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

    // Handle gate_kind change - auto-update produces
    const handleGateKindChange = (e) => {
        const gateKind = e.target.value;
        const gateConfig = PGC_GATE_KINDS.find(g => g.value === gateKind);
        const produces = gateConfig?.produces || `pgc_clarifications.${gateKind}`;
        const updated = { ...localData, gate_kind: gateKind, produces };
        setLocalData(updated);
        onChange(updated);
    };

    // PGC-specific handlers
    const handleQgTemplateChange = (e) => {
        const templateId = e.target.value;
        if (!templateId) {
            updateQuestionGeneration('template_ref', '');
            return;
        }
        const template = templates.find(t => t.template_id === templateId);
        if (template) {
            updateQuestionGeneration('template_ref', buildTemplateRef(template));
        }
    };

    const handleQgRoleChange = (e) => {
        const fragmentId = e.target.value;
        if (!fragmentId) {
            updateQuestionGenIncludes('ROLE_PROMPT', '');
            return;
        }
        const fragment = roleFragments.find(f =>
            f.fragment_id === `role:${fragmentId}` || f.id === fragmentId
        );
        if (fragment) {
            updateQuestionGenIncludes('ROLE_PROMPT', buildFragmentRef(fragment));
        }
    };

    const handleQgTaskChange = (e) => {
        const fragmentId = e.target.value;
        if (!fragmentId) {
            updateQuestionGenIncludes('TASK_PROMPT', '');
            return;
        }
        const fragment = taskFragments.find(f =>
            f.fragment_id === `task:${fragmentId}` || f.id === fragmentId
        );
        if (fragment) {
            updateQuestionGenIncludes('TASK_PROMPT', buildFragmentRef(fragment));
        }
    };

    const handleQgPgcChange = (e) => {
        const fragmentId = e.target.value;
        if (!fragmentId) {
            updateQuestionGenIncludes('PGC_CONTEXT', '');
            return;
        }
        const fragment = pgcFragments.find(f =>
            f.fragment_id === `pgc:${fragmentId}` || f.id === fragmentId
        );
        if (fragment) {
            updateQuestionGenIncludes('PGC_CONTEXT', buildFragmentRef(fragment));
        }
    };

    const handleQgSchemaChange = (e) => {
        const schemaId = e.target.value;
        if (!schemaId) {
            updateQuestionGeneration('output_schema_ref', '');
            return;
        }
        const schema = schemas.find(s => s.schema_id === schemaId);
        if (schema) {
            updateQuestionGeneration('output_schema_ref', buildSchemaRef(schema));
        }
    };

    const handleCmTemplateChange = (e) => {
        const templateId = e.target.value;
        if (!templateId) {
            updateClarificationMerge('template_ref', '');
            return;
        }
        const template = templates.find(t => t.template_id === templateId);
        if (template) {
            updateClarificationMerge('template_ref', buildTemplateRef(template));
        }
    };

    const handleCmSchemaChange = (e) => {
        const schemaId = e.target.value;
        if (!schemaId) {
            updateClarificationMerge('output_schema_ref', '');
            return;
        }
        const schema = schemas.find(s => s.schema_id === schemaId);
        if (schema) {
            updateClarificationMerge('output_schema_ref', buildSchemaRef(schema));
        }
    };

    return (
        <div
            className="w-72 border-l overflow-y-auto flex-shrink-0"
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
                    {isPgcNode ? 'PGC Gate Properties' : 'Node Properties'}
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

                {/* Gate Kind - PGC only */}
                {isPgcNode && (
                    <div>
                        <label style={labelStyle}>Gate Kind</label>
                        <select
                            value={localData.gate_kind || 'discovery'}
                            onChange={handleGateKindChange}
                            style={fieldStyle}
                        >
                            {PGC_GATE_KINDS.map(g => (
                                <option key={g.value} value={g.value}>{g.label}</option>
                            ))}
                        </select>
                    </div>
                )}

                {/* Description */}
                <div>
                    <label style={labelStyle}>Description</label>
                    <textarea
                        value={localData.description || ''}
                        onChange={e => updateField('description', e.target.value)}
                        rows={2}
                        style={{ ...fieldStyle, resize: 'vertical' }}
                    />
                </div>

                {/* Produces - for PGC and task nodes */}
                {(isPgcNode || ['task', 'intake_gate'].includes(localData.type)) && (
                    <div>
                        <label style={labelStyle}>Produces</label>
                        <input
                            type="text"
                            value={localData.produces || ''}
                            onChange={e => updateField('produces', e.target.value)}
                            placeholder={isPgcNode ? 'pgc_clarifications.discovery' : 'document_type'}
                            style={fieldStyle}
                        />
                    </div>
                )}

                {/* === PGC Gate Internals === */}
                {isPgcNode && (
                    <div className="mt-4">
                        <div style={sectionHeaderStyle}>Gate Internals</div>

                        {/* Pass A: Question Generation - controlled expansion */}
                        <CollapsibleSection
                            title="Pass A: Question Generation"
                            isOpen={expandedPass === 'A'}
                            onToggle={() => setExpandedPass(expandedPass === 'A' ? null : 'A')}
                            badge="LLM"
                        >
                            <div className="space-y-2">
                                {/* Template */}
                                <div>
                                    <label className="text-[10px] mb-1 block" style={{ color: 'var(--text-muted)' }}>
                                        Template
                                    </label>
                                    <select
                                        value={qgTemplateId || ''}
                                        onChange={handleQgTemplateChange}
                                        style={{ ...fieldStyle, fontSize: 11 }}
                                    >
                                        <option value="">-- Select Template --</option>
                                        {templates.map(t => (
                                            <option key={t.template_id} value={t.template_id}>
                                                {t.name || t.template_id.replace(/_/g, ' ')}
                                            </option>
                                        ))}
                                    </select>
                                </div>

                                {/* Role Prompt */}
                                <div>
                                    <label className="text-[10px] mb-1 block" style={{ color: 'var(--text-muted)' }}>
                                        ROLE_PROMPT
                                    </label>
                                    <select
                                        value={qgRoleId || ''}
                                        onChange={handleQgRoleChange}
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

                                {/* Task Prompt */}
                                <div>
                                    <label className="text-[10px] mb-1 block" style={{ color: 'var(--text-muted)' }}>
                                        TASK_PROMPT
                                    </label>
                                    <select
                                        value={qgTaskId || ''}
                                        onChange={handleQgTaskChange}
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

                                {/* PGC Context */}
                                <div>
                                    <label className="text-[10px] mb-1 block" style={{ color: 'var(--text-muted)' }}>
                                        PGC_CONTEXT
                                    </label>
                                    <select
                                        value={qgPgcId || ''}
                                        onChange={handleQgPgcChange}
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

                                {/* Output Schema */}
                                <div>
                                    <label className="text-[10px] mb-1 block" style={{ color: 'var(--text-muted)' }}>
                                        OUTPUT_SCHEMA
                                    </label>
                                    <select
                                        value={qgSchemaId || ''}
                                        onChange={handleQgSchemaChange}
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
                            </div>
                        </CollapsibleSection>

                        {/* Entry: Operator Answers */}
                        <div className="mt-2">
                            <CollapsibleSection title="Entry: Operator Answers" badge="UI">
                                <div className="space-y-2 text-xs" style={{ color: 'var(--text-muted)' }}>
                                    <div className="flex justify-between">
                                        <span>Renders:</span>
                                        <span className="font-mono">{internals.operator_entry?.renders || 'question_set'}</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span>Captures:</span>
                                        <span className="font-mono">{internals.operator_entry?.captures || 'pgc_answers'}</span>
                                    </div>
                                    <div
                                        className="text-[10px] mt-2 p-2 rounded"
                                        style={{ background: 'var(--bg-canvas)', color: 'var(--text-muted)' }}
                                    >
                                        Questions rendered in UI. User provides answers.
                                    </div>
                                </div>
                            </CollapsibleSection>
                        </div>

                        {/* Pass B: Clarification Merge - controlled expansion */}
                        {/* Supports both LLM and MECH internal types per ADR-047 */}
                        <div className="mt-2">
                            <CollapsibleSection
                                title="Pass B: Clarification Merge"
                                isOpen={expandedPass === 'B'}
                                onToggle={() => setExpandedPass(expandedPass === 'B' ? null : 'B')}
                                badge={internals.clarification_merge?.internal_type || 'LLM'}
                            >
                                <div className="space-y-2">
                                    {/* Internal Type selector for Pass B */}
                                    <div>
                                        <label className="text-[10px] mb-1 block" style={{ color: 'var(--text-muted)' }}>
                                            Internal Type
                                        </label>
                                        <select
                                            value={internals.clarification_merge?.internal_type || 'LLM'}
                                            onChange={e => updateClarificationMerge('internal_type', e.target.value)}
                                            style={{ ...fieldStyle, fontSize: 11 }}
                                        >
                                            <option value="LLM">LLM</option>
                                            <option value="MECH">Mechanical</option>
                                        </select>
                                    </div>

                                    {/* LLM Configuration */}
                                    {(internals.clarification_merge?.internal_type || 'LLM') === 'LLM' && (
                                        <>
                                            <div>
                                                <label className="text-[10px] mb-1 block" style={{ color: 'var(--text-muted)' }}>
                                                    Template
                                                </label>
                                                <select
                                                    value={cmTemplateId || ''}
                                                    onChange={handleCmTemplateChange}
                                                    style={{ ...fieldStyle, fontSize: 11 }}
                                                >
                                                    <option value="">-- Select Template --</option>
                                                    {templates.map(t => (
                                                        <option key={t.template_id} value={t.template_id}>
                                                            {t.name || t.template_id.replace(/_/g, ' ')}
                                                        </option>
                                                    ))}
                                                </select>
                                            </div>

                                            <div>
                                                <label className="text-[10px] mb-1 block" style={{ color: 'var(--text-muted)' }}>
                                                    OUTPUT_SCHEMA
                                                </label>
                                                <select
                                                    value={cmSchemaId || ''}
                                                    onChange={handleCmSchemaChange}
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
                                        </>
                                    )}

                                    {/* MECH Configuration (ADR-047) */}
                                    {internals.clarification_merge?.internal_type === 'MECH' && (
                                        <>
                                            <div>
                                                <label className="text-[10px] mb-1 block" style={{ color: 'var(--text-muted)' }}>
                                                    Operation
                                                </label>
                                                <select
                                                    value={parseMechOpRef(internals.clarification_merge?.op_ref) || ''}
                                                    onChange={e => {
                                                        const opId = e.target.value;
                                                        if (!opId) {
                                                            updateClarificationMerge('op_ref', '');
                                                            return;
                                                        }
                                                        const op = mechanicalOps.find(o => o.op_id === opId);
                                                        if (op) {
                                                            updateClarificationMerge('op_ref', buildMechOpRef(op));
                                                        }
                                                    }}
                                                    style={{ ...fieldStyle, fontSize: 11 }}
                                                >
                                                    <option value="">-- Select Operation --</option>
                                                    {mechanicalOps.filter(op => op.type === 'merger').map(op => (
                                                        <option key={op.op_id} value={op.op_id}>
                                                            {op.name}
                                                        </option>
                                                    ))}
                                                </select>
                                            </div>

                                            {internals.clarification_merge?.op_ref && (() => {
                                                const opId = parseMechOpRef(internals.clarification_merge.op_ref);
                                                const op = mechanicalOps.find(o => o.op_id === opId);
                                                if (!op) return null;
                                                return (
                                                    <div
                                                        className="p-2 rounded text-[10px]"
                                                        style={{ background: 'var(--bg-canvas)', border: '1px solid var(--border-panel)' }}
                                                    >
                                                        <div className="flex items-center gap-2 mb-1">
                                                            <span
                                                                className="px-1.5 py-0.5 rounded font-semibold uppercase"
                                                                style={{
                                                                    fontSize: 8,
                                                                    background: 'var(--dot-purple, #a855f7)',
                                                                    color: '#fff',
                                                                }}
                                                            >
                                                                {op.type}
                                                            </span>
                                                            <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>
                                                                {op.name}
                                                            </span>
                                                        </div>
                                                        {op.description && (
                                                            <div style={{ color: 'var(--text-muted)' }}>
                                                                {op.description}
                                                            </div>
                                                        )}
                                                    </div>
                                                );
                                            })()}

                                            <div>
                                                <label className="text-[10px] mb-1 block" style={{ color: 'var(--text-muted)' }}>
                                                    OUTPUT_SCHEMA
                                                </label>
                                                <select
                                                    value={cmSchemaId || ''}
                                                    onChange={handleCmSchemaChange}
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
                                        </>
                                    )}

                                    <div
                                        className="text-[10px] mt-2 p-2 rounded"
                                        style={{ background: 'var(--bg-canvas)', color: 'var(--text-muted)' }}
                                    >
                                        Merges questions + answers into structured clarifications artifact.
                                    </div>
                                </div>
                            </CollapsibleSection>
                        </div>
                    </div>
                )}

                {/* === Non-PGC Node Properties === */}

                {/* Internal Type selector - for task nodes (ADR-047) */}
                {localData.type === 'task' && (
                    <div>
                        <label style={labelStyle}>Internal Type</label>
                        <select
                            value={localData.internal_type || 'LLM'}
                            onChange={e => updateField('internal_type', e.target.value)}
                            style={fieldStyle}
                        >
                            {INTERNAL_TYPES.map(t => (
                                <option key={t.value} value={t.value}>{t.label}</option>
                            ))}
                        </select>
                        <div
                            className="mt-1 text-xs"
                            style={{ color: 'var(--text-muted)' }}
                        >
                            {INTERNAL_TYPES.find(t => t.value === (localData.internal_type || 'LLM'))?.description}
                        </div>
                    </div>
                )}

                {/* === LLM Configuration (default) === */}
                {/* Interaction Template - for task, qa, intake_gate when internal_type is LLM or not set */}
                {['task', 'qa', 'intake_gate'].includes(localData.type) &&
                 (localData.internal_type || 'LLM') === 'LLM' && (
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

                {/* === MECH Configuration (ADR-047) === */}
                {localData.type === 'task' && localData.internal_type === 'MECH' && (
                    <div className="space-y-3">
                        <div>
                            <label style={labelStyle}>Mechanical Operation</label>
                            <select
                                value={parseMechOpRef(localData.op_ref) || ''}
                                onChange={e => {
                                    const opId = e.target.value;
                                    if (!opId) {
                                        updateField('op_ref', '');
                                        return;
                                    }
                                    const op = mechanicalOps.find(o => o.op_id === opId);
                                    if (op) {
                                        updateField('op_ref', buildMechOpRef(op));
                                    }
                                }}
                                style={fieldStyle}
                            >
                                <option value="">-- Select Operation --</option>
                                {mechanicalOpTypes.map(opType => {
                                    const opsOfType = mechanicalOps.filter(op => op.type === opType.type_id);
                                    if (opsOfType.length === 0) return null;
                                    return (
                                        <optgroup key={opType.type_id} label={opType.name}>
                                            {opsOfType.map(op => (
                                                <option key={op.op_id} value={op.op_id}>
                                                    {op.name}
                                                </option>
                                            ))}
                                        </optgroup>
                                    );
                                })}
                            </select>
                            {localData.op_ref && (
                                <div
                                    className="mt-1 text-xs font-mono truncate"
                                    style={{ color: 'var(--text-muted)' }}
                                    title={localData.op_ref}
                                >
                                    {localData.op_ref}
                                </div>
                            )}
                        </div>

                        {/* Show operation type info when selected */}
                        {localData.op_ref && (() => {
                            const opId = parseMechOpRef(localData.op_ref);
                            const op = mechanicalOps.find(o => o.op_id === opId);
                            const opType = op ? mechanicalOpTypes.find(t => t.type_id === op.type) : null;
                            if (!op) return null;
                            return (
                                <div
                                    className="p-2 rounded text-xs"
                                    style={{ background: 'var(--bg-canvas)', border: '1px solid var(--border-panel)' }}
                                >
                                    <div className="flex items-center gap-2 mb-1">
                                        <span
                                            className="px-1.5 py-0.5 rounded font-semibold uppercase"
                                            style={{
                                                fontSize: 9,
                                                background: 'var(--dot-purple, #a855f7)',
                                                color: '#fff',
                                            }}
                                        >
                                            {opType?.name || op.type}
                                        </span>
                                        <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>
                                            {op.name}
                                        </span>
                                    </div>
                                    {op.description && (
                                        <div style={{ color: 'var(--text-muted)' }}>
                                            {op.description}
                                        </div>
                                    )}
                                </div>
                            );
                        })()}

                        {/* Output Schema for MECH nodes */}
                        <div>
                            <label style={labelStyle}>Output Schema</label>
                            <select
                                value={parseSchemaRef(localData.output_schema_ref) || ''}
                                onChange={e => {
                                    const schemaId = e.target.value;
                                    if (!schemaId) {
                                        updateField('output_schema_ref', '');
                                        return;
                                    }
                                    const schema = schemas.find(s => s.schema_id === schemaId);
                                    if (schema) {
                                        updateField('output_schema_ref', buildSchemaRef(schema));
                                    }
                                }}
                                style={fieldStyle}
                            >
                                <option value="">-- Select Schema --</option>
                                {schemas.map(s => (
                                    <option key={s.schema_id} value={s.schema_id}>
                                        {s.title || s.schema_id.replace(/_/g, ' ')}
                                    </option>
                                ))}
                            </select>
                        </div>
                    </div>
                )}

                {/* === UI Configuration (ADR-047) === */}
                {localData.type === 'task' && localData.internal_type === 'UI' && (
                    <div className="space-y-3">
                        <div
                            className="p-2 rounded text-xs"
                            style={{ background: 'var(--bg-canvas)', border: '1px solid var(--border-panel)' }}
                        >
                            <div className="flex items-center gap-2 mb-1">
                                <span
                                    className="px-1.5 py-0.5 rounded font-semibold uppercase"
                                    style={{
                                        fontSize: 9,
                                        background: '#3b82f6',
                                        color: '#fff',
                                    }}
                                >
                                    UI
                                </span>
                                <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>
                                    Operator Entry
                                </span>
                            </div>
                            <div style={{ color: 'var(--text-muted)' }}>
                                This node presents a form to the operator and captures their input.
                            </div>
                        </div>

                        <div>
                            <label style={labelStyle}>Renders</label>
                            <input
                                type="text"
                                value={localData.renders || ''}
                                onChange={e => updateField('renders', e.target.value)}
                                placeholder="e.g., question_set"
                                style={fieldStyle}
                            />
                        </div>

                        <div>
                            <label style={labelStyle}>Captures</label>
                            <input
                                type="text"
                                value={localData.captures || ''}
                                onChange={e => updateField('captures', e.target.value)}
                                placeholder="e.g., user_answers"
                                style={fieldStyle}
                            />
                        </div>
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

                {/* Includes (for task nodes with LLM internal_type - not pgc) */}
                {localData.type === 'task' && (localData.internal_type || 'LLM') === 'LLM' && (
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
