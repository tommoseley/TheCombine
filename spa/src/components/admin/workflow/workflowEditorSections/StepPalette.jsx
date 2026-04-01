import React from 'react';

/**
 * Palette for adding new workflow steps (production or iteration).
 */
export default function StepPalette({ onAddStep }) {
    return (
        <div className="flex gap-2 mt-3">
            <button
                onClick={() => onAddStep('production')}
                className="text-xs px-3 py-1.5 rounded hover:opacity-80"
                style={{
                    background: 'var(--action-primary)',
                    color: '#000',
                    fontWeight: 600,
                }}
            >
                + Production Step
            </button>
            <button
                onClick={() => onAddStep('iteration')}
                className="text-xs px-3 py-1.5 rounded hover:opacity-80"
                style={{
                    background: 'transparent',
                    color: 'var(--action-primary)',
                    border: '1px solid var(--action-primary)',
                    fontWeight: 600,
                }}
            >
                + Iteration Step
            </button>
        </div>
    );
}
