import { useEffect, useState } from 'react';
import yaml from 'js-yaml';
import { useConciergeIntake } from '../hooks';
import MessageList from './concierge/MessageList';
import ChatInput from './concierge/ChatInput';
import CompletionCard from './concierge/CompletionCard';
import ConciergeEntryForm from './admin/entry/ConciergeEntryForm';

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
        phase,
        messages,
        pendingPrompt,
        gateOutcome,
        project,
        error,
        loading,
        submitting,
        intakeClassification,
        intakeGatePhase,
        startIntake,
        submitMessage,
        reset,
    } = useConciergeIntake();

    // Intro content loaded from YAML
    const [introData, setIntroData] = useState(null);

    // Start intake and load intro content on mount
    useEffect(() => {
        startIntake();

        // Load intro content from YAML
        fetch('/content/concierge-intro.yaml')
            .then(res => res.text())
            .then(text => setIntroData(yaml.load(text)))
            .catch(err => console.error('Failed to load intro content:', err));

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

    // Handler for entry form confirmation (Gate Profile ADR-047)
    const handleEntrySubmit = (response) => {
        // Submit the confirmation as JSON string
        submitMessage(JSON.stringify(response));
    };

    const renderPhaseIndicator = () => {
        // Gate Profile flow: Describe -> Confirm -> (auto-generate) -> Done
        const phases = [
            { id: 'describe', label: 'Describe' },
            { id: 'confirm', label: 'Confirm' },
            { id: 'complete', label: 'Done' },
        ];

        // Map gate phase to UI phase for indicator
        let currentPhase = phase;
        if (intakeGatePhase === 'awaiting_confirmation') {
            currentPhase = 'confirm';
        }
        // Map old phases to new simplified phases
        if (currentPhase === 'review' || currentPhase === 'generating') {
            currentPhase = 'complete';
        }

        const currentIdx = phases.findIndex((p) => p.id === currentPhase);

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

        // Gate Profile: Show entry form when awaiting confirmation (ADR-047)
        if (intakeGatePhase === 'awaiting_confirmation' && intakeClassification) {
            return (
                <ConciergeEntryForm
                    operation={{ config: { entry_prompt: pendingPrompt } }}
                    context={intakeClassification}
                    onSubmit={handleEntrySubmit}
                    onCancel={handleClose}
                />
            );
        }

        switch (phase) {
            case 'describe':
                // Intro content loaded from YAML, scrolls with conversation
                const introContent = introData ? (
                    <div className="mb-4 pb-4 border-b" style={{ borderColor: 'var(--border-panel)' }}>
                        <h3
                            className="text-base font-semibold mb-3"
                            style={{ color: 'var(--text-primary)' }}
                        >
                            {introData.title}
                        </h3>
                        <div
                            className="text-sm space-y-3"
                            style={{ color: 'var(--text-secondary)' }}
                        >
                            {introData.paragraphs?.map((p, idx) => (
                                <p key={idx}>{p}</p>
                            ))}
                        </div>
                        {introData.call_to_action && (
                            <p
                                className="text-sm font-medium mt-4"
                                style={{ color: 'var(--text-primary)' }}
                            >
                                {introData.call_to_action}
                            </p>
                        )}
                    </div>
                ) : null;

                return (
                    <>
                        <MessageList
                            messages={messages}
                            pendingPrompt={pendingPrompt}
                            introContent={introContent}
                        />
                        <ChatInput
                            onSubmit={submitMessage}
                            disabled={submitting}
                            placeholder="Describe what you want to build..."
                        />
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
                onWheel={(e) => e.stopPropagation()}
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
