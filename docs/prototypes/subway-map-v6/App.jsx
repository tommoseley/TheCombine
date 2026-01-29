// App.jsx
// Main React Flow container and state management

import { initialData } from './data/projectData.js';
import { getLayoutedElements, buildGraph, addEpicsToLayout } from './utils/layout.js';
import DocumentNode from './components/nodes/DocumentNode.jsx';

export default function App({ React, ReactFlow, Position, useNodesState, useEdgesState, Panel }) {
    const { useState, useCallback, useMemo, useEffect } = React;
    
    const [data, setData] = useState(initialData);
    const [expandedId, setExpandedId] = useState(null);
    const [expandType, setExpandType] = useState(null);

    // Callbacks for node interactions
    const callbacks = useMemo(() => ({
        onExpand: (id, type) => { setExpandedId(id); setExpandType(type); },
        onCollapse: () => { setExpandedId(null); setExpandType(null); },
        onSubmitQuestions: (id, answers) => {
            console.log('Submitted:', id, answers);
            setExpandedId(null);
            setExpandType(null);
            setData(prev => {
                const update = (items) => items.map(item => {
                    if (item.id === id && item.stations) {
                        return { ...item, stations: item.stations.map(s => 
                            s.id === 'pgc' ? { ...s, state: 'complete', needs_input: false } :
                            s.id === 'asm' ? { ...s, state: 'active' } : s
                        )};
                    }
                    if (item.children) return { ...item, children: update(item.children) };
                    return item;
                });
                return update(prev);
            });
        }
    }), []);

    // Build and layout graph
    const { layoutNodes, layoutEdges } = useMemo(() => {
        const callbacksWithType = { ...callbacks, expandType };
        
        const { nodes, edges, epicBacklogId, epicChildren } = buildGraph(data, expandedId, callbacksWithType, Position);
        const dagreResult = getLayoutedElements(nodes, edges, Position);
        const { nodes: allNodes, edges: allEdges } = addEpicsToLayout(
            dagreResult, epicBacklogId, epicChildren, expandedId, callbacksWithType, Position
        );
        
        const nodesWithType = allNodes.map(n => ({
            ...n,
            data: { ...n.data, expandType: n.id === expandedId ? expandType : null }
        }));
        
        return { layoutNodes: nodesWithType, layoutEdges: allEdges };
    }, [data, expandedId, expandType, callbacks, Position]);

    const [nodes, setNodes, onNodesChange] = useNodesState(layoutNodes);
    const [edges, setEdges, onEdgesChange] = useEdgesState(layoutEdges);

    // Update on data/state changes
    useEffect(() => {
        const callbacksWithType = { ...callbacks, expandType };
        
        const { nodes: n, edges: e, epicBacklogId, epicChildren } = buildGraph(data, expandedId, callbacksWithType, Position);
        const dagreResult = getLayoutedElements(n, e, Position);
        const { nodes: allNodes, edges: allEdges } = addEpicsToLayout(
            dagreResult, epicBacklogId, epicChildren, expandedId, callbacksWithType, Position
        );
        
        const nodesWithType = allNodes.map(node => ({
            ...node,
            data: { ...node.data, expandType: node.id === expandedId ? expandType : null }
        }));
        
        setNodes(nodesWithType);
        setEdges(allEdges);
    }, [data, expandedId, expandType, callbacks, Position, setNodes, setEdges]);

    // Click to cycle state (demo)
    const onNodeClick = useCallback((_, node) => {
        if (expandedId) return;
        const states = ['queued', 'active', 'stabilized'];
        setData(prev => {
            const update = (items) => items.map(item => {
                if (item.id === node.id) {
                    const next = states[(states.indexOf(item.state) + 1) % states.length];
                    const newStations = item.stations?.map(s => 
                        next === 'stabilized' ? { ...s, state: 'complete', needs_input: false } :
                        next === 'active' ? (s.id === 'pgc' ? { ...s, state: 'active', needs_input: !!item.questions?.length } : { ...s, state: 'pending' }) :
                        { ...s, state: 'pending', needs_input: false }
                    );
                    return { ...item, state: next, stations: newStations };
                }
                if (item.children) return { ...item, children: update(item.children) };
                return item;
            });
            return update(prev);
        });
    }, [expandedId]);

    // Custom node type with injected dependencies
    const nodeTypes = useMemo(() => ({
        documentNode: (props) => <DocumentNode {...props} Handle={ReactFlow.Handle} Position={Position} />
    }), [Position]);

    return (
        <div className="w-full h-full">
            <ReactFlow.default
                nodes={nodes} 
                edges={edges}
                onNodesChange={onNodesChange} 
                onEdgesChange={onEdgesChange}
                onNodeClick={onNodeClick}
                nodeTypes={nodeTypes}
                nodesDraggable={false} 
                nodesConnectable={false} 
                edgesUpdatable={false} 
                edgesFocusable={false} 
                elementsSelectable={false}
                fitView 
                fitViewOptions={{ padding: 0.2 }}
                minZoom={0.3} 
                maxZoom={1.5}
                style={{ background: '#0f172a' }}
                proOptions={{ hideAttribution: true }}
                defaultEdgeOptions={{ type: 'smoothstep' }}
            >
                <Panel position="top-left">
                    <div className="bg-slate-900/90 backdrop-blur rounded-lg px-4 py-3 border border-slate-800">
                        <h1 className="text-lg font-bold text-slate-100">Production Line</h1>
                        <p className="text-slate-500 text-xs">Modular v6 | Smoothstep routing</p>
                    </div>
                </Panel>
                <Panel position="bottom-left">
                    <div className="flex gap-4 text-[10px] bg-slate-900/90 backdrop-blur px-4 py-2.5 rounded-lg border border-slate-700/50">
                        <span className="text-slate-500 font-medium">STATE:</span>
                        <div className="flex items-center gap-1.5"><div className="w-3 h-3 rounded-full bg-emerald-500" /><span className="text-slate-400">Stabilized</span></div>
                        <div className="flex items-center gap-1.5"><div className="w-3 h-3 rounded-full bg-indigo-500" /><span className="text-slate-400">Active</span></div>
                        <div className="flex items-center gap-1.5"><div className="w-3 h-3 rounded-full bg-slate-600" /><span className="text-slate-400">Queued</span></div>
                    </div>
                </Panel>
                <Panel position="bottom-right">
                    <div className="text-[10px] text-slate-600 bg-slate-900/50 px-2 py-1 rounded">Scroll to zoom | Drag to pan</div>
                </Panel>
            </ReactFlow.default>
        </div>
    );
}