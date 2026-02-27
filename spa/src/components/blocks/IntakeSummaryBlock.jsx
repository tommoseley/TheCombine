/**
 * Intake Summary block renderer
 * Displays project description and user statement
 */
export default function IntakeSummaryBlock({ block }) {
    const { data } = block;
    const { description, user_statement } = data;

    return (
        <div style={{ marginBottom: 12 }}>
            {description && (
                <div
                    style={{
                        paddingLeft: 16,
                        borderLeft: '4px solid #8b5cf6',
                        color: 'var(--text-secondary)',
                        marginBottom: 16,
                        fontSize: 14,
                        lineHeight: 1.6,
                    }}
                >
                    {description}
                </div>
            )}
            {user_statement && (
                <blockquote
                    style={{
                        paddingLeft: 16,
                        borderLeft: '4px solid #d1d5db',
                        color: 'var(--text-muted)',
                        fontStyle: 'italic',
                        margin: 0,
                        fontSize: 13,
                        lineHeight: 1.5,
                    }}
                >
                    "{user_statement}"
                </blockquote>
            )}
        </div>
    );
}
