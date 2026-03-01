/**
 * HistoryView -- HISTORY sub-view.
 *
 * Edition ledger showing: edition number, timestamp, change_summary entries, updated_by.
 *
 * WS-WB-007.
 */
import { useState, useEffect, useCallback } from 'react';

async function fetchHistory(wpId) {
    try {
        const res = await fetch(`/api/v1/work-binder/wp/${encodeURIComponent(wpId)}/history`);
        if (!res.ok) throw new Error(`${res.status}`);
        const data = await res.json();
        return Array.isArray(data) ? data : (data?.editions || []);
    } catch (e) {
        console.warn('HistoryView: fetch failed:', e.message);
        return [];
    }
}

function formatTimestamp(ts) {
    if (!ts) return '--';
    try {
        const d = new Date(ts);
        return d.toLocaleString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        });
    } catch {
        return ts;
    }
}

function EditionRow({ edition }) {
    const entries = edition.change_summary || edition.changes || [];
    return (
        <div className="wb-history-edition">
            <div className="wb-history-edition-header">
                <span className="wb-mono wb-history-edition-num">
                    Edition {edition.edition || edition.version || '?'}
                </span>
                <span className="wb-history-timestamp">
                    {formatTimestamp(edition.timestamp || edition.created_at)}
                </span>
                {edition.updated_by && (
                    <span className="wb-history-author">{edition.updated_by}</span>
                )}
            </div>
            {entries.length > 0 && (
                <ul className="wb-history-changes">
                    {entries.map((entry, idx) => (
                        <li key={idx} className="wb-history-change-item">
                            {typeof entry === 'string' ? entry : entry.description || JSON.stringify(entry)}
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
}

export default function HistoryView({ wp, projectId }) {
    const [editions, setEditions] = useState([]);
    const [loading, setLoading] = useState(true);

    const load = useCallback(async () => {
        setLoading(true);
        const data = await fetchHistory(wp.id);
        setEditions(data);
        setLoading(false);
    }, [wp.id]);

    useEffect(() => { load(); }, [load]);

    if (loading) {
        return (
            <div className="wb-history-loading">
                <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>Loading edition history...</p>
            </div>
        );
    }

    if (editions.length === 0) {
        return (
            <div className="wb-history-empty">
                <p>No edition history available for this work package.</p>
            </div>
        );
    }

    return (
        <div className="wb-history-view">
            {editions.map((edition, idx) => (
                <EditionRow key={edition.id || idx} edition={edition} />
            ))}
        </div>
    );
}
