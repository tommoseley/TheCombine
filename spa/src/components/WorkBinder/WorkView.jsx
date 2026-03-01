/**
 * WorkView -- WORK sub-view.
 *
 * Ordered WS list (each WS as a "sheet").
 * Each sheet: WS ID (monospace), title, state badge, primary action.
 * Ghost row at bottom for creating new WS.
 * Focus Mode: active/editing sheet gets --bg-node background, non-active dim.
 * Reorder with up/down buttons.
 *
 * WS-WB-007.
 */
import { useState, useEffect, useCallback } from 'react';

const STATE_BADGE = {
    DRAFT: { label: 'DRAFT', cssVar: '--state-ready-bg' },
    STABILIZED: { label: 'STABILIZED', cssVar: '--state-stabilized-bg' },
    IN_PROGRESS: { label: 'IN PROGRESS', cssVar: '--state-active-bg' },
    BLOCKED: { label: 'BLOCKED', cssVar: '--state-blocked-bg' },
    COMPLETE: { label: 'COMPLETE', cssVar: '--state-stabilized-bg' },
};

function getStateBadge(state) {
    if (!state) return STATE_BADGE.DRAFT;
    const upper = state.toUpperCase().replace(/ /g, '_');
    return STATE_BADGE[upper] || STATE_BADGE.DRAFT;
}

function formatWsId(ws) {
    return ws.ws_id || ws.code || `WS-${String(ws.sequence || '???').padStart(3, '0')}`;
}

async function fetchWorkStatements(projectId, wpId) {
    try {
        const res = await fetch(`/api/v1/work-binder/wp/${encodeURIComponent(wpId)}/work-statements`);
        if (!res.ok) throw new Error(`${res.status}`);
        const data = await res.json();
        return Array.isArray(data) ? data : (data?.items || []);
    } catch (e) {
        console.warn('WorkView: WS fetch failed:', e.message);
        return [];
    }
}

async function createWorkStatement(wpId, intent) {
    const res = await fetch(`/api/v1/work-binder/wp/${encodeURIComponent(wpId)}/work-statements`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ intent }),
    });
    if (!res.ok) throw new Error(`Failed to create WS: ${res.status}`);
    return res.json();
}

async function stabilizeWorkStatement(wsId) {
    const res = await fetch(`/api/v1/work-binder/work-statements/${encodeURIComponent(wsId)}/stabilize`, {
        method: 'POST',
    });
    if (!res.ok) throw new Error(`Failed to stabilize WS: ${res.status}`);
    return res.json();
}

async function reorderWorkStatements(wpId, wsIds) {
    const res = await fetch(`/api/v1/work-binder/wp/${encodeURIComponent(wpId)}/ws-index`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ws_ids: wsIds }),
    });
    if (!res.ok) throw new Error(`Failed to reorder: ${res.status}`);
    return res.json();
}

function WSSheet({ ws, isFocused, onFocus, onStabilize, onMoveUp, onMoveDown, isFirst, isLast }) {
    const badge = getStateBadge(ws.state);
    const wsId = formatWsId(ws);

    return (
        <div
            className={`wb-ws-sheet ${isFocused ? 'wb-ws-sheet--focused' : ''}`}
            onClick={() => onFocus(ws.id)}
        >
            <div className="wb-ws-sheet-header">
                <span className="wb-mono wb-ws-id">{wsId}</span>
                <span className="wb-ws-title">{ws.title || ws.objective || 'Untitled'}</span>
                <span
                    className="wb-ws-badge"
                    style={{ backgroundColor: `var(${badge.cssVar})` }}
                >
                    {badge.label}
                </span>
            </div>

            {isFocused && (
                <div className="wb-ws-sheet-body">
                    {ws.objective && (
                        <p className="wb-ws-objective">{ws.objective}</p>
                    )}
                    <div className="wb-ws-sheet-actions">
                        {ws.state !== 'STABILIZED' && ws.state !== 'COMPLETE' && (
                            <button
                                className="wb-btn wb-btn--primary wb-btn--sm"
                                onClick={(e) => { e.stopPropagation(); onStabilize(ws.id); }}
                            >
                                STABILIZE STATEMENT
                            </button>
                        )}
                        <div className="wb-ws-reorder">
                            <button
                                className="wb-btn wb-btn--ghost wb-btn--sm"
                                onClick={(e) => { e.stopPropagation(); onMoveUp(ws.id); }}
                                disabled={isFirst}
                                title="Move up"
                            >
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                    <path d="M12 19V5M5 12l7-7 7 7" />
                                </svg>
                            </button>
                            <button
                                className="wb-btn wb-btn--ghost wb-btn--sm"
                                onClick={(e) => { e.stopPropagation(); onMoveDown(ws.id); }}
                                disabled={isLast}
                                title="Move down"
                            >
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                    <path d="M12 5v14M5 12l7 7 7-7" />
                                </svg>
                            </button>
                        </div>
                    </div>
                    {/* Metadata footer */}
                    {ws.provenance && (
                        <div className="wb-ws-provenance">
                            <span className="wb-mono">
                                {ws.provenance.source && `SOURCE: ${ws.provenance.source}`}
                                {ws.provenance.authorization && ` | AUTH: ${ws.provenance.authorization}`}
                            </span>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

function GhostRow({ onSubmit }) {
    const [intent, setIntent] = useState('');
    const [creating, setCreating] = useState(false);

    const handleSubmit = useCallback(async () => {
        if (!intent.trim()) return;
        setCreating(true);
        try {
            await onSubmit(intent.trim());
            setIntent('');
        } finally {
            setCreating(false);
        }
    }, [intent, onSubmit]);

    return (
        <div className="wb-ws-ghost">
            <span className="wb-mono wb-ws-ghost-id">WS-NEW:</span>
            <input
                type="text"
                className="wb-ws-ghost-input"
                placeholder="ENTER INTENT"
                value={intent}
                onChange={(e) => setIntent(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') handleSubmit(); }}
                disabled={creating}
            />
            {intent.trim() && (
                <button
                    className="wb-btn wb-btn--primary wb-btn--sm"
                    onClick={handleSubmit}
                    disabled={creating}
                >
                    {creating ? 'CREATING...' : 'CREATE STATEMENT'}
                </button>
            )}
        </div>
    );
}

export default function WorkView({ wp, projectId, onRefresh }) {
    const [statements, setStatements] = useState([]);
    const [loading, setLoading] = useState(true);
    const [focusedWsId, setFocusedWsId] = useState(null);
    const [error, setError] = useState(null);

    const loadStatements = useCallback(async () => {
        setLoading(true);
        const data = await fetchWorkStatements(projectId, wp.id);
        setStatements(data);
        setLoading(false);
    }, [projectId, wp.id]);

    useEffect(() => { loadStatements(); }, [loadStatements]);

    const handleStabilize = useCallback(async (wsId) => {
        try {
            await stabilizeWorkStatement(wsId);
            await loadStatements();
        } catch (e) {
            setError('Stabilize failed: ' + e.message);
        }
    }, [loadStatements]);

    const handleCreateWs = useCallback(async (intent) => {
        try {
            await createWorkStatement(wp.id, intent);
            await loadStatements();
        } catch (e) {
            setError('Create failed: ' + e.message);
        }
    }, [wp.id, loadStatements]);

    const handleMove = useCallback(async (wsId, direction) => {
        const idx = statements.findIndex(ws => ws.id === wsId);
        if (idx < 0) return;
        const newIdx = direction === 'up' ? idx - 1 : idx + 1;
        if (newIdx < 0 || newIdx >= statements.length) return;
        const newOrder = [...statements];
        [newOrder[idx], newOrder[newIdx]] = [newOrder[newIdx], newOrder[idx]];
        setStatements(newOrder);
        try {
            await reorderWorkStatements(wp.id, newOrder.map(ws => ws.id));
        } catch (e) {
            // Revert on failure
            await loadStatements();
            setError('Reorder failed: ' + e.message);
        }
    }, [statements, wp.id, loadStatements]);

    if (loading) {
        return (
            <div className="wb-work-loading">
                <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>Loading work statements...</p>
            </div>
        );
    }

    return (
        <div className="wb-work-view">
            {error && (
                <div className="wb-error-inline">
                    <span>{error}</span>
                    <button onClick={() => setError(null)}>&times;</button>
                </div>
            )}

            {statements.length === 0 && (
                <div className="wb-work-empty">
                    <p>No work statements yet. Use the ghost row below to create one.</p>
                </div>
            )}

            <div className="wb-ws-list">
                {statements.map((ws, idx) => (
                    <WSSheet
                        key={ws.id}
                        ws={ws}
                        isFocused={focusedWsId === ws.id}
                        onFocus={setFocusedWsId}
                        onStabilize={handleStabilize}
                        onMoveUp={(id) => handleMove(id, 'up')}
                        onMoveDown={(id) => handleMove(id, 'down')}
                        isFirst={idx === 0}
                        isLast={idx === statements.length - 1}
                    />
                ))}
            </div>

            {/* Ghost row for creating new WS */}
            <GhostRow onSubmit={handleCreateWs} />
        </div>
    );
}
