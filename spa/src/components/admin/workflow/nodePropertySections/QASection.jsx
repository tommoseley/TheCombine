import React from 'react';
import { QA_MODES, fieldStyle, labelStyle } from '../../../../constants/nodeConfig';
import { buildTemplateRef, parseTemplateRef } from '../../../../utils/refFormatters';

/**
 * QA node properties: QA mode, interaction template, requires_qa flag.
 */
export default function QASection({
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

            {/* QA Mode */}
            <div>
                <label style={labelStyle}>QA Mode</label>
                <select
                    value={localData.qa_mode || 'semantic'}
                    onChange={e => updateField('qa_mode', e.target.value)}
                    style={fieldStyle}
                >
                    {QA_MODES.map(m => (
                        <option key={m} value={m}>{m}</option>
                    ))}
                </select>
            </div>
        </>
    );
}
