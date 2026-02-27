/**
 * Data Model block renderer
 * Displays an entity with description, fields, primary keys, and relationships
 */
export default function DataModelBlock({ block }) {
    const { data } = block;
    const entityName = data?.name || data?.entity_name;
    if (!data || !entityName) return null;

    const fields = Array.isArray(data.fields) ? data.fields : [];
    const primaryKeys = Array.isArray(data.primary_keys) ? data.primary_keys : [];
    const relationships = Array.isArray(data.relationships) ? data.relationships : [];

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
            <h4 style={{ margin: '0 0 4px', fontSize: 15, fontWeight: 600, color: '#1e293b' }}>
                {entityName}
            </h4>
            {data.description && (
                <p style={{ margin: '0 0 10px', fontSize: 13, color: '#475569' }}>
                    {data.description}
                </p>
            )}
            {fields.length > 0 && (
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                    <thead>
                        <tr style={{ borderBottom: '2px solid #e2e8f0' }}>
                            <th style={{ textAlign: 'left', padding: '4px 8px', color: 'var(--text-muted)', fontWeight: 600, fontSize: 11, textTransform: 'uppercase' }}>Field</th>
                            <th style={{ textAlign: 'left', padding: '4px 8px', color: 'var(--text-muted)', fontWeight: 600, fontSize: 11, textTransform: 'uppercase' }}>Type</th>
                            <th style={{ textAlign: 'center', padding: '4px 8px', color: 'var(--text-muted)', fontWeight: 600, fontSize: 11, textTransform: 'uppercase' }}>Required</th>
                            <th style={{ textAlign: 'left', padding: '4px 8px', color: 'var(--text-muted)', fontWeight: 600, fontSize: 11, textTransform: 'uppercase' }}>Notes</th>
                        </tr>
                    </thead>
                    <tbody>
                        {fields.map((f, i) => (
                            <tr key={i} style={{ borderBottom: '1px solid #f1f5f9' }}>
                                <td style={{ padding: '4px 8px', fontFamily: 'monospace', color: '#1e293b', fontWeight: primaryKeys.includes(f.name) ? 600 : 400 }}>
                                    {f.name}{primaryKeys.includes(f.name) ? ' (PK)' : ''}
                                </td>
                                <td style={{ padding: '4px 8px', color: '#6366f1', fontFamily: 'monospace' }}>
                                    {f.type}
                                </td>
                                <td style={{ padding: '4px 8px', textAlign: 'center' }}>
                                    {f.required ? 'Yes' : 'No'}
                                </td>
                                <td style={{ padding: '4px 8px', color: 'var(--text-muted)' }}>
                                    {Array.isArray(f.notes) ? f.notes.join('; ') : f.notes || f.description || ''}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            )}
            {relationships.length > 0 && (
                <div style={{ marginTop: 8 }}>
                    <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 4 }}>
                        Relationships
                    </div>
                    <ul style={{ margin: 0, paddingLeft: 18 }}>
                        {relationships.map((r, i) => (
                            <li key={i} style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                                {typeof r === 'string' ? r : `${r.type || ''} ${r.target || ''} ${r.description || ''}`.trim()}
                            </li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    );
}
