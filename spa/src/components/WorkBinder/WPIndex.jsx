/**
 * WPIndex -- Vertical Work Package Index (left panel).
 *
 * Lists candidates (from IP) above governed WPs.
 * WS-WB-030: Nested WS summary rows under selected WP.
 *
 * WS-WB-007, WS-WB-009, WS-WB-030.
 */
import { useState, useCallback } from 'react';
import { getStateBadge } from './wsUtils';

const STATE_COLORS = {
    PLANNED: 'var(--state-ready-bg)',
    READY: 'var(--state-stabilized-bg)',
    IN_PROGRESS: 'var(--state-active-bg)',
    DONE: 'var(--state-queued-bg)',
};

function getStateColor(state) {
    if (!state) return STATE_COLORS.PLANNED;
    const upper = state.toUpperCase().replace(/ /g, '_');
    return STATE_COLORS[upper] || STATE_COLORS.PLANNED;
}

function formatWpId(wp) {
    return wp.wp_id || wp.code || `WP-${String(wp.sequence || '???').padStart(3, '0')}`;
}

export default function WPIndex({
    wps, selectedWpId, onSelectWp,
    candidates = [], selectedCandidateId, onSelectCandidate,
    importAvailable = false, onImportCandidates,
    statements = [], selectedWsId, onSelectWs,
    statementsLoading = false,
}) {
    const [importing, setImporting] = useState(false);
    const [showPromoted, setShowPromoted] = useState(false);

    const promotedCount = candidates.filter(c => c.promoted).length;
    const visibleCandidates = showPromoted ? candidates : candidates.filter(c => !c.promoted);

    const handleImport = useCallback(async () => {
        setImporting(true);
        try {
            await onImportCandidates();
        } finally {
            setImporting(false);
        }
    }, [onImportCandidates]);

    const showCandidatesSection = candidates.length > 0 || importAvailable;

    return (
        <div className="wb-index">
            {/* Candidates section (above packages) */}
            {showCandidatesSection && (
                <>
                    <div className="wb-index-header">
                        <span className="wb-index-label">CANDIDATES</span>
                        {candidates.length > 0 && (
                            <span className="wb-index-count">{visibleCandidates.length}/{candidates.length}</span>
                        )}
                        {promotedCount > 0 && (
                            <label className="wb-index-toggle">
                                <input
                                    type="checkbox"
                                    checked={showPromoted}
                                    onChange={(e) => setShowPromoted(e.target.checked)}
                                />
                                <span className="wb-index-toggle-label">ALL</span>
                            </label>
                        )}
                    </div>

                    <div className="wb-index-list wb-index-list--candidates">
                        {candidates.length === 0 && importAvailable && (
                            <div className="wb-index-import">
                                <button
                                    className="wb-btn wb-btn--outline wb-import-btn"
                                    onClick={handleImport}
                                    disabled={importing}
                                >
                                    {importing ? 'IMPORTING...' : 'IMPORT CANDIDATES'}
                                </button>
                            </div>
                        )}

                        {visibleCandidates.map((cand) => {
                            const isSelected = cand.wpc_id === selectedCandidateId;
                            return (
                                <button
                                    key={cand.wpc_id}
                                    className={`wb-index-item wb-index-item--candidate ${isSelected ? 'wb-index-item--selected' : ''} ${cand.promoted ? 'wb-index-item--promoted' : ''}`}
                                    onClick={() => onSelectCandidate(cand.wpc_id)}
                                >
                                    <div
                                        className="wb-index-state-sliver"
                                        style={{ backgroundColor: cand.promoted ? 'var(--text-muted)' : 'var(--state-ready-bg)' }}
                                        title={cand.promoted ? 'PROMOTED' : 'CANDIDATE'}
                                    />
                                    <div className="wb-index-item-content">
                                        <span className="wb-index-item-id">{cand.wpc_id}</span>
                                        <span className="wb-index-item-title">{cand.title || 'Untitled'}</span>
                                    </div>
                                    <span className={`wb-candidate-badge ${cand.promoted ? 'wb-candidate-badge--promoted' : ''}`}>
                                        {cand.promoted ? 'PROMOTED' : 'WPC'}
                                    </span>
                                </button>
                            );
                        })}
                    </div>
                </>
            )}

            {/* Packages section */}
            <div className="wb-index-header">
                <span className="wb-index-label">PACKAGES</span>
                <span className="wb-index-count">{wps.length}</span>
            </div>

            <div className="wb-index-list">
                {wps.length === 0 && (
                    <div className="wb-index-empty">
                        <p>No work packages yet.</p>
                    </div>
                )}

                {wps.map((wp) => {
                    const isSelected = wp.id === selectedWpId;
                    const stateColor = getStateColor(wp.state);
                    return (
                        <div key={wp.id}>
                            <button
                                className={`wb-index-item ${isSelected ? 'wb-index-item--selected' : ''}`}
                                onClick={() => onSelectWp(wp.id)}
                            >
                                <div
                                    className="wb-index-state-sliver"
                                    style={{ backgroundColor: stateColor }}
                                    title={wp.state || 'PLANNED'}
                                />
                                <div className="wb-index-item-content">
                                    <span className="wb-index-item-id">{formatWpId(wp)}</span>
                                    <span className="wb-index-item-title">{wp.title || 'Untitled'}</span>
                                </div>
                            </button>

                            {/* WS-WB-030: Nested WS summary rows under selected WP */}
                            {isSelected && statements.length > 0 && (
                                <div className="wb-index-ws-list">
                                    {statements.map((ws) => {
                                        const badge = getStateBadge(ws.state);
                                        return (
                                            <button
                                                key={ws.ws_id}
                                                className={`wb-index-ws-row ${ws.ws_id === selectedWsId ? 'wb-index-ws-row--selected' : ''}`}
                                                onClick={() => onSelectWs(ws.ws_id)}
                                            >
                                                <span
                                                    className="wb-index-ws-pip"
                                                    style={{ backgroundColor: `var(${badge.cssVar})` }}
                                                    title={badge.label}
                                                />
                                                <span className="wb-index-ws-id wb-mono">{ws.ws_id || 'WS-???'}</span>
                                                <span className="wb-index-ws-title">{ws.title || ws.objective || 'Untitled'}</span>
                                            </button>
                                        );
                                    })}
                                </div>
                            )}
                            {isSelected && statementsLoading && (
                                <div className="wb-index-ws-list">
                                    <span className="wb-index-ws-loading">Loading...</span>
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>

        </div>
    );
}
