import React from 'react';

/**
 * Spawned children panel - shows "This plan produced N Epic documents" with chips.
 */
export default function SpawnedChildrenPanel({ children }) {
    const { count, items } = children;
    return (
        <div
            className="flex items-center gap-3 flex-wrap px-6 py-3"
            style={{ background: '#f0fdf4', borderBottom: '1px solid #bbf7d0' }}
        >
            <span style={{ fontSize: 13, color: '#166534', fontWeight: 600 }}>
                This plan produced {count} Epic document{count !== 1 ? 's' : ''}
            </span>
            <div className="flex items-center gap-1.5 flex-wrap">
                {items.map((item) => (
                    <span
                        key={item.epic_id}
                        title={item.title || item.name}
                        style={{
                            padding: '2px 8px',
                            background: '#dcfce7',
                            color: '#15803d',
                            fontSize: 11,
                            fontWeight: 500,
                            borderRadius: 4,
                            whiteSpace: 'nowrap',
                        }}
                    >
                        {item.name || item.epic_id}
                    </span>
                ))}
            </div>
        </div>
    );
}
