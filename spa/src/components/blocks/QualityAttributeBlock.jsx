/**
 * Quality Attribute block renderer
 * Displays a quality attribute with name, target, rationale, and acceptance criteria
 */
export default function QualityAttributeBlock({ block }) {
    const { data } = block;
    if (!data || !data.name) return null;

    const criteria = Array.isArray(data.acceptance_criteria) ? data.acceptance_criteria : [];

    return (
        <div
            style={{
                marginBottom: 12,
                padding: '14px 16px',
                background: '#f8fafc',
                borderRadius: 8,
                border: '1px solid #e2e8f0',
            }}
        >
            <h4 style={{ margin: '0 0 4px', fontSize: 15, fontWeight: 600, color: '#1e293b' }}>
                {data.name}
            </h4>
            {data.target && (
                <p style={{ margin: '0 0 6px', fontSize: 13, color: '#475569' }}>
                    {data.target}
                </p>
            )}
            {data.rationale && (
                <p style={{ margin: '0 0 8px', fontSize: 12, color: '#6b7280', fontStyle: 'italic' }}>
                    {data.rationale}
                </p>
            )}
            {criteria.length > 0 && (
                <div>
                    <div style={{ fontSize: 11, fontWeight: 600, color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 4 }}>
                        Acceptance Criteria
                    </div>
                    <ul style={{ margin: 0, paddingLeft: 18 }}>
                        {criteria.map((c, i) => (
                            <li key={i} style={{ fontSize: 13, color: '#374151', lineHeight: 1.5 }}>{c}</li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    );
}
