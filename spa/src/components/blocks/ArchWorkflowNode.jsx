import React, { memo } from 'react';
import { Handle, Position } from 'reactflow';

/**
 * Custom React Flow node for architecture workflow diagrams.
 * Shows component/output for traceability.
 */
function ArchWorkflowNode({ data }) {
    const { config, showLineage } = data;
    const isEnd = data.type === 'end';
    const isStart = data.type === 'start';

    // Extract lineage refs from node data
    const hasLineage = showLineage && (data.dcw_ref || data.task_ref || data.operation_ref || data.gate_profile);

    // Component and output fields (singular, as in the actual data)
    const component = data.component;
    const output = data.output;
    const hasIO = component || output;

    return (
        <div
            style={{
                background: config.bgColor,
                border: `2px solid ${config.borderColor}`,
                borderRadius: 8,
                padding: '10px 14px',
                minWidth: 260,
                maxWidth: 360,
                boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
            }}
        >
            {/* Target handle (top) - not for start nodes */}
            {!isStart && (
                <Handle
                    type="target"
                    position={Position.Top}
                    style={{
                        background: config.borderColor,
                        width: 8,
                        height: 8,
                        border: '2px solid white',
                    }}
                />
            )}

            {/* Type badge */}
            <div style={{
                fontSize: 10,
                fontWeight: 700,
                textTransform: 'uppercase',
                color: config.color,
                letterSpacing: '0.05em',
                marginBottom: 4,
            }}>
                {config.label}
            </div>

            {/* Label */}
            <div style={{
                fontSize: 13,
                fontWeight: 600,
                color: '#1e293b',
                lineHeight: '18px',
                marginBottom: 6,
            }}>
                {data.label}
            </div>

            {/* Actor */}
            {data.actor && (
                <div style={{
                    fontSize: 11,
                    color: '#4f46e5',
                    fontWeight: 500,
                    marginBottom: 4,
                }}>
                    {data.actor}
                </div>
            )}

            {/* Component and Output */}
            {hasIO && (
                <div style={{
                    marginTop: 6,
                    paddingTop: 6,
                    borderTop: '1px solid #e2e8f0',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 4,
                }}>
                    {component && (
                        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                            <span style={{ 
                                fontSize: 9, 
                                fontWeight: 600, 
                                color: 'var(--text-muted)',
                                textTransform: 'uppercase',
                                letterSpacing: '0.03em',
                                flexShrink: 0,
                                marginTop: 2,
                                width: 60,
                            }}>
                                Component
                            </span>
                            <span style={{ 
                                fontSize: 11, 
                                color: '#0d9488',
                                fontWeight: 500,
                                lineHeight: 1.4,
                            }}>
                                {component}
                            </span>
                        </div>
                    )}
                    {output && (
                        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                            <span style={{ 
                                fontSize: 9, 
                                fontWeight: 600, 
                                color: 'var(--text-muted)',
                                textTransform: 'uppercase',
                                letterSpacing: '0.03em',
                                flexShrink: 0,
                                marginTop: 2,
                                width: 60,
                            }}>
                                Output
                            </span>
                            <span style={{ 
                                fontSize: 11, 
                                color: '#7c3aed',
                                fontWeight: 500,
                                lineHeight: 1.4,
                            }}>
                                {output}
                            </span>
                        </div>
                    )}
                </div>
            )}

            {/* Lineage section */}
            {hasLineage && (
                <div
                    style={{
                        marginTop: 8,
                        paddingTop: 8,
                        borderTop: '1px dashed #cbd5e1',
                    }}
                >
                    {data.dcw_ref && (
                        <LineageRef label="DCW" value={data.dcw_ref} />
                    )}
                    {data.task_ref && (
                        <LineageRef label="Task" value={data.task_ref} />
                    )}
                    {data.operation_ref && (
                        <LineageRef label="Op" value={data.operation_ref} />
                    )}
                    {data.gate_profile && (
                        <div style={{ fontSize: 9, color: '#64748b', marginTop: 3 }}>
                            <span style={{ fontWeight: 600 }}>Gate:</span>{' '}
                            {Array.isArray(data.gate_profile)
                                ? data.gate_profile.join(' -> ')
                                : data.gate_profile}
                        </div>
                    )}
                </div>
            )}

            {/* Source handle (bottom) - not for end nodes */}
            {!isEnd && (
                <Handle
                    type="source"
                    position={Position.Bottom}
                    style={{
                        background: config.borderColor,
                        width: 8,
                        height: 8,
                        border: '2px solid white',
                    }}
                />
            )}
        </div>
    );
}

function LineageRef({ label, value }) {
    const display = value.length > 30 ? '...' + value.slice(-27) : value;
    return (
        <div
            style={{
                fontSize: 9,
                color: '#64748b',
                marginTop: 3,
                fontFamily: 'monospace',
            }}
            title={value}
        >
            <span style={{ fontWeight: 600, fontFamily: 'inherit' }}>{label}:</span> {display}
        </div>
    );
}

export default memo(ArchWorkflowNode);