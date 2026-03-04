/**
 * WorkView -- WORK sub-view.
 *
 * Ordered WS list (each WS as a "sheet").
 * Each sheet: WS ID (monospace), title, state badge, primary action.
 * Expanded: objective, scope, procedure, verification, prohibited, governance.
 * Ghost row at bottom for creating new WS.
 * Focus Mode: active/editing sheet gets --bg-node background, non-active dim.
 * Reorder with up/down buttons.
 *
 * WS-WB-007, IA audit fix (ws.id -> ws.ws_id, full field rendering).
 */
import { useState, useEffect, useCallback } from 'react';

const STATE_BADGE = {
    DRAFT: { label: 'DRAFT', cssVar: '--state-ready-bg' },
    READY: { label: 'READY', cssVar: '--state-stabilized-bg' },
    IN_PROGRESS: { label: 'IN PROGRESS', cssVar: '--state-active-bg' },
    ACCEPTED: { label: 'ACCEPTED', cssVar: '--state-stabilized-bg' },
    REJECTED: { label: 'REJECTED', cssVar: '--state-blocked-bg' },
    BLOCKED: { label: 'BLOCKED', cssVar: '--state-blocked-bg' },
};

function getStateBadge(state) {
    if (!state) return STATE_BADGE.DRAFT;
    const upper = state.toUpperCase().replace(/ /g, '_');
    return STATE_BADGE[upper] || STATE_BADGE.DRAFT;
}

function formatWsId(ws) {
    return ws.ws_id || 'WS-???';
}

async function fetchWorkStatements(projectId, wpId) {
    try {
        const res = await fetch(`/api/v1/work-binder/wp/${encodeURIComponent(wpId)}/work-statements`);
        if (!res.ok) throw new Error(`${res.status}`);
        const data = await res.json();
        return Array.isArray(data) ? data : (data?.work_statements || data?.items || []);
    } catch (e) {
        console.warn('WorkView: WS fetch failed:', e.message);
        return [];
    }
}

async function createWorkStatement(wpId, intent) {
    const res = await fetch(`/api/v1/work-binder/wp/${encodeURIComponent(wpId)}/work-statements`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: intent }),
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

async function reorderWorkStatements(wpId, wsIndexEntries) {
    const res = await fetch(`/api/v1/work-binder/wp/${encodeURIComponent(wpId)}/ws-index`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ws_index: wsIndexEntries }),
    });
    if (!res.ok) throw new Error(`Failed to reorder: ${res.status}`);
    return res.json();
}

/**
 * Renders a labeled list section if items exist.
 */
function WSListSection({ label, items }) {
    if (!items || items.length === 0) return null;
    return (
        <div className="wb-ws-section">
            <div className="wb-ws-section-label">{label}</div>
            <ul className="wb-ws-section-list">
                {items.map((item, i) => <li key={i}>{item}</li>)}
            </ul>
        </div>
    );
}

function formatWsForClipboard(ws) {
    const lines = [];
    lines.push(`# ${formatWsId(ws)}: ${ws.title || ws.objective || 'Untitled'}`);
    if (ws.state) lines.push(`State: ${ws.state}`);
    if (ws.objective) { lines.push(''); lines.push(`## Objective`); lines.push(ws.objective); }
    const listSection = (heading, items) => {
        if (!items || items.length === 0) return;
        lines.push(''); lines.push(`## ${heading}`);
        items.forEach(item => lines.push(`- ${item}`));
    };
    listSection('Scope', ws.scope_in);
    listSection('Out of Scope', ws.scope_out);
    listSection('Procedure', ws.procedure);
    listSection('Verification Criteria', ws.verification_criteria);
    listSection('Prohibited Actions', ws.prohibited_actions);
    listSection('Allowed Paths', ws.allowed_paths);
    const pins = ws.governance_pins || {};
    if (pins.ta_version_id || (pins.adr_refs && pins.adr_refs.length > 0) || (pins.policy_refs && pins.policy_refs.length > 0)) {
        lines.push(''); lines.push('## Governance Pins');
        if (pins.ta_version_id) lines.push(`- TA: ${pins.ta_version_id}`);
        if (pins.adr_refs && pins.adr_refs.length > 0) lines.push(`- ADR: ${pins.adr_refs.join(', ')}`);
        if (pins.policy_refs && pins.policy_refs.length > 0) lines.push(`- POL: ${pins.policy_refs.join(', ')}`);
    }
    return lines.join('\n');
}

function WSSheet({ ws, isFocused, onFocus, onCopy, onStabilize, onMoveUp, onMoveDown, isFirst, isLast }) {
    const badge = getStateBadge(ws.state);
    const wsId = formatWsId(ws);
    const wsKey = ws.ws_id;

    const pins = ws.governance_pins || {};
    const hasGovPins = pins.ta_version_id || (pins.adr_refs && pins.adr_refs.length > 0) || (pins.policy_refs && pins.policy_refs.length > 0);

    return (
        <div
            className={`wb-ws-sheet ${isFocused ? 'wb-ws-sheet--focused' : ''}`}
            onClick={() => onFocus(wsKey)}
        >
            <div className="wb-ws-sheet-header">
                <span className="wb-mono wb-ws-id">{wsId}</span>
                <span className="wb-ws-title">{ws.title || ws.objective || 'Untitled'}</span>
                <button
                    className="wb-btn wb-btn--ghost wb-btn--sm wb-ws-copy-btn"
                    onClick={(e) => { e.stopPropagation(); onCopy(ws); }}
                    title="Copy to clipboard"
                >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                        <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" />
                    </svg>
                </button>
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

                    <WSListSection label="SCOPE" items={ws.scope_in} />
                    <WSListSection label="OUT OF SCOPE" items={ws.scope_out} />
                    <WSListSection label="PROCEDURE" items={ws.procedure} />
                    <WSListSection label="VERIFICATION CRITERIA" items={ws.verification_criteria} />
                    <WSListSection label="PROHIBITED ACTIONS" items={ws.prohibited_actions} />
                    <WSListSection label="ALLOWED PATHS" items={ws.allowed_paths} />

                    {hasGovPins && (
                        <div className="wb-ws-section">
                            <div className="wb-ws-section-label">GOVERNANCE PINS</div>
                            <div className="wb-ws-gov-pins">
                                {pins.ta_version_id && (
                                    <span className="wb-mono wb-ws-pin">TA: {pins.ta_version_id}</span>
                                )}
                                {pins.adr_refs && pins.adr_refs.length > 0 && (
                                    <span className="wb-mono wb-ws-pin">ADR: {pins.adr_refs.join(', ')}</span>
                                )}
                                {pins.policy_refs && pins.policy_refs.length > 0 && (
                                    <span className="wb-mono wb-ws-pin">POL: {pins.policy_refs.join(', ')}</span>
                                )}
                            </div>
                        </div>
                    )}

                    <div className="wb-ws-sheet-actions">
                        {ws.state === 'DRAFT' && (
                            <button
                                className="wb-btn wb-btn--primary wb-btn--sm"
                                onClick={(e) => { e.stopPropagation(); onStabilize(wsKey); }}
                            >
                                STABILIZE STATEMENT
                            </button>
                        )}
                        <div className="wb-ws-reorder">
                            <button
                                className="wb-btn wb-btn--ghost wb-btn--sm"
                                onClick={(e) => { e.stopPropagation(); onMoveUp(wsKey); }}
                                disabled={isFirst}
                                title="Move up"
                            >
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                    <path d="M12 19V5M5 12l7-7 7 7" />
                                </svg>
                            </button>
                            <button
                                className="wb-btn wb-btn--ghost wb-btn--sm"
                                onClick={(e) => { e.stopPropagation(); onMoveDown(wsKey); }}
                                disabled={isLast}
                                title="Move down"
                            >
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                    <path d="M12 5v14M5 12l7 7 7-7" />
                                </svg>
                            </button>
                        </div>
                    </div>
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

export default function WorkView({ wp, projectId, onRefresh, onProposeStatements }) {
    const [statements, setStatements] = useState([]);
    const [loading, setLoading] = useState(true);
    const [focusedWsId, setFocusedWsId] = useState(null);
    const [error, setError] = useState(null);
    const [proposing, setProposing] = useState(false);

    const wpContentId = wp.wp_id || wp.id;

    const loadStatements = useCallback(async () => {
        setLoading(true);
        const data = await fetchWorkStatements(projectId, wpContentId);
        setStatements(data);
        setLoading(false);
    }, [projectId, wpContentId]);

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
            await createWorkStatement(wpContentId, intent);
            await loadStatements();
        } catch (e) {
            setError('Create failed: ' + e.message);
        }
    }, [wpContentId, loadStatements]);

    const handlePropose = useCallback(async () => {
        if (!onProposeStatements) return;
        setProposing(true);
        setError(null);
        try {
            await onProposeStatements(wpContentId);
            await loadStatements();
        } catch (e) {
            setError('Propose failed: ' + e.message);
        } finally {
            setProposing(false);
        }
    }, [onProposeStatements, wpContentId, loadStatements]);

    const handleCopy = useCallback((ws) => {
        const text = formatWsForClipboard(ws);
        navigator.clipboard.writeText(text).catch(() => {
            console.warn('WorkView: clipboard write failed');
        });
    }, []);

    const handleMove = useCallback(async (wsId, direction) => {
        const idx = statements.findIndex(ws => ws.ws_id === wsId);
        if (idx < 0) return;
        const newIdx = direction === 'up' ? idx - 1 : idx + 1;
        if (newIdx < 0 || newIdx >= statements.length) return;
        const newOrder = [...statements];
        [newOrder[idx], newOrder[newIdx]] = [newOrder[newIdx], newOrder[idx]];
        setStatements(newOrder);
        try {
            await reorderWorkStatements(
                wpContentId,
                newOrder.map(ws => ({ ws_id: ws.ws_id, order_key: ws.order_key || '' })),
            );
        } catch (e) {
            // Revert on failure
            await loadStatements();
            setError('Reorder failed: ' + e.message);
        }
    }, [statements, wpContentId, loadStatements]);

    if (loading) {
        return (
            <div className="wb-work-loading">
                <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>Loading work statements...</p>
            </div>
        );
    }

    const hasContent = wp.rationale || (wp.scope_in && wp.scope_in.length > 0);

    return (
        <div className="wb-work-view">
            {error && (
                <div className="wb-error-inline">
                    <span>{error}</span>
                    <button onClick={() => setError(null)}>&times;</button>
                </div>
            )}

            {/* WP Content Summary */}
            {hasContent && (
                <div className="wb-wp-summary">
                    {wp.rationale && (
                        <div className="wb-wp-summary-section">
                            <div className="wb-wp-summary-label">RATIONALE</div>
                            <p className="wb-wp-summary-text">{wp.rationale}</p>
                        </div>
                    )}
                    {wp.scope_in && wp.scope_in.length > 0 && (
                        <div className="wb-wp-summary-section">
                            <div className="wb-wp-summary-label">SCOPE</div>
                            <ul className="wb-wp-summary-list">
                                {wp.scope_in.map((item, i) => <li key={i}>{item}</li>)}
                            </ul>
                        </div>
                    )}
                    {wp.scope_out && wp.scope_out.length > 0 && (
                        <div className="wb-wp-summary-section">
                            <div className="wb-wp-summary-label">OUT OF SCOPE</div>
                            <ul className="wb-wp-summary-list">
                                {wp.scope_out.map((item, i) => <li key={i}>{item}</li>)}
                            </ul>
                        </div>
                    )}
                    {wp.dependencies && wp.dependencies.length > 0 && (
                        <div className="wb-wp-summary-section">
                            <div className="wb-wp-summary-label">DEPENDENCIES</div>
                            <ul className="wb-wp-summary-list">
                                {wp.dependencies.map((dep, i) => (
                                    <li key={i}>{typeof dep === 'string' ? dep : dep.id || JSON.stringify(dep)}</li>
                                ))}
                            </ul>
                        </div>
                    )}
                    {wp.definition_of_done && wp.definition_of_done.length > 0 && (
                        <div className="wb-wp-summary-section">
                            <div className="wb-wp-summary-label">DEFINITION OF DONE</div>
                            <ul className="wb-wp-summary-list">
                                {wp.definition_of_done.map((item, i) => <li key={i}>{item}</li>)}
                            </ul>
                        </div>
                    )}
                    {wp.source_candidate_ids && wp.source_candidate_ids.length > 0 && (
                        <div className="wb-wp-summary-section">
                            <div className="wb-wp-summary-label">SOURCE LINEAGE</div>
                            <div className="wb-wp-summary-lineage">
                                {wp.source_candidate_ids.map((cid, i) => (
                                    <span key={i} className="wb-mono wb-wp-lineage-id">{cid}</span>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}

            {statements.length === 0 && (
                <div className="wb-work-empty">
                    <p>No work statements yet. Use the ghost row below to create one{onProposeStatements ? ', or propose statements via LLM.' : '.'}</p>
                    {onProposeStatements && (
                        <button
                            className="wb-btn wb-btn--primary"
                            onClick={handlePropose}
                            disabled={proposing}
                        >
                            {proposing ? 'PROPOSING...' : 'PROPOSE STATEMENTS'}
                        </button>
                    )}
                </div>
            )}

            <div className="wb-ws-list">
                {statements.map((ws, idx) => (
                    <WSSheet
                        key={ws.ws_id}
                        ws={ws}
                        isFocused={focusedWsId === ws.ws_id}
                        onFocus={(id) => setFocusedWsId(prev => prev === id ? null : id)}
                        onCopy={handleCopy}
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
