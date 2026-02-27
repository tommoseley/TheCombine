/**
 * Open questions container block renderer
 * Displays a list of questions with summary counts
 */
import OpenQuestionBlock from './OpenQuestionBlock';

export default function OpenQuestionsBlock({ block }) {
    const { data } = block;
    const items = data.items || [];
    const totalCount = data.total_count || items.length;
    const blockingCount = data.blocking_count || items.filter(q => q.blocking).length;

    if (items.length === 0) {
        return (
            <div
                style={{
                    padding: '16px',
                    background: '#f0fdf4',
                    borderRadius: 8,
                    border: '1px solid #bbf7d0',
                    textAlign: 'center',
                    color: '#166534',
                    fontSize: 14,
                }}
            >
                No open questions
            </div>
        );
    }

    return (
        <div>
            {/* Summary bar */}
            <div
                style={{
                    display: 'flex',
                    gap: 16,
                    marginBottom: 12,
                    padding: '8px 12px',
                    background: 'var(--bg-panel)',
                    borderRadius: 6,
                    fontSize: 12,
                }}
            >
                <span style={{ color: 'var(--text-muted)' }}>
                    <strong style={{ color: 'var(--text-secondary)' }}>{totalCount}</strong> questions
                </span>
                {blockingCount > 0 && (
                    <span style={{ color: '#dc2626' }}>
                        <strong>{blockingCount}</strong> blocking
                    </span>
                )}
            </div>

            {/* Questions list */}
            {items.map((item, i) => (
                <OpenQuestionBlock
                    key={item.id || i}
                    block={{ type: 'schema:OpenQuestionV1', data: item }}
                />
            ))}
        </div>
    );
}
