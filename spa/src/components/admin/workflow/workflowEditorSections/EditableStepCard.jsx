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

// =============================================================================
// Editable Step Card
// =============================================================================

export function EditableStepCard({ step, index, documentTypes = [], onChange, onDelete, dragHandleProps, depth = 0 }) {
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
                                    <select
                                        value={localData.iterate_over?.doc_type || ''}
                                        onChange={e => updateIterateOver('doc_type', e.target.value)}
                                        style={fieldStyle}
                                    >
                                        <option value="">-- Select --</option>
                                        {documentTypes.map(dt => (
                                            <option key={dt.doc_type_id} value={dt.doc_type_id}>
                                                {dt.doc_type_id}
                                            </option>
                                        ))}
                                    </select>
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
                                    documentTypes={documentTypes}
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
                                <select
                                    value={localData.produces || ''}
                                    onChange={e => updateField('produces', e.target.value)}
                                    style={fieldStyle}
                                >
                                    <option value="">-- Select document type --</option>
                                    {documentTypes.map(dt => (
                                        <option key={dt.doc_type_id} value={dt.doc_type_id}>
                                            {dt.doc_type_id}
                                        </option>
                                    ))}
                                </select>
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
                                                    <select
                                                        value={input.doc_type || input.entity_type || ''}
                                                        onChange={e => {
                                                            const val = e.target.value;
                                                            if (input.entity_type !== undefined) {
                                                                updateInput(iIdx, 'entity_type', val);
                                                            } else {
                                                                updateInput(iIdx, 'doc_type', val);
                                                            }
                                                        }}
                                                        style={{ ...fieldStyle, fontSize: 11 }}
                                                    >
                                                        <option value="">-- Select --</option>
                                                        {documentTypes.map(dt => (
                                                            <option key={dt.doc_type_id} value={dt.doc_type_id}>
                                                                {dt.doc_type_id}
                                                            </option>
                                                        ))}
                                                    </select>
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

function NestedStepsList({ steps, documentTypes = [], onStepChange, onStepDelete, onReorder }) {
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
                        documentTypes={documentTypes}
                        onChange={onStepChange}
                        onDelete={onStepDelete}
                    />
                ))}
            </SortableContext>
        </DndContext>
    );
}

function NestedSortableStepCard({ step, index, documentTypes = [], onChange, onDelete }) {
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
                documentTypes={documentTypes}
                onChange={onChange}
                onDelete={onDelete}
                dragHandleProps={{ ...attributes, ...listeners }}
                depth={1}
            />
        </div>
    );
}
