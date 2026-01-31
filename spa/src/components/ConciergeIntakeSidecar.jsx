import { useEffect } from 'react';
import { useConciergeIntake } from '../hooks';
import MessageList from './concierge/MessageList';
import ChatInput from './concierge/ChatInput';
import InterpretationEditor from './concierge/InterpretationEditor';
import GeneratingIndicator from './concierge/GeneratingIndicator';
import CompletionCard from './concierge/CompletionCard';

/**
 * Concierge Intake Sidecar - Full conversational intake experience.
 *
 * Phases:
 * - describe: Chat interface for initial project description
 * - review: Editable interpretation fields
 * - generating: Spinner during document generation
 * - complete: Success/completion card
 */
export default function ConciergeIntakeSidecar({ onClose, onComplete }) {
    const {
        executionId,
        phase,
        messages,
        pendingPrompt,
        interpretation,
        confidence,
        missingFields,
        canInitialize,
        gateOutcome,
        project,
        error,
        loading,
        submitting,
        startIntake,
        submitMessage,
        updateField,
        lockAndGenerate,
        reset,
    } = useConciergeIntake();

    // Start intake on mount
    useEffect(() => {
        startIntake();
        return () => reset();
    }, []);

    const handleClose = () => {
        reset();
        onClose();
    };

    const handleViewProject = () => {
        if (project && onComplete) {
            onComplete(project);
        }
        handleClose();
    };

    const renderPhaseIndicator = () => {
        const phases = [
            { id: 'describe', label: 'Describe' },
            { id: 'review', label: 'Review' },
            { id: 'generating', label: 'Generate' },
            { id: 'complete', label: 'Done' },
        ];

        const currentIdx = phases.findIndex((p) => p.id === phase);

        return (
            <div className="flex items-center gap-1 text-[10px]">
                {phases.map((p, idx) => (
                    <div key={p.id} className="flex items-center">
                        <span
                            className={`px-2 py-0.5 rounded ${
                                idx === currentIdx
                                    ? 'bg-violet-500/30 text-violet-300'
                                    : idx < currentIdx
                                    ? 'text-emerald-400'
                                    : 'text-slate-500'
                            }`}
                        >
                            {p.label}
                        </span>
                        {idx < phases.length - 1 && (
                            <span className="mx-1 text-slate-600">/</span>
                        )}
                    </div>
                ))}
            </div>
        );
    };

    const renderContent = () => {
        if (loading && phase === 'idle') {
            return (
                <div className="flex-1 flex items-center justify-center">
                    <div className="w-8 h-8 border-2 border-t-violet-500 border-r-transparent border-b-transparent border-l-transparent rounded-full animate-spin" />
                </div>
            );
        }

        switch (phase) {
            case 'describe':
                return (
                    <>
                        <MessageList
                            messages={messages}
                            pendingPrompt={pendingPrompt}
                        />
                        <ChatInput
                            onSubmit={submitMessage}
                            disabled={submitting}
                            placeholder="Describe what you want to build..."
                        />
                    </>
                );

            case 'review':
                return (
                    <>
                        <MessageList messages={messages} />
                        <div
                            className="border-t"
                            style={{ borderColor: 'var(--border-panel)' }}
                        >
                            <InterpretationEditor
                                interpretation={interpretation}
                                missingFields={missingFields}
                                canInitialize={canInitialize}
                                onUpdateField={updateField}
                                onInitialize={lockAndGenerate}
                                loading={loading}
                            />
                        </div>
                    </>
                );

            case 'generating':
                return (
                    <>
                        <MessageList messages={messages} />
                        <GeneratingIndicator />
                    </>
                );

            case 'complete':
                return (
                    <>
                        <MessageList messages={messages} />
                        <CompletionCard
                            gateOutcome={gateOutcome}
                            project={project}
                            onViewProject={handleViewProject}
                            onClose={handleClose}
                        />
                    </>
                );

            default:
                return null;
        }
    };

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center"
            style={{ background: 'rgba(0, 0, 0, 0.6)' }}
        >
            <div
                className="flex flex-col w-full max-w-lg h-[80vh] rounded-xl shadow-2xl tray-slide"
                style={{
                    background: 'var(--bg-panel)',
                    border: '1px solid var(--border-panel)',
                }}
            >
                {/* Header */}
                <div
                    className="flex items-center justify-between px-4 py-3 border-b"
                    style={{ borderColor: 'var(--border-panel)' }}
                >
                    <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-violet-500/20 flex items-center justify-center">
                            <svg
                                className="w-4 h-4 text-violet-400"
                                viewBox="0 0 24 24"
                                fill="none"
                                stroke="currentColor"
                                strokeWidth="2"
                            >
                                <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
                            </svg>
                        </div>
                        <div>
                            <h2
                                className="text-sm font-semibold"
                                style={{ color: 'var(--text-primary)' }}
                            >
                                New Project
                            </h2>
                            {renderPhaseIndicator()}
                        </div>
                    </div>
                    <button
                        onClick={handleClose}
                        className="p-2 rounded-lg hover:bg-white/10 transition-colors"
                        style={{ color: 'var(--text-muted)' }}
                    >
                        <svg
                            className="w-5 h-5"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2"
                        >
                            <line x1="18" y1="6" x2="6" y2="18" />
                            <line x1="6" y1="6" x2="18" y2="18" />
                        </svg>
                    </button>
                </div>

                {/* Error banner */}
                {error && (
                    <div className="px-4 py-2 bg-red-500/20 text-red-300 text-sm">
                        {error}
                    </div>
                )}

                {/* Content */}
                {renderContent()}
            </div>
        </div>
    );
}
