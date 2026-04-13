import React from 'react';
import { INTERNAL_TYPES, fieldStyle, labelStyle } from '../../../../constants/nodeConfig';
import {
    buildTemplateRef, parseTemplateRef,
    buildFragmentRef, parseFragmentRef,
    buildSchemaRef, parseSchemaRef,
    buildMechOpRef, parseMechOpRef,
} from '../../../../utils/refFormatters';
import IncludesPanel from './IncludesPanel';

/**
 * Task node properties: internal type selector, LLM/MECH/UI configuration.
 */
export default function TaskSection({
    localData,
    templates,
    schemas,
    roleFragments,
    taskFragments,
    pgcFragments,
    mechanicalOpTypes,
    mechanicalOps,
    updateField,
    updateInclude,
    removeInclude,
    addCustomInclude,
    setLocalData,
    onChange,
}) {
    const currentTemplateId = parseTemplateRef(localData.task_ref);
    const includes = localData.includes || {};
    const currentRoleId = parseFragmentRef(includes.ROLE_PROMPT || '');
    const currentTaskId = parseFragmentRef(includes.TASK_PROMPT || '');
    const currentSchemaId = parseSchemaRef(includes.OUTPUT_SCHEMA || '');
    const currentPgcId = parseFragmentRef(includes.PGC_CONTEXT || '');

    const customIncludes = Object.entries(includes).filter(
        ([key]) => !['ROLE_PROMPT', 'TASK_PROMPT', 'OUTPUT_SCHEMA', 'PGC_CONTEXT'].includes(key)
    );

    const handleTemplateChange = (e) => {
        const templateId = e.target.value;
        if (!templateId) { updateField('task_ref', ''); return; }
        const template = templates.find(t => t.template_id === templateId);
        if (template) updateField('task_ref', buildTemplateRef(template));
    };

    const handleRoleChange = (e) => {
        const fragmentId = e.target.value;
        if (!fragmentId) { removeInclude('ROLE_PROMPT'); return; }
        const fragment = roleFragments.find(f => f.fragment_id === `role:${fragmentId}` || f.id === fragmentId);
        if (fragment) updateInclude('ROLE_PROMPT', buildFragmentRef(fragment));
    };

    const handleTaskChange = (e) => {
        const fragmentId = e.target.value;
        if (!fragmentId) { removeInclude('TASK_PROMPT'); return; }
        const fragment = taskFragments.find(f => f.fragment_id === `task:${fragmentId}` || f.id === fragmentId);
        if (fragment) updateInclude('TASK_PROMPT', buildFragmentRef(fragment));
    };

    const handleSchemaChange = (e) => {
        const schemaId = e.target.value;
        if (!schemaId) { removeInclude('OUTPUT_SCHEMA'); return; }
        const schema = schemas.find(s => s.schema_id === schemaId);
        if (schema) updateInclude('OUTPUT_SCHEMA', buildSchemaRef(schema));
    };

    const handlePgcChange = (e) => {
        const fragmentId = e.target.value;
        if (!fragmentId) { removeInclude('PGC_CONTEXT'); return; }
        const fragment = pgcFragments.find(f => f.fragment_id === `pgc:${fragmentId}` || f.id === fragmentId);
        if (fragment) updateInclude('PGC_CONTEXT', buildFragmentRef(fragment));
    };

    return (
        <>
            {/* Internal Type selector */}
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

            {/* Produces */}
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

            {/* === LLM Configuration (default) === */}
            {(localData.internal_type || 'LLM') === 'LLM' && (
                <>
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

                    {/* Includes */}
                    <IncludesPanel
                        currentRoleId={currentRoleId}
                        currentTaskId={currentTaskId}
                        currentSchemaId={currentSchemaId}
                        currentPgcId={currentPgcId}
                        customIncludes={customIncludes}
                        roleFragments={roleFragments}
                        taskFragments={taskFragments}
                        schemas={schemas}
                        pgcFragments={pgcFragments}
                        handleRoleChange={handleRoleChange}
                        handleTaskChange={handleTaskChange}
                        handleSchemaChange={handleSchemaChange}
                        handlePgcChange={handlePgcChange}
                        updateInclude={updateInclude}
                        removeInclude={removeInclude}
                        addCustomInclude={addCustomInclude}
                        localData={localData}
                        setLocalData={setLocalData}
                        onChange={onChange}
                    />
                </>
            )}

            {/* === MECH Configuration (ADR-047) === */}
            {localData.internal_type === 'MECH' && (
                <div className="space-y-3">
                    <div>
                        <label style={labelStyle}>Mechanical Operation</label>
                        <select
                            value={parseMechOpRef(localData.op_ref) || ''}
                            onChange={e => {
                                const opId = e.target.value;
                                if (!opId) { updateField('op_ref', ''); return; }
                                const op = mechanicalOps.find(o => o.op_id === opId);
                                if (op) updateField('op_ref', buildMechOpRef(op));
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
                                if (!schemaId) { updateField('output_schema_ref', ''); return; }
                                const schema = schemas.find(s => s.schema_id === schemaId);
                                if (schema) updateField('output_schema_ref', buildSchemaRef(schema));
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

            {/* === UI Configuration (ADR-047 Addendum A: Entry Operations) === */}
            {localData.internal_type === 'UI' && (
                <div className="space-y-3">
                    <div>
                        <label style={labelStyle}>Entry Operation</label>
                        <select
                            value={parseMechOpRef(localData.op_ref) || ''}
                            onChange={e => {
                                const opId = e.target.value;
                                if (!opId) { updateField('op_ref', ''); return; }
                                const op = mechanicalOps.find(o => o.op_id === opId);
                                if (op) updateField('op_ref', buildMechOpRef(op));
                            }}
                            style={fieldStyle}
                        >
                            <option value="">-- Select Entry Operation --</option>
                            {mechanicalOps.filter(op => op.type === 'entry').map(op => (
                                <option key={op.op_id} value={op.op_id}>
                                    {op.name}
                                </option>
                            ))}
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

                    {/* Show Entry operation details when selected */}
                    {localData.op_ref && (() => {
                        const opId = parseMechOpRef(localData.op_ref);
                        const op = mechanicalOps.find(o => o.op_id === opId);
                        if (!op) return null;
                        const config = op.config || {};
                        return (
                            <div
                                className="p-2 rounded text-xs space-y-2"
                                style={{ background: 'var(--bg-canvas)', border: '1px solid var(--border-panel)' }}
                            >
                                <div className="flex items-center gap-2">
                                    <span
                                        className="px-1.5 py-0.5 rounded font-semibold uppercase"
                                        style={{
                                            fontSize: 9,
                                            background: 'var(--dot-orange, #f97316)',
                                            color: '#fff',
                                        }}
                                    >
                                        Entry
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
                                <div className="pt-2 border-t space-y-1" style={{ borderColor: 'var(--border-panel)' }}>
                                    <div className="flex justify-between">
                                        <span style={{ color: 'var(--text-muted)' }}>Renders:</span>
                                        <span className="font-mono" style={{ color: 'var(--text-secondary)' }}>
                                            {config.renders || '-'}
                                        </span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span style={{ color: 'var(--text-muted)' }}>Captures:</span>
                                        <span className="font-mono" style={{ color: 'var(--text-secondary)' }}>
                                            {config.captures || '-'}
                                        </span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span style={{ color: 'var(--text-muted)' }}>Layout:</span>
                                        <span className="font-mono" style={{ color: 'var(--text-secondary)' }}>
                                            {config.layout || 'form'}
                                        </span>
                                    </div>
                                </div>
                                {config.entry_prompt && (
                                    <div
                                        className="p-2 rounded mt-2"
                                        style={{ background: 'var(--bg-panel)' }}
                                    >
                                        <div className="text-[10px] uppercase mb-1" style={{ color: 'var(--text-muted)' }}>
                                            Entry Prompt
                                        </div>
                                        <div style={{ color: 'var(--text-primary)' }}>
                                            {config.entry_prompt}
                                        </div>
                                    </div>
                                )}
                            </div>
                        );
                    })()}

                    {/* Fallback: manual renders/captures if no operation selected */}
                    {!localData.op_ref && (
                        <>
                            <div
                                className="p-2 rounded text-xs"
                                style={{ background: 'var(--bg-canvas)', color: 'var(--text-muted)' }}
                            >
                                Select an Entry operation above, or define custom renders/captures below.
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
                        </>
                    )}
                </div>
            )}
        </>
    );
}
