/**
 * WorkPlanViewer — ADR-071 final deliverable viewer.
 *
 * Read-only presentation of the assembled Work Plan:
 * - Executive summary (project overview, counts, constraints)
 * - Grouped project documents (clickable, version-pinned)
 * - Decision log (synthesis decisions with operator notes)
 * - Dependency summary
 *
 * No editing. No workflow actions. Pure consumption.
 */

import { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client.js';
import ExecutiveSummaryBlock from './blocks/ExecutiveSummaryBlock.jsx';
import GroupedDocumentsBlock from './blocks/GroupedDocumentsBlock.jsx';
import DecisionLogBlock from './blocks/DecisionLogBlock.jsx';
import DependencySummaryBlock from './blocks/DependencySummaryBlock.jsx';

export default function WorkPlanViewer({ projectId }) {
    const [plan, setPlan] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const loadPlan = useCallback(async () => {
        if (!projectId) return;
        setLoading(true);
        try {
            // Try work_plan doc first, fall back to work_binder
            let result = await api.getDocument(projectId, 'work_plan');
            if (result?.content?.executive_summary) {
                setPlan(result.content);
            } else {
                result = await api.getWorkBinder(projectId);
                if (result?.content) {
                    setPlan(result.content);
                }
            }
        } catch {
            try {
                const result = await api.getWorkBinder(projectId);
                if (result?.content) setPlan(result.content);
            } catch (err) {
                setError(err.message || 'Failed to load work plan');
            }
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

    const hasExecutiveSummary = plan.executive_summary;
    const hasDocuments = plan.referenced_documents && plan.referenced_documents.length > 0;
    const hasDecisions = plan.decision_log && plan.decision_log.length > 0;
    const hasDependencies = plan.dependency_summary && plan.dependency_summary.length > 0;

    return (
        <div style={{ padding: '20px 24px', maxWidth: 1200, margin: '0 auto' }}>
            {/* Header */}
            <div style={{ marginBottom: 24 }}>
                <h2 style={{ margin: 0, fontSize: 20, fontWeight: 700, color: 'var(--text-primary, #eee)' }}>
                    Work Plan
                </h2>
                {plan.assembled_at && (
                    <div style={{ fontSize: 12, color: 'var(--text-muted, #888)', marginTop: 4 }}>
                        Assembled {new Date(plan.assembled_at).toLocaleString()}
                        {' \u2022 '}
                        {plan.document_count} documents
                    </div>
                )}
            </div>

            {/* Executive Summary */}
            {hasExecutiveSummary && (
                <Section title="Executive Summary">
                    <ExecutiveSummaryBlock block={{ data: plan }} />
                </Section>
            )}

            {/* Project Documents */}
            {hasDocuments && (
                <Section title="Project Documents">
                    <GroupedDocumentsBlock block={{
                        data: {
                            referenced_documents: plan.referenced_documents,
                            groups: plan.groups || [],
                        },
                    }} />
                </Section>
            )}

            {/* Decision Log */}
            {hasDecisions && (
                <Section title={`Decision Log (${plan.decision_log.length})`}>
                    <DecisionLogBlock block={{ data: { decision_log: plan.decision_log } }} />
                </Section>
            )}

            {/* Dependencies */}
            {hasDependencies && (
                <Section title="Dependencies">
                    <DependencySummaryBlock block={{ data: { dependency_summary: plan.dependency_summary } }} />
                </Section>
            )}
        </div>
    );
}

function Section({ title, children }) {
    return (
        <div style={{ marginBottom: 28 }}>
            <h3 style={{
                fontSize: 13,
                fontWeight: 600,
                color: 'var(--text-muted, #888)',
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
                marginBottom: 12,
                paddingBottom: 6,
                borderBottom: '1px solid var(--border, #333)',
            }}>
                {title}
            </h3>
            {children}
        </div>
    );
}
