/**
 * WorkPlanViewer — ADR-071 final deliverable viewer.
 *
 * Narrative-first layout:
 * 1. Executive Summary (what are we building, why, key metrics)
 * 2. Key Decisions (synthesis decisions with operator resolutions)
 * 3. Constraints & Guardrails (from PD/TA)
 * 4. Work Structure (WPs with child WSs, grouped)
 * 5. Dependencies
 * 6. Project Documents (reference index)
 *
 * Read-only. No editing. No workflow actions.
 */

import { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client.js';
import DocumentLink from './DocumentLink.jsx';
import { useProjectId } from './ProjectContext.jsx';

export default function WorkPlanViewer({ projectId: propProjectId }) {
    const contextProjectId = useProjectId();
    const projectId = propProjectId || contextProjectId;
    const [plan, setPlan] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const loadPlan = useCallback(async () => {
        if (!projectId) return;
        setLoading(true);
        try {
            let result = await api.getDocument(projectId, 'work_plan').catch(() => null);
            if (result?.content?.executive_summary) {
                setPlan(result.content);
            } else {
                result = await api.getWorkBinder(projectId);
                if (result?.content) setPlan(result.content);
            }
        } catch (err) {
            setError(err.message || 'Failed to load work plan');
        } finally {
            setLoading(false);
        }
    }, [projectId]);

    useEffect(() => { loadPlan(); }, [loadPlan]);

    if (loading) {
        return <div style={{ padding: 24, color: 'var(--text-muted, #888)' }}>Loading work plan...</div>;
    }

    if (error) {
        return <div style={{ padding: 24, color: '#e53935' }}>{error}</div>;
    }

    if (!plan) {
        return (
            <div style={{ padding: '40px 20px', textAlign: 'center', color: 'var(--text-muted, #888)' }}>
                <p style={{ fontSize: 14, marginBottom: 8 }}>No work plan generated yet.</p>
                <p style={{ fontSize: 12 }}>Generate the work plan after completing the Review & Resolve step.</p>
            </div>
        );
    }

    const summary = plan.executive_summary || {};
    const decisions = plan.decision_log || [];
    const workStructure = plan.work_structure || [];
    const deps = plan.dependency_summary || [];
    const refs = plan.referenced_documents || [];
    const groups = plan.groups || [];

    return (
        <div style={{ padding: '20px 24px', maxWidth: 1100, margin: '0 auto' }}>
            {/* Header */}
            <div style={{ marginBottom: 28 }}>
                <h1 style={{ margin: 0, fontSize: 22, fontWeight: 700, color: 'var(--text-primary, #eee)' }}>
                    {summary.project_name || 'Work Plan'}
                </h1>
                {plan.assembled_at && (
                    <div style={{ fontSize: 12, color: 'var(--text-muted, #888)', marginTop: 4 }}>
                        Generated {new Date(plan.assembled_at).toLocaleString()}
                    </div>
                )}
            </div>

            {/* 1. Executive Summary */}
            {summary.project_name && (
                <Section title="Executive Summary">
                    {summary.objective && (
                        <p style={{ fontSize: 14, color: 'var(--text-secondary, #ccc)', lineHeight: 1.7, margin: '0 0 16px' }}>
                            {summary.objective}
                        </p>
                    )}
                    {summary.scope_summary && (
                        <p style={{ fontSize: 13, color: 'var(--text-secondary, #ccc)', lineHeight: 1.6, margin: '0 0 16px' }}>
                            {summary.scope_summary}
                        </p>
                    )}
                    <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
                        <Stat label="Components" value={summary.component_count} />
                        <Stat label="Work Packages" value={summary.work_package_count} />
                        <Stat label="Work Statements" value={summary.work_statement_count} />
                    </div>
                </Section>
            )}

            {/* 2. Key Decisions */}
            {decisions.length > 0 && (
                <Section title={`Key Decisions (${decisions.length})`}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                        {decisions.map((d, i) => (
                            <DecisionCard key={d.finding_id || i} decision={d} />
                        ))}
                    </div>
                </Section>
            )}

            {/* 3. Constraints */}
            {summary.key_constraints && summary.key_constraints.length > 0 && (
                <Section title="Constraints & Guardrails">
                    <ul style={{ margin: 0, paddingLeft: 20 }}>
                        {summary.key_constraints.map((c, i) => (
                            <li key={i} style={{ fontSize: 13, color: 'var(--text-secondary, #ccc)', lineHeight: 1.7, marginBottom: 4 }}>
                                {c}
                            </li>
                        ))}
                    </ul>
                </Section>
            )}

            {/* 4. Work Structure */}
            {workStructure.length > 0 && (
                <Section title="Work Structure">
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                        {workStructure.map((wp, i) => (
                            <WorkPackageCard key={wp.display_id || i} wp={wp} projectId={projectId} />
                        ))}
                    </div>
                </Section>
            )}

            {/* 5. Dependencies */}
            {deps.length > 0 && (
                <Section title="Dependencies">
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                        {deps.map((dep, i) => (
                            <div key={i} style={{
                                display: 'flex', alignItems: 'center', gap: 8,
                                padding: '6px 12px',
                                background: 'var(--bg-canvas, #0f0f23)',
                                border: '1px solid var(--border, #333)',
                                borderRadius: 4, fontSize: 13,
                            }}>
                                <DocumentLink displayId={dep.from_display_id} projectId={projectId} />
                                <span style={{ color: 'var(--text-muted, #666)', fontSize: 11 }}>depends on</span>
                                <DocumentLink displayId={dep.to_display_id} projectId={projectId} />
                            </div>
                        ))}
                    </div>
                </Section>
            )}

            {/* 6. Project Documents */}
            {refs.length > 0 && (
                <Section title="Project Documents">
                    <ProjectDocumentIndex refs={refs} groups={groups} projectId={projectId} />
                </Section>
            )}
        </div>
    );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function Section({ title, children }) {
    return (
        <div style={{ marginBottom: 28 }}>
            <h3 style={{
                fontSize: 13, fontWeight: 600,
                color: 'var(--text-muted, #888)',
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
                marginBottom: 12, paddingBottom: 6,
                borderBottom: '1px solid var(--border, #333)',
            }}>
                {title}
            </h3>
            {children}
        </div>
    );
}

function Stat({ label, value }) {
    if (value == null) return null;
    return (
        <div style={{
            padding: '10px 20px',
            background: 'var(--bg-canvas, #0f0f23)',
            border: '1px solid var(--border, #333)',
            borderRadius: 6, textAlign: 'center', minWidth: 100,
        }}>
            <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--accent-primary, #3b82f6)' }}>{value}</div>
            <div style={{ fontSize: 10, color: 'var(--text-muted, #888)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</div>
        </div>
    );
}

const SEVERITY_COLOR = { blocking: '#e53935', should_fix: '#f9a825', advisory: '#90a4ae' };

function DecisionCard({ decision }) {
    const sevColor = SEVERITY_COLOR[decision.severity] || '#90a4ae';
    return (
        <div style={{
            padding: '10px 14px',
            background: `${sevColor}0d`,
            border: '1px solid var(--border, #333)',
            borderRadius: 6, borderLeft: `3px solid ${sevColor}`,
        }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary, #eee)', flex: 1 }}>
                    {decision.headline}
                </span>
                <span style={{
                    fontSize: 10, fontWeight: 600,
                    color: decision.decision === 'accept' ? '#81c784' : '#e57373',
                    padding: '2px 8px', borderRadius: 10,
                    background: decision.decision === 'accept' ? 'rgba(76,175,80,0.15)' : 'rgba(229,57,53,0.15)',
                }}>
                    {decision.decision === 'accept' ? 'Accepted' : 'Dismissed'}
                </span>
            </div>
            {decision.note && (
                <div style={{ fontSize: 12, color: 'var(--text-secondary, #ccc)', lineHeight: 1.5 }}>
                    {decision.note}
                </div>
            )}
        </div>
    );
}

function WorkPackageCard({ wp, projectId }) {
    return (
        <div style={{
            border: '1px solid var(--border, #333)',
            borderRadius: 6, overflow: 'hidden',
        }}>
            <div style={{
                padding: '10px 14px',
                background: 'var(--bg-canvas, #0f0f23)',
                display: 'flex', alignItems: 'center', gap: 10,
            }}>
                <DocumentLink displayId={wp.display_id} title={wp.title} projectId={projectId} />
                <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary, #eee)', flex: 1 }}>
                    {wp.title}
                </span>
                <span style={{ fontSize: 11, color: 'var(--text-muted, #888)' }}>
                    {wp.ws_count} statement{wp.ws_count !== 1 ? 's' : ''}
                </span>
            </div>
            {wp.rationale && (
                <div style={{ padding: '6px 14px', fontSize: 12, color: 'var(--text-secondary, #ccc)', lineHeight: 1.5 }}>
                    {wp.rationale}
                </div>
            )}
            {wp.work_statements && wp.work_statements.length > 0 && (
                <div style={{ padding: '4px 14px 10px' }}>
                    {wp.work_statements.map((ws, i) => (
                        <div key={ws.display_id || i} style={{
                            display: 'flex', alignItems: 'flex-start', gap: 8,
                            padding: '4px 0', borderTop: i > 0 ? '1px solid var(--border, #222)' : 'none',
                        }}>
                            <span style={{ fontSize: 11, color: 'var(--text-muted, #555)', marginTop: 1 }}>&#8627;</span>
                            <DocumentLink displayId={ws.display_id} title={ws.title} projectId={projectId} />
                            <span style={{ fontSize: 12, color: 'var(--text-secondary, #ccc)', flex: 1 }}>
                                {ws.title}
                            </span>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

const DOC_TYPE_LABELS = {
    concierge_intake: 'Intake', project_discovery: 'Discovery',
    technical_architecture: 'Architecture', implementation_plan: 'Impl. Plan',
    work_package: 'Work Package', work_statement: 'Work Statement',
    work_package_candidate: 'Candidate',
};

const GROUP_LABELS = {
    intake: 'Intake', discovery: 'Project Discovery', architecture: 'Architecture',
    planning: 'Implementation Planning', candidates: 'Candidates',
    work_packages: 'Work Packages', work_statements: 'Work Statements',
};

function ProjectDocumentIndex({ refs, groups, projectId }) {
    // Group refs
    const grouped = {};
    for (const ref of refs) {
        const g = ref.group || 'other';
        if (!grouped[g]) grouped[g] = [];
        grouped[g].push(ref);
    }

    const orderedGroups = groups.length > 0 ? groups.map(g => g.id) : Object.keys(grouped);
    // Skip work_packages and work_statements — already shown in Work Structure
    const filteredGroups = orderedGroups.filter(g => g !== 'work_packages' && g !== 'work_statements');

    if (filteredGroups.length === 0) return null;

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {filteredGroups.map(groupId => {
                const groupRefs = grouped[groupId];
                if (!groupRefs || groupRefs.length === 0) return null;
                const label = (groups.find(g => g.id === groupId) || {}).label || GROUP_LABELS[groupId] || groupId;

                return (
                    <div key={groupId}>
                        <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted, #666)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                            {label}
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                            {groupRefs.map((ref, i) => (
                                <div key={ref.document_id || i} style={{
                                    display: 'flex', alignItems: 'center', gap: 10,
                                    padding: '6px 12px',
                                    background: 'var(--bg-canvas, #0f0f23)',
                                    border: '1px solid var(--border, #333)',
                                    borderRadius: 4,
                                }}>
                                    <DocumentLink displayId={ref.display_id} title={ref.title} projectId={projectId} />
                                    <span style={{ fontSize: 13, color: 'var(--text-primary, #eee)', flex: 1 }}>{ref.title}</span>
                                    <span style={{ fontSize: 10, color: 'var(--text-muted, #666)' }}>v{ref.version}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                );
            })}
        </div>
    );
}
