/**
 * Summary block renderer
 * Displays structured summary with multiple sections
 */
export default function SummaryBlock({ block }) {
    const { data } = block;
    const { problem_understanding, architectural_intent, scope_pressure_points } = data;

    const sections = [
        { title: 'Problem Understanding', content: problem_understanding },
        { title: 'Architectural Intent', content: architectural_intent },
        { title: 'Scope Pressure Points', content: scope_pressure_points },
    ].filter(s => s.content);

    if (sections.length === 0) return null;

    return (
        <div style={{ marginBottom: 12 }}>
            {sections.map((section, i) => (
                <div
                    key={i}
                    style={{
                        marginBottom: i < sections.length - 1 ? 16 : 0,
                    }}
                >
                    <h4
                        style={{
                            fontSize: 12,
                            fontWeight: 600,
                            color: '#6b7280',
                            marginBottom: 6,
                            textTransform: 'uppercase',
                            letterSpacing: '0.05em',
                        }}
                    >
                        {section.title}
                    </h4>
                    <div
                        style={{
                            padding: '12px 16px',
                            background: '#f8fafc',
                            borderRadius: 6,
                            borderLeft: '3px solid #6366f1',
                        }}
                    >
                        <p
                            style={{
                                margin: 0,
                                fontSize: 14,
                                lineHeight: 1.6,
                                color: '#374151',
                                whiteSpace: 'pre-line',
                            }}
                        >
                            {section.content}
                        </p>
                    </div>
                </div>
            ))}
        </div>
    );
}
