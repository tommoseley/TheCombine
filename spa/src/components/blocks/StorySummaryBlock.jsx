/**
 * Story summary block renderer
 * Displays story card with phase and risk indicators
 */
export default function StorySummaryBlock({ block }) {
    const { data } = block;
    const { story_id, title, intent, phase, risk_level, detail_ref } = data;

    const riskColors = {
        low: { bg: '#d1fae5', text: '#065f46' },
        medium: { bg: '#fef3c7', text: '#92400e' },
        high: { bg: '#fee2e2', text: '#991b1b' },
    };
    const riskColor = riskColors[risk_level] || null;

    const phaseColors = {
        mvp: { bg: '#dbeafe', text: '#1e40af' },
        later: { bg: '#e5e7eb', text: '#374151' },
    };
    const phaseColor = phaseColors[phase] || phaseColors.mvp;

    return (
        <div
            style={{
                padding: '10px 14px',
                background: '#fafafa',
                borderRadius: 6,
                border: '1px solid var(--border-node)',
                marginBottom: 8,
            }}
        >
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 10 }}>
                <div style={{ flex: 1 }}>
                    {/* ID and Title */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                        {story_id && (
                            <span
                                style={{
                                    fontSize: 10,
                                    fontFamily: 'monospace',
                                    color: '#059669',
                                    background: '#ecfdf5',
                                    padding: '1px 5px',
                                    borderRadius: 3,
                                }}
                            >
                                {story_id}
                            </span>
                        )}
                        <span
                            style={{
                                fontSize: 13,
                                fontWeight: 500,
                                color: 'var(--text-primary)',
                            }}
                        >
                            {title}
                        </span>
                    </div>

                    {/* Intent */}
                    {intent && (
                        <p
                            style={{
                                margin: 0,
                                fontSize: 12,
                                color: 'var(--text-muted)',
                                lineHeight: 1.4,
                            }}
                        >
                            {intent}
                        </p>
                    )}
                </div>

                {/* Badges */}
                <div style={{ display: 'flex', gap: 4 }}>
                    {phase && (
                        <span
                            style={{
                                fontSize: 9,
                                padding: '2px 6px',
                                borderRadius: 8,
                                background: phaseColor.bg,
                                color: phaseColor.text,
                                textTransform: 'uppercase',
                                fontWeight: 500,
                            }}
                        >
                            {phase}
                        </span>
                    )}
                    {riskColor && (
                        <span
                            style={{
                                fontSize: 9,
                                padding: '2px 6px',
                                borderRadius: 8,
                                background: riskColor.bg,
                                color: riskColor.text,
                                textTransform: 'uppercase',
                                fontWeight: 500,
                            }}
                        >
                            {risk_level}
                        </span>
                    )}
                </div>
            </div>
        </div>
    );
}
