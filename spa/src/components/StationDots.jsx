import React from 'react';

export default function StationDots({ stations, dormant }) {
    if (!stations?.length) return null;

    // Find indices for progress line calculation
    const lastCompleteIdx = stations.reduce((acc, s, i) =>
        s.state === 'complete' ? i : acc, -1);
    const activeIdx = stations.findIndex(s => s.state === 'active');

    // Get current step from active station
    const activeStation = stations.find(s => s.state === 'active');
    const currentStep = activeStation?.currentStep;

    // Dormant mode: all dots and lines use muted/queued color
    const dormantColor = 'var(--state-queued-bg)';

    return (
        <div className="mt-2" style={dormant ? { opacity: 0.45 } : undefined}>
            <div className="relative flex items-start">
                {/* Background line (gray) */}
                <div
                    className="absolute h-0.5 left-0 right-0"
                    style={{ top: 5, background: dormantColor }}
                />

                {/* Green progress line (up to last completed station) */}
                {!dormant && lastCompleteIdx >= 0 && (
                    <div
                        className="absolute h-0.5 left-0"
                        style={{
                            top: 5,
                            width: `${((lastCompleteIdx + 0.5) / stations.length) * 100}%`,
                            background: 'var(--state-stabilized-bg)'
                        }}
                    />
                )}

                {/* Amber line leading to active station */}
                {!dormant && activeIdx >= 0 && (
                    <div
                        className="absolute h-0.5"
                        style={{
                            top: 5,
                            left: lastCompleteIdx >= 0
                                ? `${((lastCompleteIdx + 0.5) / stations.length) * 100}%`
                                : '0%',
                            width: lastCompleteIdx >= 0
                                ? `${((activeIdx - lastCompleteIdx) / stations.length) * 100}%`
                                : `${((activeIdx + 0.5) / stations.length) * 100}%`,
                            background: 'var(--state-active-bg)'
                        }}
                    />
                )}

                {/* Station dots */}
                {stations.map((s) => {
                    const isActive = !dormant && s.state === 'active';
                    const isComplete = !dormant && s.state === 'complete';

                    const dotColor = dormant
                        ? dormantColor
                        : isComplete
                            ? 'var(--state-stabilized-bg)'
                            : isActive
                                ? 'var(--state-active-bg)'
                                : s.state === 'failed'
                                    ? 'var(--state-blocked-bg)'
                                    : dormantColor;

                    const labelColor = isActive
                        ? 'var(--state-active-text)'
                        : 'var(--text-muted)';

                    return (
                        <div key={s.id} className="flex-1 flex flex-col items-center relative z-10">
                            <div
                                className={`w-3 h-3 rounded-full${isActive ? ' station-active' : ''}${isActive && s.needs_input ? ' station-needs-input' : ''}`}
                                style={{
                                    background: dotColor,
                                    boxShadow: isActive && s.needs_input ? '0 0 0 2px var(--state-active-bg)' : undefined,
                                }}
                            />
                            <span
                                className="text-[7px] mt-0.5"
                                style={{
                                    color: isActive && s.needs_input ? 'var(--state-active-text)' : labelColor,
                                    fontWeight: isActive ? 500 : 400
                                }}
                            >
                                {s.label}
                            </span>
                        </div>
                    );
                })}
            </div>

            {/* Current step name - centered below stations (hidden when dormant) */}
            {!dormant && currentStep && (
                <div
                    className="text-center text-[8px] mt-1 font-medium"
                    style={{ color: 'var(--state-active-text)' }}
                >
                    {currentStep.name}
                </div>
            )}
        </div>
    );
}