/**
 * TimelineViewer — git-style project history graph (ADR-067).
 *
 * Renders a vertical graph with:
 * - Main trunk (active lineage path) as the primary lane
 * - Branch lanes for rewind threads that diverged
 * - Dots for document versions, diamonds for rewind events
 * - Curved connections at branch/merge points
 * - Active path highlighted, stale branches dimmed
 *
 * Data: uses parent_document_id to build the actual tree topology,
 * not just chronological grouping.
 */
import { useState, useEffect, useCallback, useMemo } from 'react';
import { api } from '../api/client';

// ============================================================================
// Constants
// ============================================================================

const STAGE_ORDER = [
    'concierge_intake', 'project_discovery', 'implementation_plan',
    'technical_architecture', 'work_package', 'work_package_candidate', 'work_statement',
];

const TYPE_LABELS = {
    concierge_intake: 'CI', project_discovery: 'PD', implementation_plan: 'IP',
    technical_architecture: 'TA', work_package: 'WP',
    work_package_candidate: 'WPC', work_statement: 'WS',
};

const STAGE_COLORS = {
    concierge_intake: '#6366f1', project_discovery: '#8b5cf6',
    implementation_plan: '#ec4899', technical_architecture: '#f59e0b',
    work_package: '#10b981', work_package_candidate: '#14b8a6',
    work_statement: '#06b6d4',
};

// Lane colors: 0=trunk (green), then branches
const LANE_COLORS = [
    '#10b981', '#f59e0b', '#3b82f6', '#ec4899',
    '#8b5cf6', '#06b6d4', '#ef4444', '#84cc16',
];

const LANE_W = 18;       // horizontal space per lane
const ROW_H = 28;        // row height
const NODE_R = 4;        // node radius
const PAD_L = 10;        // left padding

function getLaneColor(lane) { return LANE_COLORS[lane % LANE_COLORS.length]; }

function formatTime(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    return d.toLocaleDateString([], { month: 'short', day: 'numeric' }) + ' ' +
           d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

// ============================================================================
// Graph builder — builds the tree topology and assigns lanes
// ============================================================================

function buildGraphModel(timeline, activeDocIds) {
    if (!timeline.length) return { rows: [], laneCount: 1 };

    const docs = timeline.filter(e => e.type === 'document');
    const events = timeline.filter(e => e.type === 'event');
    const docMap = new Map(docs.map(d => [d.id, d]));

    // ================================================================
    // Step 1: Determine branch assignment for each document
    // ================================================================

    const branchMap = new Map(); // doc id -> lane index
    let nextBranch = 1;
    const eventBranch = new Map(); // event id -> lane index

    // Strategy A: Use rewind events + affected_document_ids when available
    const rewindEvents = events
        .filter(e => e.event_type === 'rewind' && e.affected_document_ids?.length > 0)
        .sort((a, b) => (a.created_at || '').localeCompare(b.created_at || ''));

    if (rewindEvents.length > 0) {
        // Lineage event path: assign affected docs to branch lanes
        for (const evt of rewindEvents) {
            const branch = nextBranch++;
            eventBranch.set(evt.id, branch);
            for (const docId of evt.affected_document_ids) {
                branchMap.set(docId, branch);
            }
        }
    }

    // Strategy B: Fallback — infer branches from stale/version data
    // Group docs by doc_type_id. Within each type, older stale versions
    // form branch lanes. Each "generation" of stale docs is one branch.
    const hasStale = docs.some(d => d.is_stale || (!d.is_latest && d.version > 1));
    const hasRewindData = rewindEvents.length > 0;

    if (!hasRewindData && hasStale) {
        // Group by doc_type_id, sort by version
        const byType = new Map();
        for (const doc of docs) {
            if (!byType.has(doc.doc_type_id)) byType.set(doc.doc_type_id, []);
            byType.get(doc.doc_type_id).push(doc);
        }

        // Find how many generations of stale docs exist
        // Group stale docs by approximate creation time (within 5 min = same generation)
        const staleDocs = docs.filter(d => !d.is_latest);
        if (staleDocs.length > 0) {
            // Sort stale docs by created_at
            staleDocs.sort((a, b) => (a.created_at || '').localeCompare(b.created_at || ''));

            // Cluster into generations: gap > 30 min = new generation
            const generations = [];
            let currentGen = [staleDocs[0]];
            for (let i = 1; i < staleDocs.length; i++) {
                const prev = new Date(staleDocs[i - 1].created_at || 0);
                const cur = new Date(staleDocs[i].created_at || 0);
                const gapMin = (cur - prev) / 60000;
                if (gapMin > 30) {
                    generations.push(currentGen);
                    currentGen = [staleDocs[i]];
                } else {
                    currentGen.push(staleDocs[i]);
                }
            }
            generations.push(currentGen);

            // Each generation gets a branch lane
            for (const gen of generations) {
                const branch = nextBranch++;
                for (const doc of gen) {
                    branchMap.set(doc.id, branch);
                }
            }
        }
    }

    // Assign all remaining docs (active/current) to trunk (lane 0)
    for (const doc of docs) {
        if (!branchMap.has(doc.id)) {
            branchMap.set(doc.id, 0);
        }
    }

    // ================================================================
    // Step 2: Build row entries, sorted newest-first
    // ================================================================

    const allEntries = [
        ...docs.map(d => ({
            ...d,
            sortKey: d.created_at || '',
            lane: branchMap.get(d.id) || 0,
            isActive: d.is_latest || activeDocIds.has(d.id),
        })),
        ...events.map(e => ({
            ...e,
            sortKey: e.created_at || '',
            lane: eventBranch.get(e.id) || 0,
            isActive: false,
        })),
    ];
    allEntries.sort((a, b) => b.sortKey.localeCompare(a.sortKey));

    // ================================================================
    // Step 3: Compute which lanes are alive at each row
    // ================================================================

    const laneFirstRow = new Map();
    const laneLastRow = new Map();
    allEntries.forEach((entry, rowIdx) => {
        const lane = entry.lane;
        if (!laneFirstRow.has(lane)) laneFirstRow.set(lane, rowIdx);
        laneLastRow.set(lane, rowIdx);
    });

    const rows = allEntries.map((entry, rowIdx) => {
        const activeLanes = [];
        for (const [lane, first] of laneFirstRow) {
            const last = laneLastRow.get(lane);
            if (rowIdx >= first && rowIdx <= last) {
                activeLanes.push(lane);
            }
        }

        // Is this the first row of a branch lane? (newest-first, so "first" = top of branch)
        const isBranchStart = entry.lane > 0 && laneFirstRow.get(entry.lane) === rowIdx;
        // Is this the last row of a branch lane? (newest-first, so "last" = bottom/oldest of branch)
        const isBranchEnd = entry.lane > 0 && laneLastRow.get(entry.lane) === rowIdx;

        return {
            id: entry.id,
            type: entry.type,
            eventType: entry.event_type,
            docTypeId: entry.doc_type_id,
            displayId: entry.display_id,
            title: entry.title,
            version: entry.version,
            isLatest: entry.is_latest,
            isStale: entry.is_stale,
            lane: entry.lane,
            isActive: entry.isActive,
            createdAt: entry.created_at,
            rewindToStage: entry.rewind_to_stage,
            reason: entry.reason,
            affectedCount: entry.affected_document_count,
            activeLanes,
            isBranchStart,
            isBranchEnd,
            parentWpId: entry.parent_wp_id || null,
            children: [], // populated below for WP rows
        };
    });

    // ================================================================
    // Step 4: Nest WSs under their owning WP (trunk only)
    // ================================================================

    // Build a map of WP display_id -> WP row for trunk WPs
    const wpRowMap = new Map();
    for (const row of rows) {
        if (row.lane === 0 && row.docTypeId === 'work_package' && row.displayId) {
            wpRowMap.set(row.displayId, row);
        }
    }

    // Move trunk WSs with a parent_wp_id into their WP's children
    const nestedWsIds = new Set();
    for (const row of rows) {
        if (row.lane === 0 && row.docTypeId === 'work_statement' && row.parentWpId) {
            const wp = wpRowMap.get(row.parentWpId);
            if (wp) {
                wp.children.push(row);
                nestedWsIds.add(row.id);
            }
        }
    }

    // Filter out nested WSs from top-level rows
    const finalRows = rows.filter(r => !nestedWsIds.has(r.id));

    return { rows: finalRows, laneCount: nextBranch };
}

// ============================================================================
// SVG Graph Row
// ============================================================================

function GraphNodeSvg({ row, laneCount, isFirstRow, isLastRow }) {
    const isEvent = row.type === 'event';
    const laneX = PAD_L + row.lane * LANE_W;
    const trunkX = PAD_L;
    const color = getLaneColor(row.lane);
    const stageColor = STAGE_COLORS[row.docTypeId] || color;
    const dimmed = !row.isActive && !isEvent;
    const opacity = dimmed ? 0.35 : 1;
    const svgWidth = PAD_L + Math.max(laneCount, 1) * LANE_W + 4;
    const midY = ROW_H / 2;

    return (
        <svg width={svgWidth} height={ROW_H} style={{ flexShrink: 0 }}>
            {/* Vertical lane lines — trimmed at first/last row */}
            {(row.activeLanes || []).map(lane => {
                const x = PAD_L + lane * LANE_W;
                const isThisLane = lane === row.lane;
                const y1 = (isFirstRow && isThisLane) ? midY : 0;
                const y2 = (isLastRow && isThisLane) ? midY : ROW_H;
                return (
                    <line key={lane} x1={x} y1={y1} x2={x} y2={y2}
                        stroke={getLaneColor(lane)}
                        strokeWidth={isThisLane ? 2 : 1.5}
                        opacity={isThisLane ? Math.max(opacity, 0.6) : 0.15}
                    />
                );
            })}

            {row.isBranchStart && row.lane > 0 && (
                <path d={`M ${trunkX} ${0} C ${trunkX} ${midY * 0.8}, ${laneX} ${midY * 0.2}, ${laneX} ${midY}`}
                    fill="none" stroke={color} strokeWidth={2} opacity={0.6} />
            )}
            {row.isBranchEnd && row.lane > 0 && (
                <path d={`M ${laneX} ${midY} C ${laneX} ${midY + ROW_H * 0.4}, ${trunkX} ${midY + ROW_H * 0.1}, ${trunkX} ${ROW_H}`}
                    fill="none" stroke={color} strokeWidth={2} opacity={0.6} />
            )}

            {isEvent ? (
                <g opacity={0.8}>
                    <polygon points={`${laneX},${midY - 5} ${laneX + 5},${midY} ${laneX},${midY + 5} ${laneX - 5},${midY}`}
                        fill={color} />
                </g>
            ) : (
                <g opacity={opacity}>
                    <circle cx={laneX} cy={midY} r={NODE_R}
                        fill={row.isLatest ? stageColor : 'var(--bg-canvas, #0d1117)'}
                        stroke={stageColor} strokeWidth={2} />
                    {row.isLatest && (
                        <circle cx={laneX} cy={midY} r={NODE_R + 3}
                            fill="none" stroke={stageColor} strokeWidth={1} opacity={0.3} />
                    )}
                </g>
            )}
        </svg>
    );
}

function RowLabel({ row }) {
    const isEvent = row.type === 'event';
    const color = getLaneColor(row.lane);
    const stageColor = STAGE_COLORS[row.docTypeId] || color;
    const dimmed = !row.isActive && !isEvent;
    const opacity = dimmed ? 0.35 : 1;

    return (
        <div className="flex-1 flex items-center gap-1.5 min-w-0 pr-2 overflow-hidden" style={{ opacity }}>
            {isEvent ? (
                <>
                    <span className="text-[8px] font-bold uppercase flex-shrink-0" style={{ color }}>
                        {row.eventType === 'rewind' ? `\u21A9 ${row.rewindToStage}` : row.eventType}
                    </span>
                    {row.reason && (
                        <span className="text-[8px] truncate" style={{ color: 'var(--text-muted)' }} title={row.reason}>
                            {row.reason.length > 40 ? row.reason.slice(0, 40) + '\u2026' : row.reason}
                        </span>
                    )}
                </>
            ) : (
                <>
                    <span className="text-[8px] font-mono font-bold flex-shrink-0" style={{ color: stageColor }}>
                        {TYPE_LABELS[row.docTypeId] || '??'}
                    </span>
                    <span className="text-[9px] font-medium truncate" style={{ color: 'var(--text-primary)' }}>
                        {row.displayId || row.docTypeId}
                    </span>
                    <span className="text-[8px] font-mono flex-shrink-0" style={{ color: 'var(--text-muted)' }}>
                        v{row.version}
                    </span>
                    {row.isLatest && (
                        <span className="text-[7px] px-1 rounded-full font-bold flex-shrink-0"
                              style={{ background: '#10b98122', color: '#10b981' }}>CURRENT</span>
                    )}
                    {row.isStale && !row.isLatest && (
                        <span className="text-[7px] px-1 rounded-full font-bold flex-shrink-0"
                              style={{ background: '#ef444422', color: '#ef4444' }}>STALE</span>
                    )}
                </>
            )}
        </div>
    );
}

function GraphRow({ row, laneCount, isFirstRow, isLastRow }) {
    return (
        <div className="flex items-center" style={{ height: ROW_H }}>
            <GraphNodeSvg row={row} laneCount={laneCount} isFirstRow={isFirstRow} isLastRow={isLastRow} />
            <RowLabel row={row} />
        </div>
    );
}

/** WP row with collapsible children (nested WSs) */
function WPGraphRow({ row, laneCount, expanded, onToggle, isFirstRow, isLastRow }) {
    const childCount = row.children?.length || 0;
    const stageColor = STAGE_COLORS[row.docTypeId] || getLaneColor(row.lane);

    return (
        <div>
            <div className="flex items-center" style={{ height: ROW_H, cursor: childCount > 0 ? 'pointer' : 'default' }}
                 onClick={childCount > 0 ? onToggle : undefined}>
                <GraphNodeSvg row={row} laneCount={laneCount} isFirstRow={isFirstRow} isLastRow={isLastRow && !expanded} />
                <div className="flex-1 flex items-center gap-1.5 min-w-0 pr-2 overflow-hidden">
                    {childCount > 0 && (
                        <span className="text-[8px] flex-shrink-0" style={{ color: 'var(--text-muted)' }}>
                            {expanded ? '\u25BC' : '\u25B6'}
                        </span>
                    )}
                    <span className="text-[8px] font-mono font-bold flex-shrink-0" style={{ color: stageColor }}>
                        {TYPE_LABELS[row.docTypeId] || '??'}
                    </span>
                    <span className="text-[9px] font-medium truncate" style={{ color: 'var(--text-primary)' }}>
                        {row.displayId}
                    </span>
                    <span className="text-[8px] font-mono flex-shrink-0" style={{ color: 'var(--text-muted)' }}>
                        v{row.version}
                    </span>
                    {row.isLatest && (
                        <span className="text-[7px] px-1 rounded-full font-bold flex-shrink-0"
                              style={{ background: '#10b98122', color: '#10b981' }}>CURRENT</span>
                    )}
                    {childCount > 0 && (
                        <span className="text-[8px] flex-shrink-0" style={{ color: 'var(--text-muted)' }}>
                            {childCount} WS
                        </span>
                    )}
                </div>
            </div>

            {/* Nested WS children — indented with connecting line */}
            {expanded && row.children.map(child => {
                const wsColor = STAGE_COLORS.work_statement || '#06b6d4';
                return (
                    <div key={child.id} className="flex items-center" style={{ height: ROW_H - 4, paddingLeft: PAD_L + LANE_W * 0.3 }}>
                        {/* Small indent connector */}
                        <svg width={16} height={ROW_H - 4} style={{ flexShrink: 0 }}>
                            <line x1={0} y1={0} x2={0} y2={ROW_H - 4}
                                stroke={stageColor} strokeWidth={1} opacity={0.2} />
                            <line x1={0} y1={(ROW_H - 4) / 2} x2={10} y2={(ROW_H - 4) / 2}
                                stroke={stageColor} strokeWidth={1} opacity={0.2} />
                            <circle cx={12} cy={(ROW_H - 4) / 2} r={2.5}
                                fill={child.isLatest ? wsColor : 'transparent'}
                                stroke={wsColor} strokeWidth={1.5} />
                        </svg>
                        <div className="flex items-center gap-1.5 min-w-0 pr-2 overflow-hidden ml-1">
                            <span className="text-[8px] font-mono font-bold flex-shrink-0" style={{ color: wsColor }}>
                                WS
                            </span>
                            <span className="text-[9px] font-medium truncate" style={{ color: 'var(--text-primary)' }}>
                                {child.displayId}
                            </span>
                            <span className="text-[8px] font-mono flex-shrink-0" style={{ color: 'var(--text-muted)' }}>
                                v{child.version}
                            </span>
                            {child.isLatest && (
                                <span className="text-[7px] px-1 rounded-full font-bold flex-shrink-0"
                                      style={{ background: '#10b98122', color: '#10b981' }}>CURRENT</span>
                            )}
                        </div>
                    </div>
                );
            })}
        </div>
    );
}

// ============================================================================
// Branch Summary Row (collapsed view of a branch)
// ============================================================================

function BranchSummaryRow({ branch, laneCount, expanded, onToggle }) {
    const { lane, docs } = branch;
    const color = getLaneColor(lane);
    const svgWidth = PAD_L + Math.max(laneCount, 1) * LANE_W + 4;
    const midY = ROW_H / 2;
    const trunkX = PAD_L;
    const laneX = PAD_L + lane * LANE_W;

    // Count doc types
    const typeCounts = {};
    for (const d of docs) {
        const label = TYPE_LABELS[d.docTypeId] || d.docTypeId;
        typeCounts[label] = (typeCounts[label] || 0) + 1;
    }
    const summary = Object.entries(typeCounts).map(([k, v]) => `${v} ${k}`).join(', ');
    const oldest = docs.length > 0 ? docs[docs.length - 1] : null;

    return (
        <div
            className="flex items-center cursor-pointer hover:bg-white/5 transition-colors"
            style={{ height: ROW_H + 4 }}
            onClick={onToggle}
        >
            <svg width={svgWidth} height={ROW_H + 4} style={{ flexShrink: 0 }}>
                {/* Trunk line always visible */}
                <line x1={trunkX} y1={0} x2={trunkX} y2={ROW_H + 4}
                      stroke={getLaneColor(0)} strokeWidth={2} opacity={0.6} />

                {/* Branch fork curve from trunk */}
                <path
                    d={`M ${trunkX} ${0} C ${trunkX} ${midY * 0.8}, ${laneX} ${midY * 0.2}, ${laneX} ${midY}`}
                    fill="none" stroke={color} strokeWidth={2} opacity={0.6}
                />
                {/* Branch stub / merge back */}
                <path
                    d={`M ${laneX} ${midY} C ${laneX} ${midY + ROW_H * 0.4}, ${trunkX} ${midY + ROW_H * 0.1}, ${trunkX} ${ROW_H + 4}`}
                    fill="none" stroke={color} strokeWidth={2} opacity={0.6}
                />

                {/* Summary dot */}
                <circle cx={laneX} cy={midY} r={NODE_R + 1}
                        fill={color} opacity={0.6} />
            </svg>

            <div className="flex-1 flex items-center gap-1.5 min-w-0 pr-2" style={{ opacity: 0.6 }}>
                <span className="text-[8px] font-bold flex-shrink-0" style={{ color }}>
                    {expanded ? '\u25BC' : '\u25B6'}
                </span>
                <span className="text-[9px] font-medium" style={{ color }}>
                    {docs.length} stale docs
                </span>
                <span className="text-[8px] truncate" style={{ color: 'var(--text-muted)' }}>
                    {summary}
                </span>
                {oldest && (
                    <span className="text-[8px] flex-shrink-0" style={{ color: 'var(--text-muted)' }}>
                        {formatTime(oldest.createdAt)}
                    </span>
                )}
            </div>
        </div>
    );
}

// ============================================================================
// Main Component
// ============================================================================

export default function TimelineViewer({ projectId, onRestore, onArchive }) {
    const [timeline, setTimeline] = useState([]);
    const [activeDocIds, setActiveDocIds] = useState(new Set());
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [expandedBranches, setExpandedBranches] = useState(new Set());
    const [expandedWPs, setExpandedWPs] = useState(new Set());

    const toggleBranch = useCallback((lane) => {
        setExpandedBranches(prev => {
            const next = new Set(prev);
            if (next.has(lane)) next.delete(lane); else next.add(lane);
            return next;
        });
    }, []);

    const toggleWP = useCallback((wpId) => {
        setExpandedWPs(prev => {
            const next = new Set(prev);
            if (next.has(wpId)) next.delete(wpId); else next.add(wpId);
            return next;
        });
    }, []);

    const fetchTimeline = useCallback(async () => {
        if (!projectId) return;
        setLoading(true);
        setError(null);
        try {
            const data = await api.getProjectTimeline(projectId);
            setTimeline(data.timeline || []);
            setActiveDocIds(new Set(data.active_document_ids || []));
        } catch (err) {
            setError(err.message || 'Failed to load timeline');
        } finally {
            setLoading(false);
        }
    }, [projectId]);

    useEffect(() => { fetchTimeline(); }, [fetchTimeline]);

    const { rows, laneCount } = useMemo(
        () => buildGraphModel(timeline, activeDocIds),
        [timeline, activeDocIds]
    );

    if (loading) {
        return (
            <div className="p-4 text-center text-[11px]" style={{ color: 'var(--text-muted)' }}>
                Loading history...
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-4 text-center text-[11px]" style={{ color: '#ef4444' }}>
                {error}
                <button onClick={fetchTimeline} className="ml-2 underline" style={{ color: 'var(--text-muted)' }}>Retry</button>
            </div>
        );
    }

    const totalDocs = timeline.filter(e => e.type === 'document').length;
    const totalEvents = timeline.filter(e => e.type === 'event').length;

    return (
        <div className="flex flex-col h-full">
            {/* Header */}
            <div className="flex items-center justify-between px-3 py-2 border-b"
                 style={{ borderColor: 'var(--border-node)' }}>
                <span className="text-[10px] font-medium uppercase tracking-wider"
                      style={{ color: 'var(--text-muted)' }}>
                    Project History
                </span>
                <button
                    onClick={fetchTimeline}
                    className="text-[9px] px-1.5 py-0.5 rounded hover:bg-white/10"
                    style={{ color: 'var(--text-muted)' }}
                    title="Refresh"
                >
                    Refresh
                </button>
            </div>

            {/* Legend */}
            {laneCount > 1 && (
                <div className="flex items-center gap-2 px-3 py-1 border-b"
                     style={{ borderColor: 'var(--border-node)' }}>
                    <span className="flex items-center gap-1 text-[8px]" style={{ color: 'var(--text-muted)' }}>
                        <span className="inline-block w-2 h-2 rounded-full" style={{ background: LANE_COLORS[0] }} />
                        active
                    </span>
                    {Array.from({ length: Math.min(laneCount - 1, 3) }, (_, i) => (
                        <span key={i} className="flex items-center gap-1 text-[8px]" style={{ color: 'var(--text-muted)' }}>
                            <span className="inline-block w-2 h-2 rounded-full" style={{ background: LANE_COLORS[i + 1] }} />
                            rewind {i + 1}
                        </span>
                    ))}
                </div>
            )}

            {/* Graph — branches collapsed by default */}
            <div className="flex-1 overflow-y-auto overflow-x-hidden">
                {rows.length === 0 ? (
                    <div className="p-4 text-center text-[11px]" style={{ color: 'var(--text-muted)' }}>
                        No history yet
                    </div>
                ) : (
                    <div className="py-1">
                        {(() => {
                            // Group consecutive non-trunk rows into branch segments
                            const segments = [];
                            let i = 0;
                            while (i < rows.length) {
                                const row = rows[i];
                                if (row.lane === 0) {
                                    // Trunk row — render directly
                                    segments.push({ type: 'row', row });
                                    i++;
                                } else {
                                    // Branch row — collect all consecutive rows on this lane
                                    const lane = row.lane;
                                    const branchRows = [];
                                    while (i < rows.length && rows[i].lane === lane) {
                                        branchRows.push(rows[i]);
                                        i++;
                                    }
                                    segments.push({ type: 'branch', lane, rows: branchRows });
                                }
                            }

                            const segCount = segments.length;
                            return segments.map((seg, idx) => {
                                const isFirst = idx === 0;
                                const isLast = idx === segCount - 1;
                                if (seg.type === 'row') {
                                    // WP with nested children — use expandable WPGraphRow
                                    if (seg.row.docTypeId === 'work_package' && seg.row.children?.length > 0) {
                                        return (
                                            <WPGraphRow
                                                key={seg.row.id}
                                                row={seg.row}
                                                laneCount={Math.max(laneCount, 1)}
                                                expanded={expandedWPs.has(seg.row.displayId)}
                                                onToggle={() => toggleWP(seg.row.displayId)}
                                                isFirstRow={isFirst}
                                                isLastRow={isLast}
                                            />
                                        );
                                    }
                                    return (
                                        <GraphRow
                                            key={seg.row.id}
                                            row={seg.row}
                                            laneCount={Math.max(laneCount, 1)}
                                            isFirstRow={isFirst}
                                            isLastRow={isLast}
                                        />
                                    );
                                }
                                // Branch segment
                                const expanded = expandedBranches.has(seg.lane);
                                return (
                                    <div key={`branch-${seg.lane}-${idx}`}>
                                        <BranchSummaryRow
                                            branch={{ lane: seg.lane, docs: seg.rows }}
                                            laneCount={Math.max(laneCount, 1)}
                                            expanded={expanded}
                                            onToggle={() => toggleBranch(seg.lane)}
                                        />
                                        {expanded && seg.rows.map(row => (
                                            <GraphRow
                                                key={row.id}
                                                row={row}
                                                laneCount={Math.max(laneCount, 1)}
                                            />
                                        ))}
                                    </div>
                                );
                            });
                        })()}
                    </div>
                )}
            </div>

            {/* Footer */}
            <div className="px-3 py-1.5 border-t text-[9px]"
                 style={{ borderColor: 'var(--border-node)', color: 'var(--text-muted)' }}>
                {totalDocs} documents{totalEvents > 0 && ` \u00b7 ${totalEvents} events`}
                {laneCount > 1 && ` \u00b7 ${laneCount} threads`}
            </div>
        </div>
    );
}
