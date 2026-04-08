/**
 * Paragraph block renderer
 * Displays text content with optional detail link.
 * Auto-links document references (ADR-071).
 */
import LinkedText from '../LinkedText';

export default function ParagraphBlock({ block }) {
    const { data } = block;
    const content = data.content || data.value || '';

    if (!content) return null;

    return (
        <div style={{ marginBottom: 12 }}>
            <p
                style={{
                    margin: 0,
                    fontSize: 14,
                    lineHeight: 1.6,
                    color: 'var(--text-secondary)',
                    whiteSpace: 'pre-line',
                }}
            >
                <LinkedText text={content} />
            </p>
            {data.detail_ref && (
                <a
                    href="#"
                    style={{
                        fontSize: 12,
                        color: '#6366f1',
                        textDecoration: 'none',
                        marginTop: 4,
                        display: 'inline-block',
                    }}
                >
                    View details &rarr;
                </a>
            )}
        </div>
    );
}
