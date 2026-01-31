import { useState } from 'react';

/**
 * Editable fields for the review phase.
 * Shows interpretation with lock status.
 */

const FIELD_LABELS = {
    project_name: 'Project Name',
    problem_statement: 'Problem Statement',
    project_type: 'Project Type',
};

const FIELD_ORDER = ['project_name', 'problem_statement', 'project_type'];

export default function InterpretationEditor({
    interpretation,
    missingFields,
    canInitialize,
    onUpdateField,
    onInitialize,
    loading,
}) {
    const [editingField, setEditingField] = useState(null);
    const [editValue, setEditValue] = useState('');

    const startEdit = (key, currentValue) => {
        setEditingField(key);
        setEditValue(currentValue);
    };

    const saveEdit = async () => {
        if (editingField && editValue.trim()) {
            await onUpdateField(editingField, editValue.trim());
            setEditingField(null);
            setEditValue('');
        }
    };

    const cancelEdit = () => {
        setEditingField(null);
        setEditValue('');
    };

    return (
        <div className="p-4 space-y-4">
            <div className="flex items-center gap-2 mb-2">
                <span
                    className="text-xs font-semibold uppercase tracking-wide"
                    style={{ color: 'var(--text-muted)' }}
                >
                    Review & Lock
                </span>
                {missingFields.length > 0 && (
                    <span className="text-[10px] px-2 py-0.5 rounded bg-amber-500/20 text-amber-400">
                        {missingFields.length} missing
                    </span>
                )}
            </div>

            {FIELD_ORDER.map((key) => {
                const field = interpretation[key];
                if (!field) return null;

                const isLocked = field.locked;
                const isMissing = missingFields.includes(key);
                const isEditing = editingField === key;

                return (
                    <div key={key} className="space-y-1">
                        <div className="flex items-center justify-between">
                            <label
                                className="text-[10px] font-medium"
                                style={{ color: 'var(--text-muted)' }}
                            >
                                {FIELD_LABELS[key] || key}
                                {isMissing && (
                                    <span className="text-amber-400 ml-1">*</span>
                                )}
                            </label>
                            {isLocked && (
                                <span className="text-[9px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400">
                                    locked
                                </span>
                            )}
                        </div>

                        {isEditing ? (
                            <div className="flex gap-2">
                                <input
                                    type="text"
                                    value={editValue}
                                    onChange={(e) => setEditValue(e.target.value)}
                                    onKeyDown={(e) => {
                                        if (e.key === 'Enter') saveEdit();
                                        if (e.key === 'Escape') cancelEdit();
                                    }}
                                    autoFocus
                                    className="flex-1 rounded px-2 py-1.5 text-xs"
                                    style={{
                                        background: 'var(--bg-input)',
                                        border: '1px solid var(--border-input)',
                                        color: 'var(--text-primary)',
                                    }}
                                />
                                <button
                                    onClick={saveEdit}
                                    className="px-2 py-1 rounded text-xs bg-emerald-500 text-white"
                                >
                                    Save
                                </button>
                                <button
                                    onClick={cancelEdit}
                                    className="px-2 py-1 rounded text-xs"
                                    style={{
                                        background: 'var(--bg-button)',
                                        color: 'var(--text-muted)',
                                    }}
                                >
                                    Cancel
                                </button>
                            </div>
                        ) : (
                            <div
                                onClick={() => !isLocked && startEdit(key, field.value)}
                                className={`rounded px-2 py-1.5 text-xs ${
                                    isLocked ? 'cursor-default' : 'cursor-pointer hover:bg-white/5'
                                } ${isMissing ? 'border border-amber-500/50' : ''}`}
                                style={{
                                    background: 'var(--bg-input)',
                                    color: field.value
                                        ? 'var(--text-primary)'
                                        : 'var(--text-muted)',
                                }}
                            >
                                {field.value || 'Click to edit...'}
                            </div>
                        )}
                    </div>
                );
            })}

            <button
                onClick={onInitialize}
                disabled={!canInitialize || loading}
                className={`w-full py-2.5 rounded-lg text-sm font-medium transition-colors ${
                    canInitialize && !loading
                        ? 'bg-violet-500 text-white hover:bg-violet-400'
                        : 'bg-slate-600 text-slate-400 cursor-not-allowed'
                }`}
            >
                {loading ? 'Initializing...' : 'Lock & Initialize Project'}
            </button>

            {!canInitialize && (
                <p
                    className="text-[10px] text-center"
                    style={{ color: 'var(--text-muted)' }}
                >
                    Fill all required fields to continue
                </p>
            )}
        </div>
    );
}
