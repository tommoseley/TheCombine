import React from 'react';

/**
 * Horizontal pill/chip filter for prompt fragment kinds.
 *
 * Per WS-ADR-044-002, displays filter options like:
 * [ All (23) ] [ Roles (3) ] [ Tasks (7) ] [ QA (7) ] [ PGC (6) ]
 */
export default function KindFilter({
    kinds = [],
    selectedKind = 'all',
    onSelect,
}) {
    return (
        <div
            className="flex flex-wrap gap-1.5 px-4 py-2"
            style={{ background: 'var(--bg-canvas)' }}
        >
            {kinds.map(({ id, label, count }) => {
                const isSelected = selectedKind === id;
                return (
                    <button
                        key={id}
                        onClick={() => onSelect?.(id)}
                        className="px-2.5 py-1 rounded-full text-xs font-medium transition-all"
                        style={{
                            background: isSelected
                                ? 'var(--action-primary)'
                                : 'var(--bg-panel)',
                            color: isSelected
                                ? '#000'
                                : 'var(--text-secondary)',
                            border: isSelected
                                ? 'none'
                                : '1px solid var(--border-panel)',
                            cursor: 'pointer',
                        }}
                    >
                        {label}
                        {count !== undefined && (
                            <span
                                style={{
                                    marginLeft: 4,
                                    opacity: isSelected ? 0.7 : 0.6,
                                }}
                            >
                                ({count})
                            </span>
                        )}
                    </button>
                );
            })}
        </div>
    );
}
