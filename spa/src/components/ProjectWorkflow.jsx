/**
 * ProjectWorkflow -- Workflow instance viewer for a project.
 *
 * Per ADR-046 / WS-ADR-046-001 Phase 5.
 *
 * Shows:
 * - "No workflow assigned" state with assign button
 * - Workflow picker (reference + template POWs from admin API)
 * - Instance viewer: effective workflow steps, base ref, status, drift
 */
import { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { adminApi } from '../api/adminClient';

export default function ProjectWorkflow({ projectId }) {
    const [instance, setInstance] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // Picker state
    const [showPicker, setShowPicker] = useState(false);
    const [availableWorkflows, setAvailableWorkflows] = useState([]);
    const [pickerLoading, setPickerLoading] = useState(false);
    const [assigning, setAssigning] = useState(false);

    // Drift state
    const [drift, setDrift] = useState(null);
    const [driftLoading, setDriftLoading] = useState(false);
    const [showDrift, setShowDrift] = useState(false);

    const loadInstance = useCallback(async () => {
        if (!projectId) return;
        setLoading(true);
        setError(null);
        try {
            const data = await api.getWorkflowInstance(projectId);
            setInstance(data);
        } catch (err) {
            if (err.status === 404) {
                setInstance(null);
            } else {
                setError(err.message);
            }
        } finally {
            setLoading(false);
        }
    }, [projectId]);

    useEffect(() => { loadInstance(); }, [loadInstance]);

    const handleOpenPicker = async () => {
        setShowPicker(true);
        setPickerLoading(true);
        try {
            const data = await adminApi.getOrchestrationWorkflows();
            setAvailableWorkflows(data.workflows || []);
        } catch {
            setAvailableWorkflows([]);
        } finally {
            setPickerLoading(false);
        }
    };

    const handleAssign = async (wf) => {
        setAssigning(true);
        try {
            const data = await api.createWorkflowInstance(
                projectId,
                wf.workflow_id,
                wf.active_version,
            );
            setInstance(data);
            setShowPicker(false);
        } catch (err) {
            setError(err.message);
        } finally {
            setAssigning(false);
        }
    };

    const handleLoadDrift = async () => {
        if (!instance) return;
        setShowDrift(!showDrift);
        if (drift) return; // Already loaded
        setDriftLoading(true);
        try {
            const data = await api.getWorkflowDrift(projectId);
            setDrift(data);
        } catch (err) {
            setDrift({ error: err.message });
        } finally {
            setDriftLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="p-4 text-xs" style={{ color: 'var(--text-muted)' }}>
                Loading workflow...
            </div>
        );
    }

    if (error && !instance) {
        return (
            <div className="p-4 text-xs" style={{ color: 'var(--status-error, #ef4444)' }}>
                {error}
            </div>
        );
    }

    // No instance -- show assign prompt
    if (!instance) {
        return (
            <div className="p-4">
                <div
                    className="text-xs mb-3"
                    style={{ color: 'var(--text-muted)' }}
                >
                    No workflow assigned to this project.
                </div>
                {!showPicker ? (
                    <button
                        onClick={handleOpenPicker}
                        className="text-xs px-3 py-1.5 rounded font-semibold hover:opacity-80"
                        style={{
                            background: 'var(--action-primary)',
                            color: '#000',
                            border: 'none',
                            cursor: 'pointer',
                        }}
                    >
                        Assign Workflow
                    </button>
                ) : (
                    <WorkflowPicker
                        workflows={availableWorkflows}
                        loading={pickerLoading}
                        assigning={assigning}
                        onSelect={handleAssign}
                        onCancel={() => setShowPicker(false)}
                    />
                )}
            </div>
        );
    }

    // Instance viewer
    const workflow = instance.effective_workflow || {};
    const steps = workflow.steps || [];
    const baseRef = instance.base_workflow_ref || {};

    return (
        <div className="p-4 space-y-4">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <div className="flex items-center gap-2">
                        <span
                            className="text-sm font-semibold"
                            style={{ color: 'var(--text-primary)' }}
                        >
                            {workflow.name || baseRef.workflow_id || 'Workflow'}
                        </span>
                        <StatusBadge status={instance.status} />
                    </div>
                    <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
                        From {baseRef.workflow_id} v{baseRef.version}
                        {baseRef.pow_class ? ` (${baseRef.pow_class})` : ''}
                    </div>
                </div>
                <button
                    onClick={handleLoadDrift}
                    className="text-xs px-2 py-1 rounded hover:opacity-80"
                    style={{
                        background: 'transparent',
                        border: '1px solid var(--border-panel)',
                        color: 'var(--text-secondary)',
                        cursor: 'pointer',
                    }}
                >
                    {driftLoading ? 'Checking...' : showDrift ? 'Hide Drift' : 'Check Drift'}
                </button>
            </div>

            {/* Drift panel */}
            {showDrift && drift && (
                <DriftPanel drift={drift} />
            )}

            {/* Steps */}
            <div>
                <div
                    className="text-xs font-semibold uppercase tracking-wide mb-2"
                    style={{ color: 'var(--text-muted)' }}
                >
                    Steps ({steps.length})
                </div>
                {steps.length === 0 ? (
                    <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
                        No steps defined
                    </div>
                ) : (
                    <div className="space-y-1">
                        {steps.map((step, idx) => (
                            <StepCard key={step.step_id || idx} step={step} index={idx} />
                        ))}
                    </div>
                )}
            </div>

            {error && (
                <div className="text-xs" style={{ color: 'var(--status-error, #ef4444)' }}>
                    {error}
                </div>
            )}
        </div>
    );
}


// =============================================================================
// Sub-components
// =============================================================================

function WorkflowPicker({ workflows, loading, assigning, onSelect, onCancel }) {
    const references = workflows.filter(wf => (wf.pow_class || 'reference') === 'reference');
    const templates = workflows.filter(wf => wf.pow_class === 'template');

    return (
        <div
            className="rounded p-3 space-y-2"
            style={{
                background: 'var(--bg-panel)',
                border: '1px solid var(--border-panel)',
            }}
        >
            <div
                className="text-xs font-semibold"
                style={{ color: 'var(--text-primary)' }}
            >
                Select a workflow to assign:
            </div>

            {loading ? (
                <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
                    Loading...
                </div>
            ) : (
                <>
                    {references.length > 0 && (
                        <div>
                            <div className="text-xs mb-1" style={{ color: 'var(--text-muted)' }}>
                                Reference Workflows
                            </div>
                            {references.map(wf => (
                                <button
                                    key={wf.workflow_id}
                                    onClick={() => onSelect(wf)}
                                    disabled={assigning}
                                    className="w-full text-left text-xs px-2 py-1.5 rounded mb-0.5 hover:opacity-80"
                                    style={{
                                        background: 'transparent',
                                        border: '1px solid var(--border-panel)',
                                        color: 'var(--text-secondary)',
                                        cursor: assigning ? 'default' : 'pointer',
                                        opacity: assigning ? 0.5 : 1,
                                    }}
                                >
                                    <div className="font-medium">{wf.name || wf.workflow_id}</div>
                                    <div style={{ color: 'var(--text-muted)' }}>
                                        v{wf.active_version} · {wf.step_count} steps
                                    </div>
                                </button>
                            ))}
                        </div>
                    )}
                    {templates.length > 0 && (
                        <div>
                            <div className="text-xs mb-1" style={{ color: 'var(--text-muted)' }}>
                                Template Workflows
                            </div>
                            {templates.map(wf => (
                                <button
                                    key={wf.workflow_id}
                                    onClick={() => onSelect(wf)}
                                    disabled={assigning}
                                    className="w-full text-left text-xs px-2 py-1.5 rounded mb-0.5 hover:opacity-80"
                                    style={{
                                        background: 'transparent',
                                        border: '1px solid var(--border-panel)',
                                        color: 'var(--text-secondary)',
                                        cursor: assigning ? 'default' : 'pointer',
                                        opacity: assigning ? 0.5 : 1,
                                    }}
                                >
                                    <div className="font-medium">{wf.name || wf.workflow_id}</div>
                                    <div style={{ color: 'var(--text-muted)' }}>
                                        v{wf.active_version} · {wf.step_count} steps
                                        {wf.derived_from_label ? ` · from ${wf.derived_from_label}` : ''}
                                    </div>
                                </button>
                            ))}
                        </div>
                    )}
                    {references.length === 0 && templates.length === 0 && (
                        <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
                            No workflows available
                        </div>
                    )}
                </>
            )}

            <button
                onClick={onCancel}
                className="text-xs px-2 py-1 hover:opacity-80"
                style={{
                    background: 'transparent',
                    border: 'none',
                    color: 'var(--text-muted)',
                    cursor: 'pointer',
                }}
            >
                Cancel
            </button>
        </div>
    );
}


function StatusBadge({ status }) {
    const colors = {
        active: { bg: 'var(--action-primary)', color: '#000' },
        completed: { bg: '#22c55e', color: '#000' },
        archived: { bg: 'var(--text-muted)', color: '#000' },
    };
    const c = colors[status] || colors.active;
    return (
        <span
            className="text-xs px-1.5 py-0.5 rounded font-semibold uppercase"
            style={{
                fontSize: 9,
                letterSpacing: '0.05em',
                background: c.bg,
                color: c.color,
            }}
        >
            {status}
        </span>
    );
}


function DriftPanel({ drift }) {
    if (drift.error) {
        return (
            <div
                className="text-xs p-2 rounded"
                style={{
                    background: 'var(--bg-panel)',
                    border: '1px solid var(--border-panel)',
                    color: 'var(--status-error, #ef4444)',
                }}
            >
                Drift check failed: {drift.error}
            </div>
        );
    }

    return (
        <div
            className="text-xs p-2 rounded space-y-1"
            style={{
                background: 'var(--bg-panel)',
                border: `1px solid ${drift.is_drifted ? 'var(--status-warning, #f59e0b)' : 'var(--border-panel)'}`,
            }}
        >
            <div className="flex items-center gap-2 font-semibold">
                <span style={{ color: drift.is_drifted ? 'var(--status-warning, #f59e0b)' : '#22c55e' }}>
                    {drift.is_drifted ? 'Drifted' : 'In Sync'}
                </span>
                <span style={{ color: 'var(--text-muted)' }}>
                    vs {drift.base_workflow_id} v{drift.base_version}
                </span>
            </div>
            {drift.is_drifted && (
                <div style={{ color: 'var(--text-secondary)' }}>
                    {drift.steps_added.length > 0 && (
                        <div>+ Steps added: {drift.steps_added.join(', ')}</div>
                    )}
                    {drift.steps_removed.length > 0 && (
                        <div>- Steps removed: {drift.steps_removed.join(', ')}</div>
                    )}
                    {drift.steps_reordered && <div>~ Steps reordered</div>}
                    {drift.metadata_changed && <div>~ Metadata changed</div>}
                </div>
            )}
        </div>
    );
}


function StepCard({ step, index }) {
    return (
        <div
            className="flex items-center gap-2 px-2 py-1.5 rounded text-xs"
            style={{
                background: 'var(--bg-panel)',
                border: '1px solid var(--border-panel)',
            }}
        >
            <span
                className="font-mono font-semibold"
                style={{
                    color: 'var(--text-muted)',
                    minWidth: 20,
                    textAlign: 'right',
                }}
            >
                {index + 1}
            </span>
            <div style={{ flex: 1 }}>
                <div style={{ color: 'var(--text-primary)' }}>
                    {step.step_id || `Step ${index + 1}`}
                </div>
                {step.produces && (
                    <div style={{ color: 'var(--text-muted)' }}>
                        produces: {step.produces}
                    </div>
                )}
            </div>
            {step.scope && (
                <span
                    className="px-1 py-0.5 rounded"
                    style={{
                        background: 'var(--bg-selected, #334155)',
                        color: 'var(--text-muted)',
                        fontSize: 10,
                    }}
                >
                    {step.scope}
                </span>
            )}
        </div>
    );
}
