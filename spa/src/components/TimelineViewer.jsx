/**
 * TimelineViewer — project history grouped by thread (ADR-067).
 *
 * Groups documents and events into threads:
 * - Initial thread: documents created before any rewind
 * - Rewind threads: documents created between rewind events
 * - Active thread is highlighted
 *
 * Each thread is collapsible with restore/archive actions.
 */
import { useState, useEffect, useCallback, useMemo } from 'react';
import { api } from '../api/client';

const TYPE_ICONS = {
    concierge_intake: 'CI',
    project_discovery: 'PD',
    implementation_plan: 'IP',
    technical_architecture: 'TA',
    work_package: 'WP',
    work_package_candidate: 'WPC',
    work_statement: 'WS',
};

function StatusBadge({ isLatest, isStale }) {
    if (isLatest) return (
        <span className="text-[8px] px-1 py-0.5 rounded-full font-medium"
              style={{ background: '#10b98133', color: '#10b981' }}>
            CURRENT
        </span>
    );
    if (isStale) return (
        <span className="text-[8px] px-1 py-0.5 rounded-full font-medium"
              style={{ background: '#ef444433', color: '#ef4444' }}>
            STALE
        </span>
    );
    return (
        <span className="text-[8px] px-1 py-0.5 rounded-full font-medium"
              style={{ background: '#6b728033', color: '#6b7280' }}>
            OLD
        </span>
    );
}

function formatTime(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    return d.toLocaleDateString() + ' ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

/**
 * Group timeline entries into threads.
 * A thread starts at a rewind/restore event and contains all documents
 * created until the next rewind/restore event.
 */
function groupIntoThreads(timeline) {
    if (!timeline.length) return [];

    const threads = [];
    let currentThread = {
        id: 'initial',
        label: 'Initial Pipeline',
        event: null,
        documents: [],
        isActive: false,
        startTime: null,
    };

    // Sort chronologically
    const sorted = [...timeline].sort((a, b) => (a.created_at || '').localeCompare(b.created_at || ''));

    for (const entry of sorted) {
        if (entry.type === 'event' && (entry.event_type === 'rewind' || entry.event_type === 'restore')) {
            // Close current thread
            threads.push(currentThread);
            // Start new thread
            currentThread = {
                id: entry.id,
                label: entry.event_type === 'rewind'
                    ? `Rewind to ${entry.rewind_to_stage}`
                    : 'Restored checkpoint',
                event: entry,
                documents: [],
                isActive: false,
                startTime: entry.created_at,
            };
        } else if (entry.type === 'document') {
            currentThread.documents.push(entry);
        }
        // archive/regeneration events: attach to current thread but don't start new one
    }
    // Close last thread
    threads.push(currentThread);

    // Active thread is determined by authoritative backend signal (active_document_ids),
    // applied in the component after grouping. No heuristic here.

    return threads;
}

function ThreadHeader({ thread, isExpanded, onToggle, onRestore, onArchive }) {
    const docCount = thread.documents.length;
    const currentCount = thread.documents.filter(d => d.is_latest).length;
    const staleCount = thread.documents.filter(d => d.is_stale).length;

    const borderColor = thread.isActive ? '#10b981' : thread.event?.event_type === 'rewind' ? '#f59e0b' : 'var(--border-node)';

    return (
        <div
            className="flex items-center gap-2 px-3 py-2 cursor-pointer hover:bg-white/5 transition-colors"
            style={{ borderLeft: `3px solid ${borderColor}` }}
            onClick={onToggle}
        >
            {/* Expand/collapse arrow */}
            <svg
                width="10" height="10" viewBox="0 0 24 24" fill="none"
                stroke="var(--text-muted)" strokeWidth="2"
                style={{ transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)', transition: 'transform 0.15s', flexShrink: 0 }}
            >
                <path d="M9 18l6-6-6-6" />
            </svg>

            <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                    <span className="text-[10px] font-medium" style={{ color: thread.isActive ? '#10b981' : 'var(--text-primary)' }}>
                        {thread.label}
                    </span>
                    {thread.isActive && (
                        <span className="text-[8px] px-1 py-0.5 rounded-full font-bold"
                              style={{ background: '#10b98133', color: '#10b981' }}>
                            ACTIVE
                        </span>
                    )}
                </div>
                <div className="text-[9px]" style={{ color: 'var(--text-muted)' }}>
                    {docCount} docs
                    {currentCount > 0 && ` · ${currentCount} current`}
                    {staleCount > 0 && ` · ${staleCount} stale`}
                    {thread.startTime && ` · ${formatTime(thread.startTime)}`}
                </div>
            </div>

            {/* Thread actions */}
            <div className="flex gap-1 flex-shrink-0" onClick={e => e.stopPropagation()}>
                {!thread.isActive && thread.documents.length > 0 && onRestore && (
                    <button
                        className="text-[8px] px-1.5 py-0.5 rounded border transition-colors hover:opacity-80"
                        style={{ color: '#10b981', borderColor: '#10b98144', background: 'transparent' }}
                        onClick={() => {
                            const checkpoint = thread.documents.find(d => !d.is_latest) || thread.documents[0];
                            if (checkpoint) onRestore(checkpoint.id);
                        }}
                        title="Restore this thread as active"
                    >
                        Restore
                    </button>
                )}
                {!thread.isActive && thread.event && onArchive && (
                    <button
                        className="text-[8px] px-1.5 py-0.5 rounded border transition-colors hover:opacity-80"
                        style={{ color: '#6b7280', borderColor: '#6b728044', background: 'transparent' }}
                        onClick={() => onArchive(thread.event.id)}
                        title="Archive this thread"
                    >
                        Archive
                    </button>
                )}
            </div>
        </div>
    );
}

function ThreadDocList({ documents, onRestore }) {
    // Group docs by stage for compact display
    const byStage = {};
    for (const doc of documents) {
        const stage = doc.doc_type_id;
        if (!byStage[stage]) byStage[stage] = [];
        byStage[stage].push(doc);
    }

    const stageOrder = ['concierge_intake', 'project_discovery', 'implementation_plan',
                        'technical_architecture', 'work_package', 'work_package_candidate', 'work_statement'];

    const orderedStages = stageOrder.filter(s => byStage[s]);

    return (
        <div className="pl-6 pr-2 pb-2">
            {orderedStages.map(stage => (
                <div key={stage} className="mb-1">
                    {byStage[stage].map(doc => {
                        const icon = TYPE_ICONS[doc.doc_type_id] || '??';
                        return (
                            <div key={doc.id}
                                 className="flex items-center gap-2 py-1 px-2 rounded hover:bg-white/5 transition-colors text-[10px]">
                                <span className="font-mono font-bold w-6 text-center flex-shrink-0"
                                      style={{ color: 'var(--text-muted)', fontSize: 9 }}>
                                    {icon}
                                </span>
                                <span className="font-medium" style={{ color: 'var(--text-primary)' }}>
                                    {doc.display_id || doc.doc_type_id}
                                </span>
                                <span className="font-mono" style={{ color: 'var(--text-muted)', fontSize: 9 }}>
                                    v{doc.version}
                                </span>
                                <StatusBadge isLatest={doc.is_latest} isStale={doc.is_stale} />
                                <span className="flex-1" />
                                {!doc.is_latest && onRestore && (
                                    <button
                                        className="text-[8px] px-1 py-0.5 rounded border hover:opacity-80"
                                        style={{ color: '#10b981', borderColor: '#10b98144', background: 'transparent' }}
                                        onClick={() => onRestore(doc.id)}
                                        title="Restore from this document"
                                    >
                                        Restore
                                    </button>
                                )}
                            </div>
                        );
                    })}
                </div>
            ))}
        </div>
    );
}

export default function TimelineViewer({ projectId, onRestore, onArchive }) {
    const [timeline, setTimeline] = useState([]);
    const [activeDocIds, setActiveDocIds] = useState(new Set());
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [expandedThreads, setExpandedThreads] = useState(new Set());

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

    const threads = useMemo(() => {
        const grouped = groupIntoThreads(timeline);
        // Override heuristic with authoritative active signal from backend
        if (activeDocIds.size > 0) {
            for (const thread of grouped) {
                thread.isActive = thread.documents.some(d => activeDocIds.has(d.id));
            }
        }
        return grouped;
    }, [timeline, activeDocIds]);

    // Auto-expand active thread
    useEffect(() => {
        const activeThread = threads.find(t => t.isActive);
        if (activeThread) {
            setExpandedThreads(prev => new Set(prev).add(activeThread.id));
        }
    }, [threads]);

    const toggleThread = useCallback((threadId) => {
        setExpandedThreads(prev => {
            const next = new Set(prev);
            if (next.has(threadId)) next.delete(threadId);
            else next.add(threadId);
            return next;
        });
    }, []);

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
                <span className="text-[9px]" style={{ color: 'var(--text-muted)' }}>
                    {threads.length} threads
                </span>
            </div>

            {/* Threads */}
            <div className="flex-1 overflow-y-auto">
                {threads.length === 0 ? (
                    <div className="p-4 text-center text-[11px]" style={{ color: 'var(--text-muted)' }}>
                        No history
                    </div>
                ) : (
                    /* Render newest thread first */
                    [...threads].reverse().map(thread => {
                        const isExpanded = expandedThreads.has(thread.id);
                        return (
                            <div key={thread.id}
                                 className="border-b"
                                 style={{ borderColor: 'var(--border-node)' }}>
                                <ThreadHeader
                                    thread={thread}
                                    isExpanded={isExpanded}
                                    onToggle={() => toggleThread(thread.id)}
                                    onRestore={onRestore}
                                    onArchive={onArchive}
                                />
                                {isExpanded && thread.documents.length > 0 && (
                                    <ThreadDocList
                                        documents={thread.documents}
                                        onRestore={onRestore}
                                    />
                                )}
                            </div>
                        );
                    })
                )}
            </div>

            {/* Footer */}
            <div className="px-3 py-1.5 border-t text-[9px]"
                 style={{ borderColor: 'var(--border-node)', color: 'var(--text-muted)' }}>
                {totalDocs} docs · {totalEvents} events · {threads.length} threads
            </div>
        </div>
    );
}
