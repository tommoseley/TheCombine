import React from 'react';
import { fieldStyle, labelStyle } from '../../../../constants/nodeConfig';

/**
 * Includes/references management UI: ROLE_PROMPT, TASK_PROMPT, OUTPUT_SCHEMA, PGC_CONTEXT,
 * plus custom includes with add/update/remove.
 */
export default function IncludesPanel({
    currentRoleId,
    currentTaskId,
    currentSchemaId,
    currentPgcId,
    customIncludes,
    roleFragments,
    taskFragments,
    schemas,
    pgcFragments,
    handleRoleChange,
    handleTaskChange,
    handleSchemaChange,
    handlePgcChange,
    updateInclude,
    removeInclude,
    addCustomInclude,
    localData,
    setLocalData,
    onChange,
}) {
    return (
        <div>
            <div className="flex items-center justify-between mb-2">
                <label style={labelStyle}>Includes</label>
            </div>

            {/* ROLE_PROMPT - dropdown from role fragments */}
            <div className="mb-2">
                <label
                    className="text-xs mb-1 block"
                    style={{ color: 'var(--text-muted)' }}
                >
                    ROLE_PROMPT
                </label>
                <select
                    value={currentRoleId || ''}
                    onChange={handleRoleChange}
                    style={{ ...fieldStyle, fontSize: 11 }}
                >
                    <option value="">-- Select Role --</option>
                    {roleFragments.map(f => {
                        const id = f.fragment_id?.replace('role:', '') || f.id;
                        return (
                            <option key={f.fragment_id || f.id} value={id}>
                                {f.name || id?.replace(/_/g, ' ')}
                            </option>
                        );
                    })}
                </select>
            </div>

            {/* TASK_PROMPT - dropdown from task fragments */}
            <div className="mb-2">
                <label
                    className="text-xs mb-1 block"
                    style={{ color: 'var(--text-muted)' }}
                >
                    TASK_PROMPT
                </label>
                <select
                    value={currentTaskId || ''}
                    onChange={handleTaskChange}
                    style={{ ...fieldStyle, fontSize: 11 }}
                >
                    <option value="">-- Select Task --</option>
                    {taskFragments.map(f => {
                        const id = f.fragment_id?.replace('task:', '') || f.id;
                        return (
                            <option key={f.fragment_id || f.id} value={id}>
                                {f.name || id?.replace(/_/g, ' ')}
                            </option>
                        );
                    })}
                </select>
            </div>

            {/* OUTPUT_SCHEMA - dropdown from schemas */}
            <div className="mb-2">
                <label
                    className="text-xs mb-1 block"
                    style={{ color: 'var(--text-muted)' }}
                >
                    OUTPUT_SCHEMA
                </label>
                <select
                    value={currentSchemaId || ''}
                    onChange={handleSchemaChange}
                    style={{ ...fieldStyle, fontSize: 11 }}
                >
                    <option value="">-- Select Schema --</option>
                    {schemas.map(s => (
                        <option key={s.schema_id} value={s.schema_id}>
                            {s.title || s.schema_id.replace(/_/g, ' ')}
                        </option>
                    ))}
                </select>
            </div>

            {/* PGC_CONTEXT - dropdown from PGC fragments */}
            <div className="mb-2">
                <label
                    className="text-xs mb-1 block"
                    style={{ color: 'var(--text-muted)' }}
                >
                    PGC_CONTEXT
                </label>
                <select
                    value={currentPgcId || ''}
                    onChange={handlePgcChange}
                    style={{ ...fieldStyle, fontSize: 11 }}
                >
                    <option value="">-- Select PGC Context --</option>
                    {pgcFragments.map(f => {
                        const id = f.fragment_id?.replace('pgc:', '') || f.id;
                        return (
                            <option key={f.fragment_id || f.id} value={id}>
                                {f.name || id?.replace(/_/g, ' ')}
                            </option>
                        );
                    })}
                </select>
            </div>

            {/* Custom includes */}
            {customIncludes.length > 0 && (
                <div className="mt-3 pt-2 border-t" style={{ borderColor: 'var(--border-panel)' }}>
                    <label
                        className="text-xs mb-1 block"
                        style={{ color: 'var(--text-muted)' }}
                    >
                        Custom Includes
                    </label>
                    <div className="space-y-2">
                        {customIncludes.map(([key, value]) => (
                            <div key={key} className="flex gap-1">
                                <input
                                    type="text"
                                    value={key}
                                    onChange={e => {
                                        const newIncludes = { ...localData.includes };
                                        delete newIncludes[key];
                                        newIncludes[e.target.value] = value;
                                        const updated = { ...localData, includes: newIncludes };
                                        setLocalData(updated);
                                        onChange(updated);
                                    }}
                                    style={{ ...fieldStyle, width: '35%', fontSize: 10 }}
                                    placeholder="KEY"
                                />
                                <input
                                    type="text"
                                    value={value}
                                    onChange={e => updateInclude(key, e.target.value)}
                                    style={{ ...fieldStyle, flex: 1, fontSize: 10 }}
                                    placeholder="path/to/file"
                                />
                                <button
                                    onClick={() => removeInclude(key)}
                                    className="text-xs px-1"
                                    style={{ color: '#ef4444' }}
                                >
                                    x
                                </button>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Add custom include button */}
            <button
                onClick={addCustomInclude}
                className="mt-2 text-xs px-2 py-1 rounded hover:opacity-80 w-full"
                style={{
                    color: 'var(--action-primary)',
                    background: 'transparent',
                    border: '1px dashed var(--border-panel)',
                }}
            >
                + Add Custom Include
            </button>
        </div>
    );
}
