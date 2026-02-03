import React, { useState, useEffect } from 'react';
import { adminApi } from '../../api/adminClient';

/**
 * Read-only preview of resolved/assembled prompt.
 * Shows provenance header with versions used.
 */
export default function ResolvedPreview({ workspaceId, artifactId }) {
    const [preview, setPreview] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (!workspaceId || !artifactId) {
            setPreview(null);
            setLoading(false);
            return;
        }

        const fetchPreview = async () => {
            setLoading(true);
            setError(null);

            try {
                const result = await adminApi.getPreview(workspaceId, artifactId);
                setPreview(result);
            } catch (err) {
                setError(err.message);
                console.error('Failed to load preview:', err);
            } finally {
                setLoading(false);
            }
        };

        fetchPreview();
    }, [workspaceId, artifactId]);

    return (
        <div className="flex flex-col h-full">
            {/* Provenance header */}
            <div
                className="px-3 py-2 text-xs border-b"
                style={{
                    borderColor: 'var(--border-panel)',
                    background: 'var(--bg-panel)',
                }}
            >
                <div className="flex items-center justify-between mb-2">
                    <span
                        className="font-medium"
                        style={{ color: 'var(--text-primary)' }}
                    >
                        Resolved Prompt (for execution)
                    </span>
                    <span
                        className="px-2 py-0.5 rounded"
                        style={{ background: 'var(--border-panel)', color: 'var(--text-muted)' }}
                    >
                        Read-only
                    </span>
                </div>
                {preview?.provenance && (
                    <div
                        className="space-y-1 font-mono"
                        style={{ color: 'var(--text-muted)' }}
                    >
                        {preview.provenance.role && (
                            <div>Role: {preview.provenance.role}</div>
                        )}
                        {preview.provenance.schema && (
                            <div>Schema: {preview.provenance.schema}</div>
                        )}
                        {preview.provenance.package && (
                            <div>Package: {preview.provenance.package}</div>
                        )}
                    </div>
                )}
            </div>

            {/* Content */}
            <div className="flex-1 relative overflow-auto">
                {loading ? (
                    <div
                        className="absolute inset-0 flex items-center justify-center"
                        style={{ background: 'var(--bg-canvas)' }}
                    >
                        <span style={{ color: 'var(--text-muted)' }}>Loading preview...</span>
                    </div>
                ) : error ? (
                    <div
                        className="absolute inset-0 flex items-center justify-center p-4"
                        style={{ background: 'var(--bg-canvas)' }}
                    >
                        <div
                            className="text-center p-4 rounded"
                            style={{
                                background: 'rgba(239, 68, 68, 0.1)',
                                border: '1px solid var(--state-error-bg)',
                            }}
                        >
                            <div
                                className="font-medium mb-2"
                                style={{ color: 'var(--state-error-text)' }}
                            >
                                Preview Failed
                            </div>
                            <div
                                className="text-sm"
                                style={{ color: 'var(--text-muted)' }}
                            >
                                {error}
                            </div>
                        </div>
                    </div>
                ) : (
                    <pre
                        className="p-4 font-mono text-sm whitespace-pre-wrap"
                        style={{
                            background: 'var(--bg-canvas)',
                            color: 'var(--text-primary)',
                            margin: 0,
                        }}
                    >
                        {preview?.resolved_prompt || 'No preview available'}
                    </pre>
                )}
            </div>
        </div>
    );
}
