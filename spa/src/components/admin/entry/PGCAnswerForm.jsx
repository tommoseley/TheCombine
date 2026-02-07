import React, { useState, useEffect } from 'react';

/**
 * PGC Operator Answers Form
 *
 * Specific Entry component for pgc_operator_answers operation.
 * Renders clarification questions and captures operator answers.
 *
 * Context (renders: clarification_question_set.v2):
 * - questions: Array of { id, question, context?, required? }
 * - metadata?: { generated_by, timestamp }
 *
 * Response (captures: operator_answers.v1):
 * - answers: Array of { question_id, answer, skipped? }
 * - completed_at: ISO timestamp
 */
export default function PGCAnswerForm({ operation, context, onSubmit, onCancel }) {
    const questions = context?.questions || [];
    const [answers, setAnswers] = useState({});

    // Initialize answers state from questions
    useEffect(() => {
        const initial = {};
        questions.forEach((q) => {
            initial[q.id] = '';
        });
        setAnswers(initial);
    }, [questions]);

    const config = operation?.config || {};
    const entryPrompt = config.entry_prompt || 'Please answer the clarification questions below.';

    const updateAnswer = (questionId, value) => {
        setAnswers((prev) => ({
            ...prev,
            [questionId]: value,
        }));
    };

    const requiredQuestions = questions.filter((q) => q.required !== false);
    const answeredRequired = requiredQuestions.every((q) => answers[q.id]?.trim());
    const answeredCount = Object.values(answers).filter((a) => a?.trim()).length;

    const handleSubmit = () => {
        const response = {
            answers: questions.map((q) => ({
                question_id: q.id,
                answer: answers[q.id]?.trim() || '',
                skipped: !answers[q.id]?.trim() && q.required === false,
            })),
            completed_at: new Date().toISOString(),
        };

        onSubmit(response);
    };

    return (
        <div
            className="flex flex-col h-full"
            style={{ background: 'var(--bg-canvas)' }}
        >
            {/* Header */}
            <div
                className="px-4 py-3 border-b"
                style={{ borderColor: 'var(--border-panel)', background: 'var(--bg-panel)' }}
            >
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <span
                            className="px-2 py-1 rounded font-semibold uppercase"
                            style={{
                                fontSize: 10,
                                background: 'var(--dot-blue, #3b82f6)',
                                color: '#fff',
                            }}
                        >
                            PGC
                        </span>
                        <div>
                            <div className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                                Clarification Questions
                            </div>
                            <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
                                {answeredCount} of {questions.length} answered
                            </div>
                        </div>
                    </div>

                    {/* Progress */}
                    <div className="flex items-center gap-2">
                        <div
                            className="w-32 h-2 rounded-full overflow-hidden"
                            style={{ background: 'var(--bg-canvas)' }}
                        >
                            <div
                                className="h-full rounded-full transition-all"
                                style={{
                                    width: `${questions.length ? (answeredCount / questions.length) * 100 : 0}%`,
                                    background: answeredRequired ? '#22c55e' : '#3b82f6',
                                }}
                            />
                        </div>
                    </div>
                </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-4">
                <div className="max-w-2xl space-y-6">
                    {/* Entry Prompt */}
                    <div
                        className="p-3 rounded"
                        style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-panel)' }}
                    >
                        <div className="text-sm" style={{ color: 'var(--text-primary)' }}>
                            {entryPrompt}
                        </div>
                    </div>

                    {/* Questions */}
                    {questions.length === 0 ? (
                        <div
                            className="p-4 rounded text-center"
                            style={{ background: 'var(--bg-panel)', color: 'var(--text-muted)' }}
                        >
                            No clarification questions to answer.
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {questions.map((q, index) => (
                                <div
                                    key={q.id}
                                    className="p-4 rounded"
                                    style={{
                                        background: 'var(--bg-panel)',
                                        border: '1px solid var(--border-panel)',
                                    }}
                                >
                                    {/* Question Header */}
                                    <div className="flex items-start justify-between mb-3">
                                        <div className="flex items-center gap-2">
                                            <span
                                                className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-semibold"
                                                style={{
                                                    background: answers[q.id]?.trim()
                                                        ? '#22c55e'
                                                        : 'var(--bg-canvas)',
                                                    color: answers[q.id]?.trim()
                                                        ? '#fff'
                                                        : 'var(--text-muted)',
                                                }}
                                            >
                                                {index + 1}
                                            </span>
                                            {q.required !== false && (
                                                <span
                                                    className="text-xs px-1.5 py-0.5 rounded"
                                                    style={{
                                                        background: 'rgba(239, 68, 68, 0.1)',
                                                        color: '#ef4444',
                                                    }}
                                                >
                                                    Required
                                                </span>
                                            )}
                                        </div>
                                    </div>

                                    {/* Question Text */}
                                    <div
                                        className="text-sm font-medium mb-3"
                                        style={{ color: 'var(--text-primary)' }}
                                    >
                                        {q.question}
                                    </div>

                                    {/* Context */}
                                    {q.context && (
                                        <div
                                            className="text-xs mb-3 p-2 rounded"
                                            style={{
                                                background: 'var(--bg-canvas)',
                                                color: 'var(--text-muted)',
                                            }}
                                        >
                                            {q.context}
                                        </div>
                                    )}

                                    {/* Answer Input */}
                                    <textarea
                                        value={answers[q.id] || ''}
                                        onChange={(e) => updateAnswer(q.id, e.target.value)}
                                        placeholder="Enter your answer..."
                                        className="w-full p-3 rounded text-sm"
                                        style={{
                                            background: 'var(--bg-input, var(--bg-canvas))',
                                            border: '1px solid var(--border-panel)',
                                            color: 'var(--text-primary)',
                                            minHeight: 80,
                                            resize: 'vertical',
                                        }}
                                    />
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Metadata */}
                    {context?.metadata && (
                        <div
                            className="p-3 rounded text-xs"
                            style={{ background: 'var(--bg-panel)', color: 'var(--text-muted)' }}
                        >
                            <div className="flex justify-between">
                                <span>Generated by: {context.metadata.generated_by || 'Unknown'}</span>
                                {context.metadata.timestamp && (
                                    <span>
                                        {new Date(context.metadata.timestamp).toLocaleString()}
                                    </span>
                                )}
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* Footer */}
            <div
                className="px-4 py-3 border-t flex justify-between items-center"
                style={{ borderColor: 'var(--border-panel)', background: 'var(--bg-panel)' }}
            >
                <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
                    {!answeredRequired && requiredQuestions.length > 0 && (
                        <span style={{ color: '#ef4444' }}>
                            Please answer all required questions
                        </span>
                    )}
                </div>

                <div className="flex gap-2">
                    {onCancel && (
                        <button
                            onClick={onCancel}
                            className="px-4 py-2 rounded text-sm"
                            style={{
                                background: 'var(--bg-canvas)',
                                border: '1px solid var(--border-panel)',
                                color: 'var(--text-secondary)',
                            }}
                        >
                            Cancel
                        </button>
                    )}
                    <button
                        onClick={handleSubmit}
                        disabled={!answeredRequired}
                        className="px-4 py-2 rounded text-sm font-semibold"
                        style={{
                            background: answeredRequired ? '#22c55e' : 'var(--bg-canvas)',
                            color: answeredRequired ? '#fff' : 'var(--text-muted)',
                            border: answeredRequired ? 'none' : '1px solid var(--border-panel)',
                        }}
                    >
                        Submit Answers
                    </button>
                </div>
            </div>
        </div>
    );
}
