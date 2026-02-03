import React, { useState } from 'react';

/**
 * Modal dialog for entering commit message.
 */
export default function CommitDialog({ onCommit, onCancel, loading = false }) {
    const [message, setMessage] = useState('');

    const handleSubmit = (e) => {
        e.preventDefault();
        if (message.trim() && !loading) {
            onCommit(message.trim());
        }
    };

    return (
        <div
            className="fixed inset-0 flex items-center justify-center z-50"
            style={{ background: 'rgba(0, 0, 0, 0.7)' }}
        >
            <div
                className="w-full max-w-md p-6 rounded-lg shadow-xl"
                style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-panel)' }}
            >
                <h2
                    className="text-lg font-semibold mb-4"
                    style={{ color: 'var(--text-primary)' }}
                >
                    Commit Changes
                </h2>

                <form onSubmit={handleSubmit}>
                    <div className="mb-4">
                        <label
                            className="block text-sm mb-2"
                            style={{ color: 'var(--text-muted)' }}
                        >
                            Commit Message
                        </label>
                        <textarea
                            value={message}
                            onChange={(e) => setMessage(e.target.value)}
                            placeholder="Describe your changes..."
                            className="w-full p-3 rounded text-sm font-mono resize-none"
                            style={{
                                background: 'var(--bg-input)',
                                border: '1px solid var(--border-panel)',
                                color: 'var(--text-primary)',
                                minHeight: '100px',
                            }}
                            autoFocus
                            disabled={loading}
                        />
                    </div>

                    <div className="flex justify-end gap-3">
                        <button
                            type="button"
                            onClick={onCancel}
                            disabled={loading}
                            className="px-4 py-2 rounded text-sm"
                            style={{
                                background: 'transparent',
                                border: '1px solid var(--border-panel)',
                                color: 'var(--text-muted)',
                            }}
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            disabled={!message.trim() || loading}
                            className="px-4 py-2 rounded text-sm font-medium"
                            style={{
                                background: message.trim() && !loading
                                    ? 'var(--action-success)'
                                    : 'var(--border-panel)',
                                color: message.trim() && !loading
                                    ? '#000'
                                    : 'var(--text-muted)',
                                cursor: message.trim() && !loading ? 'pointer' : 'not-allowed',
                            }}
                        >
                            {loading ? 'Committing...' : 'Commit'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
