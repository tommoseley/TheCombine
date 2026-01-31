/**
 * Intake Project Type block renderer
 * Displays category badge with confidence and rationale
 */
export default function IntakeProjectTypeBlock({ block }) {
    const { data } = block;
    const { category, confidence, rationale } = data;

    return (
        <div style={{ marginBottom: 12 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
                <span
                    style={{
                        padding: '4px 12px',
                        borderRadius: 16,
                        fontSize: 13,
                        fontWeight: 500,
                        background: '#ede9fe',
                        color: '#6d28d9',
                    }}
                >
                    {category}
                </span>
                {confidence && (
                    <span style={{ fontSize: 13, color: '#6b7280' }}>
                        Confidence: {confidence}
                    </span>
                )}
            </div>
            {rationale && (
                <p
                    style={{
                        margin: 0,
                        fontSize: 13,
                        color: '#6b7280',
                        lineHeight: 1.5,
                    }}
                >
                    {rationale}
                </p>
            )}
        </div>
    );
}
