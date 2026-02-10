import React from 'react';

export default function StationDots({ stations }) {
    if (!stations?.length) return null;

    return (
        <div className="flex items-center gap-0.5 mt-2">
            {stations.map((s, i) => {
                const dotColor = s.state === 'complete'
                    ? 'var(--state-stabilized-bg)'
                    : s.state === 'active'
                        ? 'var(--state-active-bg)'
                        : s.state === 'failed'
                            ? 'var(--state-blocked-bg)'
                            : 'var(--state-queued-bg)';

                const lineColor = s.state === 'complete'
                    ? 'var(--state-stabilized-bg)'
                    : 'var(--state-queued-bg)';

                const labelColor = s.state === 'active'
                    ? 'var(--state-active-text)'
                    : 'var(--text-muted)';

                return (
                    <React.Fragment key={s.id}>
                        {i > 0 && (
                            <div
                                className="w-4 h-0.5"
                                style={{ background: lineColor }}
                            />
                        )}
                        <div className="flex flex-col items-center">
                            <div
                                className={`w-3 h-3 rounded-full${s.state === 'active' ? ' station-active' : ''}${s.needs_input ? ' station-needs-input' : ''}`}
                                style={{
                                    background: dotColor,
                                    // Add ring for needs_input state
                                    boxShadow: s.needs_input ? '0 0 0 2px var(--state-active-bg)' : undefined,
                                }}
                            />
                            <span
                                className="text-[7px] mt-0.5"
                                style={{
                                    color: s.needs_input ? 'var(--state-active-text)' : labelColor,
                                    fontWeight: s.state === 'active' || s.needs_input ? 500 : 400
                                }}
                            >
                                {s.label}
                            </span>
                        </div>
                    </React.Fragment>
                );
            })}
        </div>
    );
}
