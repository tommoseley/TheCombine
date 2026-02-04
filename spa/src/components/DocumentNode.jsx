import { Handle, Position } from 'reactflow';
import StationDots from './StationDots';
import QuestionTray from './QuestionTray';
import FeatureGrid from './FeatureGrid';
import DocumentViewer from './DocumentViewer';

/**
 * Production state display names (operator-facing)
 */
const STATE_DISPLAY = {
    produced: 'Produced',
    in_production: 'In Production',
    ready_for_production: 'Ready',
    requirements_not_met: 'Requirements Not Met',
    awaiting_operator: 'Awaiting Operator',
    halted: 'Halted',
    // Legacy mappings
    stabilized: 'Produced',
    active: 'In Production',
    queued: 'Ready',
    blocked: 'Requirements Not Met',
    ready: 'Produced',
    waiting: 'Ready',
};

export default function DocumentNode({ data }) {
    const level = data.level || 1;
    const isL1 = level === 1;
    const isExpanded = data.isExpanded;
    const expandType = data.expandType;
    const hasQuestions = data.questions?.length > 0;
    const hasFeatures = data.features?.length > 0;
    const needsInput = data.stations?.some(s => s.needs_input);

    // Normalize state for display (handle legacy values)
    const rawState = data.state || 'ready_for_production';
    const isProduced = ['produced', 'stabilized', 'ready'].includes(rawState);
    const isInProduction = ['in_production', 'active'].includes(rawState);
    const isRequirementsNotMet = ['requirements_not_met', 'blocked'].includes(rawState);

    const showStations = isInProduction && data.stations;
    const stateClass = isInProduction ? 'node-active' : '';
    const levelLabel = isL1 ? 'DOCUMENT' : 'EPIC';
    const headerClass = isL1 ? 'subway-node-header-doc' : 'subway-node-header-epic';

    // State colors - using semantic CSS variables
    const stateBg = isProduced
        ? 'var(--state-produced-bg, var(--state-stabilized-bg))'
        : isInProduction
            ? 'var(--state-in-production-bg, var(--state-active-bg))'
            : isRequirementsNotMet
                ? 'var(--state-requirements-not-met-bg, var(--state-blocked-bg, var(--state-queued-bg)))'
                : 'var(--state-ready-bg, var(--state-queued-bg))';

    const stateText = isProduced
        ? 'var(--state-produced-text, var(--state-stabilized-text))'
        : isInProduction
            ? 'var(--state-in-production-text, var(--state-active-text))'
            : isRequirementsNotMet
                ? 'var(--state-requirements-not-met-text, var(--state-blocked-text, var(--state-queued-text)))'
                : 'var(--state-ready-text, var(--state-queued-text))';

    const borderColor = isInProduction
        ? 'var(--state-in-production-bg, var(--state-active-bg))'
        : isProduced
            ? 'var(--state-produced-bg, var(--state-stabilized-bg))'
            : 'var(--border-node)';

    // Display name for state
    const displayState = STATE_DISPLAY[rawState] || rawState;

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
                        {isL1 && isProduced && (
                            <button
                                className="px-2 py-1 bg-emerald-500/20 rounded text-[9px] hover:bg-emerald-500/30 transition-colors"
                                style={{ color: 'var(--action-success)' }}
                                onClick={(e) => {
                                    e.stopPropagation();
                                    data.onExpand?.(data.id, 'document');
                                }}
                            >
                                View Document
                            </button>
                        )}

                        {needsInput && hasQuestions && !isExpanded && (
                            <button
                                className="px-2 py-1 bg-amber-500/20 rounded text-[9px] hover:bg-amber-500/30 transition-colors amber-pulse"
                                style={{ color: 'var(--action-warning)' }}
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
                </div>
            </div>

            {/* Sidecars */}
            {isExpanded && expandType === 'questions' && hasQuestions && (
                <QuestionTray
                    questions={data.questions}
                    nodeWidth={data.width}
                    onSubmit={(answers) => data.onSubmitQuestions?.(data.id, answers)}
                    onClose={() => data.onCollapse?.()}
                    onZoomComplete={() => data.onZoomToNode?.(data.id)}
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

            {isExpanded && expandType === 'document' && isL1 && isProduced && (
                <DocumentViewer
                    document={data}
                    projectId={data.projectId}
                    projectCode={data.projectCode}
                    nodeWidth={data.width}
                    onClose={() => data.onCollapse?.()}
                    onZoomComplete={() => data.onZoomToNode?.(data.id)}
                    onViewFull={(docId) => data.onViewFullDocument?.(docId)}
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
