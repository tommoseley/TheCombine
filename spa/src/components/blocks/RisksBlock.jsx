/**
 * Risks block renderer
 * Displays a list of risks with severity indicators
 */
export default function RisksBlock({ block }) {
    const { data } = block;
    const items = data.items || [];
    const title = data.title;

    if (items.length === 0) return null;

    const severityColors = {
        low: { bg: '#d1fae5', text: '#065f46', border: '#a7f3d0' },
        medium: { bg: '#fef3c7', text: '#92400e', border: '#fde68a' },
        high: { bg: '#fee2e2', text: '#991b1b', border: '#fecaca' },
        critical: { bg: '#fecaca', text: '#7f1d1d', border: '#f87171' },
    };

    return (
        <div style={{ marginBottom: 12 }}>
            {title && (
                <h4
                    style={{
                        fontSize: 12,
                        fontWeight: 600,
                        color: '#6b7280',
                        marginBottom: 8,
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em',
                    }}
                >
                    {title}
                </h4>
            )}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {items.map((item, i) => {
                    const severity = item.severity || item.impact || item.likelihood || 'medium';
                    const colors = severityColors[severity] || severityColors.medium;

                    return (
                        <div
                            key={item.id || i}
                            style={{
                                padding: '10px 14px',
                                background: colors.bg,
                                borderRadius: 6,
                                border: `1px solid ${colors.border}`,
                            }}
                        >
                            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                                {item.id && (
                                    <span
                                        style={{
                                            fontSize: 10,
                                            fontFamily: 'monospace',
                                            color: colors.text,
                                            background: 'rgba(255,255,255,0.5)',
                                            padding: '2px 6px',
                                            borderRadius: 4,
                                            flexShrink: 0,
                                        }}
                                    >
                                        {item.id}
                                    </span>
                                )}
                                <div style={{ flex: 1 }}>
                                    <p
                                        style={{
                                            margin: 0,
                                            fontSize: 13,
                                            color: colors.text,
                                            fontWeight: 500,
                                        }}
                                    >
                                        {item.risk || item.description || item.reason || JSON.stringify(item)}
                                    </p>
                                    {item.impact && (
                                        <p
                                            style={{
                                                margin: '4px 0 0',
                                                fontSize: 12,
                                                color: colors.text,
                                                opacity: 0.8,
                                            }}
                                        >
                                            Impact: {item.impact}
                                        </p>
                                    )}
                                    {(item.impact_on_planning) && (
                                        <p
                                            style={{
                                                margin: '4px 0 0',
                                                fontSize: 12,
                                                color: colors.text,
                                                opacity: 0.8,
                                            }}
                                        >
                                            Planning impact: {item.impact_on_planning}
                                        </p>
                                    )}
                                    {(item.mitigation || item.mitigation_direction) && (
                                        <p
                                            style={{
                                                margin: '4px 0 0',
                                                fontSize: 12,
                                                color: colors.text,
                                                opacity: 0.8,
                                            }}
                                        >
                                            Mitigation: {item.mitigation || item.mitigation_direction}
                                        </p>
                                    )}
                                    {item.status && (
                                        <p
                                            style={{
                                                margin: '4px 0 0',
                                                fontSize: 11,
                                                color: colors.text,
                                                opacity: 0.7,
                                                textTransform: 'capitalize',
                                            }}
                                        >
                                            Status: {item.status}
                                        </p>
                                    )}
                                </div>
                                <span
                                    style={{
                                        fontSize: 10,
                                        padding: '2px 8px',
                                        borderRadius: 10,
                                        background: 'rgba(255,255,255,0.5)',
                                        color: colors.text,
                                        textTransform: 'uppercase',
                                        fontWeight: 600,
                                    }}
                                >
                                    {severity}
                                </span>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
