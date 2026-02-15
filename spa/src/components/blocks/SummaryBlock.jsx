/**
 * Summary block renderer
 * Displays structured summary with multiple sections
 * Handles various summary formats (Project Discovery, Architecture, Epic Backlog, etc.)
 */
export default function SummaryBlock({ block }) {
    const { data } = block;

    // Map of field names to display titles
    const fieldTitles = {
        problem_understanding: 'Problem Understanding',
        architectural_intent: 'Architectural Intent',
        scope_pressure_points: 'Scope Pressure Points',
        proposed_system_shape: 'Proposed System Shape',
        overall_intent: 'Overall Intent',
        mvp_definition: 'MVP Definition',
        refined_description: 'Description',
        architectural_style: 'Architectural Style',
        style: 'Architectural Style',
    };

    // Build sections from string fields
    const sections = Object.entries(fieldTitles)
        .filter(([field]) => data[field] && typeof data[field] === 'string')
        .map(([field, title]) => ({ title, content: data[field] }));

    // Note: key_decisions and mvp_scope_notes are excluded here because the
    // document definition provides dedicated sections for them (StringListBlockV1)

    if (sections.length === 0 && !data.title) return null;

    return (
        <div style={{ marginBottom: 12 }}>
            {data.title && (
                <h3 style={{ fontSize: 16, fontWeight: 600, color: '#1f2937', marginBottom: 12 }}>
                    {data.title}
                </h3>
            )}
            {sections.map((section, i) => (
                <div key={i} style={{ marginBottom: 16 }}>
                    <h4 style={{ fontSize: 12, fontWeight: 600, color: '#6b7280', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                        {section.title}
                    </h4>
                    <div style={{ padding: '12px 16px', background: '#f8fafc', borderRadius: 6, borderLeft: '3px solid #6366f1' }}>
                        <p style={{ margin: 0, fontSize: 14, lineHeight: 1.6, color: '#374151', whiteSpace: 'pre-line' }}>
                            {section.content}
                        </p>
                    </div>
                </div>
            ))}
        </div>
    );
}
