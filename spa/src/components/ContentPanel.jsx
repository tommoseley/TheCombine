/**
 * ContentPanel — detail view for the selected pipeline step (the "detail" in master-detail).
 *
 * Renders different content based on the selected step's type and state:
 * - Stabilized document: inline document viewer (FullDocumentViewer)
 * - In-progress document: station progress + questions
 * - Ready document: "Start Production" button
 * - Blocked document: dependency info
 * - Work Binder: WorkBinder component
 *
 * WS-PIPELINE-002: Replaces modal document viewing with inline content panel.
 */
import { useState, useCallback } from 'react';
import FullDocumentViewer from './FullDocumentViewer';
import WorkBinder from './WorkBinder';
import QuestionTray from './QuestionTray';
import StationDots from './StationDots';

function getArtifactState(rawState) {
    if (['produced', 'stabilized', 'ready', 'complete'].includes(rawState)) return 'stabilized';
    if (['requirements_not_met', 'blocked', 'halted', 'failed'].includes(rawState)) return 'blocked';
    if (['in_production', 'active', 'queued', 'awaiting_operator'].includes(rawState)) return 'in_progress';
    if (['ready_for_production', 'waiting', 'pending_acceptance'].includes(rawState)) return 'ready';
    return 'ready';
}

function formatDocTypeName(docType) {
    if (!docType) return '';
    const NAMES = {
        implementation_plan: 'Implementation Plan',
        project_discovery: 'Project Discovery',
        technical_architecture: 'Technical Architecture',
        concierge_intake: 'Concierge Intake',
    };
    if (NAMES[docType]) return NAMES[docType];
    return docType.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
}

const DOC_TYPE_DESCRIPTIONS = {
    concierge_intake:
        'Structured intake document produced by the Concierge workflow. Contains synthesized intent, constraints, and gate outcomes from the intake conversation. First document in the pipeline.',
    project_discovery:
        'Early architectural discovery performed before PM decomposition. Surfaces critical questions, identifies constraints and risks, proposes candidate directions, and establishes guardrails.',
    implementation_plan:
        'Unified implementation plan produced from project discovery. Contains candidate Work Packages (advisory), risk analysis, and architecture recommendations. Candidates are promoted to governed WPs after TA review.',
    technical_architecture:
        'Comprehensive technical architecture including components, interfaces, data models, workflows, and quality attributes. Built after implementation plan, informs final planning.',
    work_package:
        'Unit of planned work with scope, governance pins, and completion criteria. Tracks dependencies, state, and child Work Statement references.',
    work_statement:
        'Unit of authorized execution within a Work Package. Defines objective, scope, procedure, verification criteria, prohibited actions, and allowed file paths.',
};

/**
 * Empty state — document doesn't exist yet, can be produced
 */
function ReadyState({ step, onStartProduction }) {
    const description = DOC_TYPE_DESCRIPTIONS[step.id];
    return (
        <div className="flex flex-col items-center justify-center h-full gap-6">
            <div className="text-center max-w-md">
                <div
                    className="w-16 h-16 rounded-full mx-auto mb-4 flex items-center justify-center relative"
                >
                    <div
                        className="absolute inset-0 rounded-full"
                        style={{ background: 'var(--state-ready-bg)', opacity: 0.15 }}
                    />
                    <div
                        className="w-10 h-10 rounded-full relative"
                        style={{ background: 'var(--state-ready-bg)' }}
                    />
                </div>
                <h2
                    className="text-lg font-semibold mb-2"
                    style={{ color: 'var(--text-primary)' }}
                >
                    {formatDocTypeName(step.id)}
                </h2>
                {description && (
                    <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: 8 }}>
                        {description}
                    </p>
                )}
                <p style={{ fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.6 }}>
                    Ready to be produced. All prerequisite inputs are available.
                </p>
            </div>
            <button
                className="px-5 py-2.5 rounded-lg font-semibold transition-all hover:brightness-110"
                style={{
                    fontSize: 14,
                    backgroundColor: 'var(--state-ready-bg)',
                    color: 'white',
                }}
                onClick={() => onStartProduction(step.id)}
            >
                Start Production
            </button>
        </div>
    );
}

/**
 * Blocked state — document can't be produced yet
 */
function BlockedState({ step }) {
    const blockedBy = step.blockedBy || [];
    const description = DOC_TYPE_DESCRIPTIONS[step.id];
    return (
        <div className="flex flex-col items-center justify-center h-full gap-4">
            <div className="text-center max-w-md">
                <div
                    className="w-16 h-16 rounded-full mx-auto mb-4 flex items-center justify-center relative"
                >
                    <div
                        className="absolute inset-0 rounded-full"
                        style={{ background: 'var(--state-blocked-bg)', opacity: 0.15 }}
                    />
                    <svg className="w-8 h-8 relative" viewBox="0 0 24 24" fill="none" stroke="var(--state-blocked-bg)" strokeWidth="2">
                        <circle cx="12" cy="12" r="10" />
                        <path d="M15 9l-6 6M9 9l6 6" />
                    </svg>
                </div>
                <h2
                    className="text-lg font-semibold mb-2"
                    style={{ color: 'var(--text-primary)' }}
                >
                    {formatDocTypeName(step.id)}
                </h2>
                {description && (
                    <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: 8 }}>
                        {description}
                    </p>
                )}
                <p style={{ fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.6 }}>
                    Cannot be produced yet. Prerequisites are not met.
                </p>
                {blockedBy.length > 0 && (
                    <div
                        className="mt-4 rounded-lg border-l-4 p-3"
                        style={{
                            borderColor: 'var(--state-blocked-bg)',
                            background: 'var(--bg-node)',
                        }}
                    >
                        <div
                            className="text-xs font-medium uppercase tracking-wider mb-1"
                            style={{ color: 'var(--text-muted)' }}
                        >
                            Waiting for
                        </div>
                        <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                            {blockedBy.map(formatDocTypeName).join(', ')}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

/**
 * In-progress state — document is being produced
 */
function InProgressState({ step, onSubmitQuestions }) {
    const hasQuestions = step.questions?.length > 0;
    const needsInput = step.stations?.some(s => s.state === 'active' && s.needs_input);

    return (
        <div className="flex flex-col items-center justify-center h-full gap-4">
            <div className="text-center max-w-md">
                <div
                    className="w-16 h-16 rounded-full mx-auto mb-4 flex items-center justify-center relative"
                >
                    <div
                        className="absolute inset-0 rounded-full"
                        style={{ background: 'var(--state-active-bg)', opacity: 0.15 }}
                    />
                    <svg className="w-8 h-8 relative" viewBox="0 0 24 24" fill="none" stroke="var(--state-active-bg)" strokeWidth="2">
                        <circle cx="12" cy="12" r="10" />
                        <path d="M12 6v6l4 2" />
                    </svg>
                </div>
                <h2
                    className="text-lg font-semibold mb-2"
                    style={{ color: 'var(--text-primary)' }}
                >
                    {formatDocTypeName(step.id)}
                </h2>
                <p style={{ fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                    {needsInput
                        ? 'Production is waiting for your input.'
                        : 'Production is in progress. Stations are executing.'}
                </p>
            </div>

            {step.stations?.length > 0 && (
                <div
                    className="rounded-lg border p-4 w-full max-w-md"
                    style={{ background: 'var(--bg-node)', borderColor: 'var(--border-node)' }}
                >
                    <div
                        className="text-xs font-medium uppercase tracking-wider mb-3"
                        style={{ color: 'var(--text-muted)' }}
                    >
                        Station Progress
                    </div>
                    <StationDots stations={step.stations} />
                </div>
            )}

            {needsInput && hasQuestions && (
                <div className="w-full max-w-2xl">
                    <QuestionTray
                        questions={step.questions}
                        onSubmit={(answers) => onSubmitQuestions(step.id, answers)}
                        inline
                    />
                </div>
            )}
        </div>
    );
}

export default function ContentPanel({
    step,
    projectId,
    projectCode,
    onStartProduction,
    onSubmitQuestions,
}) {
    // No step selected
    if (!step) {
        return (
            <div
                className="flex-1 flex items-center justify-center h-full"
                style={{ background: 'var(--bg-canvas)' }}
            >
                <p style={{ fontSize: 14, color: 'var(--text-muted)' }}>
                    Select a pipeline step to view details
                </p>
            </div>
        );
    }

    // Work Binder — the work_package pipeline step is the Work Binder
    if (step.isWorkBinder || step.id === 'work_package') {
        return (
            <div className="flex-1 h-full overflow-y-auto" style={{ background: 'var(--bg-canvas)' }}>
                <WorkBinder projectId={projectId} projectCode={projectCode} />
            </div>
        );
    }

    // Determine document state
    const artifactState = getArtifactState(step.state || 'ready_for_production');

    // Stabilized — show document content inline
    if (artifactState === 'stabilized') {
        return (
            <div className="flex-1 h-full overflow-hidden" style={{ background: 'var(--bg-canvas)' }}>
                <FullDocumentViewer
                    projectId={projectId}
                    projectCode={projectCode}
                    docTypeId={step.id}
                    instanceId={step.instanceId}
                    onClose={() => {}}
                    inline
                />
            </div>
        );
    }

    // In Progress
    if (artifactState === 'in_progress') {
        return (
            <div className="flex-1 h-full overflow-y-auto" style={{ background: 'var(--bg-canvas)' }}>
                <InProgressState step={step} onSubmitQuestions={onSubmitQuestions} />
            </div>
        );
    }

    // Blocked
    if (artifactState === 'blocked') {
        return (
            <div className="flex-1 h-full overflow-y-auto" style={{ background: 'var(--bg-canvas)' }}>
                <BlockedState step={step} />
            </div>
        );
    }

    // Ready (default) — show "Start Production"
    return (
        <div className="flex-1 h-full overflow-y-auto" style={{ background: 'var(--bg-canvas)' }}>
            <ReadyState step={step} onStartProduction={onStartProduction} />
        </div>
    );
}
