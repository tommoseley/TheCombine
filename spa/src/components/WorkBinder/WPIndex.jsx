/**
 * WPIndex -- Vertical Work Package Index (left panel).
 *
 * Lists candidates (from IP) above governed WPs.
 * "INSERT PACKAGE" button at bottom opens inline form (not a modal).
 *
 * WS-WB-007, WS-WB-009.
 */
import { useState, useCallback } from 'react';

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
    wps, selectedWpId, onSelectWp, onInsertPackage,
    candidates = [], selectedCandidateId, onSelectCandidate,
    importAvailable = false, onImportCandidates,
}) {
    const [showInsertForm, setShowInsertForm] = useState(false);
    const [newTitle, setNewTitle] = useState('');
    const [inserting, setInserting] = useState(false);
    const [importing, setImporting] = useState(false);

    const handleSubmitInsert = useCallback(async () => {
        if (!newTitle.trim()) return;
        setInserting(true);
        try {
            await onInsertPackage(newTitle.trim());
            setNewTitle('');
            setShowInsertForm(false);
        } finally {
            setInserting(false);
        }
    }, [newTitle, onInsertPackage]);

    const handleKeyDown = useCallback((e) => {
        if (e.key === 'Enter') handleSubmitInsert();
        if (e.key === 'Escape') { setShowInsertForm(false); setNewTitle(''); }
    }, [handleSubmitInsert]);

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
                            <span className="wb-index-count">{candidates.length}</span>
                        )}
                    </div>

                    <div className="wb-index-list">
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

                        {candidates.map((cand) => {
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
                {wps.length === 0 && !showInsertForm && (
                    <div className="wb-index-empty">
                        <p>No work packages yet.</p>
                    </div>
                )}

                {wps.map((wp) => {
                    const isSelected = wp.id === selectedWpId;
                    const stateColor = getStateColor(wp.state);
                    return (
                        <button
                            key={wp.id}
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
                    );
                })}
            </div>

            {/* Insert Package -- inline form, NOT a modal */}
            <div className="wb-index-footer">
                {showInsertForm ? (
                    <div className="wb-insert-form">
                        <input
                            type="text"
                            className="wb-insert-input"
                            placeholder="Package title..."
                            value={newTitle}
                            onChange={(e) => setNewTitle(e.target.value)}
                            onKeyDown={handleKeyDown}
                            autoFocus
                            disabled={inserting}
                        />
                        <div className="wb-insert-actions">
                            <button
                                className="wb-btn wb-btn--primary"
                                onClick={handleSubmitInsert}
                                disabled={inserting || !newTitle.trim()}
                            >
                                {inserting ? 'CREATING...' : 'CREATE PACKAGE'}
                            </button>
                            <button
                                className="wb-btn wb-btn--ghost"
                                onClick={() => { setShowInsertForm(false); setNewTitle(''); }}
                                disabled={inserting}
                            >
                                CANCEL
                            </button>
                        </div>
                    </div>
                ) : (
                    <button
                        className="wb-btn wb-btn--outline wb-insert-btn"
                        onClick={() => setShowInsertForm(true)}
                    >
                        INSERT PACKAGE
                    </button>
                )}
            </div>
        </div>
    );
}
