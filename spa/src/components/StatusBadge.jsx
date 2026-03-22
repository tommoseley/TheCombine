/**
 * StatusBadge — visual indicator for document artifact status (ADR-063).
 *
 * WS-REWIND-017: Shows current/stale/superseded as colored chips.
 */

const STATUS_STYLES = {
    current: {
        bg: 'var(--state-stabilized-bg, #dcfce7)',
        text: 'var(--state-stabilized-text, #166534)',
        label: 'Current',
    },
    draft: {
        bg: 'var(--state-ready-bg, #e0e7ff)',
        text: 'var(--state-ready-text, #3730a3)',
        label: 'Draft',
    },
    active: {
        bg: 'var(--state-stabilized-bg, #dcfce7)',
        text: 'var(--state-stabilized-text, #166534)',
        label: 'Active',
    },
    stale: {
        bg: 'var(--state-blocked-bg, #fef3c7)',
        text: 'var(--state-blocked-text, #92400e)',
        label: 'Stale',
    },
    superseded: {
        bg: 'var(--surface-secondary, #e5e7eb)',
        text: 'var(--text-secondary, #6b7280)',
        label: 'Superseded',
    },
    archived: {
        bg: 'var(--surface-secondary, #e5e7eb)',
        text: 'var(--text-secondary, #6b7280)',
        label: 'Archived',
    },
};

export default function StatusBadge({ status }) {
    const style = STATUS_STYLES[status] || STATUS_STYLES.draft;

    return (
        <span
            className="inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-semibold uppercase tracking-wide"
            style={{
                backgroundColor: style.bg,
                color: style.text,
            }}
            aria-label={`Status: ${style.label}`}
        >
            {style.label}
        </span>
    );
}
