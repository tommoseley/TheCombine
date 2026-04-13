/**
 * DecisionLogBlock — synthesis decisions with operator resolutions (ADR-071).
 *
 * Renders each decision: severity badge, headline, operator decision, resolution note.
 */

const SEVERITY_STYLE = {
    blocking: { color: '#e53935', bg: 'rgba(229, 57, 53, 0.08)', label: 'BLOCKING' },
    should_fix: { color: '#f9a825', bg: 'rgba(249, 168, 37, 0.08)', label: 'SHOULD FIX' },
    advisory: { color: '#90a4ae', bg: 'rgba(144, 164, 174, 0.05)', label: 'ADVISORY' },
};

const DECISION_STYLE = {
    accept: { color: '#81c784', label: 'Accepted' },
    reject: { color: '#e57373', label: 'Dismissed' },
};

export default function DecisionLogBlock({ block }) {
    const { data } = block;
    const decisions = data.decision_log || data.items || [];

    if (decisions.length === 0) {
        return (
            <div style={{ fontSize: 13, color: 'var(--text-muted, #888)', fontStyle: 'italic' }}>
                No decisions recorded.
            </div>
        );
    }

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {decisions.map((d, i) => {
                const sev = SEVERITY_STYLE[d.severity] || SEVERITY_STYLE.advisory;
                const dec = DECISION_STYLE[d.decision] || { color: '#888', label: d.decision };

                return (
                    <div key={d.finding_id || i} style={{
                        padding: '10px 14px',
                        background: sev.bg,
                        border: '1px solid var(--border, #333)',
                        borderRadius: 6,
                        display: 'flex',
                        flexDirection: 'column',
                        gap: 4,
                    }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <span style={{
                                fontSize: 10, fontWeight: 700, color: sev.color,
                                letterSpacing: '0.05em',
                            }}>
                                {sev.label}
                            </span>
                            <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary, #eee)', flex: 1 }}>
                                {d.headline}
                            </span>
                            <span style={{
                                fontSize: 10, fontWeight: 600, color: dec.color,
                                padding: '2px 8px',
                                borderRadius: 10,
                                background: `${dec.color}22`,
                            }}>
                                {dec.label}
                            </span>
                        </div>
                        {d.note && (
                            <div style={{ fontSize: 12, color: 'var(--text-secondary, #ccc)', lineHeight: 1.5, marginTop: 2 }}>
                                {d.note}
                            </div>
                        )}
                        <div style={{ fontSize: 10, color: 'var(--text-muted, #666)', marginTop: 2 }}>
                            {d.finding_type === 'action' ? 'Proposed change' : 'Decision'} &middot; {d.finding_id}
                        </div>
                    </div>
                );
            })}
        </div>
    );
}
