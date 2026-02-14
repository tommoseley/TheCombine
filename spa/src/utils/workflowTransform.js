import dagre from 'dagre';

/**
 * Visual configuration per workflow node type.
 */
export const NODE_TYPE_CONFIG = {
    intake_gate: {
        color: '#f59e0b',
        bgColor: 'rgba(245, 158, 11, 0.15)',
        borderColor: 'rgba(245, 158, 11, 0.5)',
        label: 'Intake Gate',
    },
    task: {
        color: '#3b82f6',
        bgColor: 'rgba(59, 130, 246, 0.15)',
        borderColor: 'rgba(59, 130, 246, 0.5)',
        label: 'Task',
    },
    qa: {
        color: '#8b5cf6',
        bgColor: 'rgba(139, 92, 246, 0.15)',
        borderColor: 'rgba(139, 92, 246, 0.5)',
        label: 'QA',
    },
    pgc: {
        color: '#06b6d4',
        bgColor: 'rgba(6, 182, 212, 0.15)',
        borderColor: 'rgba(6, 182, 212, 0.5)',
        label: 'PGC',
    },
    gate: {
        color: '#f97316',
        bgColor: 'rgba(249, 115, 22, 0.15)',
        borderColor: 'rgba(249, 115, 22, 0.5)',
        label: 'Gate',
    },
    end: {
        color: '#10b981',
        bgColor: 'rgba(16, 185, 129, 0.15)',
        borderColor: 'rgba(16, 185, 129, 0.5)',
        label: 'End',
    },
};

const NEGATIVE_END_CONFIG = {
    color: '#ef4444',
    bgColor: 'rgba(239, 68, 68, 0.15)',
    borderColor: 'rgba(239, 68, 68, 0.5)',
    label: 'End',
};

const NODE_WIDTH = 220;
const NODE_HEIGHT = 110;

/**
 * Convert workflow JSON nodes/edges to React Flow format.
 */
export function workflowToReactFlow(workflowJson) {
    if (!workflowJson || !workflowJson.nodes) {
        return { nodes: [], edges: [] };
    }

    const entryNodeIds = workflowJson.entry_node_ids || [];

    const rfNodes = workflowJson.nodes.map(node => {
        const baseConfig = NODE_TYPE_CONFIG[node.type] || NODE_TYPE_CONFIG.task;
        const isNegativeEnd = node.type === 'end' &&
            ['blocked', 'abandoned'].includes(node.terminal_outcome);
        const config = isNegativeEnd ? NEGATIVE_END_CONFIG : baseConfig;

        return {
            id: node.node_id,
            type: 'workflowNode',
            position: node._position || { x: 0, y: 0 },
            data: {
                ...node,
                config,
                isEntry: entryNodeIds.includes(node.node_id),
            },
        };
    });

    const rfEdges = (workflowJson.edges || []).map(edge => {
        const isNonAdvancing = edge.non_advancing || !edge.to_node_id;
        const hasConditions = edge.conditions && edge.conditions.length > 0;

        let label = edge.label || edge.outcome;
        if (hasConditions) {
            const cond = edge.conditions[0];
            const opSymbol = { eq: '=', ne: '!=', lt: '<', lte: '<=', gt: '>', gte: '>=' }[cond.operator] || cond.operator;
            label = `${label} (${cond.type} ${opSymbol} ${cond.value})`;
        }

        return {
            id: edge.edge_id,
            source: edge.from_node_id,
            target: edge.to_node_id || edge.from_node_id,
            type: 'smoothstep',
            animated: isNonAdvancing,
            label: label,
            data: { ...edge },
            style: {
                stroke: isNonAdvancing ? '#6b7280' : '#64748b',
                strokeWidth: 2,
                strokeDasharray: isNonAdvancing ? '5,5' : undefined,
            },
            labelStyle: {
                fontSize: 10,
                fill: 'var(--text-muted)',
            },
            labelBgStyle: {
                fill: 'var(--bg-panel)',
                fillOpacity: 0.9,
            },
            markerEnd: edge.to_node_id ? { type: 'arrowclosed', color: '#64748b' } : undefined,
        };
    });

    return { nodes: rfNodes, edges: rfEdges };
}

/**
 * Convert React Flow state back to workflow JSON.
 * Merges visual state into the original workflow, preserving non-graph fields.
 */
export function reactFlowToWorkflow(rfNodes, rfEdges, originalWorkflow) {
    const nodes = rfNodes.map(rfNode => {
        const data = { ...rfNode.data };
        // Remove React Flow display-only fields
        delete data.config;
        delete data.isEntry;
        // Store position for layout persistence
        data._position = rfNode.position;
        return data;
    });

    const edges = rfEdges.map(rfEdge => {
        const data = { ...rfEdge.data };
        return data;
    });

    const entryNodeIds = rfNodes
        .filter(n => n.data.isEntry)
        .map(n => n.id);

    return {
        ...originalWorkflow,
        nodes,
        edges,
        entry_node_ids: entryNodeIds.length > 0 ? entryNodeIds : originalWorkflow.entry_node_ids,
    };
}

/**
 * Apply dagre auto-layout to React Flow nodes.
 * @param {Array} nodes - React Flow nodes
 * @param {Array} edges - React Flow edges
 * @param {string} direction - Layout direction ('TB' or 'LR')
 * @param {number} nodeWidth - Node width for layout (default: NODE_WIDTH)
 * @param {number} nodeHeight - Node height for layout (default: NODE_HEIGHT)
 */
export function applyDagreLayout(nodes, edges, direction = 'TB', nodeWidth = NODE_WIDTH, nodeHeight = NODE_HEIGHT) {
    const g = new dagre.graphlib.Graph();
    g.setDefaultEdgeLabel(() => ({}));
    g.setGraph({
        rankdir: direction,
        nodesep: 60,
        ranksep: 80,
        marginx: 40,
        marginy: 40,
    });

    nodes.forEach(node => {
        g.setNode(node.id, { width: nodeWidth, height: nodeHeight });
    });

    edges.forEach(edge => {
        if (edge.target !== edge.source) {
            g.setEdge(edge.source, edge.target);
        }
    });

    dagre.layout(g);

    return nodes.map(node => {
        const pos = g.node(node.id);
        if (!pos) return node;
        return {
            ...node,
            position: {
                x: pos.x - nodeWidth / 2,
                y: pos.y - nodeHeight / 2,
            },
        };
    });
}

/**
 * Generate a unique node ID.
 */
export function generateNodeId(type, existingNodes) {
    const existingIds = new Set(existingNodes.map(n => n.id || n.node_id));
    let counter = 1;
    let id = `${type}_${counter}`;
    while (existingIds.has(id)) {
        counter++;
        id = `${type}_${counter}`;
    }
    return id;
}

/**
 * Generate a unique edge ID.
 */
export function generateEdgeId(fromId, toId, existingEdges) {
    const existingIds = new Set(existingEdges.map(e => e.id || e.edge_id));
    let counter = 1;
    let id = `${fromId}_to_${toId}`;
    while (existingIds.has(id)) {
        counter++;
        id = `${fromId}_to_${toId}_${counter}`;
    }
    return id;
}

/**
 * Create a default node for a given type.
 */
export function createDefaultNode(type, position = { x: 100, y: 100 }) {
    const id = type + '_new';
    const node = {
        node_id: id,
        type,
        description: '',
    };

    if (type === 'end') {
        node.terminal_outcome = 'stabilized';
    }
    if (type === 'task' || type === 'pgc') {
        node.task_ref = '';
        node.includes = {};
    }
    if (type === 'qa') {
        node.requires_qa = true;
        node.qa_mode = 'semantic';
    }

    return node;
}
