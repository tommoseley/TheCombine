import { useState, useEffect } from 'react';
import { TRAY } from '../utils/constants';

export default function QuestionTray({ questions, nodeWidth, onSubmit, onClose, onZoomComplete }) {
    const [answers, setAnswers] = useState({});

    const allAnswered = questions
        .filter(q => q.required)
        .every(q => answers[q.id]);

    useEffect(() => {
        if (onZoomComplete) {
            const timer = setTimeout(() => onZoomComplete(), 150);
            return () => clearTimeout(timer);
        }
    }, [onZoomComplete]);

    return (
        <div
            className="absolute top-0 border border-amber-500/50 rounded-lg shadow-2xl tray-slide"
            style={{
                left: nodeWidth + TRAY.GAP,
                width: TRAY.WIDTH,
                boxShadow: '0 0 30px rgba(0,0,0,0.5)',
                zIndex: 1000,
                background: 'var(--bg-sidecar)'
            }}
        >
            {/* Horizontal bridge - top aligned at header center */}
            <div
                className="absolute border-t-2 border-dashed border-amber-500/60"
                style={{ top: 14, right: '100%', width: TRAY.GAP }}
            />
            <div
                className="absolute w-2 h-2 rounded-full bg-amber-500"
                style={{ top: 11, right: '100%', marginRight: -4 }}
            />

            <div className="bg-amber-500/10 border-b border-amber-500/30 px-3 py-2 flex justify-between items-center">
                <span className="text-[9px] font-semibold text-amber-600 uppercase tracking-wide">
                    Operator Input Required
                </span>
                <button
                    onClick={onClose}
                    style={{ color: 'var(--text-sidecar-muted)' }}
                    className="hover:opacity-70 text-sm leading-none"
                >
                    &times;
                </button>
            </div>

            <div className="p-3 space-y-3 max-h-64 overflow-y-auto">
                {questions.map(q => (
                    <div key={q.id}>
                        <label
                            className="block text-[10px] mb-1"
                            style={{ color: 'var(--text-sidecar-muted)' }}
                        >
                            {q.text} {q.required && <span className="text-amber-600">*</span>}
                        </label>
                        <input
                            type="text"
                            className="w-full rounded px-2 py-1.5 text-xs border"
                            style={{
                                background: 'var(--bg-input)',
                                borderColor: 'var(--border-input)',
                                color: 'var(--text-sidecar)'
                            }}
                            value={answers[q.id] || ''}
                            onChange={(e) => setAnswers(prev => ({
                                ...prev,
                                [q.id]: e.target.value
                            }))}
                        />
                    </div>
                ))}
            </div>

            <div className="p-3" style={{ borderTop: '1px solid var(--border-node)' }}>
                <button
                    className={`w-full py-2 rounded text-xs font-medium transition-colors ${
                        allAnswered
                            ? 'bg-amber-500 text-slate-900 hover:bg-amber-400'
                            : 'subway-button cursor-not-allowed'
                    }`}
                    disabled={!allAnswered}
                    onClick={() => onSubmit(answers)}
                >
                    Submit & Continue
                </button>
            </div>
        </div>
    );
}
