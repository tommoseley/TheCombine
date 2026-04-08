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
import { useState, useCallback, useEffect, useRef } from 'react';
import { api } from '../api/client';
import FullDocumentViewer from './FullDocumentViewer';
import WorkBinder from './WorkBinder';
import SynthesisReview from './SynthesisReview';
import WorkPlanViewer from './WorkPlanViewer';
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
    synthesis_delta:
        'Post-binder composition review. Dual-instance analysis identifies scope overlaps, missing coverage, platform concerns, and boundary misalignments across the complete binder.',
    work_plan:
        'Final project plan combining all documents, decisions, and dependencies into a single readable artifact. Ready for review and handoff.',
};

/**
 * Empty state — document doesn't exist yet, can be produced.
 * ADR-069: If a correction brief exists for this stage (from a prior rewind),
 * it is shown inline and editable above the action button.
 * The button reads "Restart Production" when a correction is active.
 */
function ReadyState({ step, onStartProduction, projectId }) {
    const description = DOC_TYPE_DESCRIPTIONS[step.id];
    const [correction, setCorrection] = useState(null);
    const [wasRewound, setWasRewound] = useState(false);
    const [editText, setEditText] = useState('');
    const [saving, setSaving] = useState(false);
    const [loaded, setLoaded] = useState(false);

    // Fetch existing correction AND check if stage has stale docs (rewound)
    useEffect(() => {
        if (!projectId || !step.id) return;

        const fetchCorrection = api.getCorrection(projectId, step.id)
            .then(data => {
                if (data) {
                    setCorrection(data);
                    setEditText(data.text || '');
                    setWasRewound(true);
                }
            })
            .catch(() => {});

        // Also check pipeline-status for stale docs at this stage
        // (detects rewinds that happened before authority records existed)
        const fetchPipelineStatus = api.getPipelineStatus(projectId)
            .then(status => {
                if (status?.stages) {
                    const stageInfo = status.stages.find(s =>
                        s.doc_type_id === step.id || s.stage === step.id?.toUpperCase()
                    );
                    if (stageInfo?.has_stale) {
                        setWasRewound(true);
                    }
                }
            })
            .catch(() => {});

        Promise.all([fetchCorrection, fetchPipelineStatus])
            .finally(() => setLoaded(true));
    }, [projectId, step.id]);

    const showCorrectionArea = wasRewound;
    const hasExistingCorrection = correction !== null;
    const textChanged = editText.trim() !== (correction?.text || '').trim() && editText.trim() !== '';

    const handleSaveCorrection = async () => {
        if (!textChanged) return;
        setSaving(true);
        try {
            if (hasExistingCorrection) {
                // Update existing correction
                const updated = await api.updateCorrection(projectId, step.id, editText);
                setCorrection(updated);
            } else {
                // No existing correction — create one via a lightweight rewind
                // that doesn't re-mark docs stale (they already are).
                // For now, use updateCorrection which will 404, so we use rewindPipeline
                // with the text as reason. This is a first-time correction on a pre-069 rewind.
                await api.rewindPipeline(projectId, step.id, editText);
                // Re-fetch to get the authority record
                const data = await api.getCorrection(projectId, step.id);
                if (data) {
                    setCorrection(data);
                }
            }
        } catch (err) {
            // silently fail — user can still proceed
        } finally {
            setSaving(false);
        }
    };

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
                    {showCorrectionArea
                        ? 'This stage was rewound. Describe what\u2019s wrong and what must change \u2014 this becomes a binding constraint for regeneration.'
                        : 'Ready to be produced. All prerequisite inputs are available.'}
                </p>
            </div>

            {/* ADR-069: Inline correction brief (editable before regeneration) */}
            {loaded && showCorrectionArea && (
                <div className="w-full max-w-lg">
                    <div className="flex items-center gap-2 mb-1">
                        <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--state-blocked-text, #92400e)' }}>
                            Correction Brief
                        </span>
                        <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>
                            — editable until regeneration
                        </span>
                    </div>
                    <textarea
                        value={editText}
                        onChange={(e) => setEditText(e.target.value)}
                        rows={4}
                        className="w-full text-[12px] px-3 py-2 rounded border"
                        style={{
                            borderColor: 'var(--state-blocked-bg, #fbbf24)',
                            backgroundColor: 'var(--surface-secondary, var(--bg-canvas, #1a1a2e))',
                            color: 'var(--text-primary)',
                            resize: 'vertical',
                            lineHeight: 1.5,
                        }}
                    />
                    {textChanged && (
                        <button
                            onClick={handleSaveCorrection}
                            disabled={saving}
                            className="mt-1 text-[10px] px-2 py-1 rounded"
                            style={{
                                backgroundColor: 'var(--accent-primary, #3b82f6)',
                                color: '#fff',
                                opacity: saving ? 0.5 : 1,
                            }}
                        >
                            {saving ? 'Saving...' : 'Save Changes'}
                        </button>
                    )}
                </div>
            )}

            <button
                className="px-5 py-2.5 rounded-lg font-semibold transition-all hover:brightness-110"
                style={{
                    fontSize: 14,
                    backgroundColor: 'var(--state-ready-bg)',
                    color: 'white',
                }}
                onClick={() => {
                    // Save pending edits before starting production
                    if (textChanged && editText.trim()) {
                        handleSaveCorrection().then(() => onStartProduction(step.id));
                    } else {
                        onStartProduction(step.id);
                    }
                }}
            >
                {showCorrectionArea ? 'Restart Production' : 'Start Production'}
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

const PRODUCTION_TIPS = [
    'Each document passes through a PGC clarification gate before generation to surface unknowns early.',
    'The QA gate evaluates documents against semantic quality criteria, not just schema compliance.',
    'If QA fails, the system automatically attempts remediation — up to two cycles before escalating.',
    'Every LLM call is logged with full provenance: inputs, outputs, tokens, and timing (ADR-010).',
    'Documents are produced in pipeline order: Intake, Discovery, Implementation Plan, Architecture.',
    'Work Package Candidates in the Implementation Plan become governed Work Packages after TA review.',
    'The Combine treats knowledge work like manufacturing — stations, quality gates, and audit trails.',
    'Bound constraints from the clarification gate follow the document through QA and remediation.',
    'Each document type has a certified prompt pair: a role prompt (who) and a task prompt (what).',
    'The Work Binder is where advisory candidates become governed Work Packages with real scope.',
    'Schema validation catches structural issues; semantic QA catches logical and quality issues.',
    'All prompt changes require a version bump, re-certification, and manifest regeneration.',
    'Documents can be downloaded in standard or evidence mode — evidence mode includes SHA-256 provenance.',
    'The pipeline is idempotent — re-running a step with the same inputs produces the same result.',
    'Work Statements define exactly what is authorized: scope, procedure, verification, and prohibitions.',
];

function RotatingTip() {
    const [index, setIndex] = useState(() => Math.floor(Math.random() * PRODUCTION_TIPS.length));
    const [fading, setFading] = useState(false);

    useEffect(() => {
        const interval = setInterval(() => {
            setFading(true);
            setTimeout(() => {
                setIndex(prev => (prev + 1) % PRODUCTION_TIPS.length);
                setFading(false);
            }, 400);
        }, 15000);
        return () => clearInterval(interval);
    }, []);

    return (
        <div
            className="rounded-lg border p-4 w-full max-w-md transition-opacity duration-400"
            style={{
                background: 'var(--bg-node)',
                borderColor: 'var(--border-node)',
                opacity: fading ? 0 : 1,
            }}
        >
            <div
                className="text-[10px] font-medium uppercase tracking-wider mb-2"
                style={{ color: 'var(--text-muted)' }}
            >
                Did you know?
            </div>
            <p style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.6, margin: 0 }}>
                {PRODUCTION_TIPS[index]}
            </p>
        </div>
    );
}

/**
 * In-progress state — document is being produced
 */
function InProgressState({ step, onSubmitQuestions, onCancelProduction }) {
    const hasQuestions = step.questions?.length > 0;
    const needsInput = step.stations?.some(s => s.state === 'active' && s.needs_input);

    // Pull the active station's current step for prominent display
    const activeStation = step.stations?.find(s => s.state === 'active');
    const currentStep = activeStation?.currentStep;
    const stationLabel = activeStation?.label;

    // Build a dynamic status line from the current step
    const statusLine = needsInput
        ? 'Production is waiting for your input.'
        : currentStep?.name
            ? currentStep.name
            : 'Stations are executing.';

    // Step type indicator (LLM/UI/MECH)
    const stepType = currentStep?.type;
    const typeLabel = stepType === 'LLM' ? 'LLM' : stepType === 'UI' ? 'Input' : stepType === 'MECH' ? 'Processing' : null;

    return (
        <div className="flex flex-col items-center justify-center h-full gap-4">
            <div className="text-center max-w-md">
                <div
                    className="w-16 h-16 rounded-full mx-auto mb-4 flex items-center justify-center relative"
                >
                    <div
                        className="absolute inset-0 rounded-full station-active"
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

                {/* Dynamic status line — shows current step name */}
                <p
                    className="amber-pulse"
                    style={{ fontSize: 14, color: 'var(--state-active-text)', lineHeight: 1.6, fontWeight: 500 }}
                >
                    {statusLine}
                </p>

                {/* Step type + progress indicator */}
                {currentStep && (
                    <div className="flex items-center justify-center gap-2 mt-1">
                        {typeLabel && (
                            <span
                                className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded"
                                style={{
                                    background: 'var(--state-active-bg)',
                                    color: 'white',
                                    opacity: 0.8,
                                }}
                            >
                                {typeLabel}
                            </span>
                        )}
                        {stationLabel && (
                            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                                {stationLabel}
                            </span>
                        )}
                        {currentStep.total > 1 && (
                            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                                step {currentStep.number}/{currentStep.total}
                            </span>
                        )}
                    </div>
                )}
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

            {/* Cancel button */}
            {onCancelProduction && (
                <button
                    className="px-4 py-1.5 rounded-md text-xs font-medium transition-colors hover:opacity-90"
                    style={{
                        background: 'transparent',
                        color: 'var(--text-muted)',
                        border: '1px solid var(--border-node)',
                    }}
                    onClick={() => {
                        if (window.confirm(`Cancel production for ${formatDocTypeName(step.id)}?`)) {
                            onCancelProduction(step.id);
                        }
                    }}
                >
                    Cancel Production
                </button>
            )}

            {/* Rotating tips — shown while LLM is working (not during user input) */}
            {!needsInput && <RotatingTip />}

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
    onCancelProduction,
    onSubmitQuestions,
    pipelineData = [],
    onProduceNext,
    autoImport,
}) {
    // Show "Produce Next" only on the frontier — the last completed doc
    // whose immediate next producible step is ready (not already complete).
    const nextStep = (() => {
        if (!step || !pipelineData.length) return null;
        const currentIdx = pipelineData.findIndex(d => d.id === step.id);
        if (currentIdx < 0) return null;
        // Walk forward: find the next step (including Work Binder)
        for (let i = currentIdx + 1; i < pipelineData.length; i++) {
            const s = pipelineData[i];
            // Work Binder is always a valid "next" if we reach it
            if (s.id === 'work_package') return s;
            const state = getArtifactState(s.state || 'ready_for_production');
            // If next step is already done or in-progress, no button needed
            if (state === 'stabilized' || state === 'in_progress') return null;
            if (state === 'ready') return s;
            return null; // blocked or unknown — don't show
        }
        return null;
    })();

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
                <WorkBinder projectId={projectId} projectCode={projectCode} autoImport={autoImport} />
            </div>
        );
    }

    // Synthesis — post-binder composition review (ADR-070)
    // If a delta exists (produced state), show the review UI.
    // Otherwise, fall through to normal ReadyState rendering.
    if (step.id === 'synthesis_delta' && getArtifactState(step.state) === 'stabilized') {
        return (
            <div className="flex-1 h-full overflow-y-auto" style={{ background: 'var(--bg-canvas)' }}>
                <SynthesisReview projectId={projectId} />
            </div>
        );
    }

    // Work Plan — final deliverable (ADR-071)
    // When produced, show the dedicated Work Plan viewer.
    if (step.id === 'work_plan' && getArtifactState(step.state) === 'stabilized') {
        return (
            <div className="flex-1 h-full overflow-y-auto" style={{ background: 'var(--bg-canvas)' }}>
                <WorkPlanViewer projectId={projectId} />
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
                    nextStepLabel={nextStep ? (nextStep.id === 'work_package' ? 'Work Binder' : formatDocTypeName(nextStep.id)) : null}
                    onProduceNext={nextStep && onProduceNext ? () => onProduceNext(nextStep.id) : null}
                />
            </div>
        );
    }

    // In Progress
    if (artifactState === 'in_progress') {
        return (
            <div className="flex-1 h-full overflow-y-auto" style={{ background: 'var(--bg-canvas)' }}>
                <InProgressState step={step} onSubmitQuestions={onSubmitQuestions} onCancelProduction={onCancelProduction} />
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
            <ReadyState step={step} onStartProduction={onStartProduction} projectId={projectId} />
        </div>
    );
}
