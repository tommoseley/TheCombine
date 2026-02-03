import React, { useState, useCallback } from 'react';
import { useAuth } from '../../hooks';
import { useWorkspace } from '../../hooks/useWorkspace';
import { useWorkspaceState } from '../../hooks/useWorkspaceState';
import { useAdminDocumentTypes } from '../../hooks/useAdminDocumentTypes';
import DocTypeBrowser from './DocTypeBrowser';
import PromptEditor from './PromptEditor';
import GitStatusPanel from './GitStatusPanel';

/**
 * Admin Workbench - main layout for document type prompt editing.
 *
 * Three-panel layout:
 * - Left (240px): Document type browser
 * - Center (flex-1): Prompt editor with tabs
 * - Right (320px): Git status and commit actions
 *
 * Requires admin role.
 */
export default function AdminWorkbench() {
    const { isAdmin, loading: authLoading } = useAuth();
    const [selectedDocType, setSelectedDocType] = useState(null);

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
    }, []);

    // Handle workspace close
    const handleClose = useCallback(() => {
        // Reinitialize (will create new workspace)
        reinitialize();
        setSelectedDocType(null);
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

    return (
        <div
            className="flex h-screen overflow-hidden"
            style={{ background: 'var(--bg-canvas)' }}
        >
            {/* Left panel - Document Type Browser */}
            <DocTypeBrowser
                documentTypes={documentTypes}
                loading={docTypesLoading}
                selectedDocType={selectedDocType}
                onSelect={setSelectedDocType}
            />

            {/* Center panel - Prompt Editor */}
            <PromptEditor
                workspaceId={workspaceId}
                docType={selectedDocType}
                onArtifactSave={handleArtifactSave}
            />

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
