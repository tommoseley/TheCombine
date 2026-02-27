/**
 * Interface block renderer
 * Displays an API interface with endpoints, auth, and consumer/producer info
 */
export default function InterfaceBlock({ block }) {
    const { data } = block;
    if (!data || !data.name) return null;

    const endpoints = Array.isArray(data.endpoints) ? data.endpoints : [];

    const methodColors = {
        GET: { bg: '#d1fae5', color: '#065f46' },
        POST: { bg: '#dbeafe', color: '#1e40af' },
        PUT: { bg: '#fef3c7', color: '#92400e' },
        PATCH: { bg: '#fef3c7', color: '#92400e' },
        DELETE: { bg: '#fee2e2', color: '#991b1b' },
    };

    return (
        <div
            style={{
                marginBottom: 12,
                padding: '14px 16px',
                background: 'var(--bg-panel)',
                borderRadius: 8,
                border: '1px solid var(--border-node)',
            }}
        >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                <h4 style={{ margin: 0, fontSize: 15, fontWeight: 600, color: '#1e293b' }}>
                    {data.name}
                </h4>
                {data.type && (
                    <span style={{ fontSize: 11, padding: '2px 8px', background: '#f0fdf4', color: '#166534', borderRadius: 4 }}>
                        {data.type}
                    </span>
                )}
                {data.protocol && (
                    <span style={{ fontSize: 11, padding: '2px 8px', background: '#eff6ff', color: '#1e40af', borderRadius: 4 }}>
                        {data.protocol}
                    </span>
                )}
            </div>
            {data.description && (
                <p style={{ margin: '0 0 8px', fontSize: 13, color: '#475569' }}>
                    {data.description}
                </p>
            )}
            {(data.authentication || data.authorization) && (
                <div style={{ marginBottom: 8, fontSize: 12, color: 'var(--text-muted)' }}>
                    {data.authentication && <span>Auth: {data.authentication}</span>}
                    {data.authentication && data.authorization && <span> | </span>}
                    {data.authorization && <span>Authz: {data.authorization}</span>}
                </div>
            )}
            {endpoints.length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    {endpoints.map((ep, i) => {
                        const mc = methodColors[ep.method] || { bg: '#f3f4f6', color: 'var(--text-secondary)' };
                        return (
                            <div
                                key={i}
                                style={{
                                    padding: '8px 10px',
                                    background: 'var(--bg-canvas)',
                                    borderRadius: 6,
                                    border: '1px solid var(--border-node)',
                                }}
                            >
                                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                    <span
                                        style={{
                                            fontSize: 11,
                                            fontWeight: 700,
                                            padding: '2px 6px',
                                            borderRadius: 3,
                                            background: mc.bg,
                                            color: mc.color,
                                            fontFamily: 'monospace',
                                        }}
                                    >
                                        {ep.method}
                                    </span>
                                    <code style={{ fontSize: 13, color: '#1e293b' }}>{ep.path}</code>
                                </div>
                                {ep.description && (
                                    <p style={{ margin: '4px 0 0', fontSize: 12, color: 'var(--text-muted)' }}>
                                        {ep.description}
                                    </p>
                                )}
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
