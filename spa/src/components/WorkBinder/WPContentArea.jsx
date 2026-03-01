/**
 * WPContentArea -- Per-WP Content (center panel).
 *
 * Three sub-view tabs: WORK | HISTORY | GOVERNANCE
 * Section header with Binding Block and Provenance Stamp.
 *
 * WS-WB-007.
 */
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

export default function WPContentArea({ wp, projectId, activeSubView, onChangeSubView, onRefresh }) {
    if (!wp) {
        return (
            <div className="wb-content-area">
                <div className="wb-content-empty">
                    <p>Select a work package to view its contents.</p>
                </div>
            </div>
        );
    }

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
