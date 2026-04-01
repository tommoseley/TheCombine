import React from 'react';

/** Section header with icon and count badge */
export default function SectionHeader({ config, count }) {
    return (
        <div className="flex items-center gap-2" style={{ padding: '12px 16px', borderBottom: '1px solid var(--border-node)' }}>
            <span style={{
                width: 24, height: 24, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 12, fontWeight: 700, background: `${config.color}15`, color: config.color,
            }}>{config.icon}</span>
            <h3 style={{ margin: 0, fontSize: 15, fontWeight: 600, color: 'var(--text-primary)' }}>{config.title}</h3>
            {count !== undefined && <span style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--text-dim)' }}>{count}</span>}
        </div>
    );
}
