/**
 * Intake Outcome block renderer
 * Displays status badge, rationale, and next action
 */
export default function IntakeOutcomeBlock({ block }) {
    const { data } = block;
    const { status, rationale, next_action } = data;

    const statusColors = {
        qualified: { bg: '#d1fae5', text: '#065f46' },
        not_ready: { bg: '#fef3c7', text: '#92400e' },
        out_of_scope: { bg: '#fee2e2', text: '#991b1b' },
        redirect: { bg: '#e0e7ff', text: '#3730a3' },
    };
    const colors = statusColors[status] || { bg: '#f3f4f6', text: '#374151' };

    return (
        <div style={{ marginBottom: 12 }}>
            {status && (
                <div style={{ marginBottom: 12 }}>
                    <span
                        style={{
                            padding: '4px 12px',
                            borderRadius: 16,
                            fontSize: 13,
                            fontWeight: 500,
                            background: colors.bg,
                            color: colors.text,
                        }}
                    >
                        {status}
                    </span>
                </div>
            )}
            {rationale && (
                <p
                    style={{
                        margin: 0,
                        marginBottom: next_action ? 12 : 0,
                        fontSize: 13,
                        color: 'var(--text-muted)',
                        lineHeight: 1.5,
                    }}
                >
                    {rationale}
                </p>
            )}
            {next_action && (
                <div
                    style={{
                        padding: 12,
                        borderRadius: 8,
                        background: '#ecfdf5',
                        border: '1px solid #a7f3d0',
                    }}
                >
                    <span
                        style={{
                            fontSize: 13,
                            fontWeight: 500,
                            color: '#065f46',
                        }}
                    >
                        Next: {next_action}
                    </span>
                </div>
            )}
        </div>
    );
}
