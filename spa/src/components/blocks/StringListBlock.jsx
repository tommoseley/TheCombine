/**
 * String list block renderer
 * Displays a list of strings with configurable style
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
                        key={i}
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
                        {typeof item === 'string' ? item : (item?.value || item?.text || item?.question || item?.description || JSON.stringify(item))}
                    </li>
                ))}
            </ul>
        </div>
    );
}
