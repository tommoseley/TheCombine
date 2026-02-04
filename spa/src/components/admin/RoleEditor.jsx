import React from 'react';
import PromptTab from './PromptTab';
import { usePromptEditor } from '../../hooks/usePromptEditor';

/**
 * Editor for role prompts.
 * Allows direct editing of shared role prompt content.
 */
export default function RoleEditor({
    workspaceId,
    role,
    onArtifactSave,
}) {
    // Build artifact ID for the role
    const artifactId = role
        ? `role:${role.role_id}:${role.active_version}:role_prompt`
        : null;

    // Prompt editor hook
    const {
        content,
        loading,
        error,
        saving,
        isDirty,
        updateContent,
        lastSaveResult,
    } = usePromptEditor(workspaceId, artifactId, {
        onSave: (result) => {
            onArtifactSave?.(artifactId, result);
        },
    });

    if (!role) {
        return (
            <div
                className="flex-1 flex items-center justify-center"
                style={{ background: 'var(--bg-canvas)' }}
            >
                <div
                    className="text-center p-8"
                    style={{ color: 'var(--text-muted)' }}
                >
                    <div className="text-lg mb-2">No Role Selected</div>
                    <div className="text-sm">
                        Select a role from the browser to edit its prompt.
                    </div>
                </div>
            </div>
        );
    }

    const displayName = role.role_id
        .replace(/_/g, ' ')
        .replace(/\b\w/g, c => c.toUpperCase());

    return (
        <div className="flex-1 flex flex-col h-full" style={{ background: 'var(--bg-canvas)' }}>
            {/* Header */}
            <div
                className="px-4 py-3 border-b"
                style={{ borderColor: 'var(--border-panel)', background: 'var(--bg-panel)' }}
            >
                <div className="flex items-center justify-between">
                    <div>
                        <h2
                            className="text-base font-semibold"
                            style={{ color: 'var(--text-primary)' }}
                        >
                            {displayName}
                        </h2>
                        <div
                            className="text-xs mt-0.5"
                            style={{ color: 'var(--text-muted)' }}
                        >
                            v{role.active_version} · Role Prompt
                        </div>
                    </div>
                </div>
            </div>

            {/* Single tab header for consistency */}
            <div
                className="flex border-b"
                style={{ borderColor: 'var(--border-panel)', background: 'var(--bg-panel)' }}
            >
                <div
                    className="px-4 py-2 text-sm"
                    style={{
                        color: 'var(--text-primary)',
                        background: 'var(--bg-canvas)',
                        borderBottom: '2px solid var(--action-primary)',
                    }}
                >
                    Role Prompt
                </div>
            </div>

            {/* File path display */}
            <div
                className="flex items-center justify-end px-3 py-2 border-b"
                style={{ borderColor: 'var(--border-panel)', background: 'var(--bg-panel-alt, var(--bg-panel))' }}
            >
                <span
                    className="text-xs font-mono truncate"
                    style={{ color: 'var(--text-muted)' }}
                >
                    combine-config/prompts/roles/{role.role_id}/releases/{role.active_version}/role.prompt.txt
                </span>
            </div>

            {/* Content area */}
            <div className="flex-1 overflow-hidden">
                <PromptTab
                    content={content}
                    onChange={updateContent}
                    loading={loading}
                    saving={saving}
                    isDirty={isDirty}
                    error={error}
                    placeholder="Enter role prompt content..."
                />
            </div>

            {/* Validation result from last save */}
            {lastSaveResult?.tier1 && !lastSaveResult.tier1.passed && (
                <div
                    className="px-4 py-2 border-t"
                    style={{
                        borderColor: 'var(--border-panel)',
                        background: 'rgba(239, 68, 68, 0.1)',
                    }}
                >
                    <div
                        className="text-xs"
                        style={{ color: 'var(--state-error-text)' }}
                    >
                        Validation issues found - see status panel for details
                    </div>
                </div>
            )}
        </div>
    );
}
