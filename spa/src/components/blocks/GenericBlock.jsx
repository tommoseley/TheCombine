/**
 * Generic fallback block renderer
 * Used when no specific component is registered for a block type
 */
export default function GenericBlock({ block }) {
    const { type, data } = block;

    return (
        <div
            style={{
                padding: '12px 16px',
                background: '#f8fafc',
                borderRadius: 6,
                border: '1px solid #e2e8f0',
                marginBottom: 12,
            }}
        >
            <div
                style={{
                    fontSize: 10,
                    color: '#94a3b8',
                    marginBottom: 8,
                    fontFamily: 'monospace',
                }}
            >
                {type}
            </div>
            <pre
                style={{
                    fontSize: 12,
                    color: '#475569',
                    margin: 0,
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                }}
            >
                {JSON.stringify(data, null, 2)}
            </pre>
        </div>
    );
}
