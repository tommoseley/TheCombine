import React, { useState, useCallback, useEffect, useMemo, useRef } from 'react';
import ReactFlow, {
    useNodesState,
    useEdgesState,
    addEdge,
    MiniMap,
    Panel,
    useReactFlow,
} from 'reactflow';
import 'reactflow/dist/style.css';
import WorkflowNode from './WorkflowNode';
import {
    workflowToReactFlow,
    reactFlowToWorkflow,
    applyDagreLayout,
    generateNodeId,
    generateEdgeId,
    createDefaultNode,
    NODE_TYPE_CONFIG,
} from '../../../utils/workflowTransform';

const nodeTypes = { workflowNode: WorkflowNode };

const ADD_NODE_TYPES = [
    { value: 'task', label: 'Task' },
    { value: 'qa', label: 'QA' },
    { value: 'pgc', label: 'PGC' },
    { value: 'gate', label: 'Gate' },
    { value: 'end', label: 'End' },
    { value: 'intake_gate', label: 'Intake Gate' },
];

/**
 * React Flow canvas for visual workflow editing.
 */
export default function WorkflowCanvas({
    workflowJson,
    onWorkflowChange,
    selectedNodeId,
    selectedEdgeId,
    onNodeSelect,
    onEdgeSelect,
}) {
    const reactFlowInstance = useReactFlow();
    const [nodes, setNodes, onNodesChange] = useNodesState([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState([]);
    const [showAddMenu, setShowAddMenu] = useState(false);
    const initialLayoutDone = useRef(false);

    // Convert workflow JSON to React Flow format
    useEffect(() => {
        if (!workflowJson) {
            setNodes([]);
            setEdges([]);
            return;
        }

        let { nodes: rfNodes, edges: rfEdges } = workflowToReactFlow(workflowJson);

        // Apply auto-layout only on initial load or if no positions stored
        const hasPositions = rfNodes.some(n => n.position.x !== 0 || n.position.y !== 0);
        if (!hasPositions || !initialLayoutDone.current) {
            rfNodes = applyDagreLayout(rfNodes, rfEdges);
            initialLayoutDone.current = true;
        }

        setNodes(rfNodes);
        setEdges(rfEdges);
    }, [workflowJson, setNodes, setEdges]);

    // Handle new edge connection
    const onConnect = useCallback((params) => {
        if (!workflowJson) return;

        const edgeId = generateEdgeId(params.source, params.target, workflowJson.edges || []);
        const newEdge = {
            edge_id: edgeId,
            from_node_id: params.source,
            to_node_id: params.target,
            outcome: 'success',
            label: '',
            kind: 'auto',
        };

        const updatedWorkflow = {
            ...workflowJson,
            edges: [...(workflowJson.edges || []), newEdge],
        };

        onWorkflowChange(updatedWorkflow);
    }, [workflowJson, onWorkflowChange]);

    // Handle node drag end - persist positions
    const onNodeDragStop = useCallback((event, node) => {
        if (!workflowJson) return;

        const updatedNodes = workflowJson.nodes.map(n => {
            if (n.node_id === node.id) {
                return { ...n, _position: node.position };
            }
            return n;
        });

        onWorkflowChange({ ...workflowJson, nodes: updatedNodes });
    }, [workflowJson, onWorkflowChange]);

    // Handle node click - select node
    const onNodeClick = useCallback((event, node) => {
        onNodeSelect?.(node.id);
    }, [onNodeSelect]);

    // Handle edge click - select edge
    const onEdgeClick = useCallback((event, edge) => {
        onEdgeSelect?.(edge.id);
    }, [onEdgeSelect]);

    // Handle pane click - deselect
    const onPaneClick = useCallback(() => {
        onNodeSelect?.(null);
        onEdgeSelect?.(null);
    }, [onNodeSelect, onEdgeSelect]);

    // Handle delete key
    const onKeyDown = useCallback((event) => {
        if (event.key === 'Delete' || event.key === 'Backspace') {
            if (selectedNodeId && workflowJson) {
                const updatedWorkflow = {
                    ...workflowJson,
                    nodes: workflowJson.nodes.filter(n => n.node_id !== selectedNodeId),
                    edges: workflowJson.edges.filter(
                        e => e.from_node_id !== selectedNodeId && e.to_node_id !== selectedNodeId
                    ),
                    entry_node_ids: (workflowJson.entry_node_ids || []).filter(id => id !== selectedNodeId),
                };
                onWorkflowChange(updatedWorkflow);
                onNodeSelect?.(null);
            } else if (selectedEdgeId && workflowJson) {
                const updatedWorkflow = {
                    ...workflowJson,
                    edges: workflowJson.edges.filter(e => e.edge_id !== selectedEdgeId),
                };
                onWorkflowChange(updatedWorkflow);
                onEdgeSelect?.(null);
            }
        }
    }, [selectedNodeId, selectedEdgeId, workflowJson, onWorkflowChange, onNodeSelect, onEdgeSelect]);

    // Add new node
    const handleAddNode = useCallback((type) => {
        if (!workflowJson) return;

        const nodeId = generateNodeId(type, workflowJson.nodes || []);
        const defaultNode = createDefaultNode(type);
        defaultNode.node_id = nodeId;

        // Place in center of viewport
        const viewport = reactFlowInstance.getViewport();
        const centerX = (-viewport.x + window.innerWidth / 2) / viewport.zoom;
        const centerY = (-viewport.y + window.innerHeight / 2) / viewport.zoom;
        defaultNode._position = { x: centerX - 110, y: centerY - 50 };

        const updatedWorkflow = {
            ...workflowJson,
            nodes: [...(workflowJson.nodes || []), defaultNode],
        };

        onWorkflowChange(updatedWorkflow);
        setShowAddMenu(false);
        onNodeSelect?.(nodeId);
    }, [workflowJson, onWorkflowChange, reactFlowInstance, onNodeSelect]);

    // Auto-layout
    const handleAutoLayout = useCallback(() => {
        if (!workflowJson) return;

        let { nodes: rfNodes, edges: rfEdges } = workflowToReactFlow(workflowJson);
        rfNodes = applyDagreLayout(rfNodes, rfEdges);

        // Save positions back to workflow
        const updatedNodes = workflowJson.nodes.map(n => {
            const rfNode = rfNodes.find(rf => rf.id === n.node_id);
            if (rfNode) {
                return { ...n, _position: rfNode.position };
            }
            return n;
        });

        onWorkflowChange({ ...workflowJson, nodes: updatedNodes });

        setTimeout(() => {
            reactFlowInstance.fitView({ padding: 0.2, duration: 300 });
        }, 50);
    }, [workflowJson, onWorkflowChange, reactFlowInstance]);

    // Fit view
    const handleFitView = useCallback(() => {
        reactFlowInstance.fitView({ padding: 0.2, duration: 300 });
    }, [reactFlowInstance]);

    return (
        <div
            className="flex-1 relative"
            onKeyDown={onKeyDown}
            tabIndex={0}
            style={{ outline: 'none' }}
        >
            <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onConnect={onConnect}
                onNodeDragStop={onNodeDragStop}
                onNodeClick={onNodeClick}
                onEdgeClick={onEdgeClick}
                onPaneClick={onPaneClick}
                nodeTypes={nodeTypes}
                fitView
                fitViewOptions={{ padding: 0.2 }}
                minZoom={0.2}
                maxZoom={2}
                style={{ background: 'var(--bg-canvas)' }}
                proOptions={{ hideAttribution: true }}
                defaultEdgeOptions={{ type: 'smoothstep' }}
                deleteKeyCode={null}
            >
                {/* Toolbar */}
                <Panel position="top-left">
                    <div
                        className="flex gap-2 px-3 py-2 rounded-lg border backdrop-blur"
                        style={{
                            background: 'var(--bg-panel)',
                            borderColor: 'var(--border-panel)',
                        }}
                    >
                        {/* Add Node */}
                        <div className="relative">
                            <button
                                onClick={() => setShowAddMenu(!showAddMenu)}
                                className="px-2.5 py-1.5 rounded text-xs font-medium transition-colors hover:opacity-80"
                                style={{
                                    background: 'var(--action-primary)',
                                    color: '#000',
                                }}
                            >
                                + Add Node
                            </button>
                            {showAddMenu && (
                                <div
                                    className="absolute top-full left-0 mt-1 rounded-lg border shadow-xl z-10"
                                    style={{
                                        background: 'var(--bg-panel)',
                                        borderColor: 'var(--border-panel)',
                                        minWidth: 140,
                                    }}
                                >
                                    {ADD_NODE_TYPES.map(t => {
                                        const config = NODE_TYPE_CONFIG[t.value] || {};
                                        return (
                                            <button
                                                key={t.value}
                                                onClick={() => handleAddNode(t.value)}
                                                className="w-full px-3 py-2 text-left text-xs hover:opacity-80 transition-colors flex items-center gap-2"
                                                style={{ color: 'var(--text-primary)' }}
                                            >
                                                <span
                                                    className="w-2.5 h-2.5 rounded-full"
                                                    style={{ background: config.color }}
                                                />
                                                {t.label}
                                            </button>
                                        );
                                    })}
                                </div>
                            )}
                        </div>

                        {/* Auto Layout */}
                        <button
                            onClick={handleAutoLayout}
                            className="px-2.5 py-1.5 rounded text-xs transition-colors"
                            style={{
                                background: 'transparent',
                                border: '1px solid var(--border-panel)',
                                color: 'var(--text-muted)',
                            }}
                        >
                            Auto Layout
                        </button>

                        {/* Fit View */}
                        <button
                            onClick={handleFitView}
                            className="px-2.5 py-1.5 rounded text-xs transition-colors"
                            style={{
                                background: 'transparent',
                                border: '1px solid var(--border-panel)',
                                color: 'var(--text-muted)',
                            }}
                        >
                            Fit View
                        </button>
                    </div>
                </Panel>

                {/* MiniMap */}
                <MiniMap
                    position="bottom-right"
                    nodeColor={(node) => {
                        const config = node.data?.config;
                        return config?.color || '#475569';
                    }}
                    maskColor="rgba(11, 17, 32, 0.85)"
                    style={{
                        background: 'var(--bg-panel)',
                        border: '1px solid var(--border-panel)',
                        borderRadius: 8,
                    }}
                    pannable
                    zoomable
                />

                {/* Legend */}
                <Panel position="bottom-left">
                    <div
                        className="flex gap-3 text-[10px] px-3 py-2 rounded-lg border backdrop-blur"
                        style={{
                            background: 'var(--bg-panel)',
                            borderColor: 'var(--border-panel)',
                        }}
                    >
                        {Object.entries(NODE_TYPE_CONFIG).map(([type, config]) => (
                            <div key={type} className="flex items-center gap-1">
                                <span
                                    className="w-2.5 h-2.5 rounded-full"
                                    style={{ background: config.color }}
                                />
                                <span style={{ color: 'var(--text-muted)' }}>{config.label}</span>
                            </div>
                        ))}
                    </div>
                </Panel>

                {/* Instructions */}
                <Panel position="top-right">
                    <div
                        className="text-[10px] px-2 py-1 rounded"
                        style={{ color: 'var(--text-muted)' }}
                    >
                        Drag to connect | Delete to remove | Scroll to zoom
                    </div>
                </Panel>
            </ReactFlow>
        </div>
    );
}
