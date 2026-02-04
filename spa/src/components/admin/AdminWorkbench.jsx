import React, { useState, useCallback } from 'react';
import { useAuth } from '../../hooks';
import { useWorkspace } from '../../hooks/useWorkspace';
import { useWorkspaceState } from '../../hooks/useWorkspaceState';
import { useAdminDocumentTypes } from '../../hooks/useAdminDocumentTypes';
import { useAdminRoles } from '../../hooks/useAdminRoles';
import { useAdminTemplates } from '../../hooks/useAdminTemplates';
import { useAdminWorkflows } from '../../hooks/useAdminWorkflows';
import { adminApi } from '../../api/adminClient';
import DocTypeBrowser from './DocTypeBrowser';
import PromptEditor from './PromptEditor';
import RoleEditor from './RoleEditor';
import TemplateEditor from './TemplateEditor';
import StepWorkflowEditor from './workflow/StepWorkflowEditor';
import GitStatusPanel from './GitStatusPanel';

/**
 * Admin Workbench - main layout for document type prompt editing.
 *
 * Three-panel layout:
 * - Left (240px): Document type and role browser
 * - Center (flex-1): Prompt editor with tabs
 * - Right (320px): Git status and commit actions
 *
 * Requires admin role.
 */
export default function AdminWorkbench() {
    const { isAdmin, loading: authLoading } = useAuth();
    const [selectedDocType, setSelectedDocType] = useState(null);
    const [selectedDocTypeDetails, setSelectedDocTypeDetails] = useState(null);
    const [detailsLoading, setDetailsLoading] = useState(false);
    const [selectedRole, setSelectedRole] = useState(null);
    const [selectedTemplate, setSelectedTemplate] = useState(null);
    const [selectedWorkflow, setSelectedWorkflow] = useState(null);
    const [initialTab, setInitialTab] = useState(null);

    // Workspace lifecycle
    const {
        workspaceId,
        loading: workspaceLoading,
        error: workspaceError,
        reinitialize,
    } = useWorkspace();

    // Workspace state (git status, validation)
    const {
        state: workspaceState,
        loading: stateLoading,
        refresh: refreshState,
    } = useWorkspaceState(workspaceId);

    // Document types list
    const {
        documentTypes,
        loading: docTypesLoading,
    } = useAdminDocumentTypes();

    // Roles list
    const {
        roles,
        loading: rolesLoading,
    } = useAdminRoles();

    // Templates list
    const {
        templates,
        loading: templatesLoading,
    } = useAdminTemplates();

    // Workflows list
    const {
        workflows,
        loading: workflowsLoading,
        refresh: refreshWorkflows,
    } = useAdminWorkflows();

    // Handle doc type selection - fetch full details
    const handleSelectDocType = useCallback(async (docType, tab = null) => {
        setSelectedDocType(docType);
        setSelectedRole(null);
        setSelectedTemplate(null);
        setSelectedWorkflow(null);
        setSelectedDocTypeDetails(null);
        setInitialTab(tab);

        if (!docType) return;

        setDetailsLoading(true);
        try {
            const details = await adminApi.getDocumentType(docType.doc_type_id);
            setSelectedDocTypeDetails(details);
        } catch (err) {
            console.error('Failed to load doc type details:', err);
            // Still show the doc type but with limited info
            setSelectedDocTypeDetails(docType);
        } finally {
            setDetailsLoading(false);
        }
    }, []);

    // Handle task selection - navigate to doc type's Task tab
    const handleSelectTask = useCallback((docType) => {
        handleSelectDocType(docType, 'task_prompt');
    }, [handleSelectDocType]);

    // Handle schema selection - navigate to doc type's Schema tab
    const handleSelectSchema = useCallback((docType) => {
        handleSelectDocType(docType, 'schema');
    }, [handleSelectDocType]);

    // Handle role selection
    const handleSelectRole = useCallback((role) => {
        setSelectedRole(role);
        setSelectedDocType(null);
        setSelectedDocTypeDetails(null);
        setSelectedTemplate(null);
        setSelectedWorkflow(null);
    }, []);

    // Handle template selection
    const handleSelectTemplate = useCallback((template) => {
        setSelectedTemplate(template);
        setSelectedDocType(null);
        setSelectedDocTypeDetails(null);
        setSelectedRole(null);
        setSelectedWorkflow(null);
    }, []);

    // Handle workflow selection
    const handleSelectWorkflow = useCallback((workflow) => {
        setSelectedWorkflow(workflow);
        setSelectedDocType(null);
        setSelectedDocTypeDetails(null);
        setSelectedRole(null);
        setSelectedTemplate(null);
    }, []);

    // Handle artifact save (refresh workspace state)
    const handleArtifactSave = useCallback((artifactId, result) => {
        // Refresh state to update dirty status and validation
        refreshState();
    }, [refreshState]);

    // Handle successful commit
    const handleCommit = useCallback((result) => {
        // State will refresh automatically
        console.log('Committed:', result.commit_hash);
    }, []);

    // Handle discard
    const handleDiscard = useCallback(() => {
        // Clear selection and refresh
        setSelectedDocType(null);
        setSelectedDocTypeDetails(null);
        setSelectedRole(null);
        setSelectedTemplate(null);
        setSelectedWorkflow(null);
    }, []);

    // Handle create workflow
    const handleCreateWorkflow = useCallback(async (data) => {
        if (!workspaceId) return;
        try {
            const result = await adminApi.createOrchestrationWorkflow(workspaceId, data);
            await refreshWorkflows();
            refreshState();
            // Auto-select the new workflow
            setSelectedWorkflow({
                workflow_id: result.workflow_id,
                active_version: result.version,
                name: data.name || result.workflow_id.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
            });
            setSelectedDocType(null);
            setSelectedDocTypeDetails(null);
            setSelectedRole(null);
            setSelectedTemplate(null);
        } catch (err) {
            console.error('Failed to create workflow:', err);
            alert(`Failed to create workflow: ${err.message}`);
        }
    }, [workspaceId, refreshWorkflows, refreshState]);

    // Handle delete workflow
    const handleDeleteWorkflow = useCallback(async (workflowId) => {
        if (!workspaceId) return;
        try {
            await adminApi.deleteOrchestrationWorkflow(workspaceId, workflowId);
            await refreshWorkflows();
            refreshState();
            setSelectedWorkflow(null);
        } catch (err) {
            console.error('Failed to delete workflow:', err);
            alert(`Failed to delete workflow: ${err.message}`);
        }
    }, [workspaceId, refreshWorkflows, refreshState]);

    // Handle workspace close
    const handleClose = useCallback(() => {
        // Reinitialize (will create new workspace)
        reinitialize();
        setSelectedDocType(null);
        setSelectedDocTypeDetails(null);
        setSelectedRole(null);
        setSelectedTemplate(null);
        setSelectedWorkflow(null);
    }, [reinitialize]);

    // Auth check
    if (authLoading) {
        return (
            <div
                className="flex items-center justify-center h-screen"
                style={{ background: 'var(--bg-canvas)' }}
            >
                <span style={{ color: 'var(--text-muted)' }}>Loading...</span>
            </div>
        );
    }

    if (!isAdmin) {
        return (
            <div
                className="flex items-center justify-center h-screen"
                style={{ background: 'var(--bg-canvas)' }}
            >
                <div
                    className="text-center p-8 rounded-lg"
                    style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-panel)' }}
                >
                    <div
                        className="text-lg font-semibold mb-2"
                        style={{ color: 'var(--state-error-text)' }}
                    >
                        Access Denied
                    </div>
                    <div style={{ color: 'var(--text-muted)' }}>
                        Admin access required for the Workbench.
                    </div>
                </div>
            </div>
        );
    }

    // Workspace initialization
    if (workspaceLoading) {
        return (
            <div
                className="flex items-center justify-center h-screen"
                style={{ background: 'var(--bg-canvas)' }}
            >
                <div className="text-center">
                    <div
                        className="text-lg mb-2"
                        style={{ color: 'var(--text-primary)' }}
                    >
                        Initializing Workspace
                    </div>
                    <div style={{ color: 'var(--text-muted)' }}>
                        Setting up your editing environment...
                    </div>
                </div>
            </div>
        );
    }

    // Workspace error
    if (workspaceError) {
        return (
            <div
                className="flex items-center justify-center h-screen"
                style={{ background: 'var(--bg-canvas)' }}
            >
                <div
                    className="text-center p-8 rounded-lg max-w-md"
                    style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-panel)' }}
                >
                    <div
                        className="text-lg font-semibold mb-2"
                        style={{ color: 'var(--state-error-text)' }}
                    >
                        Workspace Error
                    </div>
                    <div className="mb-4" style={{ color: 'var(--text-muted)' }}>
                        {workspaceError}
                    </div>
                    <button
                        onClick={reinitialize}
                        className="px-4 py-2 rounded text-sm"
                        style={{
                            background: 'var(--action-primary)',
                            color: '#000',
                        }}
                    >
                        Retry
                    </button>
                </div>
            </div>
        );
    }

    // Determine which editor to show
    const showRoleEditor = selectedRole && !selectedDocType && !selectedTemplate && !selectedWorkflow;
    const showTemplateEditor = selectedTemplate && !selectedDocType && !selectedRole && !selectedWorkflow;
    const showWorkflowEditor = selectedWorkflow && !selectedDocType && !selectedRole && !selectedTemplate;
    const showPromptEditor = !showRoleEditor && !showTemplateEditor && !showWorkflowEditor;

    return (
        <div
            className="flex h-screen overflow-hidden"
            style={{ background: 'var(--bg-canvas)' }}
        >
            {/* Left panel - Document Type, Role & Template Browser */}
            <DocTypeBrowser
                documentTypes={documentTypes}
                roles={roles}
                templates={templates}
                workflows={workflows}
                loading={docTypesLoading}
                rolesLoading={rolesLoading}
                templatesLoading={templatesLoading}
                workflowsLoading={workflowsLoading}
                selectedDocType={selectedDocType}
                selectedRole={selectedRole}
                selectedTemplate={selectedTemplate}
                selectedWorkflow={selectedWorkflow}
                onSelectDocType={handleSelectDocType}
                onSelectRole={handleSelectRole}
                onSelectTemplate={handleSelectTemplate}
                onSelectWorkflow={handleSelectWorkflow}
                onCreateWorkflow={handleCreateWorkflow}
                onSelectTask={handleSelectTask}
                onSelectSchema={handleSelectSchema}
            />

            {/* Center panel - Editor (Prompt, Role, Template, or Workflow) */}
            {showRoleEditor ? (
                <RoleEditor
                    workspaceId={workspaceId}
                    role={selectedRole}
                    onArtifactSave={handleArtifactSave}
                />
            ) : showTemplateEditor ? (
                <TemplateEditor
                    workspaceId={workspaceId}
                    template={selectedTemplate}
                    onArtifactSave={handleArtifactSave}
                />
            ) : showWorkflowEditor ? (
                <StepWorkflowEditor
                    workspaceId={workspaceId}
                    workflow={selectedWorkflow}
                    onArtifactSave={handleArtifactSave}
                    onDelete={handleDeleteWorkflow}
                />
            ) : (
                <PromptEditor
                    workspaceId={workspaceId}
                    docType={selectedDocTypeDetails}
                    loading={detailsLoading}
                    roles={roles}
                    onArtifactSave={handleArtifactSave}
                    initialTab={initialTab}
                />
            )}

            {/* Right panel - Git Status */}
            <GitStatusPanel
                workspaceId={workspaceId}
                state={workspaceState}
                loading={stateLoading}
                onCommit={handleCommit}
                onDiscard={handleDiscard}
                onClose={handleClose}
                onRefresh={refreshState}
            />
        </div>
    );
}
