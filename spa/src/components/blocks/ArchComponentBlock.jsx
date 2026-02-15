/**
 * Architecture Component block renderer
 * Displays a component with name, purpose, technology, interfaces, and dependencies
 * Handles multiple data shapes from different LLM outputs
 */
export default function ArchComponentBlock({ block }) {
    const { data } = block;
    if (!data || !data.name) return null;

    // Normalize fields across different data shapes
    const technology = data.technology
        || (Array.isArray(data.technology_choices) ? data.technology_choices.join(', ') : null);
    const interfaces = data.interfaces || [];
    const dependencies = data.dependencies || data.depends_on_components || [];
    const responsibilities = data.responsibilities || [];
    const layer = data.layer;
    const mvpPhase = data.mvp_phase;

    const labelStyle = {
        fontSize: 11,
        fontWeight: 600,
        color: '#6b7280',
        textTransform: 'uppercase',
        letterSpacing: '0.04em',
        marginBottom: 2,
    };

    const valueStyle = {
        fontSize: 13,
        color: '#374151',
        lineHeight: 1.5,
        margin: 0,
    };

    const chipStyle = (bg, color) => ({
        fontSize: 12,
        padding: '2px 8px',
        background: bg,
        color: color,
        borderRadius: 4,
    });

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
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                <h4 style={{ margin: 0, fontSize: 15, fontWeight: 600, color: '#1e293b' }}>
                    {data.name}
                </h4>
                {layer && (
                    <span style={chipStyle('#f0fdf4', '#166534')}>{layer}</span>
                )}
                {mvpPhase && (
                    <span style={chipStyle('#eff6ff', '#1e40af')}>{mvpPhase}</span>
                )}
            </div>
            {data.purpose && (
                <p style={{ ...valueStyle, marginBottom: 10, color: '#475569' }}>
                    {data.purpose}
                </p>
            )}
            {technology && (
                <div style={{ marginBottom: 8 }}>
                    <div style={labelStyle}>Technology</div>
                    <p style={valueStyle}>{technology}</p>
                </div>
            )}
            {Array.isArray(responsibilities) && responsibilities.length > 0 && (
                <div style={{ marginBottom: 8 }}>
                    <div style={labelStyle}>Responsibilities</div>
                    <ul style={{ margin: 0, paddingLeft: 18 }}>
                        {responsibilities.map((r, i) => (
                            <li key={i} style={{ fontSize: 13, color: '#374151', lineHeight: 1.5 }}>{r}</li>
                        ))}
                    </ul>
                </div>
            )}
            {Array.isArray(interfaces) && interfaces.length > 0 && (
                <div style={{ marginBottom: 8 }}>
                    <div style={labelStyle}>Interfaces</div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                        {interfaces.map((iface, i) => (
                            <span key={i} style={chipStyle('#e0e7ff', '#3730a3')}>{iface}</span>
                        ))}
                    </div>
                </div>
            )}
            {Array.isArray(dependencies) && dependencies.length > 0 && (
                <div>
                    <div style={labelStyle}>Dependencies</div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                        {dependencies.map((dep, i) => (
                            <span key={i} style={chipStyle('#fef3c7', '#92400e')}>{dep}</span>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
