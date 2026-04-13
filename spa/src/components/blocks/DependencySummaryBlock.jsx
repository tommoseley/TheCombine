/**
 * DependencySummaryBlock — WP/WS dependency relationships (ADR-071).
 *
 * Renders dependency edges as a readable list with document titles.
 */

import LinkedText from '../LinkedText';

export default function DependencySummaryBlock({ block }) {
    const { data } = block;
    const deps = data.dependency_summary || data.items || [];

    if (deps.length === 0) {
        return (
            <div style={{ fontSize: 13, color: 'var(--text-muted, #888)', fontStyle: 'italic' }}>
                No dependencies declared.
            </div>
        );
    }

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {deps.map((dep, i) => (
                <div key={i} style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                    padding: '6px 12px',
                    background: 'var(--bg-canvas, #0f0f23)',
                    border: '1px solid var(--border, #333)',
                    borderRadius: 4,
                    fontSize: 13,
                }}>
                    <span style={{ color: 'var(--text-primary, #eee)', fontWeight: 500 }}>
                        <LinkedText text={dep.from_display_id} />
                    </span>
                    <span style={{ color: 'var(--text-muted, #666)', fontSize: 11 }}>
                        {dep.dependency_type === 'depends_on' ? 'depends on' : dep.dependency_type}
                    </span>
                    <span style={{ color: 'var(--text-primary, #eee)', fontWeight: 500 }}>
                        <LinkedText text={dep.to_display_id} />
                    </span>
                    {dep.from_title && dep.from_title !== dep.from_display_id && (
                        <span style={{ color: 'var(--text-muted, #666)', fontSize: 11, marginLeft: 'auto' }}>
                            {dep.from_title}
                        </span>
                    )}
                </div>
            ))}
        </div>
    );
}
