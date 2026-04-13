import React from 'react';
import CollapsibleSection from '../../../common/CollapsibleSection';
import { PGC_GATE_KINDS, fieldStyle, labelStyle, sectionHeaderStyle } from '../../../../constants/nodeConfig';
import {
    buildTemplateRef, parseTemplateRef,
    buildFragmentRef, parseFragmentRef,
    buildSchemaRef, parseSchemaRef,
    buildMechOpRef, parseMechOpRef,
} from '../../../../utils/refFormatters';

/**
 * PGC Gate internals section: Pass A (Question Generation), Operator Entry, Pass B (Clarification Merge).
 */
export default function PGCSection({
    localData,
    internals,
    expandedPass,
    setExpandedPass,
    templates,
    schemas,
    roleFragments,
    taskFragments,
    pgcFragments,
    mechanicalOps,
    updateField,
    updateQuestionGeneration,
    updateQuestionGenIncludes,
    updateClarificationMerge,
    handleGateKindChange,
}) {
    // Parse current refs from internals
    const qgTemplateId = parseTemplateRef(internals.question_generation?.template_ref);
    const qgRoleId = parseFragmentRef(internals.question_generation?.includes?.ROLE_PROMPT);
    const qgTaskId = parseFragmentRef(internals.question_generation?.includes?.TASK_PROMPT);
    const qgPgcId = parseFragmentRef(internals.question_generation?.includes?.PGC_CONTEXT);
    const qgSchemaId = parseSchemaRef(internals.question_generation?.output_schema_ref);
    const cmTemplateId = parseTemplateRef(internals.clarification_merge?.template_ref);
    const cmSchemaId = parseSchemaRef(internals.clarification_merge?.output_schema_ref);

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
        <>
            {/* Gate Kind */}
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

            {/* Produces */}
            <div>
                <label style={labelStyle}>Produces</label>
                <input
                    type="text"
                    value={localData.produces || ''}
                    onChange={e => updateField('produces', e.target.value)}
                    placeholder="pgc_clarifications.discovery"
                    style={fieldStyle}
                />
            </div>

            {/* Gate Internals */}
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
        </>
    );
}
