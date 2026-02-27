/**
 * PipelineRail — static vertical pipeline for the left rail.
 *
 * Replaces the ReactFlow subway map with a simple CSS-based vertical list.
 * Each node shows: type label, name, state indicator, station dots.
 * A vertical connecting line runs behind the nodes.
 *
 * WS-PIPELINE-002: Persistent left-aligned pipeline rail.
 */
import StationDots from './StationDots';

const DEFAULT_STATIONS = [
    { id: 'pgc', label: 'PGC', state: 'queued' },
    { id: 'draft', label: 'DRAFT', state: 'queued' },
    { id: 'qa', label: 'QA', state: 'queued' },
    { id: 'done', label: 'DONE', state: 'queued' },
];

function getArtifactState(rawState) {
    if (['produced', 'stabilized', 'ready', 'complete'].includes(rawState)) return 'stabilized';
    if (['requirements_not_met', 'blocked', 'halted', 'failed'].includes(rawState)) return 'blocked';
    if (['in_production', 'active', 'queued', 'awaiting_operator'].includes(rawState)) return 'in_progress';
    if (['ready_for_production', 'waiting', 'pending_acceptance'].includes(rawState)) return 'ready';
    return 'ready';
}

const ARTIFACT_COLORS = {
    blocked: { bg: 'var(--state-blocked-bg)', text: 'var(--state-blocked-text)' },
    in_progress: { bg: 'var(--state-active-bg)', text: 'var(--state-active-text)' },
    ready: { bg: 'var(--state-ready-bg)', text: 'var(--state-ready-text)' },
    stabilized: { bg: 'var(--state-stabilized-bg)', text: 'var(--state-stabilized-text)' },
};

const ARTIFACT_DISPLAY = {
    blocked: 'Blocked',
    in_progress: 'In Progress',
    ready: 'Ready',
    stabilized: 'Stabilized',
};

const DOC_TYPE_DISPLAY_NAMES = {
    implementation_plan: 'Implementation Plan',
    project_discovery: 'Project Discovery',
    technical_architecture: 'Technical Architecture',
    concierge_intake: 'Concierge Intake',
};

function formatDocTypeName(docType) {
    if (!docType) return '';
    if (DOC_TYPE_DISPLAY_NAMES[docType]) return DOC_TYPE_DISPLAY_NAMES[docType];
    return docType.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
}

/**
 * Single rail node — a card in the vertical pipeline.
 */
function RailNode({ item, isSelected, onClick }) {
    const rawState = item.state || 'ready_for_production';
    const artifactState = getArtifactState(rawState);
    const colors = ARTIFACT_COLORS[artifactState];
    const displayState = ARTIFACT_DISPLAY[artifactState];
    const isBlocked = artifactState === 'blocked';
    const isInProgress = artifactState === 'in_progress';
    const isWorkBinder = item.id === 'work_package';
    const levelLabel = isWorkBinder ? 'WORK BINDER' : 'DOCUMENT';
    const headerClass = isWorkBinder ? 'subway-node-header-wp' : 'subway-node-header-doc';

    return (
        <div
            className={`subway-node rounded-lg border overflow-hidden cursor-pointer transition-all ${isInProgress ? 'node-active' : ''}`}
            style={{
                borderColor: isSelected ? 'var(--accent, #7c3aed)' : colors.bg,
                borderWidth: isSelected ? 2 : 1,
                boxShadow: isSelected ? '0 0 0 2px var(--accent, rgba(124,58,237,0.3))' : undefined,
            }}
            onClick={onClick}
        >
            {/* Header */}
            <div className={`${headerClass} border-b px-3 py-1.5 flex items-center gap-2`}>
                <span
                    className="text-[8px] font-bold uppercase tracking-wider"
                    style={{ color: isWorkBinder ? 'var(--header-text-wp, var(--header-text-doc))' : 'var(--header-text-doc)' }}
                >
                    {levelLabel}
                </span>
                <span
                    className="text-[10px] font-medium"
                    style={{ color: 'var(--text-primary)' }}
                >
                    {isWorkBinder ? 'Work Binder' : formatDocTypeName(item.id)}
                </span>
            </div>

            {/* Body */}
            <div className="p-3">
                <div className="flex items-center gap-2">
                    <div
                        className="w-5 h-5 rounded-full flex-shrink-0"
                        style={{ backgroundColor: colors.bg }}
                    />
                    <span
                        className="text-[10px] font-semibold uppercase tracking-wide"
                        style={{ color: colors.text }}
                    >
                        {displayState}
                    </span>
                </div>

                {/* Station dots — Work Binder is a container, no stations */}
                {!isWorkBinder && (
                    <StationDots
                        stations={item.stations?.length > 0 ? item.stations : DEFAULT_STATIONS}
                        dormant={isBlocked || !(item.stations?.length > 0)}
                    />
                )}
            </div>
        </div>
    );
}

/**
 * Vertical connector segment between rail nodes.
 * Color reflects the state of the edge between source and target.
 */
function Connector({ sourceState, targetState, theme }) {
    // Use target state when blocked (red path = spatial truth)
    const targetArtifact = getArtifactState(targetState || 'ready_for_production');
    const edgeState = targetArtifact === 'blocked' ? targetState : sourceState;
    const artifactState = getArtifactState(edgeState || 'ready_for_production');
    const color = ARTIFACT_COLORS[artifactState]?.bg || 'var(--state-queued-bg)';

    return (
        <div className="flex justify-center" style={{ height: 24 }}>
            <div style={{ width: 3, height: '100%', background: color, borderRadius: 2 }} />
        </div>
    );
}

export default function PipelineRail({ data, selectedNodeId, onSelectNode, theme }) {
    // Filter to L1 items only
    const l1Items = data.filter(d => (d.level || 1) === 1);

    if (l1Items.length === 0) return null;

    return (
        <div className="flex flex-col gap-0 px-4 py-3">
            {l1Items.map((item, idx) => (
                <div key={item.id}>
                    <RailNode
                        item={item}
                        isSelected={selectedNodeId === item.id}
                        onClick={() => onSelectNode(item.id)}
                    />
                    {idx < l1Items.length - 1 && (
                        <Connector
                            sourceState={item.state}
                            targetState={l1Items[idx + 1]?.state}
                            theme={theme}
                        />
                    )}
                </div>
            ))}

        </div>
    );
}
