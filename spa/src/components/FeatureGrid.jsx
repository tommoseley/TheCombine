import { useEffect } from 'react';
import { TRAY } from '../utils/constants';

export default function FeatureGrid({ features, epicName, nodeWidth, onClose, onZoomComplete }) {
    const useVertical = features.length > 6;
    const gridWidth = useVertical ? 240 : 320;

    useEffect(() => {
        if (onZoomComplete) {
            const timer = setTimeout(() => onZoomComplete(), 150);
            return () => clearTimeout(timer);
        }
    }, [onZoomComplete]);

    // Stop events from propagating to ReactFlow canvas
    const stopPropagation = (e) => e.stopPropagation();

    return (
        <div
            className="absolute top-0 border border-indigo-500/50 rounded-lg shadow-2xl tray-slide nowheel nopan nodrag"
            style={{
                left: nodeWidth + TRAY.GAP,
                width: gridWidth,
                boxShadow: '0 0 30px rgba(0,0,0,0.5)',
                zIndex: 1000,
                background: 'var(--bg-sidecar)',
                userSelect: 'text',
            }}
            onMouseDown={stopPropagation}
            onPointerDown={stopPropagation}
            onWheel={stopPropagation}
        >
            {/* Horizontal bridge */}
            <div
                className="absolute border-t-2 border-dashed border-indigo-500/60"
                style={{ top: 14, right: '100%', width: TRAY.GAP }}
            />
            <div
                className="absolute w-2 h-2 rounded-full bg-indigo-500"
                style={{ top: 11, right: '100%', marginRight: -4 }}
            />

            <div className="bg-indigo-500/10 border-b border-indigo-500/30 px-3 py-2 flex justify-between items-center">
                <span
                    className="text-[9px] font-semibold uppercase tracking-wide"
                    style={{ color: 'var(--text-sidecar-muted)' }}
                >
                    Features - {epicName}
                </span>
                <button
                    onClick={onClose}
                    style={{ color: 'var(--text-sidecar-muted)' }}
                    className="hover:opacity-70 text-sm leading-none"
                >
                    &times;
                </button>
            </div>

            <div className={`p-3 max-h-64 overflow-y-auto ${useVertical ? '' : 'grid grid-cols-2 gap-2'}`}>
                {features.map(f => {
                    const stateColor = f.state === 'complete'
                        ? 'var(--state-stabilized-bg)'
                        : f.state === 'active'
                            ? 'var(--state-active-bg)'
                            : 'var(--state-queued-bg)';

                    return (
                        <div
                            key={f.id}
                            className={`flex items-center gap-2 p-1.5 rounded cursor-pointer hover:opacity-80 ${useVertical ? 'mb-1' : ''}`}
                        >
                            <div
                                className="w-2 h-2 rounded-full flex-shrink-0"
                                style={{ background: stateColor }}
                            />
                            <span
                                className="text-[10px] truncate"
                                style={{ color: 'var(--text-sidecar)' }}
                            >
                                {f.name}
                            </span>
                        </div>
                    );
                })}
            </div>

            <div
                className="px-3 py-2 text-[9px]"
                style={{
                    borderTop: '1px solid var(--border-node)',
                    color: 'var(--text-sidecar-muted)'
                }}
            >
                {features.length} features
            </div>
        </div>
    );
}
