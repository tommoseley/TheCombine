export const NODE_TYPES = [
    { value: 'intake_gate', label: 'Intake Gate' },
    { value: 'task', label: 'Task' },
    { value: 'qa', label: 'QA' },
    { value: 'pgc', label: 'PGC Gate' },
    { value: 'gate', label: 'Gate' },
    { value: 'end', label: 'End' },
];

// ADR-047: Node internal types
export const INTERNAL_TYPES = [
    { value: 'LLM', label: 'LLM', description: 'AI-powered interaction' },
    { value: 'MECH', label: 'Mechanical', description: 'Deterministic operation' },
    { value: 'UI', label: 'UI', description: 'Operator entry' },
];

export const PGC_GATE_KINDS = [
    { value: 'intake', label: 'Intake Gate', produces: 'pgc_clarifications.intake' },
    { value: 'discovery', label: 'Discovery Gate', produces: 'pgc_clarifications.discovery' },
    { value: 'plan', label: 'Plan Gate', produces: 'pgc_clarifications.plan' },
    { value: 'architecture', label: 'Architecture Gate', produces: 'pgc_clarifications.architecture' },
    { value: 'work_package', label: 'Work Package Gate', produces: 'pgc_clarifications.work_package' },
    { value: 'remediation', label: 'Remediation Gate', produces: 'pgc_clarifications.remediation' },
    { value: 'compliance', label: 'Compliance Gate', produces: 'pgc_clarifications.compliance' },
];

export const QA_MODES = ['semantic', 'structural', 'hybrid'];
export const TERMINAL_OUTCOMES = ['stabilized', 'blocked', 'abandoned'];

export const fieldStyle = {
    width: '100%',
    padding: '6px 8px',
    borderRadius: 4,
    fontSize: 12,
    background: 'var(--bg-input, var(--bg-canvas))',
    border: '1px solid var(--border-panel)',
    color: 'var(--text-primary)',
};

export const labelStyle = {
    display: 'block',
    fontSize: 10,
    fontWeight: 600,
    color: 'var(--text-muted)',
    marginBottom: 2,
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
};

export const sectionHeaderStyle = {
    fontSize: 10,
    fontWeight: 700,
    color: 'var(--text-primary)',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    padding: '6px 0',
    borderBottom: '1px solid var(--border-panel)',
    marginBottom: 8,
};

export const passHeaderStyle = {
    fontSize: 10,
    fontWeight: 600,
    color: 'var(--action-primary)',
    marginBottom: 4,
    display: 'flex',
    alignItems: 'center',
    gap: 6,
};
