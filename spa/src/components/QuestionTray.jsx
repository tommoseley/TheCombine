import { useState } from 'react';
import { TRAY } from '../utils/constants';

const NORMAL_WIDTH = 400;
const EXPANDED_WIDTH = 560;

/**
 * Render the appropriate input control based on question type
 */
function QuestionInput({ question, value, onChange }) {
    const answerType = question.answer_type || 'text';
    const choices = question.choices || [];

    // Single choice - radio buttons
    if (answerType === 'single_choice' && choices.length > 0) {
        return (
            <div className="space-y-1.5">
                {choices.map((choice) => (
                    <label
                        key={choice.value}
                        className="flex items-center gap-2 cursor-pointer group"
                    >
                        <input
                            type="radio"
                            name={question.id}
                            value={choice.value}
                            checked={value === choice.value}
                            onChange={() => onChange(choice.value)}
                            className="w-3.5 h-3.5 accent-amber-500"
                        />
                        <span
                            className="text-xs group-hover:opacity-80"
                            style={{ color: 'var(--text-sidecar)' }}
                        >
                            {choice.label}
                        </span>
                    </label>
                ))}
            </div>
        );
    }

    // Multi choice - checkboxes
    if (answerType === 'multi_choice' && choices.length > 0) {
        const selected = Array.isArray(value) ? value : [];
        return (
            <div className="space-y-1.5">
                {choices.map((choice) => (
                    <label
                        key={choice.value}
                        className="flex items-center gap-2 cursor-pointer group"
                    >
                        <input
                            type="checkbox"
                            checked={selected.includes(choice.value)}
                            onChange={(e) => {
                                if (e.target.checked) {
                                    onChange([...selected, choice.value]);
                                } else {
                                    onChange(selected.filter(v => v !== choice.value));
                                }
                            }}
                            className="w-3.5 h-3.5 accent-amber-500"
                        />
                        <span
                            className="text-xs group-hover:opacity-80"
                            style={{ color: 'var(--text-sidecar)' }}
                        >
                            {choice.label}
                        </span>
                    </label>
                ))}
            </div>
        );
    }

    // Boolean - yes/no toggle
    if (answerType === 'boolean') {
        return (
            <div className="flex gap-3">
                {[{ label: 'Yes', value: true }, { label: 'No', value: false }].map((opt) => (
                    <label
                        key={String(opt.value)}
                        className="flex items-center gap-2 cursor-pointer group"
                    >
                        <input
                            type="radio"
                            name={question.id}
                            checked={value === opt.value}
                            onChange={() => onChange(opt.value)}
                            className="w-3.5 h-3.5 accent-amber-500"
                        />
                        <span
                            className="text-xs group-hover:opacity-80"
                            style={{ color: 'var(--text-sidecar)' }}
                        >
                            {opt.label}
                        </span>
                    </label>
                ))}
            </div>
        );
    }

    // Number input
    if (answerType === 'number') {
        return (
            <input
                type="number"
                className="w-full rounded px-2 py-1.5 text-xs border"
                style={{
                    background: 'var(--bg-input)',
                    borderColor: 'var(--border-input)',
                    color: 'var(--text-input)'
                }}
                value={value || ''}
                onChange={(e) => onChange(e.target.value ? Number(e.target.value) : '')}
            />
        );
    }

    // Long text / free text - textarea
    if (answerType === 'free_text' || answerType === 'long_text') {
        return (
            <textarea
                className="w-full rounded px-2 py-1.5 text-xs border resize-none"
                style={{
                    background: 'var(--bg-input)',
                    borderColor: 'var(--border-input)',
                    color: 'var(--text-input)',
                    minHeight: 60,
                }}
                value={value || ''}
                onChange={(e) => onChange(e.target.value)}
            />
        );
    }

    // Default: text input
    return (
        <input
            type="text"
            className="w-full rounded px-2 py-1.5 text-xs border"
            style={{
                background: 'var(--bg-input)',
                borderColor: 'var(--border-input)',
                color: 'var(--text-input)'
            }}
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
        />
    );
}

/**
 * Priority badge
 */
function PriorityBadge({ priority }) {
    if (!priority) return null;

    const colors = {
        must: { bg: 'bg-red-500/20', text: 'text-red-400' },
        should: { bg: 'bg-amber-500/20', text: 'text-amber-400' },
        could: { bg: 'bg-blue-500/20', text: 'text-blue-400' },
    };

    const c = colors[priority] || colors.should;

    return (
        <span className={`${c.bg} ${c.text} text-[8px] px-1.5 py-0.5 rounded uppercase font-semibold`}>
            {priority}
        </span>
    );
}

export default function QuestionTray({ questions, nodeWidth, onSubmit, onClose }) {
    const [answers, setAnswers] = useState({});
    const [isExpanded, setIsExpanded] = useState(false);
    const [isSubmitting, setIsSubmitting] = useState(false);

    const allAnswered = questions
        .filter(q => q.required)
        .every(q => {
            const val = answers[q.id];
            if (Array.isArray(val)) return val.length > 0;
            return val !== undefined && val !== '';
        });

    const width = isExpanded ? EXPANDED_WIDTH : NORMAL_WIDTH;

    const handleChange = (questionId, value) => {
        setAnswers(prev => ({ ...prev, [questionId]: value }));
    };

    const handleSubmit = async () => {
        setIsSubmitting(true);
        try {
            await onSubmit(answers);
        } catch (err) {
            console.error('Submit failed:', err);
            setIsSubmitting(false);
        }
        // Don't reset isSubmitting - component will unmount after successful submit
    };

    // Stop events from propagating to ReactFlow canvas
    const stopPropagation = (e) => e.stopPropagation();

    return (
        <div
            className="absolute top-0 border border-amber-500/50 rounded-lg shadow-2xl tray-slide nowheel nopan nodrag"
            style={{
                left: nodeWidth + TRAY.GAP,
                width,
                boxShadow: '0 0 30px rgba(0,0,0,0.5)',
                zIndex: 1000,
                background: 'var(--bg-sidecar)',
                transition: 'width 0.2s ease',
                userSelect: 'text',
            }}
            onMouseDown={stopPropagation}
            onPointerDown={stopPropagation}
            onWheel={stopPropagation}
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
                <div className="flex items-center gap-1">
                    <button
                        onClick={() => setIsExpanded(!isExpanded)}
                        title={isExpanded ? 'Contract' : 'Expand'}
                        className="hover:opacity-70 transition-opacity p-1"
                        style={{ color: 'var(--text-sidecar-muted)' }}
                    >
                        {isExpanded ? (
                            <svg width="12" height="12" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5">
                                <path d="M9 1v4h4M5 13v-4H1M9 5L13 1M5 9L1 13" />
                            </svg>
                        ) : (
                            <svg width="12" height="12" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5">
                                <path d="M13 5V1h-4M1 9v4h4M13 1L9 5M1 13l4-4" />
                            </svg>
                        )}
                    </button>
                    <button
                        onClick={onClose}
                        style={{ color: 'var(--text-sidecar-muted)' }}
                        className="hover:opacity-70 text-sm leading-none"
                    >
                        &times;
                    </button>
                </div>
            </div>

            <div className={`p-3 space-y-4 overflow-y-auto nowheel ${isExpanded ? 'max-h-[520px]' : 'max-h-[420px]'}`}>
                {questions.map(q => (
                    <div
                        key={q.id}
                        className="pb-3"
                        style={{ borderBottom: '1px solid var(--border-input)' }}
                    >
                        {/* Question header with priority */}
                        <div className="flex items-start justify-between gap-2 mb-1">
                            <label
                                className="block text-[11px] font-medium"
                                style={{ color: 'var(--text-sidecar)' }}
                            >
                                {q.text} {q.required && <span className="text-amber-500">*</span>}
                            </label>
                            <PriorityBadge priority={q.priority} />
                        </div>

                        {/* Why it matters */}
                        {q.why_it_matters && (
                            <p
                                className="text-[9px] mb-2 italic"
                                style={{ color: 'var(--text-sidecar-muted)' }}
                            >
                                {q.why_it_matters}
                            </p>
                        )}

                        {/* Input control */}
                        <QuestionInput
                            question={q}
                            value={answers[q.id]}
                            onChange={(val) => handleChange(q.id, val)}
                        />
                    </div>
                ))}
            </div>

            <div className="p-3" style={{ borderTop: '1px solid var(--border-node)' }}>
                <button
                    className={`w-full py-2 rounded text-xs font-medium transition-colors ${
                        allAnswered && !isSubmitting
                            ? 'bg-amber-500 text-slate-900 hover:bg-amber-400'
                            : 'subway-button cursor-not-allowed'
                    }`}
                    disabled={!allAnswered || isSubmitting}
                    onClick={handleSubmit}
                >
                    {isSubmitting ? 'Submitting...' : 'Submit & Continue'}
                </button>
            </div>
        </div>
    );
}
