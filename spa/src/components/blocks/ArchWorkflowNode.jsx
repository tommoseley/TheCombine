import React, { memo } from 'react';
import { Handle, Position } from 'reactflow';

/**
 * Custom React Flow node for architecture workflow diagrams.
 * Read-only, compact (~160x80) for document-embedded display.
 * Follows WorkflowNode.jsx pattern but optimized for viewing, not editing.
 */
function ArchWorkflowNode({ data }) {
    const { config } = data;
    const isEnd = data.type === 'end';
    const isStart = data.type === 'start';

    return (
        <div
            style={{
                background: config.bgColor,
                border: `1.5px solid ${config.borderColor}`,
                borderRadius: 6,
                padding: '6px 10px',
                minWidth: 120,
                maxWidth: 160,
            }}
        >
            {/* Target handle (top) - not for start nodes */}
            {!isStart && (
                <Handle
                    type="target"
                    position={Position.Top}
                    style={{
                        background: config.color,
                        width: 6,
                        height: 6,
                        border: 'none',
                    }}
                />
            )}

            {/* Type badge */}
            <div style={{
                fontSize: 9,
                fontWeight: 700,
                textTransform: 'uppercase',
                color: config.color,
                letterSpacing: '0.04em',
                marginBottom: 2,
            }}>
                {config.label}
            </div>

            {/* Label */}
            <div style={{
                fontSize: 11,
                fontWeight: 600,
                color: 'var(--text-primary, #1e293b)',
                lineHeight: '14px',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                display: '-webkit-box',
                WebkitLineClamp: 2,
                WebkitBoxOrient: 'vertical',
                maxHeight: '28px',
            }}>
                {data.label}
            </div>

            {/* Actor (small, indigo) */}
            {data.actor && (
                <div style={{
                    fontSize: 9,
                    color: '#6366f1',
                    marginTop: 2,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                }}>
                    {data.actor}
                </div>
            )}

            {/* Source handle (bottom) - not for end nodes */}
            {!isEnd && (
                <Handle
                    type="source"
                    position={Position.Bottom}
                    style={{
                        background: config.color,
                        width: 6,
                        height: 6,
                        border: 'none',
                    }}
                />
            )}
        </div>
    );
}

export default memo(ArchWorkflowNode);
