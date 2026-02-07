import React, { useState, useEffect } from 'react';
import { adminApi } from '../../api/adminClient';

const fieldStyle = {
    width: '100%',
    padding: '6px 8px',
    borderRadius: 4,
    fontSize: 12,
    background: 'var(--bg-input, var(--bg-canvas))',
    border: '1px solid var(--border-panel)',
    color: 'var(--text-primary)',
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

/**
 * Editor panel for viewing mechanical operation details.
 * Per ADR-047, mechanical operations are deterministic data transformations.
 * Currently read-only - shows operation metadata, type info, and config.
 */
export default function MechanicalOpEditor({ mechanicalOp, mechanicalOpTypes = [] }) {
    const [opDetails, setOpDetails] = useState(null);
    const [typeDetails, setTypeDetails] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    // Load full operation details
    useEffect(() => {
        if (!mechanicalOp?.op_id) {
            setOpDetails(null);
            setTypeDetails(null);
            return;
        }

        const loadDetails = async () => {
            setLoading(true);
            setError(null);
            try {
                const details = await adminApi.getMechanicalOp(mechanicalOp.op_id);
                setOpDetails(details);

                // Find type details from loaded types or fetch
                const opType = mechanicalOpTypes.find(t => t.type_id === details.type);
                if (opType) {
                    setTypeDetails(opType);
                } else {
                    try {
                        const typeData = await adminApi.getMechanicalOpType(details.type);
                        setTypeDetails(typeData);
                    } catch {
                        // Type details optional
                    }
                }
            } catch (err) {
                console.error('Failed to load mechanical op details:', err);
                setError(err.message);
                // Use passed-in data as fallback
                setOpDetails(mechanicalOp);
            } finally {
                setLoading(false);
            }
        };

        loadDetails();
    }, [mechanicalOp?.op_id, mechanicalOpTypes]);

    if (!mechanicalOp) {
        return (
            <div
                className="flex-1 flex items-center justify-center"
                style={{ background: 'var(--bg-canvas)' }}
            >
                <div className="text-center" style={{ color: 'var(--text-muted)' }}>
                    <div className="text-lg mb-1">Mechanical Operation Editor</div>
                    <div className="text-sm">Select an operation from the Building Blocks tray</div>
                </div>
            </div>
        );
    }

    const op = opDetails || mechanicalOp;

    return (
        <div className="flex-1 flex flex-col overflow-hidden" style={{ background: 'var(--bg-canvas)' }}>
            {/* Header */}
            <div
                className="px-4 py-3 border-b"
                style={{ borderColor: 'var(--border-panel)', background: 'var(--bg-panel)' }}
            >
                <div className="flex items-center gap-3">
                    <span
                        className="px-2 py-1 rounded font-semibold uppercase"
                        style={{
                            fontSize: 10,
                            background: 'var(--dot-purple, #a855f7)',
                            color: '#fff',
                        }}
                    >
                        {typeDetails?.name || op.type}
                    </span>
                    <div>
                        <div className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                            {op.name}
                        </div>
                        <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
                            v{op.active_version || op.version}
                        </div>
                    </div>
                </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-4">
                {loading && (
                    <div style={{ color: 'var(--text-muted)' }}>Loading...</div>
                )}

                {error && (
                    <div
                        className="mb-4 p-3 rounded text-sm"
                        style={{ background: 'rgba(239, 68, 68, 0.1)', color: '#ef4444' }}
                    >
                        {error}
                    </div>
                )}

                {!loading && (
                    <div className="space-y-6 max-w-2xl">
                        {/* Basic Info */}
                        <section>
                            <h3
                                className="text-xs font-semibold uppercase tracking-wide mb-3"
                                style={{ color: 'var(--text-muted)' }}
                            >
                                Operation Details
                            </h3>

                            <div className="space-y-3">
                                <div>
                                    <label style={labelStyle}>Operation ID</label>
                                    <div style={fieldStyle} className="font-mono">
                                        {op.op_id}
                                    </div>
                                </div>

                                <div>
                                    <label style={labelStyle}>Name</label>
                                    <div style={fieldStyle}>{op.name}</div>
                                </div>

                                {op.description && (
                                    <div>
                                        <label style={labelStyle}>Description</label>
                                        <div style={{ ...fieldStyle, whiteSpace: 'pre-wrap' }}>
                                            {op.description}
                                        </div>
                                    </div>
                                )}

                                <div className="grid grid-cols-2 gap-3">
                                    <div>
                                        <label style={labelStyle}>Type</label>
                                        <div style={fieldStyle}>{op.type}</div>
                                    </div>
                                    <div>
                                        <label style={labelStyle}>Version</label>
                                        <div style={fieldStyle}>{op.active_version || op.version}</div>
                                    </div>
                                </div>
                            </div>
                        </section>

                        {/* Type Info */}
                        {typeDetails && (
                            <section>
                                <h3
                                    className="text-xs font-semibold uppercase tracking-wide mb-3"
                                    style={{ color: 'var(--text-muted)' }}
                                >
                                    Operation Type
                                </h3>

                                <div
                                    className="p-3 rounded"
                                    style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-panel)' }}
                                >
                                    <div className="flex items-center gap-2 mb-2">
                                        <span style={{ fontSize: 16 }}>
                                            {typeDetails.icon === 'git-merge' && '⑂'}
                                            {typeDetails.icon === 'scissors' && '✂'}
                                            {typeDetails.icon === 'check-circle' && '✓'}
                                            {typeDetails.icon === 'shuffle' && '⇄'}
                                            {typeDetails.icon === 'git-branch' && '⎇'}
                                        </span>
                                        <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>
                                            {typeDetails.name}
                                        </span>
                                        <span
                                            className="text-xs px-1.5 py-0.5 rounded"
                                            style={{ background: 'var(--bg-canvas)', color: 'var(--text-muted)' }}
                                        >
                                            {typeDetails.category}
                                        </span>
                                    </div>
                                    <div className="text-sm" style={{ color: 'var(--text-muted)' }}>
                                        {typeDetails.description}
                                    </div>

                                    {/* Inputs/Outputs */}
                                    <div className="mt-3 grid grid-cols-2 gap-3">
                                        {typeDetails.inputs?.length > 0 && (
                                            <div>
                                                <div className="text-xs font-semibold mb-1" style={{ color: 'var(--text-muted)' }}>
                                                    Inputs
                                                </div>
                                                {typeDetails.inputs.map((input, i) => (
                                                    <div key={i} className="text-xs font-mono" style={{ color: 'var(--text-secondary)' }}>
                                                        {input.name}: {input.type}
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                        {typeDetails.outputs?.length > 0 && (
                                            <div>
                                                <div className="text-xs font-semibold mb-1" style={{ color: 'var(--text-muted)' }}>
                                                    Outputs
                                                </div>
                                                {typeDetails.outputs.map((output, i) => (
                                                    <div key={i} className="text-xs font-mono" style={{ color: 'var(--text-secondary)' }}>
                                                        {output.name}: {output.type}
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </section>
                        )}

                        {/* Configuration */}
                        {op.config && (
                            <section>
                                <h3
                                    className="text-xs font-semibold uppercase tracking-wide mb-3"
                                    style={{ color: 'var(--text-muted)' }}
                                >
                                    Configuration
                                </h3>

                                <pre
                                    className="p-3 rounded text-xs font-mono overflow-x-auto"
                                    style={{
                                        background: 'var(--bg-panel)',
                                        border: '1px solid var(--border-panel)',
                                        color: 'var(--text-secondary)',
                                    }}
                                >
                                    {JSON.stringify(op.config, null, 2)}
                                </pre>
                            </section>
                        )}

                        {/* Metadata */}
                        {op.metadata && (
                            <section>
                                <h3
                                    className="text-xs font-semibold uppercase tracking-wide mb-3"
                                    style={{ color: 'var(--text-muted)' }}
                                >
                                    Metadata
                                </h3>

                                <div className="space-y-2">
                                    {op.metadata.created_date && (
                                        <div className="flex justify-between text-xs">
                                            <span style={{ color: 'var(--text-muted)' }}>Created</span>
                                            <span style={{ color: 'var(--text-secondary)' }}>{op.metadata.created_date}</span>
                                        </div>
                                    )}
                                    {op.metadata.author && (
                                        <div className="flex justify-between text-xs">
                                            <span style={{ color: 'var(--text-muted)' }}>Author</span>
                                            <span style={{ color: 'var(--text-secondary)' }}>{op.metadata.author}</span>
                                        </div>
                                    )}
                                    {op.metadata.tags?.length > 0 && (
                                        <div>
                                            <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Tags</span>
                                            <div className="flex gap-1 mt-1">
                                                {op.metadata.tags.map(tag => (
                                                    <span
                                                        key={tag}
                                                        className="text-xs px-1.5 py-0.5 rounded"
                                                        style={{ background: 'var(--bg-canvas)', color: 'var(--text-muted)' }}
                                                    >
                                                        {tag}
                                                    </span>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </section>
                        )}

                        {/* Read-only notice */}
                        <div
                            className="p-3 rounded text-xs"
                            style={{ background: 'var(--bg-panel)', color: 'var(--text-muted)' }}
                        >
                            <strong>Note:</strong> Mechanical operations are currently read-only in the workbench.
                            Edit the YAML files in <code>combine-config/mechanical_ops/</code> to modify.
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
