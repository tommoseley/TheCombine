/**
 * Workflow block renderer
 * Displays a workflow with name, trigger, description, and ordered steps
 * Handles multiple step shapes from different LLM outputs
 */
export default function WorkflowBlock({ block }) {
    const { data } = block;
    if (!data || !data.name) return null;

    const steps = Array.isArray(data.steps) ? data.steps : [];
    // Sort by step/order field if present
    const sortedSteps = [...steps].sort((a, b) => (a.step || a.order || 0) - (b.step || b.order || 0));

    return (
        <div
            style={{
                marginBottom: 12,
                padding: '14px 16px',
                background: 'var(--bg-panel)',
                borderRadius: 8,
                border: '1px solid var(--border-node)',
            }}
        >
            <h4 style={{ margin: '0 0 4px', fontSize: 15, fontWeight: 600, color: '#1e293b' }}>
                {data.name}
            </h4>
            {data.description && (
                <p style={{ margin: '0 0 8px', fontSize: 13, color: '#475569' }}>
                    {data.description}
                </p>
            )}
            {data.trigger && (
                <p style={{ margin: '0 0 12px', fontSize: 13, color: 'var(--text-muted)', fontStyle: 'italic' }}>
                    Trigger: {data.trigger}
                </p>
            )}
            {sortedSteps.length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    {sortedSteps.map((step, i) => (
                        <div
                            key={i}
                            style={{
                                display: 'flex',
                                gap: 10,
                                padding: '8px 10px',
                                background: 'var(--bg-canvas)',
                                borderRadius: 6,
                                border: '1px solid var(--border-node)',
                            }}
                        >
                            <span
                                style={{
                                    flexShrink: 0,
                                    width: 24,
                                    height: 24,
                                    borderRadius: '50%',
                                    background: '#6366f1',
                                    color: '#fff',
                                    fontSize: 12,
                                    fontWeight: 600,
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                }}
                            >
                                {step.step || step.order || i + 1}
                            </span>
                            <div style={{ flex: 1, minWidth: 0 }}>
                                <p style={{ margin: 0, fontSize: 13, color: 'var(--text-primary)', lineHeight: 1.4 }}>
                                    {step.action}
                                </p>
                                <div style={{ display: 'flex', gap: 12, marginTop: 3, flexWrap: 'wrap' }}>
                                    {step.component && (
                                        <span style={{ fontSize: 11, color: '#6366f1', fontWeight: 500 }}>
                                            {step.component}
                                        </span>
                                    )}
                                    {step.actor && (
                                        <span style={{ fontSize: 11, color: '#6366f1', fontWeight: 500 }}>
                                            {step.actor}
                                        </span>
                                    )}
                                    {step.output && (
                                        <span style={{ fontSize: 11, color: 'var(--text-dim)' }}>
                                            &rarr; {step.output}
                                        </span>
                                    )}
                                    {Array.isArray(step.outputs) && step.outputs.length > 0 && (
                                        <span style={{ fontSize: 11, color: 'var(--text-dim)' }}>
                                            &rarr; {step.outputs.join(', ')}
                                        </span>
                                    )}
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
