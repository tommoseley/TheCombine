import { useState, useMemo } from 'react';
import ReactFlow, { ReactFlowProvider } from 'reactflow';
import { applyDagreLayout } from '../../utils/workflowTransform';
import {
    ARCH_WORKFLOW_NODE_CONFIG,
    ARCH_WORKFLOW_EDGE_CONFIG,
} from '../../utils/archWorkflowConfig';
import ArchWorkflowNode from '../blocks/ArchWorkflowNode';
import WorkflowAuditDrawer from './WorkflowAuditDrawer';

const nodeTypes = { archWorkflowNode: ArchWorkflowNode };

const STUDIO_NODE_WIDTH = 300;
const STUDIO_NODE_HEIGHT = 140;

function convertV1ToGraph(steps) {
    if (!Array.isArray(steps) || steps.length === 0) return { nodes: [], edges: [] };
    const sorted = [...steps].sort((a, b) => (a.step || a.order || 0) - (b.step || b.order || 0));
    const nodes = sorted.map((step, i) => ({
        ...step,  // Spread all step properties
        node_id: `step_${i + 1}`,
        type: step.type || 'action',
        label: step.action || step.label || `Step ${i + 1}`,
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

function buildReactFlowData(nodes, edges, showLineage = false) {
    const rfNodes = nodes.map(node => {
        const config = ARCH_WORKFLOW_NODE_CONFIG[node.type] || ARCH_WORKFLOW_NODE_CONFIG.action;
        return {
            id: node.node_id,
            type: 'archWorkflowNode',
            position: { x: 0, y: 0 },
            data: { ...node, config, showLineage },
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
            labelStyle: { fontSize: 10, fill: 'var(--text-muted, #64748b)' },
            labelBgStyle: { fill: 'var(--bg-panel, #ffffff)', fillOpacity: 0.9 },
            markerEnd: { type: 'arrowclosed', color: edgeConfig.stroke },
        };
    });
    const layoutedNodes = applyDagreLayout(rfNodes, rfEdges, 'TB', STUDIO_NODE_WIDTH, STUDIO_NODE_HEIGHT);
    return { nodes: layoutedNodes, edges: rfEdges };
}

export default function WorkflowStudioPanel({ workflows }) {
    const [selectedId, setSelectedId] = useState(workflows[0]?.id || null);
    const [showLineage, setShowLineage] = useState(false);
    const [auditOpen, setAuditOpen] = useState(false);

    const selectedWorkflow = workflows.find(w => w.id === selectedId);

    const rfData = useMemo(() => {
        if (!selectedWorkflow?.block?.data) return null;
        const data = selectedWorkflow.block.data;
        const hasNodes = Array.isArray(data.nodes) && data.nodes.length > 0;
        const hasSteps = Array.isArray(data.steps) && data.steps.length > 0;
        let graphNodes, graphEdges;
        if (hasNodes) {
            graphNodes = data.nodes;
            graphEdges = data.edges || [];
        } else if (hasSteps) {
            const converted = convertV1ToGraph(data.steps);
            graphNodes = converted.nodes;
            graphEdges = converted.edges;
        } else {
            return null;
        }
        return buildReactFlowData(graphNodes, graphEdges, showLineage);
    }, [selectedWorkflow, showLineage]);

    const handleKeyDown = (e) => {
        const currentIdx = workflows.findIndex(w => w.id === selectedId);
        if (e.key === 'ArrowDown' && currentIdx < workflows.length - 1) {
            e.preventDefault();
            setSelectedId(workflows[currentIdx + 1].id);
        } else if (e.key === 'ArrowUp' && currentIdx > 0) {
            e.preventDefault();
            setSelectedId(workflows[currentIdx - 1].id);
        }
    };

    return (
        <div className="flex h-full" onKeyDown={handleKeyDown} tabIndex={0}>
            {/* Left Rail */}
            <div 
                className="flex-shrink-0 border-r overflow-y-auto"
                style={{ width: 220, background: '#f8fafc', borderColor: '#e2e8f0' }}
                onWheel={(e) => e.stopPropagation()}
            >
                <div className="p-3">
                    <div className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: '#64748b' }}>
                        Workflows ({workflows.length})
                    </div>
                    {workflows.map((wf) => {
                        const isSelected = wf.id === selectedId;
                        return (
                            <button
                                key={wf.id}
                                onClick={() => setSelectedId(wf.id)}
                                className="w-full text-left p-2.5 rounded-md mb-1 transition-colors"
                                style={{
                                    background: isSelected ? '#eef2ff' : 'transparent',
                                    borderLeft: isSelected ? '3px solid #4f46e5' : '3px solid transparent',
                                }}
                            >
                                <div className="text-sm font-medium truncate" style={{ color: isSelected ? '#4f46e5' : '#1e293b' }}>
                                    {wf.name}
                                </div>
                                <div className="text-xs mt-0.5" style={{ color: '#64748b' }}>
                                    {wf.nodeCount} steps
                                </div>
                            </button>
                        );
                    })}
                </div>
            </div>

            {/* Main Workspace */}
            <div className="flex-1 flex flex-col min-w-0">
                {selectedWorkflow ? (
                    <>
                        <div className="flex-shrink-0 px-4 py-3 border-b" style={{ borderColor: '#e2e8f0' }}>
                            <div className="flex items-start justify-between">
                                <div>
                                    <h3 className="text-lg font-semibold" style={{ color: '#1e293b' }}>{selectedWorkflow.name}</h3>
                                    {selectedWorkflow.description && (
                                        <p className="text-sm mt-0.5" style={{ color: '#64748b' }}>{selectedWorkflow.description}</p>
                                    )}
                                    {selectedWorkflow.trigger && (
                                        <p className="text-sm mt-1 italic" style={{ color: '#9ca3af' }}>Trigger: {selectedWorkflow.trigger}</p>
                                    )}
                                </div>
                                <div className="flex items-center gap-2">
                                    <button
                                        onClick={() => setShowLineage(prev => !prev)}
                                        className="px-3 py-1.5 text-xs font-medium rounded transition-colors"
                                        style={{
                                            background: showLineage ? '#eef2ff' : '#f1f5f9',
                                            color: showLineage ? '#4f46e5' : '#64748b',
                                            border: `1px solid ${showLineage ? '#c7d2fe' : '#e2e8f0'}`,
                                        }}
                                    >
                                        {showLineage ? 'Hide Lineage' : 'Show Lineage'}
                                    </button>
                                    <button
                                        onClick={() => setAuditOpen(true)}
                                        className="px-3 py-1.5 text-xs font-medium rounded transition-colors"
                                        style={{ background: '#f1f5f9', color: '#64748b', border: '1px solid #e2e8f0' }}
                                    >
                                        Audit
                                    </button>
                                </div>
                            </div>
                        </div>
                        <div className="flex-1 min-h-0" style={{ background: '#ffffff' }}>
                            {rfData && rfData.nodes.length > 0 ? (
                                <ReactFlowProvider>
                                    <ReactFlow
                                        nodes={rfData.nodes}
                                        edges={rfData.edges}
                                        nodeTypes={nodeTypes}
                                        nodesDraggable={false}
                                        nodesConnectable={false}
                                        elementsSelectable={false}
                                        panOnScroll={true}
                                        zoomOnScroll={true}
                                        fitView
                                        fitViewOptions={{ padding: 0.15 }}
                                        proOptions={{ hideAttribution: true }}
                                        minZoom={0.2}
                                        maxZoom={2}
                                    />
                                </ReactFlowProvider>
                            ) : (
                                <div className="flex items-center justify-center h-full" style={{ color: '#9ca3af' }}>
                                    No workflow steps defined
                                </div>
                            )}
                        </div>
                    </>
                ) : (
                    <div className="flex items-center justify-center h-full" style={{ color: '#9ca3af' }}>
                        Select a workflow from the list
                    </div>
                )}
            </div>
            {auditOpen && selectedWorkflow && (
                <WorkflowAuditDrawer workflow={selectedWorkflow} onClose={() => setAuditOpen(false)} />
            )}
        </div>
    );
}