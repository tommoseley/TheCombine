import React, { useState } from 'react';
import { labelStyle } from '../../constants/nodeConfig';

/**
 * Collapsible section component.
 * Supports both uncontrolled (defaultOpen) and controlled (isOpen + onToggle) modes.
 */
export default function CollapsibleSection({ title, defaultOpen = false, isOpen: controlledOpen, onToggle, children, badge }) {
    const [internalOpen, setInternalOpen] = useState(defaultOpen);

    // Use controlled mode if isOpen prop is provided
    const isControlled = controlledOpen !== undefined;
    const isOpen = isControlled ? controlledOpen : internalOpen;

    const handleToggle = () => {
        if (isControlled && onToggle) {
            onToggle();
        } else {
            setInternalOpen(!internalOpen);
        }
    };

    return (
        <div className="border rounded" style={{ borderColor: 'var(--border-panel)' }}>
            <button
                onClick={handleToggle}
                className="w-full px-2 py-1.5 flex items-center justify-between text-left hover:bg-white/5 transition-colors"
                style={{ background: 'var(--bg-canvas)' }}
            >
                <div className="flex items-center gap-2">
                    <svg
                        width="10"
                        height="10"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        style={{
                            color: 'var(--text-muted)',
                            transform: isOpen ? 'rotate(90deg)' : 'rotate(0deg)',
                            transition: 'transform 0.15s ease',
                        }}
                    >
                        <path d="M9 18l6-6-6-6" />
                    </svg>
                    <span style={{ ...labelStyle, marginBottom: 0 }}>{title}</span>
                </div>
                {badge && (
                    <span
                        className="text-[9px] px-1.5 py-0.5 rounded"
                        style={{ background: 'var(--action-primary)', color: '#fff' }}
                    >
                        {badge}
                    </span>
                )}
            </button>
            {isOpen && (
                <div className="p-2 border-t" style={{ borderColor: 'var(--border-panel)' }}>
                    {children}
                </div>
            )}
        </div>
    );
}
