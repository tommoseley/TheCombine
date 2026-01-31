/**
 * Epic summary block renderer
 * Displays epic card with phase, risk level, and detail link
 */
export default function EpicSummaryBlock({ block }) {
    const { data } = block;
    const { epic_id, title, name, intent, phase, risk_level, stories, detail_ref } = data;

    const displayTitle = title || name;
    const riskColors = {
        low: { bg: '#d1fae5', text: '#065f46' },
        medium: { bg: '#fef3c7', text: '#92400e' },
        high: { bg: '#fee2e2', text: '#991b1b' },
    };
    const riskColor = riskColors[risk_level] || riskColors.medium;

    const phaseColors = {
        mvp: { bg: '#dbeafe', text: '#1e40af' },
        later: { bg: '#e5e7eb', text: '#374151' },
    };
    const phaseColor = phaseColors[phase] || phaseColors.mvp;

    return (
        <div
            style={{
                padding: '14px 16px',
                background: '#ffffff',
                borderRadius: 8,
                border: '1px solid #e2e8f0',
                marginBottom: 12,
                boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
            }}
        >
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 }}>
                <div style={{ flex: 1 }}>
                    {/* ID and Title */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                        {epic_id && (
                            <span
                                style={{
                                    fontSize: 10,
                                    fontFamily: 'monospace',
                                    color: '#6366f1',
                                    background: '#eef2ff',
                                    padding: '2px 6px',
                                    borderRadius: 4,
                                }}
                            >
                                {epic_id}
                            </span>
                        )}
                        <h4
                            style={{
                                margin: 0,
                                fontSize: 14,
                                fontWeight: 600,
                                color: '#111827',
                            }}
                        >
                            {displayTitle}
                        </h4>
                    </div>

                    {/* Intent */}
                    {intent && (
                        <p
                            style={{
                                margin: 0,
                                fontSize: 13,
                                color: '#6b7280',
                                lineHeight: 1.5,
                            }}
                        >
                            {intent}
                        </p>
                    )}

                    {/* Stories count */}
                    {stories && stories.length > 0 && (
                        <div style={{ marginTop: 8, fontSize: 12, color: '#6b7280' }}>
                            {stories.length} stories
                        </div>
                    )}
                </div>

                {/* Badges */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4, alignItems: 'flex-end' }}>
                    {phase && (
                        <span
                            style={{
                                fontSize: 10,
                                padding: '2px 8px',
                                borderRadius: 10,
                                background: phaseColor.bg,
                                color: phaseColor.text,
                                textTransform: 'uppercase',
                                fontWeight: 500,
                            }}
                        >
                            {phase}
                        </span>
                    )}
                    {risk_level && (
                        <span
                            style={{
                                fontSize: 10,
                                padding: '2px 8px',
                                borderRadius: 10,
                                background: riskColor.bg,
                                color: riskColor.text,
                                textTransform: 'uppercase',
                                fontWeight: 500,
                            }}
                        >
                            {risk_level} risk
                        </span>
                    )}
                </div>
            </div>

            {/* Detail link */}
            {detail_ref && (
                <div style={{ marginTop: 10, paddingTop: 10, borderTop: '1px solid #f3f4f6' }}>
                    <a
                        href="#"
                        style={{
                            fontSize: 12,
                            color: '#6366f1',
                            textDecoration: 'none',
                        }}
                    >
                        View epic details &rarr;
                    </a>
                </div>
            )}
        </div>
    );
}
