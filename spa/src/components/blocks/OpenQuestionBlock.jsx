/**
 * Open question block renderer
 * Displays a single question with priority and blocking indicator
 */
export default function OpenQuestionBlock({ block }) {
    const { data } = block;
    const text = data.text || data.question || data.decision_area;
    const { id, blocking, priority, tags, options } = data;
    const why_it_matters = data.why_it_matters || data.why_early;
    const directed_to = data.directed_to;
    const recommendation = data.recommendation_direction;

    const priorityColors = {
        must: { bg: '#fee2e2', text: '#991b1b' },
        should: { bg: '#fef3c7', text: '#92400e' },
        could: { bg: '#e5e7eb', text: '#374151' },
    };

    const priorityColor = priorityColors[priority] || priorityColors.should;

    return (
        <div
            style={{
                padding: '12px 16px',
                background: blocking ? '#fef2f2' : '#f8fafc',
                borderRadius: 8,
                border: `1px solid ${blocking ? '#fecaca' : '#e2e8f0'}`,
                marginBottom: 12,
            }}
        >
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                {/* Question ID */}
                <span
                    style={{
                        fontSize: 10,
                        fontFamily: 'monospace',
                        color: '#6b7280',
                        background: '#e5e7eb',
                        padding: '2px 6px',
                        borderRadius: 4,
                        flexShrink: 0,
                    }}
                >
                    {id}
                </span>

                <div style={{ flex: 1 }}>
                    {/* Question text */}
                    <p
                        style={{
                            margin: 0,
                            fontSize: 14,
                            fontWeight: 500,
                            color: '#111827',
                            marginBottom: 6,
                        }}
                    >
                        {text}
                    </p>

                    {/* Why it matters */}
                    {why_it_matters && (
                        <p
                            style={{
                                margin: 0,
                                fontSize: 12,
                                color: '#6b7280',
                                fontStyle: 'italic',
                            }}
                        >
                            {why_it_matters}
                        </p>
                    )}

                    {/* Tags and priority */}
                    <div style={{ display: 'flex', gap: 6, marginTop: 8, flexWrap: 'wrap' }}>
                        {blocking && (
                            <span
                                style={{
                                    fontSize: 10,
                                    padding: '2px 8px',
                                    borderRadius: 10,
                                    background: '#fee2e2',
                                    color: '#991b1b',
                                    fontWeight: 600,
                                }}
                            >
                                BLOCKING
                            </span>
                        )}
                        {directed_to && (
                            <span
                                style={{
                                    fontSize: 10,
                                    padding: '2px 8px',
                                    borderRadius: 10,
                                    background: '#e0e7ff',
                                    color: '#3730a3',
                                }}
                            >
                                {directed_to.replace(/_/g, ' ')}
                            </span>
                        )}
                        {priority && (
                            <span
                                style={{
                                    fontSize: 10,
                                    padding: '2px 8px',
                                    borderRadius: 10,
                                    background: priorityColor.bg,
                                    color: priorityColor.text,
                                    textTransform: 'uppercase',
                                }}
                            >
                                {priority}
                            </span>
                        )}
                        {tags?.map((tag, i) => (
                            <span
                                key={i}
                                style={{
                                    fontSize: 10,
                                    padding: '2px 8px',
                                    borderRadius: 10,
                                    background: '#e0e7ff',
                                    color: '#3730a3',
                                }}
                            >
                                {tag}
                            </span>
                        ))}
                    </div>

                    {/* Options if present */}
                    {options && options.length > 0 && (
                        <div style={{ marginTop: 8 }}>
                            <span style={{ fontSize: 11, color: '#6b7280', fontWeight: 500 }}>Options: </span>
                            {options.map((opt, i) => (
                                <span
                                    key={i}
                                    style={{
                                        fontSize: 11,
                                        color: '#374151',
                                        marginLeft: i > 0 ? 8 : 4,
                                    }}
                                >
                                    {opt}
                                </span>
                            ))}
                        </div>
                    )}

                    {/* Recommendation direction */}
                    {recommendation && (
                        <p
                            style={{
                                margin: '4px 0 0',
                                fontSize: 12,
                                color: '#059669',
                            }}
                        >
                            Recommendation: {recommendation}
                        </p>
                    )}
                </div>
            </div>
        </div>
    );
}
