// utils/layout.js
// Dagre layout and grid positioning logic

import { GRID_CONFIG, getColors } from '../data/constants.js';

const { EPICS_PER_ROW, EPIC_WIDTH, EPIC_HEIGHT, EPIC_GAP_X, EPIC_GAP_Y, EPIC_OFFSET_X, EPIC_OFFSET_Y } = GRID_CONFIG;

/**
 * Apply Dagre layout to L1 spine nodes
 */
export const getLayoutedElements = (nodes, edges, Position) => {
    const g = new dagre.graphlib.Graph();
    g.setGraph({ rankdir: 'TB', align: 'UL', nodesep: 20, ranksep: 70, marginx: 100, marginy: 30, ranker: 'longest-path' });
    g.setDefaultEdgeLabel(() => ({}));

    nodes.forEach((n) => {
        g.setNode(n.id, { width: n.data.width ?? 280, height: n.data.height ?? 90 });
    });
    edges.forEach((e) => g.setEdge(e.source, e.target));

    dagre.layout(g);

    return {
        nodes: nodes.map((n) => {
            const pos = g.node(n.id);
            return {
                ...n,
                targetPosition: Position.Top,
                sourcePosition: Position.Bottom,
                position: {
                    x: pos.x - (n.data.width ?? 280) / 2,
                    y: pos.y - (n.data.height ?? 90) / 2
                }
            };
        }),
        edges
    };
};

/**
 * Build React Flow graph from hierarchical data (L1 nodes only for Dagre)
 */
export const buildGraph = (data, expandedId, callbacks, Position) => {
    let nodes = [], edges = [], prevId = null;
    let epicBacklogId = null;
    let epicChildren = [];
    
    data.forEach((item, idx) => {
        const level = item.level || 1;
        if (level !== 1) return;
        
        const width = 280;
        let height = 95;
        if (item.state === 'active' && item.stations) height += 35;

        const isExpanded = expandedId === item.id;

        nodes.push({
            id: item.id, 
            type: 'documentNode',
            data: { ...item, width, height, isExpanded, ...callbacks },
            draggable: false, 
            connectable: false, 
            position: { x: 0, y: 0 },
            zIndex: isExpanded ? 1000 : 0
        });

        if (prevId) {
            const prevState = data[idx-1]?.state;
            edges.push({
                id: 'e-'+prevId+'-'+item.id,
                source: prevId,
                target: item.id,
                type: 'smoothstep',
                animated: prevState === 'active',
                style: { stroke: getColors(prevState).edge, strokeWidth: 3 }
            });
        }

        if (item.children && item.children.length > 0) {
            epicBacklogId = item.id;
            epicChildren = item.children;
        }
        
        prevId = item.id;
    });
    
    return { nodes, edges, epicBacklogId, epicChildren };
};

/**
 * Position L2 epics in grid with smoothstep edges
 */
export const addEpicsToLayout = (layoutResult, epicBacklogId, epicChildren, expandedId, callbacks, Position) => {
    const { nodes, edges } = layoutResult;
    
    if (!epicBacklogId || !epicChildren.length) return { nodes, edges };
    
    const backlogNode = nodes.find(n => n.id === epicBacklogId);
    if (!backlogNode) return { nodes, edges };
    
    const backlogX = backlogNode.position.x;
    const backlogY = backlogNode.position.y + (backlogNode.data.height || 95);
    const backlogState = backlogNode.data.state;
    const edgeColor = getColors(backlogState).edge;
    const isAnimated = backlogState === 'active';
    
    const ROW_HEIGHT = EPIC_HEIGHT + EPIC_GAP_Y;
    
    epicChildren.forEach((epic, idx) => {
        const row = Math.floor(idx / EPICS_PER_ROW);
        const col = idx % EPICS_PER_ROW;
        
        const x = backlogX + EPIC_OFFSET_X + col * (EPIC_WIDTH + EPIC_GAP_X);
        const y = backlogY + EPIC_OFFSET_Y + row * ROW_HEIGHT;
        
        const isExpanded = expandedId === epic.id;
        
        nodes.push({
            id: epic.id,
            type: 'documentNode',
            data: { ...epic, width: EPIC_WIDTH, height: EPIC_HEIGHT, isExpanded, ...callbacks },
            draggable: false,
            connectable: false,
            position: { x, y },
            targetPosition: Position.Top,
            sourcePosition: Position.Bottom,
            zIndex: isExpanded ? 1000 : 0
        });
        
        edges.push({
            id: 'e-' + epicBacklogId + '-' + epic.id,
            source: epicBacklogId,
            target: epic.id,
            type: 'smoothstep',
            pathOptions: { borderRadius: 20 },
            animated: isAnimated,
            style: { stroke: edgeColor, strokeWidth: 2 }
        });
    });
    
    return { nodes, edges };
};