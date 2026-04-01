import React from 'react';
import { fieldStyle, labelStyle } from '../../../../constants/nodeConfig';
import { buildTemplateRef, parseTemplateRef } from '../../../../utils/refFormatters';

/**
 * Intake gate node properties: interaction template, produces.
 */
export default function IntakeGateSection({
    localData,
    templates,
    updateField,
}) {
    const currentTemplateId = parseTemplateRef(localData.task_ref);

    const handleTemplateChange = (e) => {
        const templateId = e.target.value;
        if (!templateId) { updateField('task_ref', ''); return; }
        const template = templates.find(t => t.template_id === templateId);
        if (template) updateField('task_ref', buildTemplateRef(template));
    };

    return (
        <>
            {/* Produces */}
            <div>
                <label style={labelStyle}>Produces</label>
                <input
                    type="text"
                    value={localData.produces || ''}
                    onChange={e => updateField('produces', e.target.value)}
                    placeholder="document_type"
                    style={fieldStyle}
                />
            </div>

            {/* Interaction Template */}
            <div>
                <label style={labelStyle}>Interaction Template</label>
                <select
                    value={currentTemplateId || ''}
                    onChange={handleTemplateChange}
                    style={fieldStyle}
                >
                    <option value="">-- Select Template --</option>
                    {templates.map(t => (
                        <option key={t.template_id} value={t.template_id}>
                            {t.name || t.template_id.replace(/_/g, ' ')}
                        </option>
                    ))}
                </select>
                {localData.task_ref && (
                    <div
                        className="mt-1 text-xs font-mono truncate"
                        style={{ color: 'var(--text-muted)' }}
                        title={localData.task_ref}
                    >
                        {localData.task_ref}
                    </div>
                )}
            </div>
        </>
    );
}
