/**
 * ExecutiveSummaryBlock — Work Plan executive summary (ADR-071).
 *
 * Renders project overview: name, objective, scope, constraints, counts.
 */

export default function ExecutiveSummaryBlock({ block }) {
    const { data } = block;
    const summary = data.executive_summary || data;

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {summary.project_name && (
                <div>
                    <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary, #eee)' }}>
                        {summary.project_name}
                    </div>
                </div>
            )}

            {summary.objective && (
                <div>
                    <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted, #888)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>
                        Objective
                    </div>
                    <div style={{ fontSize: 14, color: 'var(--text-secondary, #ccc)', lineHeight: 1.6 }}>
                        {summary.objective}
                    </div>
                </div>
            )}

            {summary.scope_summary && (
                <div>
                    <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted, #888)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>
                        Scope
                    </div>
                    <div style={{ fontSize: 14, color: 'var(--text-secondary, #ccc)', lineHeight: 1.6 }}>
                        {summary.scope_summary}
                    </div>
                </div>
            )}

            {summary.key_constraints && summary.key_constraints.length > 0 && (
                <div>
                    <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted, #888)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>
                        Key Constraints
                    </div>
                    <ul style={{ margin: 0, paddingLeft: 20 }}>
                        {summary.key_constraints.map((c, i) => (
                            <li key={i} style={{ fontSize: 13, color: 'var(--text-secondary, #ccc)', lineHeight: 1.6, marginBottom: 2 }}>
                                {c}
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            <div style={{ display: 'flex', gap: 20, marginTop: 4 }}>
                <Stat label="Components" value={summary.component_count} />
                <Stat label="Work Packages" value={summary.work_package_count} />
                <Stat label="Work Statements" value={summary.work_statement_count} />
            </div>
        </div>
    );
}

function Stat({ label, value }) {
    if (value == null) return null;
    return (
        <div style={{
            padding: '8px 16px',
            background: 'var(--bg-canvas, #0f0f23)',
            border: '1px solid var(--border, #333)',
            borderRadius: 6,
            textAlign: 'center',
        }}>
            <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--accent-primary, #3b82f6)' }}>
                {value}
            </div>
            <div style={{ fontSize: 10, color: 'var(--text-muted, #888)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                {label}
            </div>
        </div>
    );
}
