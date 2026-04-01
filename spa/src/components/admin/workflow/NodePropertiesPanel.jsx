import React, { useState, useEffect } from 'react';
import { NODE_TYPES, PGC_GATE_KINDS, fieldStyle, labelStyle } from '../../../constants/nodeConfig';
import PGCSection from './nodePropertySections/PGCSection';
import TaskSection from './nodePropertySections/TaskSection';
import QASection from './nodePropertySections/QASection';
import IntakeGateSection from './nodePropertySections/IntakeGateSection';
import EndSection from './nodePropertySections/EndSection';

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
    const internals = localData.internals || getDefaultPgcInternals();

    // Handle gate_kind change - auto-update produces
    const handleGateKindChange = (e) => {
        const gateKind = e.target.value;
        const gateConfig = PGC_GATE_KINDS.find(g => g.value === gateKind);
        const produces = gateConfig?.produces || `pgc_clarifications.${gateKind}`;
        const updated = { ...localData, gate_kind: gateKind, produces };
        setLocalData(updated);
        onChange(updated);
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

                {/* PGC Gate section */}
                {isPgcNode && (
                    <PGCSection
                        localData={localData}
                        internals={internals}
                        expandedPass={expandedPass}
                        setExpandedPass={setExpandedPass}
                        templates={templates}
                        schemas={schemas}
                        roleFragments={roleFragments}
                        taskFragments={taskFragments}
                        pgcFragments={pgcFragments}
                        mechanicalOps={mechanicalOps}
                        updateField={updateField}
                        updateQuestionGeneration={updateQuestionGeneration}
                        updateQuestionGenIncludes={updateQuestionGenIncludes}
                        updateClarificationMerge={updateClarificationMerge}
                        handleGateKindChange={handleGateKindChange}
                    />
                )}

                {/* Non-PGC: Description */}
                {!isPgcNode && (
                    <div>
                        <label style={labelStyle}>Description</label>
                        <textarea
                            value={localData.description || ''}
                            onChange={e => updateField('description', e.target.value)}
                            rows={2}
                            style={{ ...fieldStyle, resize: 'vertical' }}
                        />
                    </div>
                )}

                {/* Task node section */}
                {localData.type === 'task' && (
                    <TaskSection
                        localData={localData}
                        templates={templates}
                        schemas={schemas}
                        roleFragments={roleFragments}
                        taskFragments={taskFragments}
                        pgcFragments={pgcFragments}
                        mechanicalOpTypes={mechanicalOpTypes}
                        mechanicalOps={mechanicalOps}
                        updateField={updateField}
                        updateInclude={updateInclude}
                        removeInclude={removeInclude}
                        addCustomInclude={addCustomInclude}
                        setLocalData={setLocalData}
                        onChange={onChange}
                    />
                )}

                {/* QA node section */}
                {localData.type === 'qa' && (
                    <QASection
                        localData={localData}
                        templates={templates}
                        updateField={updateField}
                    />
                )}

                {/* Intake gate section */}
                {localData.type === 'intake_gate' && (
                    <IntakeGateSection
                        localData={localData}
                        templates={templates}
                        updateField={updateField}
                    />
                )}

                {/* End node section */}
                {localData.type === 'end' && (
                    <EndSection
                        localData={localData}
                        updateField={updateField}
                    />
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
            </div>
        </div>
    );
}
