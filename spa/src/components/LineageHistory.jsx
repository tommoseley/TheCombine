/**
 * LineageHistory — audit/history view for rewind events (ADR-063).
 *
 * WS-REWIND-019: Shows chronological list of rewind and regeneration
 * events for a project. Expandable event details.
 */
import { useState, useEffect } from 'react';
import { api } from '../api/client';

function formatTimestamp(isoString) {
    try {
        const d = new Date(isoString);
        return d.toLocaleString(undefined, {
            month: 'short', day: 'numeric',
            hour: '2-digit', minute: '2-digit',
        });
    } catch {
        return isoString;
    }
}

const EVENT_STYLES = {
    rewind: {
        icon: '↩',
        color: 'var(--state-blocked-text, #d97706)',
        bg: 'var(--state-blocked-bg, #fef3c7)',
        label: 'Rewind',
    },
    regeneration: {
        icon: '↻',
        color: 'var(--state-stabilized-text, #166534)',
        bg: 'var(--state-stabilized-bg, #dcfce7)',
        label: 'Regeneration',
    },
};

function LineageEvent({ event }) {
    const [expanded, setExpanded] = useState(false);
    const style = EVENT_STYLES[event.event_type] || EVENT_STYLES.rewind;

    return (
        <div
            className="border rounded px-3 py-2 cursor-pointer"
            style={{ borderColor: 'var(--border-primary, #e5e7eb)' }}
            onClick={() => setExpanded(!expanded)}
        >
            <div className="flex items-center gap-2">
                <span
                    className="w-5 h-5 rounded-full flex items-center justify-center text-[10px]"
                    style={{ backgroundColor: style.bg, color: style.color }}
                >
                    {style.icon}
                </span>
                <span className="text-[11px] font-medium" style={{ color: 'var(--text-primary)' }}>
                    {style.label} → {event.rewind_to_stage}
                </span>
                <span className="text-[9px] ml-auto" style={{ color: 'var(--text-secondary)' }}>
                    {formatTimestamp(event.created_at)}
                </span>
            </div>

            {expanded && (
                <div className="mt-2 text-[10px] space-y-1 pl-7" style={{ color: 'var(--text-secondary)' }}>
                    <p><strong>Reason:</strong> {event.reason}</p>
                    <p><strong>Actor:</strong> {event.actor}</p>
                    <p><strong>Documents affected:</strong> {event.affected_document_count}</p>
                </div>
            )}
        </div>
    );
}

export default function LineageHistory({ projectId }) {
    const [events, setEvents] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (!projectId) return;
        setLoading(true);
        api.getLineage(projectId)
            .then(data => { setEvents(data); setLoading(false); })
            .catch(err => { setError(err.message); setLoading(false); });
    }, [projectId]);

    if (loading) {
        return (
            <div className="text-[10px] p-3" style={{ color: 'var(--text-secondary)' }}>
                Loading lineage...
            </div>
        );
    }

    if (error) {
        return (
            <div className="text-[10px] p-3" style={{ color: 'var(--state-blocked-text, #dc2626)' }}>
                Error: {error}
            </div>
        );
    }

    if (events.length === 0) {
        return (
            <div className="text-[10px] p-3" style={{ color: 'var(--text-secondary)' }}>
                No rewind events yet.
            </div>
        );
    }

    return (
        <div className="space-y-2 p-3">
            <div className="text-[10px] font-semibold uppercase tracking-wide mb-2"
                 style={{ color: 'var(--text-secondary)' }}>
                Pipeline History
            </div>
            {events.map(event => (
                <LineageEvent key={event.id} event={event} />
            ))}
        </div>
    );
}
