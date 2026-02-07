import React, { useMemo } from 'react';
import WorkflowEditorContent from './WorkflowEditorContent';

/**
 * Standalone workflow editor wrapper for the Admin Workbench.
 * Builds artifact ID from workflow selection and delegates to WorkflowEditorContent.
 */
export default function WorkflowEditor({
    workspaceId,
    workflow,
    onArtifactSave,
    // ADR-047: Mechanical operations
    mechanicalOpTypes = [],
    mechanicalOps = [],
}) {
    const artifactId = useMemo(() => {
        if (!workflow) return null;
        return `workflow:${workflow.workflow_id}:${workflow.active_version}:definition`;
    }, [workflow]);

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
        <WorkflowEditorContent
            workspaceId={workspaceId}
            artifactId={artifactId}
            onArtifactSave={onArtifactSave}
            mechanicalOpTypes={mechanicalOpTypes}
            mechanicalOps={mechanicalOps}
        />
    );
}
