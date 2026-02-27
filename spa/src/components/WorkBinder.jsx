/**
 * WorkBinder — Work Package / Work Statement management panel.
 *
 * Displayed when the Work Binder node is selected in the pipeline rail.
 * Shows candidate WPs (from IP output) and governed WPs (from backend).
 * Provides actions to create WPs and WSs.
 *
 * WS-PIPELINE-002, Phase 3.
 */
import { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';

function getArtifactState(rawState) {
    if (['produced', 'stabilized', 'ready', 'complete'].includes(rawState)) return 'stabilized';
    if (['requirements_not_met', 'blocked', 'halted', 'failed'].includes(rawState)) return 'blocked';
    if (['in_production', 'active', 'queued', 'awaiting_operator'].includes(rawState)) return 'in_progress';
    if (['ready_for_production', 'waiting', 'pending_acceptance'].includes(rawState)) return 'ready';
    return 'ready';
}

function stateCssName(state) {
    return state === 'in_progress' ? 'active' : state;
}

const STATE_DISPLAY = {
    blocked: 'Blocked',
    in_progress: 'In Progress',
    ready: 'Ready',
    stabilized: 'Stabilized',
};

function StateDot({ state }) {
    const css = stateCssName(getArtifactState(state || 'ready'));
    return (
        <div
            className="rounded-full flex-shrink-0"
            style={{ width: 8, height: 8, backgroundColor: `var(--state-${css}-bg)` }}
        />
    );
}

export default function WorkBinder({ projectId, projectCode }) {
    const [candidateWPs, setCandidateWPs] = useState([]);
    const [governedWPs, setGovernedWPs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [generating, setGenerating] = useState(false);
    const [error, setError] = useState(null);
    const [expandedWP, setExpandedWP] = useState(null);

    const fetchData = useCallback(async () => {
        try {
            setLoading(true);
            setError(null);

            // Fetch governed WPs from backend
            let wps = [];
            try {
                const res = await api.getWorkPackages(projectId);
                wps = res || [];
            } catch (e) {
                // Endpoint may not exist yet — that's OK
                console.log('Work packages endpoint not available:', e.message);
            }
            setGovernedWPs(wps);

            // Fetch candidate WPs from IP document content
            try {
                const ipDoc = await api.getDocument(projectId, 'implementation_plan');
                const candidates = ipDoc?.content?.candidate_work_packages || ipDoc?.content?.work_packages || [];
                setCandidateWPs(Array.isArray(candidates) ? candidates : []);
            } catch (e) {
                // IP may not exist yet
                setCandidateWPs([]);
            }
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    }, [projectId]);

    useEffect(() => { fetchData(); }, [fetchData]);

    const handleCreateWPs = useCallback(async () => {
        setGenerating(true);
        try {
            await api.generateWorkPackages(projectId);
            await fetchData();
        } catch (e) {
            setError('Failed to generate work packages: ' + e.message);
        } finally {
            setGenerating(false);
        }
    }, [projectId, fetchData]);

    const handleCreateWSs = useCallback(async (wpId) => {
        try {
            await api.generateWorkStatements(projectId, wpId);
            await fetchData();
        } catch (e) {
            setError('Failed to generate work statements: ' + e.message);
        }
    }, [projectId, fetchData]);

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <p style={{ fontSize: 14, color: 'var(--text-muted)' }}>Loading work binder...</p>
            </div>
        );
    }

    return (
        <div className="p-6 max-w-5xl mx-auto">
            {/* Header */}
            <div className="mb-6">
                <h2
                    className="text-xl font-bold"
                    style={{ color: 'var(--text-primary)' }}
                >
                    Work Binder
                </h2>
                <p
                    className="text-sm mt-1"
                    style={{ color: 'var(--text-secondary)' }}
                >
                    {projectCode} &mdash; Manage Work Packages and Work Statements
                </p>
            </div>

            {error && (
                <div
                    className="mb-4 p-3 rounded-lg border-l-4"
                    style={{ borderColor: 'var(--state-blocked-bg)', background: 'var(--bg-node)' }}
                >
                    <p style={{ fontSize: 13, color: 'var(--state-blocked-text)' }}>{error}</p>
                </div>
            )}

            {/* Candidate Work Packages (from IP) */}
            <section className="mb-8">
                <div className="flex items-center justify-between mb-3">
                    <h3
                        className="text-sm font-semibold uppercase tracking-wider"
                        style={{ color: 'var(--text-muted)', letterSpacing: '0.05em' }}
                    >
                        Candidate Work Packages
                    </h3>
                    {candidateWPs.length > 0 && (
                        <button
                            onClick={handleCreateWPs}
                            disabled={generating}
                            className="px-4 py-2 rounded-lg text-sm font-semibold transition-all hover:brightness-110 disabled:opacity-50"
                            style={{ backgroundColor: 'var(--action-primary)', color: 'white' }}
                        >
                            {generating ? 'Generating...' : 'Create Work Packages'}
                        </button>
                    )}
                </div>
                {candidateWPs.length === 0 ? (
                    <div
                        className="rounded-lg border p-6 text-center"
                        style={{ background: 'var(--bg-node)', borderColor: 'var(--border-node)' }}
                    >
                        <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
                            No candidate work packages. Complete the Implementation Plan first.
                        </p>
                    </div>
                ) : (
                    <div className="space-y-2">
                        {candidateWPs.map((wp, idx) => (
                            <div
                                key={idx}
                                className="rounded-lg border p-3"
                                style={{ background: 'var(--bg-node)', borderColor: 'var(--border-node)' }}
                            >
                                <div className="flex items-start gap-3">
                                    <span
                                        className="font-mono text-xs px-1.5 py-0.5 rounded flex-shrink-0"
                                        style={{ background: 'var(--bg-badge, rgba(100,116,139,0.15))', color: 'var(--text-muted)' }}
                                    >
                                        C-{idx + 1}
                                    </span>
                                    <div className="flex-1 min-w-0">
                                        <div className="font-semibold text-sm" style={{ color: 'var(--text-primary)' }}>
                                            {wp.title || wp.name || `Candidate ${idx + 1}`}
                                        </div>
                                        {(wp.scope_summary || wp.description) && (
                                            <p className="text-xs mt-1" style={{ color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                                                {wp.scope_summary || wp.description}
                                            </p>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </section>

            {/* Governed Work Packages */}
            <section>
                <h3
                    className="text-sm font-semibold uppercase tracking-wider mb-3"
                    style={{ color: 'var(--text-muted)', letterSpacing: '0.05em' }}
                >
                    Governed Work Packages
                </h3>
                {governedWPs.length === 0 ? (
                    <div
                        className="rounded-lg border p-6 text-center"
                        style={{ background: 'var(--bg-node)', borderColor: 'var(--border-node)' }}
                    >
                        <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
                            No governed work packages yet. Use "Create Work Packages" above to generate them.
                        </p>
                    </div>
                ) : (
                    <div className="space-y-2">
                        {governedWPs.map(wp => {
                            const isExpanded = expandedWP === wp.id;
                            const wpState = getArtifactState(wp.state || 'ready');
                            return (
                                <div
                                    key={wp.id}
                                    className="rounded-lg border overflow-hidden"
                                    style={{ background: 'var(--bg-node)', borderColor: 'var(--border-node)' }}
                                >
                                    <button
                                        onClick={() => setExpandedWP(isExpanded ? null : wp.id)}
                                        className="w-full text-left p-3 hover:brightness-95 transition-all"
                                        style={{ background: 'transparent', border: 'none', cursor: 'pointer' }}
                                    >
                                        <div className="flex items-center gap-3">
                                            <StateDot state={wp.state} />
                                            <span
                                                className="font-mono text-xs flex-shrink-0"
                                                style={{ color: 'var(--text-muted)' }}
                                            >
                                                {wp.wp_id || wp.id?.slice(0, 8)}
                                            </span>
                                            <span
                                                className="font-semibold text-sm flex-1 truncate"
                                                style={{ color: 'var(--text-primary)' }}
                                            >
                                                {wp.title || wp.name}
                                            </span>
                                            <span
                                                className="text-xs font-medium"
                                                style={{ color: `var(--state-${stateCssName(wpState)}-text)` }}
                                            >
                                                {STATE_DISPLAY[wpState]}
                                            </span>
                                            {wp.ws_count !== undefined && (
                                                <span
                                                    className="text-xs px-1.5 py-0.5 rounded"
                                                    style={{ background: 'var(--bg-badge, rgba(100,116,139,0.15))', color: 'var(--text-muted)' }}
                                                >
                                                    {wp.ws_count} WS
                                                </span>
                                            )}
                                        </div>
                                    </button>
                                    {isExpanded && (
                                        <div
                                            className="px-3 pb-3 border-t"
                                            style={{ borderColor: 'var(--border-node)' }}
                                        >
                                            <div className="pt-3 flex items-center justify-between">
                                                <div>
                                                    {wp.provenance && (
                                                        <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                                                            Source: IP v{wp.provenance.source_ip_version || '?'}
                                                            {wp.provenance.generated_by && ` | Generated by: ${wp.provenance.generated_by}`}
                                                        </span>
                                                    )}
                                                </div>
                                                <button
                                                    onClick={() => handleCreateWSs(wp.id)}
                                                    className="px-3 py-1.5 rounded text-xs font-semibold transition-all hover:brightness-110"
                                                    style={{ backgroundColor: 'var(--action-primary)', color: 'white' }}
                                                >
                                                    Create Work Statements
                                                </button>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                )}
            </section>
        </div>
    );
}
