/**
 * Intake Constraints block renderer
 * Displays explicit and inferred constraints with sub-headers
 */
export default function IntakeConstraintsBlock({ block }) {
    const { data } = block;
    const { explicit = [], inferred = [] } = data;

    const hasExplicit = explicit && explicit.length > 0;
    const hasInferred = inferred && inferred.length > 0;

    if (!hasExplicit && !hasInferred) return null;

    return (
        <div style={{ marginBottom: 12 }}>
            {hasExplicit && (
                <div style={{ marginBottom: hasInferred ? 16 : 0 }}>
                    <h4
                        style={{
                            fontSize: 12,
                            fontWeight: 500,
                            color: '#6b7280',
                            marginBottom: 8,
                            marginTop: 0,
                        }}
                    >
                        Explicit
                    </h4>
                    <ul style={{ margin: 0, paddingLeft: 20, listStyle: 'none' }}>
                        {explicit.map((item, i) => (
                            <li
                                key={i}
                                style={{
                                    display: 'flex',
                                    alignItems: 'flex-start',
                                    gap: 8,
                                    marginBottom: 6,
                                    fontSize: 13,
                                    color: '#374151',
                                }}
                            >
                                <span style={{ color: '#f59e0b' }}>&#128274;</span>
                                <span>{item}</span>
                            </li>
                        ))}
                    </ul>
                </div>
            )}
            {hasInferred && (
                <div>
                    <h4
                        style={{
                            fontSize: 12,
                            fontWeight: 500,
                            color: '#6b7280',
                            marginBottom: 8,
                            marginTop: 0,
                        }}
                    >
                        Inferred
                    </h4>
                    <ul style={{ margin: 0, paddingLeft: 20, listStyle: 'none' }}>
                        {inferred.map((item, i) => (
                            <li
                                key={i}
                                style={{
                                    display: 'flex',
                                    alignItems: 'flex-start',
                                    gap: 8,
                                    marginBottom: 6,
                                    fontSize: 13,
                                    color: '#374151',
                                }}
                            >
                                <span style={{ color: '#3b82f6' }}>&#128161;</span>
                                <span>{item}</span>
                            </li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    );
}
