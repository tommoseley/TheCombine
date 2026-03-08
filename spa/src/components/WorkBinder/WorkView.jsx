/**
 * WorkView -- WP Overview + WS summary cards.
 *
 * Shows WP-level content (rationale, scope, DoD, lineage) and a clickable
 * list of WS summary cards. Clicking a card opens WSDetailView via onSelectWs.
 * Ghost row and PROPOSE STATEMENTS remain here (WP-level actions).
 *
 * WS-WB-030: Slimmed from inline-expand WSSheet to summary cards.
 */
import { useState, useCallback } from 'react';
import { getStateBadge, formatWsId } from './wsUtils';

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

export default function WorkView({ wp, statements = [], onSelectWs, onProposeStatements, onCreateWs, onStabilizePackage }) {
    const [proposing, setProposing] = useState(false);
    const [stabilizing, setStabilizing] = useState(false);
    const [error, setError] = useState(null);

    const wpContentId = wp.wp_id || wp.id;

    const handlePropose = useCallback(async () => {
        if (!onProposeStatements) return;
        setProposing(true);
        setError(null);
        try {
            await onProposeStatements(wpContentId);
        } catch (e) {
            setError('Propose failed: ' + e.message);
        } finally {
            setProposing(false);
        }
    }, [onProposeStatements, wpContentId]);

    const handleStabilizePackage = useCallback(async () => {
        if (!onStabilizePackage) return;
        setStabilizing(true);
        setError(null);
        try {
            await onStabilizePackage(wpContentId);
        } catch (e) {
            setError('Stabilize failed: ' + e.message);
        } finally {
            setStabilizing(false);
        }
    }, [onStabilizePackage, wpContentId]);

    const hasDrafts = statements.some(ws => (ws.state || 'DRAFT') === 'DRAFT');
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

            {/* WS summary cards — click to open detail */}
            <div className="wb-ws-list">
                {statements.map((ws) => {
                    const badge = getStateBadge(ws.state);
                    return (
                        <button
                            key={ws.ws_id}
                            className="wb-ws-summary-card"
                            onClick={() => onSelectWs(ws.ws_id)}
                        >
                            <span
                                className="wb-index-ws-pip"
                                style={{ backgroundColor: `var(${badge.cssVar})` }}
                            />
                            <span className="wb-mono wb-ws-id">{formatWsId(ws)}</span>
                            <span className="wb-ws-title">{ws.title || ws.objective || 'Untitled'}</span>
                            <span
                                className="wb-ws-badge"
                                style={{ backgroundColor: `var(${badge.cssVar})` }}
                            >
                                {badge.label}
                            </span>
                        </button>
                    );
                })}
            </div>

            {/* WP-level stabilize: visible when DRAFT WSs exist (WS-WB-040) */}
            {statements.length > 0 && hasDrafts && onStabilizePackage && (
                <div className="wb-wp-stabilize">
                    <button
                        className="wb-btn wb-btn--primary"
                        onClick={handleStabilizePackage}
                        disabled={stabilizing}
                    >
                        {stabilizing ? 'STABILIZING...' : 'STABILIZE PACKAGE'}
                    </button>
                </div>
            )}

            {/* Ghost row for creating new WS */}
            <GhostRow onSubmit={onCreateWs} />
        </div>
    );
}
