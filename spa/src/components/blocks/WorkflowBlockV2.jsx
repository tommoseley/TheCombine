import { useState, useMemo } from 'react';
import ReactFlow, { ReactFlowProvider } from 'reactflow';
import { applyDagreLayout } from '../../utils/workflowTransform';
import {
    ARCH_WORKFLOW_NODE_CONFIG,
    ARCH_WORKFLOW_EDGE_CONFIG,
    ARCH_NODE_WIDTH,
    ARCH_NODE_HEIGHT,
} from '../../utils/archWorkflowConfig';
import ArchWorkflowNode from './ArchWorkflowNode';

const nodeTypes = { archWorkflowNode: ArchWorkflowNode };

/**
 * Convert V1 steps[] data to a linear graph of nodes/edges.
 * Returns { nodes, edges } in V2 format.
 */
function convertV1ToGraph(steps) {
    if (!Array.isArray(steps) || steps.length === 0) return { nodes: [], edges: [] };

    const sorted = [...steps].sort((a, b) => (a.step || a.order || 0) - (b.step || b.order || 0));

    const nodes = sorted.map((step, i) => ({
        node_id: `step_${i + 1}`,
        type: 'action',
        label: step.action || `Step ${i + 1}`,
        actor: step.actor,
        description: step.description,
        inputs: step.inputs,
        outputs: step.outputs,
        notes: step.notes,
    }));

    const edges = [];
    for (let i = 0; i < nodes.length - 1; i++) {
        edges.push({
            edge_id: `e_${i + 1}_${i + 2}`,
            from_node_id: nodes[i].node_id,
            to_node_id: nodes[i + 1].node_id,
            type: 'normal',
        });
    }

    return { nodes, edges };
}

/**
 * Convert V2 schema nodes/edges to React Flow format with dagre layout.
 */
function buildReactFlowData(nodes, edges) {
    const rfNodes = nodes.map(node => {
        const config = ARCH_WORKFLOW_NODE_CONFIG[node.type] || ARCH_WORKFLOW_NODE_CONFIG.action;
        return {
            id: node.node_id,
            type: 'archWorkflowNode',
            position: { x: 0, y: 0 },
            data: { ...node, config },
        };
    });

    const rfEdges = edges.map(edge => {
        const edgeType = edge.type || 'normal';
        const edgeConfig = ARCH_WORKFLOW_EDGE_CONFIG[edgeType] || ARCH_WORKFLOW_EDGE_CONFIG.normal;

        return {
            id: edge.edge_id,
            source: edge.from_node_id,
            target: edge.to_node_id,
            type: 'smoothstep',
            animated: edgeConfig.animated || false,
            label: edge.label,
            style: {
                stroke: edgeConfig.stroke,
                strokeWidth: edgeConfig.strokeWidth,
                strokeDasharray: edgeConfig.strokeDasharray,
            },
            labelStyle: {
                fontSize: 9,
                fill: 'var(--text-muted, #64748b)',
            },
            labelBgStyle: {
                fill: 'var(--bg-panel, #ffffff)',
                fillOpacity: 0.9,
            },
            markerEnd: { type: 'arrowclosed', color: edgeConfig.stroke },
        };
    });

    const layoutedNodes = applyDagreLayout(rfNodes, rfEdges, 'TB', ARCH_NODE_WIDTH, ARCH_NODE_HEIGHT);
    return { nodes: layoutedNodes, edges: rfEdges };
}

/**
 * WorkflowBlockV2 - React Flow graph renderer for architecture workflows.
 *
 * - V1 data (steps[] only) is auto-converted to a linear graph
 * - V2 data (nodes[] + edges[]) renders full branching diagrams
 * - Each block gets its own ReactFlowProvider
 * - Read-only: no drag, no connect, fitView
 */
export default function WorkflowBlockV2({ block }) {
    const { data } = block;
    if (!data || !data.name) return null;

    const [expanded, setExpanded] = useState(false);

    const { graphNodes, graphEdges, isV1 } = useMemo(() => {
        const hasNodes = Array.isArray(data.nodes) && data.nodes.length > 0;
        const hasSteps = Array.isArray(data.steps) && data.steps.length > 0;

        if (hasNodes) {
            return {
                graphNodes: data.nodes,
                graphEdges: data.edges || [],
                isV1: false,
            };
        }

        if (hasSteps) {
            const { nodes, edges } = convertV1ToGraph(data.steps);
            return { graphNodes: nodes, graphEdges: edges, isV1: true };
        }

        return { graphNodes: [], graphEdges: [], isV1: false };
    }, [data.nodes, data.edges, data.steps]);

    const rfData = useMemo(() => {
        if (graphNodes.length === 0) return null;
        return buildReactFlowData(graphNodes, graphEdges);
    }, [graphNodes, graphEdges]);

    const containerHeight = expanded ? 600 : 350;

    return (
        <div
            style={{
                marginBottom: 12,
                padding: '14px 16px',
                background: '#f8fafc',
                borderRadius: 8,
                border: '1px solid #e2e8f0',
            }}
        >
            {/* Header */}
            <h4 style={{ margin: '0 0 4px', fontSize: 15, fontWeight: 600, color: '#1e293b' }}>
                {data.name}
            </h4>
            {data.description && (
                <p style={{ margin: '0 0 8px', fontSize: 13, color: '#475569' }}>
                    {data.description}
                </p>
            )}
            {data.trigger && (
                <p style={{ margin: '0 0 8px', fontSize: 13, color: '#6b7280', fontStyle: 'italic' }}>
                    Trigger: {data.trigger}
                </p>
            )}

            {/* React Flow canvas */}
            {rfData && rfData.nodes.length > 0 ? (
                <>
                    <div
                        style={{
                            height: containerHeight,
                            border: '1px solid #e5e7eb',
                            borderRadius: 6,
                            background: '#ffffff',
                            overflow: 'hidden',
                            transition: 'height 0.2s ease',
                        }}
                    >
                        <ReactFlowProvider>
                            <ReactFlow
                                nodes={rfData.nodes}
                                edges={rfData.edges}
                                nodeTypes={nodeTypes}
                                nodesDraggable={false}
                                nodesConnectable={false}
                                elementsSelectable={false}
                                panOnScroll={true}
                                zoomOnScroll={false}
                                fitView
                                fitViewOptions={{ padding: 0.2 }}
                                proOptions={{ hideAttribution: true }}
                                minZoom={0.3}
                                maxZoom={1.5}
                            />
                        </ReactFlowProvider>
                    </div>

                    {/* Expand/collapse toggle */}
                    <button
                        onClick={() => setExpanded(prev => !prev)}
                        style={{
                            marginTop: 6,
                            padding: '3px 10px',
                            fontSize: 11,
                            color: '#6366f1',
                            background: 'none',
                            border: '1px solid #e5e7eb',
                            borderRadius: 4,
                            cursor: 'pointer',
                        }}
                    >
                        {expanded ? 'Collapse' : 'Expand'}
                    </button>
                </>
            ) : (
                <p style={{ margin: 0, fontSize: 13, color: '#9ca3af', fontStyle: 'italic' }}>
                    No workflow steps defined.
                </p>
            )}
        </div>
    );
}
