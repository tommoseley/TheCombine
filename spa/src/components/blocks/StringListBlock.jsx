/**
 * String list block renderer
 * Displays a list of items with smart field extraction for structured objects.
 */
export default function StringListBlock({ block }) {
    const { data } = block;
    const items = data.items || [];
    const style = data.style || 'bullet'; // bullet, numbered, check

    if (items.length === 0) return null;

    const listStyle = style === 'numbered' ? 'decimal' : 'disc';

    return (
        <div style={{ marginBottom: 12 }}>
            {data.title && (
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
                    {data.title}
                </h4>
            )}
            <ul
                style={{
                    margin: 0,
                    paddingLeft: style === 'check' ? 0 : 20,
                    listStyle: style === 'check' ? 'none' : listStyle,
                }}
            >
                {items.map((item, i) => (
                    <li
                        key={item?.id || i}
                        style={{
                            fontSize: 14,
                            lineHeight: 1.6,
                            color: '#374151',
                            marginBottom: 4,
                            display: style === 'check' ? 'flex' : 'list-item',
                            alignItems: 'flex-start',
                            gap: 8,
                        }}
                    >
                        {style === 'check' && (
                            <span style={{ color: '#10b981' }}>&#10003;</span>
                        )}
                        {typeof item === 'string' ? (
                            item
                        ) : typeof item === 'object' && item !== null ? (
                            <StringListItem item={item} />
                        ) : (
                            String(item)
                        )}
                    </li>
                ))}
            </ul>
        </div>
    );
}

/** Render a structured object item with smart field extraction */
function StringListItem({ item }) {
    // Extract primary text from known field names
    const text = item.value || item.text || item.constraint || item.assumption
        || item.guardrail || item.recommendation || item.question
        || item.description || item.statement || item.name;

    if (!text) {
        // No recognizable text field - show key-value pairs inline
        return (
            <span>
                {Object.entries(item).map(([k, v], i) => (
                    <span key={k}>
                        {i > 0 && ' \u00B7 '}
                        <span style={{ fontWeight: 500 }}>{k}:</span> {typeof v === 'string' ? v : JSON.stringify(v)}
                    </span>
                ))}
            </span>
        );
    }

    return (
        <span>
            {item.id && (
                <span style={{ fontFamily: 'monospace', fontSize: 11, color: '#9ca3af', marginRight: 6 }}>{item.id}</span>
            )}
            {text}
            {item.constraint_type && (
                <span style={{ marginLeft: 6, fontSize: 11, padding: '1px 6px', background: '#f3f4f6', borderRadius: 4, color: '#6b7280' }}>{item.constraint_type}</span>
            )}
            {item.confidence && (
                <span style={{
                    marginLeft: 6, fontSize: 11, padding: '1px 6px', borderRadius: 4, fontWeight: 600,
                    background: item.confidence === 'high' ? '#dcfce7' : item.confidence === 'medium' ? '#fef3c7' : '#fee2e2',
                    color: item.confidence === 'high' ? '#166534' : item.confidence === 'medium' ? '#92400e' : '#991b1b',
                }}>{item.confidence}</span>
            )}
            {item.validation_approach && (
                <div style={{ fontSize: 12, color: '#6b7280', marginTop: 2 }}>
                    <span style={{ fontWeight: 500 }}>Validation:</span> {item.validation_approach}
                </div>
            )}
        </span>
    );
}
