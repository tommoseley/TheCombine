/**
 * Intake Open Gaps block renderer
 * Displays questions, missing context, and assumptions with sub-headers
 */
export default function IntakeOpenGapsBlock({ block }) {
    const { data } = block;
    const { questions = [], missing_context = [], assumptions_made = [] } = data;

    const hasQuestions = questions && questions.length > 0;
    const hasMissingContext = missing_context && missing_context.length > 0;
    const hasAssumptions = assumptions_made && assumptions_made.length > 0;

    if (!hasQuestions && !hasMissingContext && !hasAssumptions) return null;

    return (
        <div style={{ marginBottom: 12 }}>
            {hasQuestions && (
                <div style={{ marginBottom: (hasMissingContext || hasAssumptions) ? 16 : 0 }}>
                    <h4
                        style={{
                            fontSize: 12,
                            fontWeight: 500,
                            color: 'var(--text-muted)',
                            marginBottom: 8,
                            marginTop: 0,
                        }}
                    >
                        Questions
                    </h4>
                    <ul style={{ margin: 0, paddingLeft: 20, listStyle: 'none' }}>
                        {questions.map((item, i) => (
                            <li
                                key={i}
                                style={{
                                    display: 'flex',
                                    alignItems: 'flex-start',
                                    gap: 8,
                                    marginBottom: 6,
                                    fontSize: 13,
                                    color: 'var(--text-secondary)',
                                }}
                            >
                                <span style={{ color: '#3b82f6' }}>&#10067;</span>
                                <span>{item}</span>
                            </li>
                        ))}
                    </ul>
                </div>
            )}
            {hasMissingContext && (
                <div style={{ marginBottom: hasAssumptions ? 16 : 0 }}>
                    <h4
                        style={{
                            fontSize: 12,
                            fontWeight: 500,
                            color: 'var(--text-muted)',
                            marginBottom: 8,
                            marginTop: 0,
                        }}
                    >
                        Missing Context
                    </h4>
                    <ul style={{ margin: 0, paddingLeft: 20, listStyle: 'none' }}>
                        {missing_context.map((item, i) => (
                            <li
                                key={i}
                                style={{
                                    display: 'flex',
                                    alignItems: 'flex-start',
                                    gap: 8,
                                    marginBottom: 6,
                                    fontSize: 13,
                                    color: 'var(--text-secondary)',
                                }}
                            >
                                <span style={{ color: '#f59e0b' }}>&#9888;</span>
                                <span>{item}</span>
                            </li>
                        ))}
                    </ul>
                </div>
            )}
            {hasAssumptions && (
                <div>
                    <h4
                        style={{
                            fontSize: 12,
                            fontWeight: 500,
                            color: 'var(--text-muted)',
                            marginBottom: 8,
                            marginTop: 0,
                        }}
                    >
                        Assumptions
                    </h4>
                    <ul style={{ margin: 0, paddingLeft: 20, listStyle: 'none' }}>
                        {assumptions_made.map((item, i) => (
                            <li
                                key={i}
                                style={{
                                    display: 'flex',
                                    alignItems: 'flex-start',
                                    gap: 8,
                                    marginBottom: 6,
                                    fontSize: 13,
                                    color: 'var(--text-secondary)',
                                }}
                            >
                                <span style={{ color: 'var(--text-muted)' }}>&#128161;</span>
                                <span>{item}</span>
                            </li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    );
}
