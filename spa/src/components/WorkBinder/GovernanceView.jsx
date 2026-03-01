/**
 * GovernanceView -- GOVERNANCE sub-view.
 *
 * Displays governance_pins, transformation metadata, source_candidate_ids with lineage.
 * Mostly read-only.
 *
 * WS-WB-007.
 */

function PinItem({ label, value }) {
    if (!value && value !== 0 && value !== false) return null;
    return (
        <div className="wb-gov-pin">
            <span className="wb-gov-pin-label">{label}</span>
            <span className="wb-gov-pin-value wb-mono">
                {typeof value === 'object' ? JSON.stringify(value) : String(value)}
            </span>
        </div>
    );
}

function Section({ title, children, empty }) {
    return (
        <div className="wb-gov-section">
            <h4 className="wb-gov-section-title">{title}</h4>
            {children || <p className="wb-gov-empty">{empty || 'No data available.'}</p>}
        </div>
    );
}

export default function GovernanceView({ wp }) {
    const pins = wp.governance_pins || wp.governance || {};
    const transformation = wp.transformation || wp.transform_metadata || null;
    const candidates = wp.source_candidate_ids || wp.candidates || [];
    const hasPins = Object.keys(pins).length > 0;

    return (
        <div className="wb-governance-view">
            {/* Governance Pins */}
            <Section title="Governance Pins" empty="No governance pins defined.">
                {hasPins && (
                    <div className="wb-gov-pins-grid">
                        {Object.entries(pins).map(([key, val]) => (
                            <PinItem key={key} label={key} value={val} />
                        ))}
                    </div>
                )}
            </Section>

            {/* Transformation Metadata */}
            <Section title="Transformation" empty="No transformation metadata.">
                {transformation && (
                    <div className="wb-gov-transform">
                        {transformation.type && (
                            <PinItem label="Type" value={transformation.type} />
                        )}
                        {(transformation.transformation || transformation.description) && (
                            <p className="wb-gov-transform-desc">
                                {transformation.transformation || transformation.description}
                            </p>
                        )}
                        {transformation.transformation_notes && (
                            <div className="wb-gov-transform-notes">
                                <span className="wb-gov-pin-label">Notes</span>
                                <p>{transformation.transformation_notes}</p>
                            </div>
                        )}
                    </div>
                )}
            </Section>

            {/* Source Candidate IDs / Lineage */}
            <Section title="Source Lineage" empty="No source candidates linked.">
                {candidates.length > 0 && (
                    <ul className="wb-gov-candidates">
                        {candidates.map((cid, idx) => (
                            <li key={idx} className="wb-gov-candidate wb-mono">
                                {typeof cid === 'string' ? cid : cid.id || JSON.stringify(cid)}
                            </li>
                        ))}
                    </ul>
                )}
            </Section>
        </div>
    );
}
