/**
 * Indicator block renderer
 * Displays derived values with color-coded badges
 */
export default function IndicatorBlock({ block }) {
    const { data } = block;
    const value = data.value || 'unknown';
    const label = data.label;

    // Color mapping for common indicator values
    const colorMap = {
        low: { bg: '#d1fae5', text: '#065f46' },
        medium: { bg: '#fef3c7', text: '#92400e' },
        high: { bg: '#fee2e2', text: '#991b1b' },
        critical: { bg: '#fecaca', text: '#7f1d1d' },
        none: { bg: '#e5e7eb', text: '#374151' },
        external: { bg: '#dbeafe', text: '#1e40af' },
        qualified: { bg: '#d1fae5', text: '#065f46' },
        not_ready: { bg: '#fef3c7', text: '#92400e' },
    };

    const colors = colorMap[value.toLowerCase()] || { bg: '#f3f4f6', text: '#374151' };

    return (
        <div
            style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 8,
                marginBottom: 12,
            }}
        >
            {label && (
                <span
                    style={{
                        fontSize: 12,
                        color: 'var(--text-muted)',
                        fontWeight: 500,
                    }}
                >
                    {label}:
                </span>
            )}
            <span
                style={{
                    display: 'inline-block',
                    padding: '4px 12px',
                    borderRadius: 20,
                    background: colors.bg,
                    color: colors.text,
                    fontSize: 12,
                    fontWeight: 500,
                    textTransform: 'capitalize',
                }}
            >
                {value}
            </span>
        </div>
    );
}
