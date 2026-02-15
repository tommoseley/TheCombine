import dagre from 'dagre';
import { Position } from 'reactflow';
import { GRID, getEdgeColor } from './constants';

/**
 * Apply Dagre layout to nodes and edges (L1 spine only)
 */
export const getLayoutedElements = (nodes, edges, savedPositions = null) => {
    const g = new dagre.graphlib.Graph();
    g.setGraph({
        rankdir: 'TB',
        align: 'UL',
        nodesep: 20,
        ranksep: 70,
        marginx: 100,
        marginy: 30,
        ranker: 'longest-path'
    });
    g.setDefaultEdgeLabel(() => ({}));

    nodes.forEach((n) => {
        g.setNode(n.id, { width: n.data.width ?? 280, height: n.data.height ?? 90 });
    });
    edges.forEach((e) => {
        g.setEdge(e.source, e.target);
    });

    dagre.layout(g);

    return {
        nodes: nodes.map((n) => {
            const pos = g.node(n.id);
            const dagrePos = {
                x: pos.x - (n.data.width ?? 280) / 2,
                y: pos.y - (n.data.height ?? 90) / 2
            };
            // Use saved position if available, otherwise Dagre
            const saved = savedPositions?.[n.id];
            return {
                ...n,
                targetPosition: Position.Top,
                sourcePosition: Position.Bottom,
                position: saved || dagrePos
            };
        }),
        edges
    };
};

/**
 * Build React Flow graph from document data
 */
export const buildGraph = (data, expandedId, callbacks) => {
    let nodes = [];
    let edges = [];
    let prevId = null;
    let epicBacklogId = null;
    let epicChildren = [];
    const theme = callbacks.theme || 'industrial';

    data.forEach((item, idx) => {
        if ((item.level || 1) !== 1) return;

        const width = 280;
        let height = 95;
        if (item.stations?.length > 0) height += 35;

        const isExpanded = expandedId === item.id;

        nodes.push({
            id: item.id,
            type: 'documentNode',
            data: { ...item, width, height, isExpanded, ...callbacks },
            connectable: false,
            position: { x: 0, y: 0 },
            zIndex: isExpanded ? 1000 : 0
        });

        if (prevId) {
            const prevState = data[idx - 1]?.state;
            edges.push({
                id: 'e-' + prevId + '-' + item.id,
                source: prevId,
                target: item.id,
                type: 'smoothstep',
                animated: prevState === 'active',
                style: { stroke: getEdgeColor(prevState, theme), strokeWidth: 3 }
            });
        }

        if (item.children?.length > 0) {
            epicBacklogId = item.id;
            epicChildren = item.children;
        }

        prevId = item.id;
    });

    return { nodes, edges, epicBacklogId, epicChildren };
};

/**
 * Add L2 epic nodes to the layout with manifold routing
 */
export const addEpicsToLayout = (layoutResult, epicBacklogId, epicChildren, expandedId, callbacks) => {
    const { nodes, edges } = layoutResult;
    if (!epicBacklogId || !epicChildren.length) return { nodes, edges };

    const backlogNode = nodes.find(n => n.id === epicBacklogId);
    if (!backlogNode) return { nodes, edges };

    const backlogX = backlogNode.position.x;
    const backlogY = backlogNode.position.y + (backlogNode.data.height || 95);
    const backlogState = backlogNode.data.state;
    const theme = callbacks.theme || 'industrial';
    const edgeColor = getEdgeColor(backlogState, theme);
    const isAnimated = backlogState === 'active';

    const ROW_HEIGHT = GRID.EPIC_HEIGHT + GRID.EPIC_GAP_Y;
    const numRows = Math.ceil(epicChildren.length / GRID.EPICS_PER_ROW);

    // Spine X position (15% from left of backlog node)
    const SPINE_X = backlogX + 280 * 0.15;
    const JUNCTION_OFFSET_Y = 50;

    // Group epics by row
    const epicsByRow = {};
    epicChildren.forEach((epic, idx) => {
        const row = Math.floor(idx / GRID.EPICS_PER_ROW);
        if (!epicsByRow[row]) epicsByRow[row] = [];
        epicsByRow[row].push({ epic, idx });
    });

    // Create junction waypoints and edges for each row
    for (let row = 0; row < numRows; row++) {
        const rowEpics = epicsByRow[row] || [];
        if (rowEpics.length === 0) continue;

        const rowY = backlogY + GRID.EPIC_OFFSET_Y + row * ROW_HEIGHT;
        const junctionId = `junction-row-${row}`;

        // Add invisible junction waypoint
        nodes.push({
            id: junctionId,
            type: 'waypoint',
            position: { x: SPINE_X, y: rowY - JUNCTION_OFFSET_Y },
            draggable: false,
            connectable: false,
            selectable: false
        });

        // Edge from backlog (row 0) or previous junction to this junction
        if (row === 0) {
            edges.push({
                id: `e-spine-drop-${row}`,
                source: epicBacklogId,
                target: junctionId,
                type: 'straight',
                animated: isAnimated,
                style: { stroke: edgeColor, strokeWidth: 2 }
            });
        } else {
            edges.push({
                id: `e-spine-${row - 1}-to-${row}`,
                source: `junction-row-${row - 1}`,
                target: junctionId,
                type: 'straight',
                animated: isAnimated,
                style: { stroke: edgeColor, strokeWidth: 2 }
            });
        }

        // Add epic nodes and edges from junction to each epic
        rowEpics.forEach(({ epic, idx }) => {
            const col = idx % GRID.EPICS_PER_ROW;
            const x = backlogX + GRID.EPIC_OFFSET_X + col * (GRID.EPIC_WIDTH + GRID.EPIC_GAP_X);
            const y = rowY;
            const isExpanded = expandedId === epic.id;

            nodes.push({
                id: epic.id,
                type: 'documentNode',
                data: { ...epic, width: GRID.EPIC_WIDTH, height: GRID.EPIC_HEIGHT, isExpanded, ...callbacks },
                draggable: false,
                connectable: false,
                position: { x, y },
                targetPosition: Position.Top,
                sourcePosition: Position.Bottom,
                zIndex: isExpanded ? 1000 : 0
            });

            // Edge from junction to epic (manifold branch)
            edges.push({
                id: `e-branch-${epic.id}`,
                source: junctionId,
                target: epic.id,
                type: 'smoothstep',
                pathOptions: { borderRadius: 20 },
                animated: isAnimated,
                style: { stroke: edgeColor, strokeWidth: 2 }
            });
        });
    }

    return { nodes, edges };
};
