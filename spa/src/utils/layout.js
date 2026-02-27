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
    let parentId = null;
    let childNodes = [];
    const theme = callbacks.theme || 'industrial';

    data.forEach((item, idx) => {
        if ((item.level || 1) !== 1) return;

        const isCompact = !!callbacks.compact;
        const width = 280;
        // Compact: fixed height (all nodes show stations, same size)
        // Full: variable height based on content
        let height = isCompact ? 90 : 95;
        if (!isCompact && item.stations?.length > 0) height += 35;

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
            const targetState = item.state;
            // Edge color: use target state when blocked (red path = spatial truth)
            const edgeState = ['requirements_not_met', 'blocked', 'halted', 'failed'].includes(targetState)
                ? targetState : prevState;
            edges.push({
                id: 'e-' + prevId + '-' + item.id,
                source: prevId,
                target: item.id,
                type: 'smoothstep',
                animated: prevState === 'active',
                style: { stroke: getEdgeColor(edgeState, theme), strokeWidth: 3 }
            });
        }

        if (item.children?.length > 0) {
            parentId = item.id;
            childNodes = item.children;
        }

        prevId = item.id;
    });

    return { nodes, edges, parentId, childNodes };
};

/**
 * Add L2 child nodes (Work Packages) to the layout with manifold routing
 */
export const addChildrenToLayout = (layoutResult, parentId, childNodes, expandedId, callbacks) => {
    const { nodes, edges } = layoutResult;
    if (!parentId || !childNodes.length) return { nodes, edges };

    const parentNode = nodes.find(n => n.id === parentId);
    if (!parentNode) return { nodes, edges };

    const parentX = parentNode.position.x;
    const parentY = parentNode.position.y + (parentNode.data.height || 95);
    const parentState = parentNode.data.state;
    const theme = callbacks.theme || 'industrial';
    const edgeColor = getEdgeColor(parentState, theme);
    const isAnimated = parentState === 'active';

    const ROW_HEIGHT = GRID.WP_HEIGHT + GRID.WP_GAP_Y;
    const numRows = Math.ceil(childNodes.length / GRID.WPS_PER_ROW);

    // Spine X position (15% from left of parent node)
    const SPINE_X = parentX + 280 * 0.15;
    const JUNCTION_OFFSET_Y = 50;

    // Group children by row
    const childrenByRow = {};
    childNodes.forEach((child, idx) => {
        const row = Math.floor(idx / GRID.WPS_PER_ROW);
        if (!childrenByRow[row]) childrenByRow[row] = [];
        childrenByRow[row].push({ child, idx });
    });

    // Create junction waypoints and edges for each row
    for (let row = 0; row < numRows; row++) {
        const rowChildren = childrenByRow[row] || [];
        if (rowChildren.length === 0) continue;

        const rowY = parentY + GRID.WP_OFFSET_Y + row * ROW_HEIGHT;
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

        // Edge from parent (row 0) or previous junction to this junction
        if (row === 0) {
            edges.push({
                id: `e-spine-drop-${row}`,
                source: parentId,
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

        // Add child nodes and edges from junction
        rowChildren.forEach(({ child, idx }) => {
            const col = idx % GRID.WPS_PER_ROW;
            const x = parentX + GRID.WP_OFFSET_X + col * (GRID.WP_WIDTH + GRID.WP_GAP_X);
            const y = rowY;
            const isExpanded = expandedId === child.id;

            nodes.push({
                id: child.id,
                type: 'documentNode',
                data: { ...child, width: GRID.WP_WIDTH, height: GRID.WP_HEIGHT, isExpanded, ...callbacks },
                draggable: false,
                connectable: false,
                position: { x, y },
                targetPosition: Position.Top,
                sourcePosition: Position.Bottom,
                zIndex: isExpanded ? 1000 : 0
            });

            // Edge from junction to child (manifold branch)
            // Use child state when blocked (red branch = spatial truth)
            const childState = child.state;
            const branchBlocked = ['requirements_not_met', 'blocked', 'halted', 'failed'].includes(childState);
            const branchColor = branchBlocked ? getEdgeColor(childState, theme) : edgeColor;

            edges.push({
                id: `e-branch-${child.id}`,
                source: junctionId,
                target: child.id,
                type: 'smoothstep',
                pathOptions: { borderRadius: 20 },
                animated: isAnimated && !branchBlocked,
                style: { stroke: branchColor, strokeWidth: 2 }
            });
        });
    }

    return { nodes, edges };
};
