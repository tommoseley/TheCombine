/**
 * DocumentReferenceListBlock — renders a list of document references
 * as clickable cards (ADR-071 WS-BINDER-005).
 *
 * Each card shows display_id badge, title, and doc type.
 * Click opens DocumentModal with the referenced document.
 */

import DocumentLink from '../DocumentLink';
import { useProjectId } from '../ProjectContext';

// Short labels for doc types
const DOC_TYPE_LABELS = {
    concierge_intake: 'Intake',
    project_discovery: 'Discovery',
    technical_architecture: 'Architecture',
    implementation_plan: 'Implementation Plan',
    work_package: 'Work Package',
    work_statement: 'Work Statement',
    work_package_candidate: 'Candidate',
};

export default function DocumentReferenceListBlock({ block }) {
    const projectId = useProjectId();
    const { data } = block;
    const refs = data.items || data.referenced_documents || [];

    if (refs.length === 0) return null;

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {refs.map((ref, i) => (
                <div
                    key={ref.document_id || i}
                    style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 10,
                        padding: '8px 12px',
                        background: 'var(--bg-canvas, #0f0f23)',
                        border: '1px solid var(--border, #333)',
                        borderRadius: 4,
                    }}
                >
                    <span style={{
                        fontSize: 11,
                        fontWeight: 700,
                        color: 'var(--accent-primary, #3b82f6)',
                        fontFamily: 'monospace',
                        flexShrink: 0,
                    }}>
                        <DocumentLink
                            displayId={ref.display_id}
                            title={ref.title}
                            projectId={projectId}
                        />
                    </span>
                    <span style={{
                        fontSize: 13,
                        color: 'var(--text-primary, #eee)',
                        flex: 1,
                    }}>
                        {ref.title}
                    </span>
                    <span style={{
                        fontSize: 10,
                        color: 'var(--text-muted, #888)',
                        padding: '2px 8px',
                        background: 'var(--bg-surface, #1a1a2e)',
                        borderRadius: 10,
                        flexShrink: 0,
                    }}>
                        {DOC_TYPE_LABELS[ref.doc_type_id] || ref.doc_type_id}
                    </span>
                    {ref.version && (
                        <span style={{
                            fontSize: 10,
                            color: 'var(--text-muted, #666)',
                            flexShrink: 0,
                        }}>
                            v{ref.version}
                        </span>
                    )}
                </div>
            ))}
        </div>
    );
}
