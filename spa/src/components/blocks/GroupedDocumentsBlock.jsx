/**
 * GroupedDocumentsBlock — renders documents grouped by category
 * with section headers (ADR-071 WS-BINDER-005).
 *
 * Groups documents by the `group` field, renders section headers,
 * then document reference cards per group. WSs are nested under
 * their parent WP.
 */

import DocumentLink from '../DocumentLink';
import { useProjectId } from '../ProjectContext';

// Short labels for doc types
const DOC_TYPE_LABELS = {
    concierge_intake: 'Intake',
    project_discovery: 'Discovery',
    technical_architecture: 'Architecture',
    implementation_plan: 'Impl. Plan',
    work_package: 'Work Package',
    work_statement: 'Work Statement',
    work_package_candidate: 'Candidate',
};

const GROUP_LABELS = {
    intake: 'Intake',
    discovery: 'Project Discovery',
    architecture: 'Architecture',
    planning: 'Implementation Planning',
    candidates: 'Work Package Candidates',
    work_packages: 'Work Packages',
    work_statements: 'Work Statements',
};

function DocCard({ docRef, projectId, indent = false }) {
    return (
        <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            padding: '8px 12px',
            paddingLeft: indent ? 32 : 12,
            background: 'var(--bg-canvas, #0f0f23)',
            border: '1px solid var(--border, #333)',
            borderRadius: 4,
        }}>
            {indent && (
                <span style={{ color: 'var(--text-muted, #555)', fontSize: 11 }}>&#8627;</span>
            )}
            <span style={{
                fontSize: 11,
                fontWeight: 700,
                color: 'var(--accent-primary, #3b82f6)',
                fontFamily: 'monospace',
                flexShrink: 0,
            }}>
                <DocumentLink
                    displayId={docRef.display_id}
                    title={docRef.title}
                    projectId={projectId}
                />
            </span>
            <span style={{
                fontSize: 13,
                color: 'var(--text-primary, #eee)',
                flex: 1,
            }}>
                {docRef.title}
            </span>
            <span style={{
                fontSize: 10,
                color: 'var(--text-muted, #888)',
                padding: '2px 8px',
                background: 'var(--bg-surface, #1a1a2e)',
                borderRadius: 10,
                flexShrink: 0,
            }}>
                {DOC_TYPE_LABELS[docRef.doc_type_id] || docRef.doc_type_id}
            </span>
            {docRef.version && (
                <span style={{
                    fontSize: 10,
                    color: 'var(--text-muted, #666)',
                    flexShrink: 0,
                }}>
                    v{docRef.version}
                </span>
            )}
        </div>
    );
}

export default function GroupedDocumentsBlock({ block }) {
    const projectId = useProjectId();
    const { data } = block;
    const refs = data.items || data.referenced_documents || [];
    const groups = data.groups || [];

    if (refs.length === 0) return null;

    // Group refs by group field
    const grouped = {};
    for (const ref of refs) {
        const g = ref.group || 'other';
        if (!grouped[g]) grouped[g] = [];
        grouped[g].push(ref);
    }

    // Use groups order if available, else use keys
    const orderedGroups = groups.length > 0
        ? groups.map(g => g.id)
        : Object.keys(grouped);

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {orderedGroups.map(groupId => {
                const groupRefs = grouped[groupId];
                if (!groupRefs || groupRefs.length === 0) return null;

                const label = (groups.find(g => g.id === groupId) || {}).label
                    || GROUP_LABELS[groupId]
                    || groupId;

                // For work_packages group: nest WSs under their parent WP
                const isWpGroup = groupId === 'work_packages';
                const wsRefs = isWpGroup ? (grouped['work_statements'] || []) : [];

                return (
                    <div key={groupId}>
                        <h4 style={{
                            fontSize: 12,
                            fontWeight: 600,
                            color: 'var(--text-muted, #888)',
                            textTransform: 'uppercase',
                            letterSpacing: '0.06em',
                            marginBottom: 8,
                        }}>
                            {label} ({groupRefs.length}{isWpGroup && wsRefs.length > 0 ? ` + ${wsRefs.length} statements` : ''})
                        </h4>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                            {groupRefs.map((ref, i) => {
                                // For WPs, render the WP then its child WSs
                                const childWs = isWpGroup
                                    ? wsRefs.filter(ws => ws.parent_display_id === ref.display_id)
                                    : [];
                                return (
                                    <div key={ref.document_id || i}>
                                        <DocCard docRef={ref} projectId={projectId} />
                                        {childWs.map((ws, j) => (
                                            <DocCard
                                                key={ws.document_id || j}
                                                docRef={ws}
                                                projectId={projectId}
                                                indent={true}
                                            />
                                        ))}
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                );
            })}

            {/* Render work_statements group only if NOT already nested under WPs */}
            {grouped['work_statements'] && !grouped['work_packages'] && (
                <div>
                    <h4 style={{
                        fontSize: 12,
                        fontWeight: 600,
                        color: 'var(--text-muted, #888)',
                        textTransform: 'uppercase',
                        letterSpacing: '0.06em',
                        marginBottom: 8,
                    }}>
                        Work Statements ({grouped['work_statements'].length})
                    </h4>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                        {grouped['work_statements'].map((ref, i) => (
                            <DocCard key={ref.document_id || i} ref={ref} projectId={projectId} />
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
