import { useState, useEffect, useCallback, useMemo } from 'react';
import ReactFlow, {
    useNodesState,
    useEdgesState,
    useReactFlow,
    Panel,
    MiniMap
} from 'reactflow';
import 'reactflow/dist/style.css';

import DocumentNode from './DocumentNode';
import WaypointNode from './WaypointNode';
import FullDocumentViewer from './FullDocumentViewer';
import { buildGraph, getLayoutedElements, addEpicsToLayout } from '../utils/layout';
import { THEMES } from '../utils/constants';
import { useProductionStatus } from '../hooks';

const nodeTypes = { documentNode: DocumentNode, waypoint: WaypointNode };
const THEME_LABELS = { industrial: 'Industrial', light: 'Light', blueprint: 'Blueprint' };

export default function Floor({ projectId, projectCode, projectName, isArchived, autoExpandNodeId, theme, onThemeChange, onProjectUpdate, onProjectArchive, onProjectUnarchive, onProjectDelete }) {
    const {
        data: productionData,
        lineState,
        loading,
        error,
        connected,
        resolveInterrupt,
        startProduction,
    } = useProductionStatus(projectId);

    const [data, setData] = useState([]);
    const [expandedId, setExpandedId] = useState(null);
    const [expandType, setExpandType] = useState(null);
    const [fullViewerDocId, setFullViewerDocId] = useState(null);
    const [isEditingName, setIsEditingName] = useState(false);
    const [editName, setEditName] = useState('');
    const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
    const [actionLoading, setActionLoading] = useState(false);
    const reactFlowInstance = useReactFlow();

    // Update data when productionData changes
    useEffect(() => {
        if (productionData.length > 0) {
            setData(productionData);
        }
    }, [productionData]);

    // Auto-expand only when explicitly requested (new project)
    useEffect(() => {
        if (autoExpandNodeId && data.length > 0) {
            setTimeout(() => {
                setExpandedId(autoExpandNodeId);
                setExpandType('questions');
            }, 300);
        }
    }, [autoExpandNodeId, data.length]);

    // Reset expansion when project changes
    useEffect(() => {
        setExpandedId(null);
        setExpandType(null);
    }, [projectId]);

    const cycleTheme = useCallback(() => {
        const idx = THEMES.indexOf(theme);
        onThemeChange(THEMES[(idx + 1) % THEMES.length]);
    }, [theme, onThemeChange]);

    const handleStartEdit = useCallback(() => {
        setEditName(projectName || '');
        setIsEditingName(true);
    }, [projectName]);

    const handleSaveName = useCallback(async () => {
        if (!editName.trim() || editName === projectName) {
            setIsEditingName(false);
            return;
        }
        setActionLoading(true);
        try {
            await onProjectUpdate(projectId, { name: editName.trim() });
            setIsEditingName(false);
        } catch (err) {
            console.error('Failed to update name:', err);
        } finally {
            setActionLoading(false);
        }
    }, [editName, projectName, projectId, onProjectUpdate]);

    const handleCancelEdit = useCallback(() => {
        setIsEditingName(false);
        setEditName('');
    }, []);

    const handleArchiveToggle = useCallback(async () => {
        setActionLoading(true);
        try {
            if (isArchived) {
                await onProjectUnarchive(projectId);
            } else {
                await onProjectArchive(projectId);
            }
        } catch (err) {
            console.error('Failed to toggle archive:', err);
        } finally {
            setActionLoading(false);
        }
    }, [projectId, isArchived, onProjectArchive, onProjectUnarchive]);

    const handleDelete = useCallback(async () => {
        setActionLoading(true);
        try {
            await onProjectDelete(projectId);
            setShowDeleteConfirm(false);
        } catch (err) {
            console.error('Failed to delete:', err);
        } finally {
            setActionLoading(false);
        }
    }, [projectId, onProjectDelete]);

    const onZoomToNode = useCallback((nodeId) => {
        const node = reactFlowInstance.getNode(nodeId);
        if (node) {
            const zoom = 0.9;
            const viewportWidth = window.innerWidth;
            const x = -node.position.x * zoom + viewportWidth / 2 - 400;
            const y = -node.position.y * zoom + 120;
            reactFlowInstance.setViewport({ x, y, zoom }, { duration: 800 });
        }
    }, [reactFlowInstance]);

    const callbacks = useMemo(() => ({
        onExpand: (id, type) => { setExpandedId(id); setExpandType(type); },
        onCollapse: () => {
            setExpandedId(null);
            setExpandType(null);
            setTimeout(() => reactFlowInstance.fitView({ padding: 0.2, duration: 300 }), 50);
        },
        onViewFullDocument: (docId) => {
            setFullViewerDocId(docId);
        },
        onSubmitQuestions: async (id, answers) => {
            console.log('Submitted:', id, answers);

            // Find the document to get its interruptId
            const doc = data.find(d => d.id === id);
            if (doc?.interruptId) {
                try {
                    await resolveInterrupt(doc.interruptId, answers);
                } catch (err) {
                    console.error('Failed to submit answers:', err);
                }
            }

            setExpandedId(null);
            setExpandType(null);

            // Optimistically update local state
            setData(prev => {
                const update = (items) => items.map(item => {
                    if (item.id === id && item.stations) {
                        return {
                            ...item, stations: item.stations.map(s =>
                                s.id === 'pgc' ? { ...s, state: 'complete', needs_input: false } :
                                    s.id === 'asm' ? { ...s, state: 'active' } : s
                            )
                        };
                    }
                    if (item.children) return { ...item, children: update(item.children) };
                    return item;
                });
                return update(prev);
            });
        }
    }), [reactFlowInstance, data, resolveInterrupt]);

    const { layoutNodes, layoutEdges } = useMemo(() => {
        if (data.length === 0) return { layoutNodes: [], layoutEdges: [] };

        const callbacksWithType = { ...callbacks, expandType, theme, onZoomToNode, projectId, projectCode };
        const { nodes, edges, epicBacklogId, epicChildren } = buildGraph(data, expandedId, callbacksWithType);
        const dagreResult = getLayoutedElements(nodes, edges);
        const { nodes: allNodes, edges: allEdges } = addEpicsToLayout(dagreResult, epicBacklogId, epicChildren, expandedId, callbacksWithType);
        const nodesWithType = allNodes.map(n => ({ ...n, data: { ...n.data, expandType: n.id === expandedId ? expandType : null } }));
        return { layoutNodes: nodesWithType, layoutEdges: allEdges };
    }, [data, expandedId, expandType, callbacks, theme, onZoomToNode, projectId, projectCode]);

    const [nodes, setNodes, onNodesChange] = useNodesState(layoutNodes);
    const [edges, setEdges, onEdgesChange] = useEdgesState(layoutEdges);

    useEffect(() => {
        if (data.length === 0) return;

        const callbacksWithType = { ...callbacks, expandType, theme, onZoomToNode, projectId, projectCode };
        const { nodes: n, edges: e, epicBacklogId, epicChildren } = buildGraph(data, expandedId, callbacksWithType);
        const dagreResult = getLayoutedElements(n, e);
        const { nodes: allNodes, edges: allEdges } = addEpicsToLayout(dagreResult, epicBacklogId, epicChildren, expandedId, callbacksWithType);
        const nodesWithType = allNodes.map(node => ({ ...node, data: { ...node.data, expandType: node.id === expandedId ? expandType : null } }));
        setNodes(nodesWithType);
        setEdges(allEdges);
    }, [data, expandedId, expandType, callbacks, setNodes, setEdges, theme, onZoomToNode, projectId, projectCode]);

    const onNodeClick = useCallback((_, node) => {
        if (expandedId) return;
        // Clicking a node could start production for that document type
        // For now, just cycle state for demo purposes
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

    if (loading && data.length === 0) {
        return (
            <div className="flex items-center justify-center h-full" style={{ background: 'var(--bg-canvas)' }}>
                <div className="text-center">
                    <img
                        src="/logo-light.png"
                        alt="The Combine"
                        className="h-12 mx-auto mb-4 animate-pulse"
                    />
                    <p style={{ color: 'var(--text-muted)' }}>Loading production line...</p>
                </div>
            </div>
        );
    }

    if (error && data.length === 0) {
        return (
            <div className="flex items-center justify-center h-full" style={{ background: 'var(--bg-canvas)' }}>
                <div className="text-center p-6 rounded-lg" style={{ background: 'var(--bg-panel)' }}>
                    <p className="text-red-500 mb-4">{error}</p>
                </div>
            </div>
        );
    }

    return (
        <div className="w-full h-full">
            <ReactFlow
                nodes={nodes} edges={edges}
                onNodesChange={onNodesChange} onEdgesChange={onEdgesChange}
                onNodeClick={onNodeClick}
                nodeTypes={nodeTypes}
                nodesDraggable={false} nodesConnectable={false} edgesUpdatable={false} edgesFocusable={false} elementsSelectable={false}
                fitView fitViewOptions={{ padding: 0.2 }}
                minZoom={0.3} maxZoom={1.5}
                style={{ background: 'var(--bg-canvas)' }}
                proOptions={{ hideAttribution: true }}
                defaultEdgeOptions={{ type: 'smoothstep' }}
            >
                <Panel position="top-left">
                    <div className="space-y-2">
                        {/* Production Line Status */}
                        <div className="subway-panel backdrop-blur rounded-lg px-4 py-3 border">
                            <div className="flex items-center justify-between gap-4">
                                <div>
                                    <h1 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>Production Line</h1>
                                    <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                                        {lineState === 'active' && <span className="text-amber-500">● Active</span>}
                                        {lineState === 'stopped' && <span className="text-red-500">● Stopped</span>}
                                        {lineState === 'complete' && <span className="text-emerald-500">● Complete</span>}
                                        {lineState === 'idle' && <span>● Idle</span>}
                                        {!connected && <span className="ml-2 text-red-400">(Disconnected)</span>}
                                    </p>
                                </div>
                                <button
                                    onClick={cycleTheme}
                                    className="subway-button px-3 py-1.5 rounded-md text-xs font-medium transition-colors"
                                >
                                    {THEME_LABELS[theme]}
                                </button>
                            </div>
                        </div>

                        {/* Project Info */}
                        <div className="subway-panel backdrop-blur rounded-lg px-4 py-3 border">
                            <div className="flex items-center gap-3">
                                <div
                                    className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0"
                                    style={{ background: 'var(--state-active-bg)' }}
                                >
                                    <svg className="w-5 h-5 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                        <path d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                                    </svg>
                                </div>
                                <div className="min-w-0 flex-1">
                                    <p
                                        className="text-xs font-mono"
                                        style={{ color: 'var(--text-muted)' }}
                                    >
                                        {projectCode || 'No Project'}
                                    </p>
                                    {isEditingName ? (
                                        <div className="flex items-center gap-2 mt-1">
                                            <input
                                                type="text"
                                                value={editName}
                                                onChange={(e) => setEditName(e.target.value)}
                                                onKeyDown={(e) => {
                                                    if (e.key === 'Enter') handleSaveName();
                                                    if (e.key === 'Escape') handleCancelEdit();
                                                }}
                                                className="flex-1 px-2 py-1 text-sm rounded border bg-transparent"
                                                style={{
                                                    color: 'var(--text-primary)',
                                                    borderColor: 'var(--border-panel)',
                                                }}
                                                autoFocus
                                                disabled={actionLoading}
                                            />
                                            <button
                                                onClick={handleSaveName}
                                                disabled={actionLoading}
                                                className="p-1 rounded hover:bg-white/10"
                                                title="Save"
                                            >
                                                <svg className="w-4 h-4 text-emerald-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                                    <path d="M5 13l4 4L19 7" />
                                                </svg>
                                            </button>
                                            <button
                                                onClick={handleCancelEdit}
                                                disabled={actionLoading}
                                                className="p-1 rounded hover:bg-white/10"
                                                title="Cancel"
                                            >
                                                <svg className="w-4 h-4" style={{ color: 'var(--text-muted)' }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                                    <path d="M6 18L18 6M6 6l12 12" />
                                                </svg>
                                            </button>
                                        </div>
                                    ) : (
                                        <p
                                            className="text-sm font-semibold truncate"
                                            style={{ color: 'var(--text-primary)' }}
                                        >
                                            {projectName || 'Untitled Project'}
                                        </p>
                                    )}
                                </div>
                                {!isEditingName && (
                                    <div className="flex items-center gap-1">
                                        <button
                                            onClick={handleStartEdit}
                                            className="p-1.5 rounded hover:bg-white/10 transition-colors"
                                            style={{ color: 'var(--text-muted)' }}
                                            title="Edit name"
                                        >
                                            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                                <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" />
                                                <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" />
                                            </svg>
                                        </button>
                                        <button
                                            onClick={handleArchiveToggle}
                                            disabled={actionLoading}
                                            className="p-1.5 rounded hover:bg-white/10 transition-colors"
                                            style={{ color: isArchived ? '#f59e0b' : 'var(--text-muted)' }}
                                            title={isArchived ? 'Unarchive project' : 'Archive project'}
                                        >
                                            <svg className="w-4 h-4 relative" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                                <path d="M21 8v13H3V8M1 3h22v5H1zM10 12h4" />
                                                {isArchived && (
                                                    <path d="M4 20L20 4" strokeWidth="2.5" stroke="currentColor" />
                                                )}
                                            </svg>
                                        </button>
                                        <button
                                            onClick={() => setShowDeleteConfirm(true)}
                                            disabled={actionLoading || !isArchived}
                                            className={`p-1.5 rounded transition-colors ${isArchived ? 'hover:bg-red-500/20' : ''}`}
                                            style={{
                                                color: 'var(--text-muted)',
                                                opacity: isArchived ? 1 : 0.3,
                                                cursor: isArchived ? 'pointer' : 'not-allowed',
                                            }}
                                            title={isArchived ? 'Delete project' : 'Archive project first to delete'}
                                        >
                                            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                                <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" />
                                            </svg>
                                        </button>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                </Panel>
                <MiniMap
                    position="top-right"
                    nodeColor={(node) => {
                        if (node.data?.state === 'stabilized') return '#10b981';
                        if (node.data?.state === 'active') return '#f59e0b';
                        return '#475569';
                    }}
                    maskColor="rgba(11, 17, 32, 0.85)"
                    style={{
                        background: 'var(--bg-panel)',
                        border: '1px solid var(--border-panel)',
                        borderRadius: 8
                    }}
                    pannable
                    zoomable
                />
                <Panel position="bottom-left">
                    <div className="subway-panel flex gap-4 text-[10px] backdrop-blur px-4 py-2.5 rounded-lg border">
                        <span style={{ color: 'var(--text-muted)' }} className="font-medium">STATE:</span>
                        <div className="flex items-center gap-1.5"><div className="w-3 h-3 rounded-full" style={{ background: 'var(--state-stabilized-bg)' }} /><span style={{ color: 'var(--text-muted)' }}>Stabilized</span></div>
                        <div className="flex items-center gap-1.5"><div className="w-3 h-3 rounded-full" style={{ background: 'var(--state-active-bg)' }} /><span style={{ color: 'var(--text-muted)' }}>Active</span></div>
                        <div className="flex items-center gap-1.5"><div className="w-3 h-3 rounded-full" style={{ background: 'var(--state-queued-bg)' }} /><span style={{ color: 'var(--text-muted)' }}>Queued</span></div>
                    </div>
                </Panel>
                <Panel position="bottom-right">
                    <div className="subway-panel text-[10px] px-2 py-1 rounded" style={{ color: 'var(--text-muted)' }}>Scroll to zoom | Drag to pan</div>
                </Panel>
            </ReactFlow>

            {/* Full Document Viewer Modal */}
            {fullViewerDocId && (
                <FullDocumentViewer
                    projectId={projectId}
                    docTypeId={fullViewerDocId}
                    onClose={() => setFullViewerDocId(null)}
                />
            )}

            {/* Delete Confirmation Modal */}
            {showDeleteConfirm && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
                    <div
                        className="rounded-lg p-6 max-w-sm mx-4"
                        style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-panel)' }}
                    >
                        <h3 className="text-lg font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>
                            Delete Project?
                        </h3>
                        <p className="text-sm mb-4" style={{ color: 'var(--text-muted)' }}>
                            This will permanently delete <strong>{projectName}</strong> and all its documents.
                            This action cannot be undone.
                        </p>
                        <div className="flex gap-3 justify-end">
                            <button
                                onClick={() => setShowDeleteConfirm(false)}
                                disabled={actionLoading}
                                className="px-4 py-2 rounded text-sm font-medium transition-colors"
                                style={{ color: 'var(--text-muted)' }}
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleDelete}
                                disabled={actionLoading}
                                className="px-4 py-2 rounded text-sm font-medium bg-red-500 text-white hover:bg-red-600 transition-colors"
                            >
                                {actionLoading ? 'Deleting...' : 'Delete'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
