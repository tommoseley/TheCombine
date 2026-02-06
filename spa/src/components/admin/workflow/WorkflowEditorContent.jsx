import React, { useState, useCallback, useMemo } from 'react';
import { ReactFlowProvider } from 'reactflow';
import { useWorkflowEditor } from '../../../hooks/useWorkflowEditor';
import { useAdminTemplates } from '../../../hooks/useAdminTemplates';
import { useAdminSchemas } from '../../../hooks/useAdminSchemas';
import usePromptFragments from '../../../hooks/usePromptFragments';
import WorkflowCanvas from './WorkflowCanvas';
import NodePropertiesPanel from './NodePropertiesPanel';
import EdgePropertiesPanel from './EdgePropertiesPanel';

const TAB_STYLE = {
    padding: '6px 14px',
    fontSize: 12,
    fontWeight: 600,
    border: 'none',
    cursor: 'pointer',
    transition: 'opacity 0.15s',
    background: 'transparent',
};

/**
 * Reusable workflow editor content - Canvas/JSON/Metadata sub-tabs with
 * properties panels. Used both embedded in PromptEditor (as a doc type tab)
 * and standalone in WorkflowEditor.
 */
export default function WorkflowEditorContent({ workspaceId, artifactId, onArtifactSave }) {
    const [activeTab, setActiveTab] = useState('canvas');
    const [selectedNodeId, setSelectedNodeId] = useState(null);
    const [selectedEdgeId, setSelectedEdgeId] = useState(null);
    const [jsonText, setJsonText] = useState('');
    const [jsonError, setJsonError] = useState(null);

    const {
        workflowJson,
        loading,
        error,
        saving,
        lastSaveResult,
        updateWorkflow,
    } = useWorkflowEditor(workspaceId, artifactId, {
        onSave: (result) => {
            onArtifactSave?.(artifactId, result);
        },
    });

    // Fetch templates, schemas, and prompt fragments for node property dropdowns
    const { templates } = useAdminTemplates();
    const { schemas } = useAdminSchemas();
    const { fragmentsByKind } = usePromptFragments();

    // Get selected node data
    const selectedNode = useMemo(() => {
        if (!selectedNodeId || !workflowJson) return null;
        return workflowJson.nodes?.find(n => n.node_id === selectedNodeId) || null;
    }, [selectedNodeId, workflowJson]);

    // Get selected edge data
    const selectedEdge = useMemo(() => {
        if (!selectedEdgeId || !workflowJson) return null;
        return workflowJson.edges?.find(e => e.edge_id === selectedEdgeId) || null;
    }, [selectedEdgeId, workflowJson]);

    // All node IDs for edge dropdowns
    const nodeIds = useMemo(() => {
        if (!workflowJson?.nodes) return [];
        return workflowJson.nodes.map(n => n.node_id);
    }, [workflowJson]);

    // Handle workflow changes from canvas
    const handleWorkflowChange = useCallback((newWorkflow) => {
        updateWorkflow(newWorkflow);
    }, [updateWorkflow]);

    // Handle node property change
    const handleNodeChange = useCallback((updatedNode) => {
        if (!workflowJson) return;

        const updatedNodes = workflowJson.nodes.map(n =>
            n.node_id === selectedNodeId ? updatedNode : n
        );

        // If node_id changed, update edges and entry_node_ids
        let updatedEdges = workflowJson.edges;
        let updatedEntryIds = workflowJson.entry_node_ids || [];
        if (updatedNode.node_id !== selectedNodeId) {
            updatedEdges = workflowJson.edges.map(e => ({
                ...e,
                from_node_id: e.from_node_id === selectedNodeId ? updatedNode.node_id : e.from_node_id,
                to_node_id: e.to_node_id === selectedNodeId ? updatedNode.node_id : e.to_node_id,
            }));
            updatedEntryIds = updatedEntryIds.map(id =>
                id === selectedNodeId ? updatedNode.node_id : id
            );
            setSelectedNodeId(updatedNode.node_id);
        }

        updateWorkflow({
            ...workflowJson,
            nodes: updatedNodes,
            edges: updatedEdges,
            entry_node_ids: updatedEntryIds,
        });
    }, [workflowJson, selectedNodeId, updateWorkflow]);

    // Handle edge property change
    const handleEdgeChange = useCallback((updatedEdge) => {
        if (!workflowJson) return;

        const updatedEdges = workflowJson.edges.map(e =>
            e.edge_id === selectedEdgeId ? updatedEdge : e
        );

        if (updatedEdge.edge_id !== selectedEdgeId) {
            setSelectedEdgeId(updatedEdge.edge_id);
        }

        updateWorkflow({ ...workflowJson, edges: updatedEdges });
    }, [workflowJson, selectedEdgeId, updateWorkflow]);

    // Handle node delete from panel
    const handleNodeDelete = useCallback((nodeId) => {
        if (!workflowJson) return;

        updateWorkflow({
            ...workflowJson,
            nodes: workflowJson.nodes.filter(n => n.node_id !== nodeId),
            edges: workflowJson.edges.filter(
                e => e.from_node_id !== nodeId && e.to_node_id !== nodeId
            ),
            entry_node_ids: (workflowJson.entry_node_ids || []).filter(id => id !== nodeId),
        });
        setSelectedNodeId(null);
    }, [workflowJson, updateWorkflow]);

    // Handle edge delete from panel
    const handleEdgeDelete = useCallback((edgeId) => {
        if (!workflowJson) return;

        updateWorkflow({
            ...workflowJson,
            edges: workflowJson.edges.filter(e => e.edge_id !== edgeId),
        });
        setSelectedEdgeId(null);
    }, [workflowJson, updateWorkflow]);

    // Handle node selection
    const handleNodeSelect = useCallback((nodeId) => {
        setSelectedNodeId(nodeId);
        if (nodeId) setSelectedEdgeId(null);
    }, []);

    // Handle edge selection
    const handleEdgeSelect = useCallback((edgeId) => {
        setSelectedEdgeId(edgeId);
        if (edgeId) setSelectedNodeId(null);
    }, []);

    // Switch to JSON tab - sync text
    const handleTabChange = useCallback((tab) => {
        if (tab === 'json' && workflowJson) {
            setJsonText(JSON.stringify(workflowJson, null, 2));
            setJsonError(null);
        }
        setActiveTab(tab);
    }, [workflowJson]);

    // Handle raw JSON edit
    const handleJsonTextChange = useCallback((e) => {
        const text = e.target.value;
        setJsonText(text);
        try {
            const parsed = JSON.parse(text);
            setJsonError(null);
            updateWorkflow(parsed);
        } catch (err) {
            setJsonError(err.message);
        }
    }, [updateWorkflow]);

    // Validation info from last save
    const validationResults = lastSaveResult?.tier1_report?.results || [];
    const errorCount = validationResults.filter(r => r.severity === 'error').length;
    const warningCount = validationResults.filter(r => r.severity === 'warning').length;

    return (
        <div className="flex-1 flex flex-col overflow-hidden" style={{ background: 'var(--bg-canvas)' }}>
            {/* Status bar */}
            <div
                className="flex items-center justify-between px-4 py-1.5 border-b"
                style={{ borderColor: 'var(--border-panel)', background: 'var(--bg-panel)' }}
            >
                <div className="flex items-center gap-3">
                    {saving && (
                        <span className="text-xs" style={{ color: 'var(--action-primary)' }}>
                            Saving...
                        </span>
                    )}
                    {error && (
                        <span className="text-xs" style={{ color: '#ef4444' }}>
                            {error}
                        </span>
                    )}
                    {!saving && !error && workflowJson && (
                        <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                            {workflowJson.nodes?.length || 0} nodes, {workflowJson.edges?.length || 0} edges
                        </span>
                    )}
                </div>
            </div>

            {/* Sub-tab bar */}
            <div
                className="flex items-center border-b px-2"
                style={{ borderColor: 'var(--border-panel)', background: 'var(--bg-panel)' }}
            >
                {[
                    { id: 'canvas', label: 'Canvas' },
                    { id: 'json', label: 'JSON' },
                    { id: 'metadata', label: 'Metadata' },
                ].map(tab => (
                    <button
                        key={tab.id}
                        onClick={() => handleTabChange(tab.id)}
                        style={{
                            ...TAB_STYLE,
                            color: activeTab === tab.id ? 'var(--text-primary)' : 'var(--text-muted)',
                            borderBottom: activeTab === tab.id
                                ? '2px solid var(--action-primary)'
                                : '2px solid transparent',
                        }}
                    >
                        {tab.label}
                    </button>
                ))}
            </div>

            {/* Main content area */}
            {loading ? (
                <div className="flex-1 flex items-center justify-center">
                    <span style={{ color: 'var(--text-muted)' }}>Loading workflow...</span>
                </div>
            ) : (
                <div className="flex-1 flex overflow-hidden">
                    {/* Canvas tab */}
                    {activeTab === 'canvas' && (
                        <>
                            <ReactFlowProvider>
                                <WorkflowCanvas
                                    workflowJson={workflowJson}
                                    onWorkflowChange={handleWorkflowChange}
                                    selectedNodeId={selectedNodeId}
                                    selectedEdgeId={selectedEdgeId}
                                    onNodeSelect={handleNodeSelect}
                                    onEdgeSelect={handleEdgeSelect}
                                />
                            </ReactFlowProvider>
                            {/* Properties panel */}
                            {selectedNode && (
                                <NodePropertiesPanel
                                    node={selectedNode}
                                    onChange={handleNodeChange}
                                    onDelete={handleNodeDelete}
                                    templates={templates}
                                    schemas={schemas}
                                    roleFragments={fragmentsByKind.role || []}
                                    taskFragments={fragmentsByKind.task || []}
                                    pgcFragments={fragmentsByKind.pgc || []}
                                />
                            )}
                            {selectedEdge && (
                                <EdgePropertiesPanel
                                    edge={selectedEdge}
                                    nodeIds={nodeIds}
                                    onChange={handleEdgeChange}
                                    onDelete={handleEdgeDelete}
                                />
                            )}
                        </>
                    )}

                    {/* JSON tab */}
                    {activeTab === 'json' && (
                        <div className="flex-1 flex flex-col p-4">
                            <textarea
                                value={jsonText}
                                onChange={handleJsonTextChange}
                                className="flex-1 font-mono text-xs p-3 rounded"
                                style={{
                                    background: 'var(--bg-input, var(--bg-canvas))',
                                    border: jsonError
                                        ? '1px solid #ef4444'
                                        : '1px solid var(--border-panel)',
                                    color: 'var(--text-primary)',
                                    resize: 'none',
                                    outline: 'none',
                                }}
                                spellCheck={false}
                            />
                            {jsonError && (
                                <div className="mt-2 text-xs" style={{ color: '#ef4444' }}>
                                    JSON Error: {jsonError}
                                </div>
                            )}
                        </div>
                    )}

                    {/* Metadata tab */}
                    {activeTab === 'metadata' && (
                        <div className="flex-1 p-4 overflow-y-auto">
                            {workflowJson ? (
                                <MetadataView workflow={workflowJson} />
                            ) : (
                                <div style={{ color: 'var(--text-muted)' }}>No workflow loaded</div>
                            )}
                        </div>
                    )}
                </div>
            )}

            {/* Validation bar */}
            {validationResults.length > 0 && (
                <div
                    className="px-4 py-1.5 border-t flex items-center gap-3 text-xs"
                    style={{ borderColor: 'var(--border-panel)', background: 'var(--bg-panel)' }}
                >
                    {errorCount > 0 && (
                        <span style={{ color: '#ef4444' }}>
                            {errorCount} error{errorCount !== 1 ? 's' : ''}
                        </span>
                    )}
                    {warningCount > 0 && (
                        <span style={{ color: '#f59e0b' }}>
                            {warningCount} warning{warningCount !== 1 ? 's' : ''}
                        </span>
                    )}
                    {errorCount === 0 && warningCount === 0 && (
                        <span style={{ color: '#10b981' }}>Valid</span>
                    )}
                    <span style={{ color: 'var(--text-muted)' }}>
                        {validationResults.map(r => r.message).join(' | ')}
                    </span>
                </div>
            )}
        </div>
    );
}

/**
 * Read-only metadata view for workflow governance fields.
 */
function MetadataView({ workflow }) {
    const fieldStyle = {
        fontSize: 12,
        color: 'var(--text-primary)',
        padding: '6px 8px',
        borderRadius: 4,
        background: 'var(--bg-input, var(--bg-canvas))',
        border: '1px solid var(--border-panel)',
        width: '100%',
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

    const fields = [
        { key: 'workflow_id', label: 'Workflow ID' },
        { key: 'name', label: 'Name' },
        { key: 'version', label: 'Version' },
        { key: 'description', label: 'Description' },
    ];

    const threadOwnership = workflow.thread_ownership || {};
    const threadFields = Object.entries(threadOwnership);
    const entryNodeIds = workflow.entry_node_ids || [];

    return (
        <div className="space-y-4 max-w-lg">
            <h3
                className="text-xs font-semibold uppercase tracking-wide"
                style={{ color: 'var(--text-muted)' }}
            >
                Workflow Metadata
            </h3>

            {fields.map(f => (
                <div key={f.key}>
                    <label style={labelStyle}>{f.label}</label>
                    <div style={fieldStyle}>{workflow[f.key] || '-'}</div>
                </div>
            ))}

            <div>
                <label style={labelStyle}>Entry Node IDs</label>
                <div style={fieldStyle}>
                    {entryNodeIds.length > 0 ? entryNodeIds.join(', ') : '-'}
                </div>
            </div>

            {threadFields.length > 0 && (
                <>
                    <h3
                        className="text-xs font-semibold uppercase tracking-wide pt-2"
                        style={{ color: 'var(--text-muted)' }}
                    >
                        Thread Ownership
                    </h3>
                    {threadFields.map(([nodeId, owner]) => (
                        <div key={nodeId}>
                            <label style={labelStyle}>{nodeId}</label>
                            <div style={fieldStyle}>{owner}</div>
                        </div>
                    ))}
                </>
            )}
        </div>
    );
}
