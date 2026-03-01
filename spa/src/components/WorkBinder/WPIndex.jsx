/**
 * WPIndex -- Vertical Work Package Index (left panel).
 *
 * Lists WPs as tabs with state sliver on left edge.
 * "INSERT PACKAGE" button at bottom opens inline form (not a modal).
 *
 * WS-WB-007.
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

export default function WPIndex({ wps, selectedWpId, onSelectWp, onInsertPackage }) {
    const [showInsertForm, setShowInsertForm] = useState(false);
    const [newTitle, setNewTitle] = useState('');
    const [inserting, setInserting] = useState(false);

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

    return (
        <div className="wb-index">
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
