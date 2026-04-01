import React, { useCallback, useMemo } from 'react';
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

import { EditableStepCard } from './EditableStepCard';

// Re-export for backward compatibility (parent imports from this module)
export { StepMetadataView } from './StepMetadataView';

// =============================================================================
// Sortable Steps List (top-level DnD container)
// =============================================================================

export function EditableStepsList({ steps, documentTypes = [], onStepChange, onStepDelete, onReorder }) {
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
            onReorder(arrayMove(steps, oldIndex, newIndex));
        }
    }, [steps, onReorder]);

    return (
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
            <SortableContext items={stepIds} strategy={verticalListSortingStrategy}>
                {steps.map((step, idx) => (
                    <SortableStepCard
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

// =============================================================================
// Sortable Step Card (wrapper for drag behavior)
// =============================================================================

function SortableStepCard({ step, index, documentTypes = [], onChange, onDelete }) {
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
            />
        </div>
    );
}
