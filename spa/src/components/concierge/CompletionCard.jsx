/**
 * Success/completion card shown when intake is finished.
 */

const OUTCOME_STYLES = {
    qualified: {
        icon: 'check',
        iconBg: 'bg-emerald-500/20',
        iconColor: 'text-emerald-400',
        title: 'Project Created',
        description: 'Your project is ready for PM Discovery.',
    },
    not_ready: {
        icon: 'warning',
        iconBg: 'bg-amber-500/20',
        iconColor: 'text-amber-400',
        title: 'Not Ready',
        description: 'Additional information is needed before proceeding.',
    },
    out_of_scope: {
        icon: 'x',
        iconBg: 'bg-slate-500/20',
        iconColor: 'text-slate-400',
        title: 'Out of Scope',
        description: 'This request is outside the scope of The Combine.',
    },
    redirect: {
        icon: 'arrow',
        iconBg: 'bg-blue-500/20',
        iconColor: 'text-blue-400',
        title: 'Redirected',
        description: 'This request has been redirected to a different engagement type.',
    },
    blocked: {
        icon: 'warning',
        iconBg: 'bg-amber-500/20',
        iconColor: 'text-amber-400',
        title: 'Blocked',
        description: 'The workflow could not complete due to validation issues.',
    },
};

function Icon({ type, className }) {
    switch (type) {
        case 'check':
            return (
                <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="20 6 9 17 4 12" />
                </svg>
            );
        case 'warning':
            return (
                <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M12 9v4M12 17h.01" />
                    <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
                </svg>
            );
        case 'x':
            return (
                <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <line x1="18" y1="6" x2="6" y2="18" />
                    <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
            );
        case 'arrow':
            return (
                <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <line x1="5" y1="12" x2="19" y2="12" />
                    <polyline points="12 5 19 12 12 19" />
                </svg>
            );
        default:
            return null;
    }
}

export default function CompletionCard({ gateOutcome, project, onViewProject, onClose }) {
    const style = OUTCOME_STYLES[gateOutcome] || OUTCOME_STYLES.blocked;
    const isQualified = gateOutcome === 'qualified';

    return (
        <div className="p-6 text-center">
            {/* Icon */}
            <div
                className={`w-16 h-16 rounded-full ${style.iconBg} flex items-center justify-center mx-auto mb-4`}
            >
                <Icon type={style.icon} className={`w-8 h-8 ${style.iconColor}`} />
            </div>

            {/* Title */}
            <h3
                className="text-lg font-semibold mb-2"
                style={{ color: 'var(--text-primary)' }}
            >
                {style.title}
            </h3>

            {/* Description */}
            <p
                className="text-sm mb-4"
                style={{ color: 'var(--text-muted)' }}
            >
                {style.description}
            </p>

            {/* Project info */}
            {isQualified && project && (
                <div
                    className="rounded-lg p-3 mb-4"
                    style={{ background: 'var(--bg-input)' }}
                >
                    <p
                        className="text-xs font-mono mb-1"
                        style={{ color: 'var(--text-muted)' }}
                    >
                        {project.project_id}
                    </p>
                    <p
                        className="text-sm font-medium"
                        style={{ color: 'var(--text-primary)' }}
                    >
                        {project.name}
                    </p>
                </div>
            )}

            {/* Actions */}
            <div className="flex gap-2 justify-center">
                {isQualified && project && (
                    <button
                        onClick={onViewProject}
                        className="px-4 py-2 rounded-lg text-sm font-medium bg-emerald-500 text-white hover:bg-emerald-400 transition-colors"
                    >
                        View Project
                    </button>
                )}
                <button
                    onClick={onClose}
                    className="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                    style={{
                        background: 'var(--bg-button)',
                        color: 'var(--text-muted)',
                    }}
                >
                    Close
                </button>
            </div>
        </div>
    );
}
