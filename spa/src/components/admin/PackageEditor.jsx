import React, { useState, useEffect, useCallback } from 'react';
import { adminApi } from '../../api/adminClient';

/**
 * Editor for package.yaml metadata.
 * Allows editing document type configuration like role associations,
 * authority level, dependencies, etc.
 */
export default function PackageEditor({
    workspaceId,
    docType,
    roles = [],
    onSave,
}) {
    const [formData, setFormData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState(null);
    const [isDirty, setIsDirty] = useState(false);

    // Initialize form data from docType
    useEffect(() => {
        if (docType) {
            setFormData({
                display_name: docType.display_name || '',
                description: docType.description || '',
                authority_level: docType.authority_level || 'elaborative',
                creation_mode: docType.creation_mode || 'llm_generated',
                production_mode: docType.production_mode || '',
                scope: docType.scope || 'project',
                role_prompt_ref: docType.role_prompt_ref || '',
                template_ref: docType.template_ref || '',
                required_inputs: docType.required_inputs || [],
                optional_inputs: docType.optional_inputs || [],
                creates_children: docType.creates_children || [],
                parent_doc_type: docType.parent_doc_type || '',
                ui_icon: docType.ui?.icon || '',
                ui_category: docType.ui?.category || '',
                ui_display_order: docType.ui?.display_order || 0,
            });
            setIsDirty(false);
            setError(null);
        }
    }, [docType]);

    // Handle field change
    const handleChange = useCallback((field, value) => {
        setFormData(prev => ({
            ...prev,
            [field]: value,
        }));
        setIsDirty(true);
    }, []);

    // Handle array field change (comma-separated)
    const handleArrayChange = useCallback((field, value) => {
        const arr = value.split(',').map(s => s.trim()).filter(s => s);
        setFormData(prev => ({
            ...prev,
            [field]: arr,
        }));
        setIsDirty(true);
    }, []);

    // Build role reference from role_id
    const buildRoleRef = useCallback((roleId) => {
        if (!roleId) return '';
        const role = roles.find(r => r.role_id === roleId);
        if (!role) return '';
        return `prompt:role:${roleId}:${role.active_version}`;
    }, [roles]);

    // Parse role_id from role reference
    const parseRoleId = useCallback((ref) => {
        if (!ref) return '';
        const parts = ref.split(':');
        if (parts.length >= 3 && parts[0] === 'prompt' && parts[1] === 'role') {
            return parts[2];
        }
        return '';
    }, []);

    // Save changes
    const handleSave = useCallback(async () => {
        if (!workspaceId || !docType || !formData) return;

        setSaving(true);
        setError(null);

        try {
            // Build the artifact ID for the package manifest
            const version = docType.version || docType.active_version;
            const artifactId = `doctype:${docType.doc_type_id}:${version}:manifest`;

            // Build YAML content from form data
            const yamlContent = buildYamlContent(docType.doc_type_id, version, formData);

            // Save via workspace API
            const result = await adminApi.writeArtifact(workspaceId, artifactId, yamlContent);

            setIsDirty(false);
            onSave?.(artifactId, result);
        } catch (err) {
            console.error('Failed to save package:', err);
            setError(err.message);
        } finally {
            setSaving(false);
        }
    }, [workspaceId, docType, formData, onSave]);

    if (!docType || !formData) {
        return (
            <div
                className="flex items-center justify-center h-full"
                style={{ color: 'var(--text-muted)' }}
            >
                Loading package configuration...
            </div>
        );
    }

    return (
        <div className="flex flex-col h-full">
            {/* Status bar */}
            <div
                className="flex items-center justify-between px-3 py-2 text-xs border-b"
                style={{
                    borderColor: 'var(--border-panel)',
                    background: 'var(--bg-panel)',
                }}
            >
                <div className="flex items-center gap-2">
                    {isDirty && (
                        <span style={{ color: 'var(--text-muted)' }}>Modified</span>
                    )}
                </div>
                <div className="flex items-center gap-2">
                    {saving && (
                        <span style={{ color: 'var(--state-active-text)' }}>Saving...</span>
                    )}
                    {error && (
                        <span style={{ color: 'var(--state-error-text)' }}>Error: {error}</span>
                    )}
                    <button
                        onClick={handleSave}
                        disabled={!isDirty || saving}
                        className="px-3 py-1 rounded text-xs"
                        style={{
                            background: isDirty ? 'var(--action-primary)' : 'var(--bg-panel)',
                            color: isDirty ? '#000' : 'var(--text-muted)',
                            opacity: isDirty && !saving ? 1 : 0.5,
                        }}
                    >
                        Save Package
                    </button>
                </div>
            </div>

            {/* Form */}
            <div
                className="flex-1 overflow-y-auto p-4"
                style={{ background: 'var(--bg-canvas)' }}
            >
                <div className="max-w-2xl space-y-6">
                    {/* Identity Section */}
                    <Section title="Identity">
                        <Field label="Display Name">
                            <input
                                type="text"
                                value={formData.display_name}
                                onChange={(e) => handleChange('display_name', e.target.value)}
                                className="w-full px-3 py-2 rounded text-sm"
                                style={{
                                    background: 'var(--bg-panel)',
                                    color: 'var(--text-primary)',
                                    border: '1px solid var(--border-panel)',
                                }}
                            />
                        </Field>
                        <Field label="Description">
                            <textarea
                                value={formData.description}
                                onChange={(e) => handleChange('description', e.target.value)}
                                rows={3}
                                className="w-full px-3 py-2 rounded text-sm resize-none"
                                style={{
                                    background: 'var(--bg-panel)',
                                    color: 'var(--text-primary)',
                                    border: '1px solid var(--border-panel)',
                                }}
                            />
                        </Field>
                    </Section>

                    {/* Classification Section */}
                    <Section title="Classification">
                        <Field label="Authority Level">
                            <select
                                value={formData.authority_level}
                                onChange={(e) => handleChange('authority_level', e.target.value)}
                                className="w-full px-3 py-2 rounded text-sm"
                                style={{
                                    background: 'var(--bg-panel)',
                                    color: 'var(--text-primary)',
                                    border: '1px solid var(--border-panel)',
                                }}
                            >
                                <option value="descriptive">Descriptive</option>
                                <option value="prescriptive">Prescriptive</option>
                                <option value="constructive">Constructive</option>
                                <option value="elaborative">Elaborative</option>
                            </select>
                        </Field>
                        <Field label="Creation Mode">
                            <select
                                value={formData.creation_mode}
                                onChange={(e) => handleChange('creation_mode', e.target.value)}
                                className="w-full px-3 py-2 rounded text-sm"
                                style={{
                                    background: 'var(--bg-panel)',
                                    color: 'var(--text-primary)',
                                    border: '1px solid var(--border-panel)',
                                }}
                            >
                                <option value="llm_generated">LLM Generated</option>
                                <option value="constructed">Constructed</option>
                                <option value="extracted">Extracted</option>
                            </select>
                        </Field>
                        <Field label="Scope">
                            <select
                                value={formData.scope}
                                onChange={(e) => handleChange('scope', e.target.value)}
                                className="w-full px-3 py-2 rounded text-sm"
                                style={{
                                    background: 'var(--bg-panel)',
                                    color: 'var(--text-primary)',
                                    border: '1px solid var(--border-panel)',
                                }}
                            >
                                <option value="project">Project</option>
                                <option value="epic">Epic</option>
                                <option value="feature">Feature</option>
                            </select>
                        </Field>
                    </Section>

                    {/* References Section */}
                    <Section title="Shared References">
                        <Field label="Role Prompt">
                            <select
                                value={parseRoleId(formData.role_prompt_ref)}
                                onChange={(e) => handleChange('role_prompt_ref', buildRoleRef(e.target.value))}
                                className="w-full px-3 py-2 rounded text-sm"
                                style={{
                                    background: 'var(--bg-panel)',
                                    color: 'var(--text-primary)',
                                    border: '1px solid var(--border-panel)',
                                }}
                            >
                                <option value="">None</option>
                                {roles.map(role => (
                                    <option key={role.role_id} value={role.role_id}>
                                        {role.role_id.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                                    </option>
                                ))}
                            </select>
                            {formData.role_prompt_ref && (
                                <div className="mt-1 text-xs" style={{ color: 'var(--text-muted)' }}>
                                    {formData.role_prompt_ref}
                                </div>
                            )}
                        </Field>
                    </Section>

                    {/* Dependencies Section */}
                    <Section title="Dependencies">
                        <Field label="Required Inputs" hint="Comma-separated doc type IDs">
                            <input
                                type="text"
                                value={formData.required_inputs.join(', ')}
                                onChange={(e) => handleArrayChange('required_inputs', e.target.value)}
                                placeholder="e.g., project_discovery, technical_architecture"
                                className="w-full px-3 py-2 rounded text-sm"
                                style={{
                                    background: 'var(--bg-panel)',
                                    color: 'var(--text-primary)',
                                    border: '1px solid var(--border-panel)',
                                }}
                            />
                        </Field>
                        <Field label="Optional Inputs" hint="Comma-separated doc type IDs">
                            <input
                                type="text"
                                value={formData.optional_inputs.join(', ')}
                                onChange={(e) => handleArrayChange('optional_inputs', e.target.value)}
                                placeholder="e.g., technical_architecture"
                                className="w-full px-3 py-2 rounded text-sm"
                                style={{
                                    background: 'var(--bg-panel)',
                                    color: 'var(--text-primary)',
                                    border: '1px solid var(--border-panel)',
                                }}
                            />
                        </Field>
                        <Field label="Parent Doc Type">
                            <input
                                type="text"
                                value={formData.parent_doc_type}
                                onChange={(e) => handleChange('parent_doc_type', e.target.value)}
                                placeholder="e.g., implementation_plan"
                                className="w-full px-3 py-2 rounded text-sm"
                                style={{
                                    background: 'var(--bg-panel)',
                                    color: 'var(--text-primary)',
                                    border: '1px solid var(--border-panel)',
                                }}
                            />
                        </Field>
                        <Field label="Creates Children" hint="Comma-separated doc type IDs">
                            <input
                                type="text"
                                value={formData.creates_children.join(', ')}
                                onChange={(e) => handleArrayChange('creates_children', e.target.value)}
                                placeholder="e.g., feature, story"
                                className="w-full px-3 py-2 rounded text-sm"
                                style={{
                                    background: 'var(--bg-panel)',
                                    color: 'var(--text-primary)',
                                    border: '1px solid var(--border-panel)',
                                }}
                            />
                        </Field>
                    </Section>

                    {/* UI Section */}
                    <Section title="UI Configuration">
                        <Field label="Icon">
                            <input
                                type="text"
                                value={formData.ui_icon}
                                onChange={(e) => handleChange('ui_icon', e.target.value)}
                                placeholder="e.g., search, package, map"
                                className="w-full px-3 py-2 rounded text-sm"
                                style={{
                                    background: 'var(--bg-panel)',
                                    color: 'var(--text-primary)',
                                    border: '1px solid var(--border-panel)',
                                }}
                            />
                        </Field>
                        <Field label="Category">
                            <select
                                value={formData.ui_category}
                                onChange={(e) => handleChange('ui_category', e.target.value)}
                                className="w-full px-3 py-2 rounded text-sm"
                                style={{
                                    background: 'var(--bg-panel)',
                                    color: 'var(--text-primary)',
                                    border: '1px solid var(--border-panel)',
                                }}
                            >
                                <option value="">Select category...</option>
                                <option value="intake">Intake</option>
                                <option value="architecture">Architecture</option>
                                <option value="planning">Planning</option>
                                <option value="execution">Execution</option>
                            </select>
                        </Field>
                        <Field label="Display Order">
                            <input
                                type="number"
                                value={formData.ui_display_order}
                                onChange={(e) => handleChange('ui_display_order', parseInt(e.target.value) || 0)}
                                className="w-full px-3 py-2 rounded text-sm"
                                style={{
                                    background: 'var(--bg-panel)',
                                    color: 'var(--text-primary)',
                                    border: '1px solid var(--border-panel)',
                                }}
                            />
                        </Field>
                    </Section>
                </div>
            </div>
        </div>
    );
}

// Helper components
function Section({ title, children }) {
    return (
        <div>
            <h3
                className="text-sm font-semibold mb-3 uppercase tracking-wide"
                style={{ color: 'var(--text-muted)' }}
            >
                {title}
            </h3>
            <div className="space-y-4">
                {children}
            </div>
        </div>
    );
}

function Field({ label, hint, children }) {
    return (
        <div>
            <label
                className="block text-sm mb-1"
                style={{ color: 'var(--text-secondary)' }}
            >
                {label}
                {hint && (
                    <span className="ml-2 text-xs" style={{ color: 'var(--text-muted)' }}>
                        ({hint})
                    </span>
                )}
            </label>
            {children}
        </div>
    );
}

// Build YAML content from form data
function buildYamlContent(docTypeId, version, formData) {
    const lines = [
        `# ${formData.display_name} Package`,
        `# Version ${version}`,
        '',
        `doc_type_id: ${docTypeId}`,
        `display_name: "${formData.display_name}"`,
        `version: "${version}"`,
        `description: >`,
        `  ${formData.description.replace(/\n/g, '\n  ')}`,
        '',
        '# Classification',
        `authority_level: ${formData.authority_level}`,
        `creation_mode: ${formData.creation_mode}`,
        formData.production_mode ? `production_mode: ${formData.production_mode}` : 'production_mode: null',
        `scope: ${formData.scope}`,
        '',
        '# Dependencies',
        `required_inputs: [${formData.required_inputs.map(s => `"${s}"`).join(', ')}]`,
        `optional_inputs: [${formData.optional_inputs.map(s => `"${s}"`).join(', ')}]`,
        `creates_children: [${formData.creates_children.map(s => `"${s}"`).join(', ')}]`,
        `parent_doc_type: ${formData.parent_doc_type ? `"${formData.parent_doc_type}"` : 'null'}`,
        '',
        '# Shared artifact references',
        `role_prompt_ref: ${formData.role_prompt_ref ? `"${formData.role_prompt_ref}"` : 'null'}`,
        `template_ref: ${formData.template_ref ? `"${formData.template_ref}"` : 'null'}`,
        '',
        '# Packaged artifacts',
        'artifacts:',
        '  task_prompt: "prompts/task.prompt.txt"',
        '  qa_prompt: null',
        '  reflection_prompt: null',
        '  pgc_context: null',
        '  questions_prompt: null',
        '  schema: "schemas/output.schema.json"',
        '',
        '# Tests',
        'tests:',
        '  fixtures: []',
        '  golden_traces: []',
        '',
        '# Gating rules',
        'gating_rules:',
        '  lifecycle_states: []',
        '  design_status: []',
        '  acceptance_required: false',
        '  accepted_by: []',
        '',
        '# UI configuration',
        'ui:',
        `  icon: ${formData.ui_icon || 'file'}`,
        `  category: ${formData.ui_category || 'other'}`,
        `  display_order: ${formData.ui_display_order || 0}`,
        '',
    ];

    return lines.join('\n');
}
