import React, { useState, useCallback, useMemo } from 'react';
import { arrayMove } from '@dnd-kit/sortable';
import { useWorkflowEditor } from '../../../hooks/useWorkflowEditor';
import EditorToolbar from './workflowEditorSections/EditorToolbar';
import StepPalette from './workflowEditorSections/StepPalette';
import { EditableStepsList, StepMetadataView } from './workflowEditorSections/WorkflowCanvasShell';

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
export default function StepWorkflowEditor({ workspaceId, workflow, documentTypes = [], onArtifactSave, onDelete, onNavigateToWorkflow }) {
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
            <EditorToolbar
                workflow={workflow}
                workflowJson={workflowJson}
                activeTab={activeTab}
                onTabChange={handleTabChange}
                saving={saving}
                error={error}
                onDelete={onDelete}
                onDeleteWorkflow={handleDeleteWorkflow}
            />

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
                                documentTypes={documentTypes}
                                onStepChange={handleStepChange}
                                onStepDelete={handleStepDelete}
                                onReorder={handleStepsReorder}
                            />
                            <StepPalette onAddStep={handleAddStep} />
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
