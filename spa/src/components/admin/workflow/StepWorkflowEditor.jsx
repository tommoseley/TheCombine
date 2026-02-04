import React, { useState, useCallback, useMemo, useEffect } from 'react';
import {
    DndContext,
    closestCenter,
    KeyboardSensor,
    PointerSensor,
    useSensor,
    useSensors,
} from '@dnd-kit/core';
import {
    SortableContext,
    sortableKeyboardCoordinates,
    verticalListSortingStrategy,
    useSortable,
    arrayMove,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { useWorkflowEditor } from '../../../hooks/useWorkflowEditor';

const TAB_STYLE = {
    padding: '6px 14px',
    fontSize: 12,
    fontWeight: 600,
    border: 'none',
    cursor: 'pointer',
    transition: 'opacity 0.15s',
    background: 'transparent',
};

const fieldStyle = {
    width: '100%',
    padding: '5px 8px',
    borderRadius: 4,
    fontSize: 12,
    background: 'var(--bg-input, var(--bg-canvas))',
    border: '1px solid var(--border-panel)',
    color: 'var(--text-primary)',
    outline: 'none',
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

const DEFAULT_PRODUCTION_STEP = {
    step_id: 'new_step',
    produces: '',
    scope: '',
    inputs: [],
};

const DEFAULT_ITERATION_STEP = {
    step_id: 'new_iteration',
    iterate_over: { doc_type: '', collection_field: '', entity_type: '' },
    scope: '',
    steps: [],
};

/**
 * Editor for step-based project orchestration workflows (workflow.v1 format).
 * Steps tab: editable inline forms, drag-to-reorder, add/delete.
 * JSON tab: raw editable textarea.
 * Metadata tab: read-only governance fields.
 */
export default function StepWorkflowEditor({ workspaceId, workflow, onArtifactSave, onDelete, onNavigateToWorkflow }) {
    const [activeTab, setActiveTab] = useState('steps');
    const [jsonText, setJsonText] = useState('');
    const [jsonError, setJsonError] = useState(null);

    const artifactId = useMemo(() => {
        if (!workflow) return null;
        return `workflow:${workflow.workflow_id}:${workflow.active_version}:definition`;
    }, [workflow]);

    const {
        workflowJson,
        loading,
        error,
        saving,
        updateWorkflow,
    } = useWorkflowEditor(workspaceId, artifactId, {
        onSave: (result) => {
            onArtifactSave?.(artifactId, result);
        },
    });

    // Switch to JSON tab - sync text
    const handleTabChange = useCallback((tab) => {
        if (tab === 'json' && workflowJson) {
            setJsonText(JSON.stringify(workflowJson, null, 2));
            setJsonError(null);
        }
        setActiveTab(tab);
    }, [workflowJson]);

    // Handle raw JSON edit
    const handleJsonTextChange = useCallback((e) => {
        const text = e.target.value;
        setJsonText(text);
        try {
            const parsed = JSON.parse(text);
            setJsonError(null);
            updateWorkflow(parsed);
        } catch (err) {
            setJsonError(err.message);
        }
    }, [updateWorkflow]);

    // Steps array mutation helpers
    const handleStepChange = useCallback((index, updatedStep) => {
        if (!workflowJson) return;
        const newSteps = [...workflowJson.steps];
        newSteps[index] = updatedStep;
        updateWorkflow({ ...workflowJson, steps: newSteps });
    }, [workflowJson, updateWorkflow]);

    const handleStepDelete = useCallback((index) => {
        if (!workflowJson) return;
        const newSteps = workflowJson.steps.filter((_, i) => i !== index);
        updateWorkflow({ ...workflowJson, steps: newSteps });
    }, [workflowJson, updateWorkflow]);

    const handleAddStep = useCallback((type) => {
        if (!workflowJson) return;
        const skeleton = type === 'iteration'
            ? { ...DEFAULT_ITERATION_STEP, step_id: `new_iteration_${(workflowJson.steps?.length || 0) + 1}` }
            : { ...DEFAULT_PRODUCTION_STEP, step_id: `new_step_${(workflowJson.steps?.length || 0) + 1}` };
        updateWorkflow({
            ...workflowJson,
            steps: [...(workflowJson.steps || []), skeleton],
        });
    }, [workflowJson, updateWorkflow]);

    const handleStepsReorder = useCallback((oldIndex, newIndex) => {
        if (!workflowJson) return;
        const newSteps = arrayMove(workflowJson.steps, oldIndex, newIndex);
        updateWorkflow({ ...workflowJson, steps: newSteps });
    }, [workflowJson, updateWorkflow]);

    // Delete workflow handler
    const handleDeleteWorkflow = useCallback(() => {
        if (!onDelete || !workflow) return;
        if (window.confirm(`Delete workflow "${workflow.workflow_id}"? This cannot be undone until you discard workspace changes.`)) {
            onDelete(workflow.workflow_id);
        }
    }, [onDelete, workflow]);

    if (!workflow) {
        return (
            <div
                className="flex-1 flex items-center justify-center"
                style={{ background: 'var(--bg-canvas)' }}
            >
                <div className="text-center" style={{ color: 'var(--text-muted)' }}>
                    <div className="text-lg mb-1">Workflow Editor</div>
                    <div className="text-sm">Select a workflow from the sidebar to begin editing</div>
                </div>
            </div>
        );
    }

    return (
        <div className="flex-1 flex flex-col overflow-hidden" style={{ background: 'var(--bg-canvas)' }}>
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
                                onClick={handleDeleteWorkflow}
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
                {[
                    { id: 'steps', label: 'Steps' },
                    { id: 'json', label: 'JSON' },
                    { id: 'metadata', label: 'Metadata' },
                ].map(tab => (
                    <button
                        key={tab.id}
                        onClick={() => handleTabChange(tab.id)}
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

            {/* Content */}
            {loading ? (
                <div className="flex-1 flex items-center justify-center">
                    <span style={{ color: 'var(--text-muted)' }}>Loading workflow...</span>
                </div>
            ) : (
                <div className="flex-1 overflow-hidden">
                    {/* Steps tab */}
                    {activeTab === 'steps' && (
                        <div className="h-full overflow-y-auto p-4">
                            <EditableStepsList
                                steps={workflowJson?.steps || []}
                                onStepChange={handleStepChange}
                                onStepDelete={handleStepDelete}
                                onReorder={handleStepsReorder}
                            />
                            <div className="flex gap-2 mt-3">
                                <button
                                    onClick={() => handleAddStep('production')}
                                    className="text-xs px-3 py-1.5 rounded hover:opacity-80"
                                    style={{
                                        background: 'var(--action-primary)',
                                        color: '#000',
                                        fontWeight: 600,
                                    }}
                                >
                                    + Production Step
                                </button>
                                <button
                                    onClick={() => handleAddStep('iteration')}
                                    className="text-xs px-3 py-1.5 rounded hover:opacity-80"
                                    style={{
                                        background: 'transparent',
                                        color: 'var(--action-primary)',
                                        border: '1px solid var(--action-primary)',
                                        fontWeight: 600,
                                    }}
                                >
                                    + Iteration Step
                                </button>
                            </div>
                        </div>
                    )}

                    {/* JSON tab */}
                    {activeTab === 'json' && (
                        <div className="h-full flex flex-col p-4">
                            <textarea
                                value={jsonText}
                                onChange={handleJsonTextChange}
                                className="flex-1 font-mono text-xs p-3 rounded"
                                style={{
                                    background: 'var(--bg-input, var(--bg-canvas))',
                                    border: jsonError
                                        ? '1px solid #ef4444'
                                        : '1px solid var(--border-panel)',
                                    color: 'var(--text-primary)',
                                    resize: 'none',
                                    outline: 'none',
                                }}
                                spellCheck={false}
                            />
                            {jsonError && (
                                <div className="mt-2 text-xs" style={{ color: '#ef4444' }}>
                                    JSON Error: {jsonError}
                                </div>
                            )}
                        </div>
                    )}

                    {/* Metadata tab */}
                    {activeTab === 'metadata' && (
                        <div className="h-full overflow-y-auto p-4">
                            {workflowJson ? (
                                <StepMetadataView
                                    workflow={workflowJson}
                                    onUpdateWorkflow={updateWorkflow}
                                    onNavigateToWorkflow={onNavigateToWorkflow}
                                />
                            ) : (
                                <div style={{ color: 'var(--text-muted)' }}>No workflow loaded</div>
                            )}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

// =============================================================================
// Sortable Steps List
// =============================================================================

function EditableStepsList({ steps, onStepChange, onStepDelete, onReorder }) {
    const sensors = useSensors(
        useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
        useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
    );

    const stepIds = useMemo(() => steps.map(s => s.step_id), [steps]);

    const handleDragEnd = useCallback((event) => {
        const { active, over } = event;
        if (!over || active.id === over.id) return;
        const oldIndex = steps.findIndex(s => s.step_id === active.id);
        const newIndex = steps.findIndex(s => s.step_id === over.id);
        if (oldIndex !== -1 && newIndex !== -1) {
            onReorder(oldIndex, newIndex);
        }
    }, [steps, onReorder]);

    if (steps.length === 0) {
        return (
            <div className="text-sm py-4" style={{ color: 'var(--text-muted)' }}>
                No steps defined. Add a step to get started.
            </div>
        );
    }

    return (
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
            <SortableContext items={stepIds} strategy={verticalListSortingStrategy}>
                {steps.map((step, idx) => (
                    <SortableStepCard
                        key={step.step_id}
                        step={step}
                        index={idx}
                        onChange={onStepChange}
                        onDelete={onStepDelete}
                    />
                ))}
            </SortableContext>
        </DndContext>
    );
}

// =============================================================================
// Sortable Step Card (wrapper for drag behavior)
// =============================================================================

function SortableStepCard({ step, index, onChange, onDelete }) {
    const {
        attributes,
        listeners,
        setNodeRef,
        transform,
        transition,
        isDragging,
    } = useSortable({ id: step.step_id });

    const style = {
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.5 : 1,
    };

    return (
        <div ref={setNodeRef} style={style}>
            <EditableStepCard
                step={step}
                index={index}
                onChange={onChange}
                onDelete={onDelete}
                dragHandleProps={{ ...attributes, ...listeners }}
            />
        </div>
    );
}

// =============================================================================
// Editable Step Card
// =============================================================================

function EditableStepCard({ step, index, onChange, onDelete, dragHandleProps, depth = 0 }) {
    const [localData, setLocalData] = useState(step);
    const [expanded, setExpanded] = useState(true);

    useEffect(() => {
        setLocalData(step);
    }, [step]);

    const isIteration = !!localData.iterate_over;

    const updateField = (field, value) => {
        const updated = { ...localData, [field]: value };
        setLocalData(updated);
        onChange(index, updated);
    };

    const updateIterateOver = (field, value) => {
        const iterateOver = { ...localData.iterate_over, [field]: value };
        const updated = { ...localData, iterate_over: iterateOver };
        setLocalData(updated);
        onChange(index, updated);
    };

    // Input array management
    const addInput = () => {
        const inputs = [...(localData.inputs || []), { doc_type: '', scope: '' }];
        const updated = { ...localData, inputs };
        setLocalData(updated);
        onChange(index, updated);
    };

    const updateInput = (inputIdx, field, value) => {
        const inputs = [...(localData.inputs || [])];
        inputs[inputIdx] = { ...inputs[inputIdx], [field]: value };
        const updated = { ...localData, inputs };
        setLocalData(updated);
        onChange(index, updated);
    };

    const removeInput = (inputIdx) => {
        const inputs = (localData.inputs || []).filter((_, i) => i !== inputIdx);
        const updated = { ...localData, inputs };
        setLocalData(updated);
        onChange(index, updated);
    };

    // Nested step management for iteration steps
    const handleNestedStepChange = useCallback((nestedIdx, updatedStep) => {
        const newSteps = [...(localData.steps || [])];
        newSteps[nestedIdx] = updatedStep;
        const updated = { ...localData, steps: newSteps };
        setLocalData(updated);
        onChange(index, updated);
    }, [localData, index, onChange]);

    const handleNestedStepDelete = useCallback((nestedIdx) => {
        const newSteps = (localData.steps || []).filter((_, i) => i !== nestedIdx);
        const updated = { ...localData, steps: newSteps };
        setLocalData(updated);
        onChange(index, updated);
    }, [localData, index, onChange]);

    const handleNestedStepAdd = useCallback(() => {
        const newSteps = [
            ...(localData.steps || []),
            { ...DEFAULT_PRODUCTION_STEP, step_id: `nested_step_${(localData.steps?.length || 0) + 1}` },
        ];
        const updated = { ...localData, steps: newSteps };
        setLocalData(updated);
        onChange(index, updated);
    }, [localData, index, onChange]);

    const handleNestedReorder = useCallback((oldIdx, newIdx) => {
        const newSteps = arrayMove(localData.steps || [], oldIdx, newIdx);
        const updated = { ...localData, steps: newSteps };
        setLocalData(updated);
        onChange(index, updated);
    }, [localData, index, onChange]);

    const cardStyle = {
        background: 'var(--bg-input, var(--bg-canvas))',
        border: '1px solid var(--border-panel)',
        borderRadius: 6,
        marginBottom: 8,
        marginLeft: depth * 20,
        borderLeft: isIteration
            ? '3px solid var(--action-primary)'
            : '3px solid var(--border-panel)',
    };

    return (
        <div style={cardStyle}>
            {/* Card header */}
            <div
                className="flex items-center gap-2 px-3 py-2"
                style={{
                    borderBottom: expanded ? '1px solid var(--border-panel)' : 'none',
                    background: 'var(--bg-panel)',
                    borderRadius: expanded ? '6px 6px 0 0' : 6,
                }}
            >
                {/* Drag handle */}
                {dragHandleProps && (
                    <span
                        {...dragHandleProps}
                        style={{ cursor: 'grab', color: 'var(--text-muted)', lineHeight: 1 }}
                        title="Drag to reorder"
                    >
                        <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor">
                            <circle cx="5" cy="3" r="1.5" />
                            <circle cx="11" cy="3" r="1.5" />
                            <circle cx="5" cy="8" r="1.5" />
                            <circle cx="11" cy="8" r="1.5" />
                            <circle cx="5" cy="13" r="1.5" />
                            <circle cx="11" cy="13" r="1.5" />
                        </svg>
                    </span>
                )}

                {/* Step type badge */}
                <span
                    className="text-xs font-mono px-1.5 py-0.5 rounded"
                    style={{
                        background: isIteration ? 'var(--action-primary)' : 'var(--bg-canvas)',
                        color: isIteration ? '#000' : 'var(--action-primary)',
                        border: '1px solid var(--border-panel)',
                        fontSize: 10,
                        fontWeight: 700,
                    }}
                >
                    {isIteration ? 'ITER' : 'STEP'}
                </span>

                {/* Step ID inline */}
                <span
                    className="text-xs font-mono"
                    style={{ color: 'var(--text-primary)', fontWeight: 600 }}
                >
                    {localData.step_id}
                </span>

                <span style={{ flex: 1 }} />

                {/* Expand/collapse */}
                <button
                    onClick={() => setExpanded(!expanded)}
                    className="p-0.5 rounded hover:opacity-80"
                    style={{ color: 'var(--text-muted)', background: 'transparent', border: 'none', cursor: 'pointer' }}
                    title={expanded ? 'Collapse' : 'Expand'}
                >
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        {expanded
                            ? <path d="M18 15l-6-6-6 6" />
                            : <path d="M6 9l6 6 6-6" />
                        }
                    </svg>
                </button>

                {/* Delete */}
                <button
                    onClick={() => onDelete(index)}
                    className="p-0.5 rounded hover:bg-red-500/20 transition-colors"
                    style={{ color: '#ef4444', background: 'transparent', border: 'none', cursor: 'pointer' }}
                    title="Delete step"
                >
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M18 6L6 18M6 6l12 12" />
                    </svg>
                </button>
            </div>

            {/* Card body */}
            {expanded && (
                <div className="p-3 space-y-2">
                    {/* Step ID */}
                    <div>
                        <label style={labelStyle}>Step ID</label>
                        <input
                            type="text"
                            value={localData.step_id || ''}
                            onChange={e => updateField('step_id', e.target.value)}
                            style={fieldStyle}
                        />
                    </div>

                    {isIteration ? (
                        <>
                            {/* Iterate Over fields */}
                            <div className="grid grid-cols-3 gap-2">
                                <div>
                                    <label style={labelStyle}>Doc Type</label>
                                    <input
                                        type="text"
                                        value={localData.iterate_over?.doc_type || ''}
                                        onChange={e => updateIterateOver('doc_type', e.target.value)}
                                        style={fieldStyle}
                                    />
                                </div>
                                <div>
                                    <label style={labelStyle}>Collection Field</label>
                                    <input
                                        type="text"
                                        value={localData.iterate_over?.collection_field || ''}
                                        onChange={e => updateIterateOver('collection_field', e.target.value)}
                                        style={fieldStyle}
                                    />
                                </div>
                                <div>
                                    <label style={labelStyle}>Entity Type</label>
                                    <input
                                        type="text"
                                        value={localData.iterate_over?.entity_type || ''}
                                        onChange={e => updateIterateOver('entity_type', e.target.value)}
                                        style={fieldStyle}
                                    />
                                </div>
                            </div>

                            {/* Scope */}
                            <div>
                                <label style={labelStyle}>Scope</label>
                                <input
                                    type="text"
                                    value={localData.scope || ''}
                                    onChange={e => updateField('scope', e.target.value)}
                                    style={fieldStyle}
                                />
                            </div>

                            {/* Nested steps */}
                            <div className="mt-3">
                                <div className="flex items-center justify-between mb-2">
                                    <label style={labelStyle}>Nested Steps</label>
                                    <button
                                        onClick={handleNestedStepAdd}
                                        className="text-xs px-2 py-0.5 rounded hover:opacity-80"
                                        style={{
                                            color: 'var(--action-primary)',
                                            background: 'transparent',
                                            border: 'none',
                                            cursor: 'pointer',
                                            fontWeight: 600,
                                        }}
                                    >
                                        + Add
                                    </button>
                                </div>
                                <NestedStepsList
                                    steps={localData.steps || []}
                                    onStepChange={handleNestedStepChange}
                                    onStepDelete={handleNestedStepDelete}
                                    onReorder={handleNestedReorder}
                                />
                            </div>
                        </>
                    ) : (
                        <>
                            {/* Production step fields */}
                            <div>
                                <label style={labelStyle}>Produces</label>
                                <input
                                    type="text"
                                    value={localData.produces || ''}
                                    onChange={e => updateField('produces', e.target.value)}
                                    placeholder="document_type (e.g., project_discovery)"
                                    style={fieldStyle}
                                />
                            </div>

                            <div className="grid grid-cols-2 gap-2">
                                <div>
                                    <label style={labelStyle}>Scope</label>
                                    <input
                                        type="text"
                                        value={localData.scope || ''}
                                        onChange={e => updateField('scope', e.target.value)}
                                        placeholder="project"
                                        style={fieldStyle}
                                    />
                                </div>
                                <div>
                                    <label style={labelStyle}>Creates Entities</label>
                                    <input
                                        type="text"
                                        value={localData.creates_entities || ''}
                                        onChange={e => updateField('creates_entities', e.target.value || undefined)}
                                        placeholder="e.g., epic"
                                        style={fieldStyle}
                                    />
                                </div>
                            </div>

                            {/* Inputs */}
                            <div>
                                <div className="flex items-center justify-between mb-1">
                                    <label style={labelStyle}>Inputs</label>
                                    <button
                                        onClick={addInput}
                                        className="text-xs hover:opacity-80"
                                        style={{
                                            color: 'var(--action-primary)',
                                            background: 'transparent',
                                            border: 'none',
                                            cursor: 'pointer',
                                            fontWeight: 600,
                                        }}
                                    >
                                        + Add
                                    </button>
                                </div>
                                {(localData.inputs || []).length === 0 ? (
                                    <div className="text-xs py-1" style={{ color: 'var(--text-muted)' }}>
                                        No inputs
                                    </div>
                                ) : (
                                    <div className="space-y-1">
                                        {(localData.inputs || []).map((input, iIdx) => (
                                            <div key={iIdx} className="flex gap-1 items-end">
                                                <div style={{ flex: 1 }}>
                                                    {iIdx === 0 && <label style={{ ...labelStyle, fontSize: 9 }}>Doc/Entity Type</label>}
                                                    <input
                                                        type="text"
                                                        value={input.doc_type || input.entity_type || ''}
                                                        onChange={e => {
                                                            const val = e.target.value;
                                                            if (input.entity_type !== undefined) {
                                                                updateInput(iIdx, 'entity_type', val);
                                                            } else {
                                                                updateInput(iIdx, 'doc_type', val);
                                                            }
                                                        }}
                                                        placeholder="doc_type"
                                                        style={{ ...fieldStyle, fontSize: 11 }}
                                                    />
                                                </div>
                                                <div style={{ width: '30%' }}>
                                                    {iIdx === 0 && <label style={{ ...labelStyle, fontSize: 9 }}>Scope</label>}
                                                    <input
                                                        type="text"
                                                        value={input.scope || ''}
                                                        onChange={e => updateInput(iIdx, 'scope', e.target.value)}
                                                        placeholder="scope"
                                                        style={{ ...fieldStyle, fontSize: 11 }}
                                                    />
                                                </div>
                                                <label
                                                    className="flex items-center gap-1 text-xs pb-0.5"
                                                    style={{ color: 'var(--text-muted)', whiteSpace: 'nowrap' }}
                                                >
                                                    <input
                                                        type="checkbox"
                                                        checked={input.context || false}
                                                        onChange={e => updateInput(iIdx, 'context', e.target.checked || undefined)}
                                                    />
                                                    ctx
                                                </label>
                                                <button
                                                    onClick={() => removeInput(iIdx)}
                                                    className="pb-0.5"
                                                    style={{
                                                        color: '#ef4444',
                                                        background: 'transparent',
                                                        border: 'none',
                                                        cursor: 'pointer',
                                                        fontSize: 12,
                                                        fontWeight: 700,
                                                    }}
                                                >
                                                    x
                                                </button>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </>
                    )}
                </div>
            )}
        </div>
    );
}

// =============================================================================
// Nested Steps List (for iteration steps - own DndContext)
// =============================================================================

function NestedStepsList({ steps, onStepChange, onStepDelete, onReorder }) {
    const sensors = useSensors(
        useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
        useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
    );

    const stepIds = useMemo(() => steps.map(s => s.step_id), [steps]);

    const handleDragEnd = useCallback((event) => {
        const { active, over } = event;
        if (!over || active.id === over.id) return;
        const oldIndex = steps.findIndex(s => s.step_id === active.id);
        const newIndex = steps.findIndex(s => s.step_id === over.id);
        if (oldIndex !== -1 && newIndex !== -1) {
            onReorder(oldIndex, newIndex);
        }
    }, [steps, onReorder]);

    if (steps.length === 0) {
        return (
            <div className="text-xs py-1" style={{ color: 'var(--text-muted)' }}>
                No nested steps
            </div>
        );
    }

    return (
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
            <SortableContext items={stepIds} strategy={verticalListSortingStrategy}>
                {steps.map((step, idx) => (
                    <NestedSortableStepCard
                        key={step.step_id}
                        step={step}
                        index={idx}
                        onChange={onStepChange}
                        onDelete={onStepDelete}
                    />
                ))}
            </SortableContext>
        </DndContext>
    );
}

function NestedSortableStepCard({ step, index, onChange, onDelete }) {
    const {
        attributes,
        listeners,
        setNodeRef,
        transform,
        transition,
        isDragging,
    } = useSortable({ id: step.step_id });

    const style = {
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.5 : 1,
    };

    return (
        <div ref={setNodeRef} style={style}>
            <EditableStepCard
                step={step}
                index={index}
                onChange={onChange}
                onDelete={onDelete}
                dragHandleProps={{ ...attributes, ...listeners }}
                depth={1}
            />
        </div>
    );
}

// =============================================================================
// Metadata View (unchanged)
// =============================================================================

function StepMetadataView({ workflow, onUpdateWorkflow, onNavigateToWorkflow }) {
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
