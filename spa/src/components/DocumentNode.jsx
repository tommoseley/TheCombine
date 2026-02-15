import { Handle, Position } from 'reactflow';
import StationDots from './StationDots';
import QuestionTray from './QuestionTray';
import FeatureGrid from './FeatureGrid';

/**
 * Unified Artifact State Model
 *
 * 4 artifact states (what users see):
 * - Blocked: Can't proceed (missing inputs, failed QA, needs operator)
 * - In Progress: Work happening (queued or actively executing)
 * - Ready: Gates passed, awaiting acceptance
 * - Stabilized: Governed, immutable, trusted
 *
 * Execution state (queued/active/complete) is hidden - only for engine/logs.
 */

// Artifact state colors via CSS variables (defined in themes.css)
const ARTIFACT_COLORS = {
    blocked: { bg: 'var(--state-blocked-bg)', text: 'var(--state-blocked-text)' },
    in_progress: { bg: 'var(--state-active-bg)', text: 'var(--state-active-text)' },
    ready: { bg: 'var(--state-ready-bg)', text: 'var(--state-ready-text)' },
    stabilized: { bg: 'var(--state-stabilized-bg)', text: 'var(--state-stabilized-text)' },
};

/**
 * Map raw execution/legacy states to unified artifact states
 */
function getArtifactState(rawState) {
    // Stabilized (green) - governed, immutable
    if (['produced', 'stabilized', 'ready', 'complete'].includes(rawState)) {
        return 'stabilized';
    }
    // Blocked (red) - can't proceed
    if (['requirements_not_met', 'blocked', 'halted', 'failed'].includes(rawState)) {
        return 'blocked';
    }
    // In Progress (amber) - work happening
    if (['in_production', 'active', 'queued', 'awaiting_operator'].includes(rawState)) {
        return 'in_progress';
    }
    // Ready (yellow) - gates passed, awaiting acceptance
    if (['ready_for_production', 'waiting', 'pending_acceptance'].includes(rawState)) {
        return 'ready';
    }
    // Default to ready for unknown states
    return 'ready';
}

/**
 * Display names for artifact states
 */
const ARTIFACT_DISPLAY = {
    blocked: 'Blocked',
    in_progress: 'In Progress',
    ready: 'Ready',
    stabilized: 'Stabilized',
};

/**
 * Format document type ID as human-readable name
 * e.g., "technical_architecture" -> "Technical Architecture"
 */
function formatDocTypeName(docType) {
    if (!docType) return '';
    return docType
        .split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}

export default function DocumentNode({ data }) {
    const level = data.level || 1;
    const isL1 = level === 1;
    const isExpanded = data.isExpanded;
    const expandType = data.expandType;
    const hasQuestions = data.questions?.length > 0;
    const hasFeatures = data.features?.length > 0;
    const needsInput = data.stations?.some(s => s.state === 'active' && s.needs_input);

    // Map raw state to unified artifact state
    const rawState = data.state || 'ready_for_production';
    const artifactState = getArtifactState(rawState);

    // Derived booleans for logic
    const isStabilized = artifactState === 'stabilized';
    const isInProgress = artifactState === 'in_progress';
    const isBlocked = artifactState === 'blocked';

    // Show stations whenever they exist (produced shows all complete, in-progress shows progress)
    const showStations = data.stations?.length > 0;
    const stateClass = isInProgress ? 'node-active' : '';
    const levelLabel = isL1 ? 'DOCUMENT' : 'EPIC';
    const headerClass = isL1 ? 'subway-node-header-doc' : 'subway-node-header-epic';

    // Colors from artifact state
    const colors = ARTIFACT_COLORS[artifactState];
    const stateBg = colors.bg;
    const stateText = colors.text;

    // Border color emphasizes the state
    const borderColor = colors.bg;

    // Display name for state
    const displayState = ARTIFACT_DISPLAY[artifactState];

    return (
        <div className="relative">
            <Handle
                type="target"
                position={Position.Top}
                className="!opacity-0"
                style={{ left: '15%' }}
            />

            <div
                className={`subway-node rounded-lg border ${stateClass} overflow-hidden`}
                style={{ width: data.width, minHeight: data.height, borderColor }}
            >
                {/* Header */}
                <div className={`${headerClass} border-b px-3 py-1.5 flex items-center justify-between`}>
                    <div className="flex items-center gap-2">
                        <span
                            className="text-[8px] font-bold uppercase tracking-wider"
                            style={{ color: isL1 ? 'var(--header-text-doc)' : 'var(--header-text-epic)' }}
                        >
                            {levelLabel}
                        </span>
                        <span
                            className="text-[10px] font-medium"
                            style={{ color: 'var(--text-primary)' }}
                        >
                            {data.name}
                        </span>
                    </div>
                    {data.intent === 'optional' && (
                        <span className="subway-button text-[8px] px-1.5 py-0.5 rounded">
                            OPTIONAL
                        </span>
                    )}
                </div>

                {/* Body */}
                <div className="p-3">
                    <div className="flex items-center gap-2">
                        <div
                            className="rounded-full flex-shrink-0"
                            style={{
                                width: isL1 ? 24 : 18,
                                height: isL1 ? 24 : 18,
                                backgroundColor: stateBg
                            }}
                        />
                        <div className="flex-1 min-w-0">
                            <span
                                className="text-[10px] font-semibold uppercase tracking-wide"
                                style={{ color: stateText }}
                            >
                                {displayState}
                            </span>
                            {isL1 && data.desc && (
                                <p
                                    className="text-[9px] mt-0.5 truncate"
                                    style={{ color: 'var(--text-muted)' }}
                                >
                                    {data.desc}
                                </p>
                            )}
                        </div>
                    </div>

                    {showStations && <StationDots stations={data.stations} />}

                    {/* Action buttons */}
                    <div className="mt-2 flex flex-wrap gap-1.5">
                        {isL1 && isStabilized && (
                            <button
                                className="px-2 py-1 rounded text-[9px] font-semibold hover:brightness-110 transition-all"
                                style={{ backgroundColor: 'var(--state-stabilized-bg)', color: 'white' }}
                                onClick={(e) => {
                                    e.stopPropagation();
                                    data.onViewFullDocument?.(data.id);
                                }}
                            >
                                View Document
                            </button>
                        )}

                        {isL1 && artifactState === 'ready' && (
                            <button
                                className="px-2 py-1 rounded text-[9px] font-semibold hover:brightness-110 transition-all"
                                style={{ backgroundColor: 'var(--state-ready-bg)', color: 'white' }}
                                onClick={(e) => {
                                    e.stopPropagation();
                                    data.onStartProduction?.(data.id);
                                }}
                            >
                                Start Production
                            </button>
                        )}

                        {needsInput && hasQuestions && !isExpanded && (
                            <button
                                className="px-2 py-1 rounded text-[9px] font-semibold hover:brightness-110 transition-all amber-pulse"
                                style={{ backgroundColor: 'var(--state-active-bg)', color: 'white' }}
                                onClick={(e) => {
                                    e.stopPropagation();
                                    data.onExpand?.(data.id, 'questions');
                                }}
                            >
                                Answer Questions
                            </button>
                        )}

                        {!isL1 && hasFeatures && (
                            isExpanded && expandType === 'features' ? (
                                <span className="text-[9px] text-indigo-400">
                                    {data.features.length} features expanded
                                </span>
                            ) : (
                                <button
                                    className="subway-button px-2 py-1 rounded text-[9px] transition-colors flex items-center gap-1"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        data.onExpand?.(data.id, 'features');
                                    }}
                                >
                                    <span className="text-indigo-400">{data.features.length}</span>
                                    <span>features</span>
                                    <span className="text-indigo-400">&#9654;</span>
                                </button>
                            )
                        )}
                    </div>

                    {/* Show what this node is waiting for */}
                    {data.blockedBy?.length > 0 && (isBlocked || artifactState === 'ready') && (
                        <div
                            className="mt-2 pt-2 border-t text-[8px]"
                            style={{ borderColor: 'var(--border-node)', color: 'var(--text-muted)' }}
                        >
                            <span className="font-medium">Waiting for: </span>
                            {data.blockedBy.map(formatDocTypeName).join(', ')}
                        </div>
                    )}
                </div>
            </div>

            {/* Sidecars */}
            {isExpanded && expandType === 'questions' && hasQuestions && (
                <QuestionTray
                    questions={data.questions}
                    nodeWidth={data.width}
                    onSubmit={(answers) => data.onSubmitQuestions?.(data.id, answers)}
                    onClose={() => data.onCollapse?.()}
                />
            )}

            {isExpanded && expandType === 'features' && hasFeatures && (
                <FeatureGrid
                    features={data.features}
                    epicName={data.name}
                    nodeWidth={data.width}
                    onClose={() => data.onCollapse?.()}
                    onZoomComplete={() => data.onZoomToNode?.(data.id)}
                />
            )}

            

            <Handle
                type="source"
                position={Position.Bottom}
                className="!opacity-0"
                style={{ left: '15%' }}
            />
        </div>
    );
}
