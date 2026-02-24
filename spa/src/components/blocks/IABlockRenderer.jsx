/**
 * IABlockRenderer - Generic render_as dispatcher for Level 2 IA binds.
 *
 * Each bind declares its render_as type (paragraph, list, ordered-list,
 * table, key-value-pairs, card-list, nested-object). This component
 * dispatches to the appropriate renderer. card-list and nested-object
 * recurse into IABlockRenderer for sub-fields.
 *
 * WS-IA-003
 */

/** Convert snake_case field name to Title Case label */
function formatFieldLabel(key) {
    return key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

/** Top-level dispatcher: renders data according to bind.render_as */
export default function IABlockRenderer({ bind, data, label }) {
    if (data === null || data === undefined) {
        return <span style={{ color: '#9ca3af', fontSize: 13 }}>No data</span>;
    }

    const renderAs = bind?.render_as || 'paragraph';

    switch (renderAs) {
        case 'paragraph':
            return <ParagraphRenderer data={data} />;
        case 'list':
            return <ListRenderer data={data} />;
        case 'ordered-list':
            return <OrderedListRenderer data={data} />;
        case 'table':
            return <TableRenderer data={data} columns={bind.columns} />;
        case 'key-value-pairs':
            return <KeyValuePairsRenderer data={data} />;
        case 'card-list':
            return <CardListRenderer data={data} card={bind.card} />;
        case 'nested-object':
            return <NestedObjectRenderer data={data} fields={bind.fields} />;
        default:
            return <ParagraphRenderer data={data} />;
    }
}

function ParagraphRenderer({ data }) {
    const text = typeof data === 'string' ? data : JSON.stringify(data);
    return (
        <p style={{ fontSize: 14, color: '#1f2937', margin: 0, lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
            {text}
        </p>
    );
}

function ListRenderer({ data }) {
    if (!Array.isArray(data) || data.length === 0) {
        return <span style={{ color: '#9ca3af', fontSize: 13 }}>Empty list</span>;
    }
    return (
        <ul style={{ margin: 0, paddingLeft: 20 }}>
            {data.map((item, i) => (
                <li key={i} style={{ fontSize: 14, color: '#374151', marginBottom: 4 }}>
                    {typeof item === 'string' ? item : JSON.stringify(item)}
                </li>
            ))}
        </ul>
    );
}

function OrderedListRenderer({ data }) {
    if (!Array.isArray(data) || data.length === 0) {
        return <span style={{ color: '#9ca3af', fontSize: 13 }}>Empty list</span>;
    }
    return (
        <ol style={{ margin: 0, paddingLeft: 20 }}>
            {data.map((item, i) => (
                <li key={i} style={{ fontSize: 14, color: '#374151', marginBottom: 4 }}>
                    {typeof item === 'string' ? item : JSON.stringify(item)}
                </li>
            ))}
        </ol>
    );
}

function TableRenderer({ data, columns }) {
    if (!Array.isArray(data) || data.length === 0) {
        return <span style={{ color: '#9ca3af', fontSize: 13 }}>No data</span>;
    }
    if (!columns || columns.length === 0) {
        // Fallback: auto-detect columns from first item
        const firstItem = data[0];
        if (typeof firstItem === 'object' && firstItem !== null) {
            columns = Object.keys(firstItem).map(k => ({ field: k, label: formatFieldLabel(k) }));
        } else {
            return <ListRenderer data={data} />;
        }
    }
    return (
        <div className="rounded border overflow-hidden" style={{ borderColor: '#e2e8f0' }}>
            <table className="w-full text-sm" style={{ borderCollapse: 'collapse' }}>
                <thead>
                    <tr style={{ background: '#f1f5f9' }}>
                        {columns.map(col => (
                            <th
                                key={col.field}
                                className="px-3 py-2 text-left font-medium"
                                style={{ color: '#64748b', borderBottom: '1px solid #e2e8f0' }}
                            >
                                {col.label}
                            </th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {data.map((row, i) => (
                        <tr key={i} style={{ borderTop: i > 0 ? '1px solid #e2e8f0' : 'none' }}>
                            {columns.map(col => {
                                const val = row?.[col.field];
                                return (
                                    <td key={col.field} className="px-3 py-2" style={{ color: '#1e293b', fontSize: 13 }}>
                                        {val === null || val === undefined ? '-'
                                            : typeof val === 'boolean' ? (val ? 'Yes' : 'No')
                                            : typeof val === 'object' ? JSON.stringify(val)
                                            : String(val)}
                                    </td>
                                );
                            })}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}

function KeyValuePairsRenderer({ data }) {
    if (typeof data !== 'object' || data === null || Array.isArray(data)) {
        return <ParagraphRenderer data={data} />;
    }
    return (
        <div className="space-y-2">
            {Object.entries(data).map(([k, v]) => (
                <div key={k} style={{ display: 'flex', gap: 12, fontSize: 14 }}>
                    <span style={{ fontWeight: 600, color: '#6b7280', minWidth: 120, flexShrink: 0 }}>
                        {formatFieldLabel(k)}
                    </span>
                    <span style={{ color: '#1f2937' }}>
                        {typeof v === 'string' ? v : JSON.stringify(v)}
                    </span>
                </div>
            ))}
        </div>
    );
}

function CardListRenderer({ data, card }) {
    if (!Array.isArray(data) || data.length === 0) {
        return <span style={{ color: '#9ca3af', fontSize: 13 }}>No items</span>;
    }
    if (!card) {
        // Fallback: render as simple list
        return <ListRenderer data={data.map(item => typeof item === 'string' ? item : JSON.stringify(item))} />;
    }
    const titleKey = card.title || 'name';
    const fields = card.fields || [];

    return (
        <div className="space-y-4">
            {data.map((item, i) => {
                const title = item[titleKey] || `Item ${i + 1}`;
                return (
                    <div
                        key={item.id || i}
                        style={{
                            background: '#fff',
                            border: '1px solid #e2e8f0',
                            borderRadius: 8,
                            overflow: 'hidden',
                        }}
                    >
                        <div
                            style={{
                                padding: '12px 16px',
                                borderBottom: '1px solid #e2e8f0',
                                background: '#f8fafc',
                            }}
                        >
                            <h4 style={{ margin: 0, fontSize: 15, fontWeight: 600, color: '#1f2937' }}>
                                {title}
                            </h4>
                        </div>
                        <div style={{ padding: 16 }} className="space-y-4">
                            {fields.map(field => {
                                const fieldData = item[field.path];
                                if (fieldData === null || fieldData === undefined) return null;
                                return (
                                    <div key={field.path}>
                                        <div style={{
                                            fontSize: 11,
                                            fontWeight: 600,
                                            color: '#6b7280',
                                            textTransform: 'uppercase',
                                            letterSpacing: '0.05em',
                                            marginBottom: 6,
                                        }}>
                                            {field.label || formatFieldLabel(field.path)}
                                        </div>
                                        <IABlockRenderer bind={field} data={fieldData} />
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                );
            })}
        </div>
    );
}

function NestedObjectRenderer({ data, fields }) {
    if (typeof data !== 'object' || data === null || Array.isArray(data)) {
        return <ParagraphRenderer data={data} />;
    }
    if (!fields || fields.length === 0) {
        return <KeyValuePairsRenderer data={data} />;
    }
    return (
        <div className="space-y-4">
            {fields.map(field => {
                const fieldData = data[field.path];
                if (fieldData === null || fieldData === undefined) return null;
                return (
                    <div key={field.path} style={{ borderLeft: '3px solid #e2e8f0', paddingLeft: 12 }}>
                        <div style={{
                            fontSize: 11,
                            fontWeight: 600,
                            color: '#6b7280',
                            textTransform: 'uppercase',
                            letterSpacing: '0.05em',
                            marginBottom: 6,
                        }}>
                            {field.label || formatFieldLabel(field.path)}
                        </div>
                        <IABlockRenderer bind={field} data={fieldData} />
                    </div>
                );
            })}
        </div>
    );
}
