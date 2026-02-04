import React, { useState, useRef, useEffect } from 'react';

/**
 * Tab-sized button with dropdown menu for grouping artifacts by Interaction Pass.
 *
 * Props:
 *   label       - Display text (e.g., "Generation")
 *   items       - Array of { id, label, viewOnly? }
 *   selectedId  - Currently selected item ID within this group (or null)
 *   onSelect    - Callback when item is clicked: onSelect(id)
 *   isGroupActive - Whether any item in this group is currently selected
 */
export default function TabDropdown({ label, items, selectedId, onSelect, isGroupActive }) {
    const [open, setOpen] = useState(false);
    const ref = useRef(null);

    // Close on click outside
    useEffect(() => {
        if (!open) return;
        const handler = (e) => {
            if (ref.current && !ref.current.contains(e.target)) {
                setOpen(false);
            }
        };
        document.addEventListener('mousedown', handler);
        return () => document.removeEventListener('mousedown', handler);
    }, [open]);

    if (items.length === 0) return null;

    return (
        <div ref={ref} style={{ position: 'relative' }}>
            <button
                onClick={() => setOpen(!open)}
                className="px-4 py-2 text-sm font-medium transition-colors"
                style={{
                    color: isGroupActive
                        ? 'var(--text-primary)'
                        : 'var(--text-muted)',
                    background: isGroupActive
                        ? 'var(--bg-selected, rgba(255,255,255,0.1))'
                        : 'transparent',
                    borderBottom: isGroupActive
                        ? '2px solid var(--action-primary)'
                        : '2px solid transparent',
                    marginBottom: '-1px',
                    cursor: 'pointer',
                }}
            >
                {label}
                <span style={{ fontSize: 9, opacity: 0.6, marginLeft: 4 }}>&#9662;</span>
            </button>
            {open && (
                <div
                    style={{
                        position: 'absolute',
                        top: '100%',
                        left: 0,
                        zIndex: 50,
                        minWidth: 160,
                        background: 'var(--bg-panel)',
                        border: '1px solid var(--border-panel)',
                        borderRadius: 6,
                        boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
                        paddingTop: 4,
                        paddingBottom: 4,
                        marginTop: 1,
                    }}
                >
                    {items.map(item => (
                        <button
                            key={item.id}
                            onClick={() => {
                                onSelect(item.id);
                                setOpen(false);
                            }}
                            className="w-full text-left px-3 py-1.5 hover:opacity-80 transition-opacity"
                            style={{
                                background: selectedId === item.id
                                    ? 'var(--bg-selected)'
                                    : 'transparent',
                                color: selectedId === item.id
                                    ? 'var(--text-primary)'
                                    : 'var(--text-secondary)',
                                border: 'none',
                                cursor: 'pointer',
                                fontSize: 12,
                                fontWeight: 'normal',
                            }}
                        >
                            {item.label}
                            {item.viewOnly && (
                                <span
                                    style={{
                                        color: 'var(--text-muted)',
                                        marginLeft: 4,
                                        fontSize: 11,
                                    }}
                                >
                                    (view)
                                </span>
                            )}
                        </button>
                    ))}
                </div>
            )}
        </div>
    );
}
