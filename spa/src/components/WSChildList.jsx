import { useEffect } from 'react';
import { TRAY } from '../utils/constants';

/**
 * WS status badge colors
 */
const STATUS_COLORS = {
    DRAFT: { bg: '#e5e7eb', text: '#374151' },
    READY: { bg: '#fef3c7', text: '#92400e' },
    IN_PROGRESS: { bg: '#fde68a', text: '#78350f' },
    ACCEPTED: { bg: '#d1fae5', text: '#065f46' },
    REJECTED: { bg: '#fee2e2', text: '#991b1b' },
    BLOCKED: { bg: '#fecaca', text: '#991b1b' },
};

/**
 * Verification mode indicator colors
 */
const MODE_COLORS = {
    A: { bg: '#dbeafe', text: '#1e40af' },
    B: { bg: '#fef3c7', text: '#92400e' },
};

/**
 * Format ISO timestamp to short display
 */
function formatTimestamp(ts) {
    if (!ts) return '';
    try {
        const d = new Date(ts);
        return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
            + ' ' + d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
    } catch {
        return ts;
    }
}

export default function WSChildList({ workStatements, wpName, nodeWidth, onClose, onZoomComplete }) {
    const listWidth = 320;

    useEffect(() => {
        if (onZoomComplete) {
            const timer = setTimeout(() => onZoomComplete(), 150);
            return () => clearTimeout(timer);
        }
    }, [onZoomComplete]);

    const stopPropagation = (e) => e.stopPropagation();

    return (
        <div
            className="absolute top-0 border border-sky-500/50 rounded-lg shadow-2xl tray-slide nowheel nopan nodrag"
            style={{
                left: nodeWidth + TRAY.GAP,
                width: listWidth,
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
                className="absolute border-t-2 border-dashed border-sky-500/60"
                style={{ top: 14, right: '100%', width: TRAY.GAP }}
            />
            <div
                className="absolute w-2 h-2 rounded-full bg-sky-500"
                style={{ top: 11, right: '100%', marginRight: -4 }}
            />

            <div className="bg-sky-500/10 border-b border-sky-500/30 px-3 py-2 flex justify-between items-center">
                <span
                    className="text-[9px] font-semibold uppercase tracking-wide"
                    style={{ color: 'var(--text-sidecar-muted)' }}
                >
                    Work Statements - {wpName}
                </span>
                <button
                    onClick={onClose}
                    style={{ color: 'var(--text-sidecar-muted)' }}
                    className="hover:opacity-70 text-sm leading-none"
                >
                    &times;
                </button>
            </div>

            <div className="p-2 max-h-72 overflow-y-auto space-y-1.5">
                {workStatements.map(ws => {
                    const status = ws.state || ws.status || 'DRAFT';
                    const statusColor = STATUS_COLORS[status] || STATUS_COLORS.DRAFT;
                    const mode = ws.verification_mode || ws.mode || 'A';
                    const modeColor = MODE_COLORS[mode] || MODE_COLORS.A;

                    return (
                        <div
                            key={ws.ws_id || ws.id}
                            className="px-2.5 py-2 rounded border"
                            style={{
                                borderColor: 'var(--border-node)',
                                background: 'var(--bg-sidecar)',
                            }}
                        >
                            {/* Title row */}
                            <div className="flex items-center justify-between gap-2 mb-1">
                                <span
                                    className="text-[10px] font-medium truncate flex-1"
                                    style={{ color: 'var(--text-sidecar)' }}
                                >
                                    {ws.title || ws.ws_id || ws.id}
                                </span>
                                {/* Mode badge */}
                                <span
                                    className="text-[8px] font-bold px-1.5 py-0.5 rounded flex-shrink-0"
                                    style={{ background: modeColor.bg, color: modeColor.text }}
                                >
                                    Mode {mode}
                                </span>
                            </div>
                            {/* Status + timestamp row */}
                            <div className="flex items-center justify-between gap-2">
                                <span
                                    className="text-[8px] font-semibold uppercase px-1.5 py-0.5 rounded"
                                    style={{ background: statusColor.bg, color: statusColor.text }}
                                >
                                    {status}
                                </span>
                                {ws.updated_at && (
                                    <span
                                        className="text-[8px]"
                                        style={{ color: 'var(--text-sidecar-muted)' }}
                                    >
                                        {formatTimestamp(ws.updated_at)}
                                    </span>
                                )}
                            </div>
                        </div>
                    );
                })}
                {workStatements.length === 0 && (
                    <div
                        className="text-center py-4 text-[10px]"
                        style={{ color: 'var(--text-sidecar-muted)' }}
                    >
                        No work statements yet
                    </div>
                )}
            </div>

            <div
                className="px-3 py-2 text-[9px]"
                style={{
                    borderTop: '1px solid var(--border-node)',
                    color: 'var(--text-sidecar-muted)',
                }}
            >
                {workStatements.length} work statement{workStatements.length !== 1 ? 's' : ''}
            </div>
        </div>
    );
}
