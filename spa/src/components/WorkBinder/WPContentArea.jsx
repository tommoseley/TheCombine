/**
 * WPContentArea -- Per-WP Content (center panel).
 *
 * Three sub-view tabs: WORK | HISTORY | GOVERNANCE
 * Section header with Binding Block and Provenance Stamp.
 * Also renders candidate detail when a WPC is selected (WS-WB-009).
 *
 * WS-WB-007, WS-WB-009.
 */
import { useState } from 'react';
import WorkView from './WorkView';
import HistoryView from './HistoryView';
import GovernanceView from './GovernanceView';

const SUB_VIEWS = ['WORK', 'HISTORY', 'GOVERNANCE'];

function formatWpId(wp) {
    return wp.wp_id || wp.code || `WP-${String(wp.sequence || '???').padStart(3, '0')}`;
}

function BindingBlock({ wp }) {
    const componentId = wp.ta_component_id || wp.binding?.component_id || null;
    return (
        <div className="wb-binding-block">
            <span className="wb-binding-label">TA COMPONENT</span>
            {componentId ? (
                <span className="wb-binding-value wb-mono">{componentId}</span>
            ) : (
                <span className="wb-binding-unbound">Unbound</span>
            )}
        </div>
    );
}

function ProvenanceStamp({ wp }) {
    const source = wp.provenance?.source || wp.source || 'UNKNOWN';
    const auth = wp.provenance?.authorization || wp.authorization || 'UNKNOWN';
    return (
        <div className="wb-provenance">
            <span className="wb-mono wb-provenance-text">
                SOURCE: {source} | AUTH: {auth}
            </span>
        </div>
    );
}

function CandidateDetail({ candidate, onPromote }) {
    const [promoting, setPromoting] = useState(false);

    const handlePromote = async () => {
        setPromoting(true);
        try {
            await onPromote(candidate.wpc_id);
        } finally {
            setPromoting(false);
        }
    };

    return (
        <div className="wb-content-area">
            <div className="wb-content-header">
                <div className="wb-content-header-top">
                    <h3 className="wb-content-title">
                        <span className="wb-mono">{candidate.wpc_id}</span>
                        {candidate.title && <span className="wb-content-title-text">{candidate.title}</span>}
                    </h3>
                </div>
                <div className="wb-content-meta">
                    <div className="wb-provenance">
                        <span className="wb-mono wb-provenance-text">
                            SOURCE: {candidate.source_ip_id ? candidate.source_ip_id.slice(0, 8) : 'IP'}
                            {candidate.frozen_at && ` | FROZEN: ${candidate.frozen_at.split('T')[0]}`}
                        </span>
                    </div>
                </div>
            </div>

            <div className="wb-content-body">
                <div className="wb-candidate-detail">
                    {candidate.rationale && (
                        <div className="wb-candidate-section">
                            <div className="wb-candidate-section-label">RATIONALE</div>
                            <p className="wb-candidate-section-text">{candidate.rationale}</p>
                        </div>
                    )}

                    {candidate.scope_summary?.length > 0 && (
                        <div className="wb-candidate-section">
                            <div className="wb-candidate-section-label">SCOPE</div>
                            <ul className="wb-candidate-scope-list">
                                {candidate.scope_summary.map((item, i) => (
                                    <li key={i}>{item}</li>
                                ))}
                            </ul>
                        </div>
                    )}

                    <div className="wb-candidate-actions">
                        {candidate.promoted ? (
                            <div className="wb-candidate-promoted-msg">
                                This candidate has been promoted to a governed Work Package.
                            </div>
                        ) : (
                            <button
                                className="wb-btn wb-btn--primary"
                                onClick={handlePromote}
                                disabled={promoting}
                            >
                                {promoting ? 'PROMOTING...' : 'PROMOTE CANDIDATE'}
                            </button>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}

export default function WPContentArea({ wp, candidate, projectId, activeSubView, onChangeSubView, onRefresh, onPromote }) {
    // Candidate selected — show candidate detail
    if (candidate) {
        return <CandidateDetail candidate={candidate} onPromote={onPromote} />;
    }

    // No selection
    if (!wp) {
        return (
            <div className="wb-content-area">
                <div className="wb-content-empty">
                    <p>Select a work package or candidate to view its contents.</p>
                </div>
            </div>
        );
    }

    // WP selected — existing sub-view tabs
    return (
        <div className="wb-content-area">
            {/* Section Header */}
            <div className="wb-content-header">
                <div className="wb-content-header-top">
                    <h3 className="wb-content-title">
                        <span className="wb-mono">{formatWpId(wp)}</span>
                        {wp.title && <span className="wb-content-title-text">{wp.title}</span>}
                    </h3>
                </div>
                <div className="wb-content-meta">
                    <BindingBlock wp={wp} />
                    <ProvenanceStamp wp={wp} />
                </div>
            </div>

            {/* Sub-view tabs */}
            <div className="wb-tabs">
                {SUB_VIEWS.map((view) => (
                    <button
                        key={view}
                        className={`wb-tab ${activeSubView === view ? 'wb-tab--active' : ''}`}
                        onClick={() => onChangeSubView(view)}
                    >
                        {view}
                    </button>
                ))}
            </div>

            {/* Active sub-view */}
            <div className="wb-content-body">
                {activeSubView === 'WORK' && (
                    <WorkView
                        wp={wp}
                        projectId={projectId}
                        onRefresh={onRefresh}
                    />
                )}
                {activeSubView === 'HISTORY' && (
                    <HistoryView
                        wp={wp}
                        projectId={projectId}
                    />
                )}
                {activeSubView === 'GOVERNANCE' && (
                    <GovernanceView wp={wp} />
                )}
            </div>
        </div>
    );
}
