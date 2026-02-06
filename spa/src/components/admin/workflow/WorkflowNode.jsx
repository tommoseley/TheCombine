import React, { memo } from 'react';
import { Handle, Position } from 'reactflow';

/**
 * Custom React Flow node for workflow graph editor.
 * Displays node type, ID, description, and metadata badges.
 */
function WorkflowNode({ data, selected }) {
    const { config, isEntry } = data;
    const isEnd = data.type === 'end';

    return (
        <div
            style={{
                background: config.bgColor,
                border: `2px solid ${selected ? config.color : config.borderColor}`,
                borderRadius: 8,
                padding: '8px 12px',
                minWidth: 180,
                maxWidth: 220,
                boxShadow: selected
                    ? `0 0 0 3px ${config.color}60, 0 0 20px ${config.color}80, 0 0 40px ${config.color}40`
                    : 'none',
                transition: 'box-shadow 0.2s, border-color 0.2s',
            }}
        >
            {/* Target handle (top) */}
            <Handle
                type="target"
                position={Position.Top}
                style={{
                    background: config.color,
                    width: 8,
                    height: 8,
                    border: 'none',
                }}
            />

            {/* Header: type badge + entry marker */}
            <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                marginBottom: 4,
            }}>
                <span style={{
                    fontSize: 10,
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    color: config.color,
                    letterSpacing: '0.05em',
                }}>
                    {config.label}
                </span>
                {isEntry && (
                    <span style={{
                        fontSize: 8,
                        padding: '1px 5px',
                        borderRadius: 3,
                        background: config.color,
                        color: '#fff',
                        fontWeight: 700,
                        letterSpacing: '0.05em',
                    }}>
                        ENTRY
                    </span>
                )}
            </div>

            {/* Node ID */}
            <div style={{
                fontSize: 12,
                fontWeight: 600,
                color: 'var(--text-primary)',
                marginBottom: 2,
            }}>
                {data.node_id}
            </div>

            {/* Description */}
            {data.description && (
                <div style={{
                    fontSize: 10,
                    color: 'var(--text-muted)',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    display: '-webkit-box',
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: 'vertical',
                    lineHeight: '14px',
                    maxHeight: '28px',
                }}>
                    {data.description}
                </div>
            )}

            {/* Metadata badges */}
            <div style={{
                display: 'flex',
                gap: 4,
                marginTop: 4,
                flexWrap: 'wrap',
            }}>
                {data.produces && (
                    <span style={{
                        fontSize: 8,
                        padding: '1px 4px',
                        borderRadius: 3,
                        background: 'rgba(59,130,246,0.2)',
                        color: '#3b82f6',
                    }}>
                        {data.produces}
                    </span>
                )}
                {data.terminal_outcome && (
                    <span style={{
                        fontSize: 8,
                        padding: '1px 4px',
                        borderRadius: 3,
                        background: data.terminal_outcome === 'stabilized'
                            ? 'rgba(16,185,129,0.2)' : 'rgba(239,68,68,0.2)',
                        color: data.terminal_outcome === 'stabilized'
                            ? '#10b981' : '#ef4444',
                    }}>
                        {data.terminal_outcome}
                    </span>
                )}
                {data.requires_qa && (
                    <span style={{
                        fontSize: 8,
                        padding: '1px 4px',
                        borderRadius: 3,
                        background: 'rgba(139,92,246,0.2)',
                        color: '#8b5cf6',
                    }}>
                        QA
                    </span>
                )}
                {data.qa_mode && (
                    <span style={{
                        fontSize: 8,
                        padding: '1px 4px',
                        borderRadius: 3,
                        background: 'rgba(139,92,246,0.1)',
                        color: '#8b5cf6',
                    }}>
                        {data.qa_mode}
                    </span>
                )}
            </div>

            {/* Source handle (bottom) - not for end nodes */}
            {!isEnd && (
                <Handle
                    type="source"
                    position={Position.Bottom}
                    style={{
                        background: config.color,
                        width: 8,
                        height: 8,
                        border: 'none',
                    }}
                />
            )}
        </div>
    );
}

export default memo(WorkflowNode);
