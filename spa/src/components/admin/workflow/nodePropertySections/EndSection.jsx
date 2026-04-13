import React from 'react';
import { TERMINAL_OUTCOMES, fieldStyle, labelStyle } from '../../../../constants/nodeConfig';

/**
 * End node properties: terminal outcome and gate outcome.
 */
export default function EndSection({
    localData,
    updateField,
}) {
    return (
        <>
            <div>
                <label style={labelStyle}>Terminal Outcome</label>
                <select
                    value={localData.terminal_outcome || 'stabilized'}
                    onChange={e => updateField('terminal_outcome', e.target.value)}
                    style={fieldStyle}
                >
                    {TERMINAL_OUTCOMES.map(o => (
                        <option key={o} value={o}>{o}</option>
                    ))}
                </select>
            </div>
            <div>
                <label style={labelStyle}>Gate Outcome</label>
                <input
                    type="text"
                    value={localData.gate_outcome || ''}
                    onChange={e => updateField('gate_outcome', e.target.value)}
                    placeholder="e.g., complete, failed"
                    style={fieldStyle}
                />
            </div>
        </>
    );
}
