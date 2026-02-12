import { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useAuth } from '../hooks/useAuth';

/**
 * Accounts Sidecar - Manage linked OAuth accounts
 */
export default function AccountsSidecar({ onClose }) {
    const { isAdmin } = useAuth();
    const [accounts, setAccounts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [message, setMessage] = useState(null);

    const loadAccounts = async () => {
        try {
            setLoading(true);
            setError(null);
            const response = await fetch('/auth/accounts', { credentials: 'include' });
            if (!response.ok) {
                throw new Error('Failed to load accounts');
            }
            const data = await response.json();
            setAccounts(data.identities || []);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadAccounts();
    }, []);

    const handleLinkProvider = (provider) => {
        // Navigate to link flow - will redirect back after OAuth
        window.location.href = `/auth/accounts/link/${provider}`;
    };

    const handleUnlinkProvider = async (provider) => {
        if (accounts.length <= 1) {
            setMessage({ type: 'error', text: 'Cannot unlink your only account' });
            return;
        }

        if (!confirm(`Unlink your ${provider} account?`)) {
            return;
        }

        try {
            const csrfToken = document.cookie
                .split('; ')
                .find(row => row.startsWith('csrf=') || row.startsWith('__Host-csrf='))
                ?.split('=')[1];

            const response = await fetch(`/auth/accounts/${provider}`, {
                method: 'DELETE',
                credentials: 'include',
                headers: {
                    'X-CSRF-Token': csrfToken || '',
                },
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.detail || 'Failed to unlink account');
            }

            setMessage({ type: 'success', text: 'Account unlinked successfully' });
            await loadAccounts();
        } catch (err) {
            setMessage({ type: 'error', text: err.message });
        }
    };

    const formatDate = (isoString) => {
        if (!isoString) return '';
        try {
            return new Date(isoString).toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                year: 'numeric',
            });
        } catch {
            return '';
        }
    };

    const providerIcons = {
        google: (
            <svg className="w-5 h-5" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
            </svg>
        ),
        microsoft: (
            <svg className="w-5 h-5" viewBox="0 0 23 23">
                <path fill="#f35325" d="M1 1h10v10H1z" />
                <path fill="#81bc06" d="M12 1h10v10H12z" />
                <path fill="#05a6f0" d="M1 12h10v10H1z" />
                <path fill="#ffba08" d="M12 12h10v10H12z" />
            </svg>
        ),
    };

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center"
            style={{ background: 'rgba(0, 0, 0, 0.6)' }}
            onClick={(e) => {
                if (e.target === e.currentTarget) onClose();
            }}
        >
            <div
                className="flex flex-col w-full max-w-md max-h-[80vh] rounded-xl shadow-2xl tray-slide"
                onWheel={(e) => e.stopPropagation()}
                style={{
                    background: 'var(--bg-panel)',
                    border: '1px solid var(--border-panel)',
                }}
            >
                {/* Header */}
                <div
                    className="flex items-center justify-between px-4 py-3 border-b"
                    style={{ borderColor: 'var(--border-panel)' }}
                >
                    <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-blue-500/20 flex items-center justify-center">
                            <svg
                                className="w-4 h-4 text-blue-400"
                                viewBox="0 0 24 24"
                                fill="none"
                                stroke="currentColor"
                                strokeWidth="2"
                            >
                                <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
                                <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
                            </svg>
                        </div>
                        <h2
                            className="text-sm font-semibold"
                            style={{ color: 'var(--text-primary)' }}
                        >
                            Linked Accounts
                        </h2>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 rounded-lg hover:bg-white/10 transition-colors"
                        style={{ color: 'var(--text-muted)' }}
                    >
                        <svg
                            className="w-5 h-5"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2"
                        >
                            <line x1="18" y1="6" x2="6" y2="18" />
                            <line x1="6" y1="6" x2="18" y2="18" />
                        </svg>
                    </button>
                </div>

                {/* Message banner */}
                {message && (
                    <div
                        className={`px-4 py-2 text-sm ${
                            message.type === 'error'
                                ? 'bg-red-500/20 text-red-300'
                                : 'bg-emerald-500/20 text-emerald-300'
                        }`}
                    >
                        {message.text}
                    </div>
                )}

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-4">
                    {loading ? (
                        <div className="flex items-center justify-center py-8">
                            <div className="w-8 h-8 border-2 border-t-blue-500 border-r-transparent border-b-transparent border-l-transparent rounded-full animate-spin" />
                        </div>
                    ) : error ? (
                        <div className="text-center py-8">
                            <p className="text-red-400 text-sm mb-4">{error}</p>
                            <button
                                onClick={loadAccounts}
                                className="px-4 py-2 bg-blue-500 text-white text-sm rounded-lg hover:bg-blue-600"
                            >
                                Retry
                            </button>
                        </div>
                    ) : (
                        <>
                            {/* Admin links (only for admins) */}
                            {isAdmin && (
                                <div className="mb-6">
                                    <h3
                                        className="text-xs font-medium uppercase tracking-wide mb-3"
                                        style={{ color: 'var(--text-muted)' }}
                                    >
                                        Administration
                                    </h3>
                                    <div className="space-y-2">
                                        <a
                                            href="/admin"
                                            className="w-full flex items-center gap-3 p-3 rounded-lg hover:bg-white/5 transition-colors"
                                            style={{
                                                background: 'var(--bg-canvas)',
                                                border: '1px solid var(--border-panel)',
                                                color: 'var(--text-primary)',
                                                textDecoration: 'none',
                                            }}
                                        >
                                            <div className="w-10 h-10 rounded-lg bg-amber-500/20 flex items-center justify-center">
                                                <svg
                                                    className="w-5 h-5 text-amber-400"
                                                    viewBox="0 0 24 24"
                                                    fill="none"
                                                    stroke="currentColor"
                                                    strokeWidth="2"
                                                >
                                                    <path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z" />
                                                    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1Z" />
                                                </svg>
                                            </div>
                                            <div>
                                                <div className="text-sm font-medium">Admin Panel</div>
                                                <div
                                                    className="text-xs"
                                                    style={{ color: 'var(--text-muted)' }}
                                                >
                                                    System configuration
                                                </div>
                                            </div>
                                        </a>
                                        <a
                                            href="/admin/workbench"
                                            className="w-full flex items-center gap-3 p-3 rounded-lg hover:bg-white/5 transition-colors"
                                            style={{
                                                background: 'var(--bg-canvas)',
                                                border: '1px solid var(--border-panel)',
                                                color: 'var(--text-primary)',
                                                textDecoration: 'none',
                                            }}
                                        >
                                            <div className="w-10 h-10 rounded-lg bg-purple-500/20 flex items-center justify-center">
                                                <svg
                                                    className="w-5 h-5 text-purple-400"
                                                    viewBox="0 0 24 24"
                                                    fill="none"
                                                    stroke="currentColor"
                                                    strokeWidth="2"
                                                >
                                                    <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
                                                    <polyline points="14 2 14 8 20 8" />
                                                    <line x1="16" y1="13" x2="8" y2="13" />
                                                    <line x1="16" y1="17" x2="8" y2="17" />
                                                    <line x1="10" y1="9" x2="8" y2="9" />
                                                </svg>
                                            </div>
                                            <div>
                                                <div className="text-sm font-medium">Prompt Workbench</div>
                                                <div
                                                    className="text-xs"
                                                    style={{ color: 'var(--text-muted)' }}
                                                >
                                                    Edit document type prompts
                                                </div>
                                            </div>
                                        </a>
                                    </div>
                                </div>
                            )}

                            {/* Linked accounts list */}
                            <div className="mb-6">
                                <h3
                                    className="text-xs font-medium uppercase tracking-wide mb-3"
                                    style={{ color: 'var(--text-muted)' }}
                                >
                                    Your Accounts
                                </h3>
                                <div className="space-y-2">
                                    {accounts.map((account) => (
                                        <div
                                            key={account.provider_id}
                                            className="flex items-center justify-between p-3 rounded-lg"
                                            style={{
                                                background: 'var(--bg-canvas)',
                                                border: '1px solid var(--border-panel)',
                                            }}
                                        >
                                            <div className="flex items-center gap-3">
                                                <div className="w-10 h-10 rounded-lg bg-white/10 flex items-center justify-center">
                                                    {providerIcons[account.provider_id] || (
                                                        <span className="text-sm font-semibold">
                                                            {account.provider_id.charAt(0).toUpperCase()}
                                                        </span>
                                                    )}
                                                </div>
                                                <div>
                                                    <div
                                                        className="text-sm font-medium"
                                                        style={{ color: 'var(--text-primary)' }}
                                                    >
                                                        {account.provider_email}
                                                    </div>
                                                    <div
                                                        className="text-xs"
                                                        style={{ color: 'var(--text-muted)' }}
                                                    >
                                                        {account.provider_id.charAt(0).toUpperCase() +
                                                            account.provider_id.slice(1)}{' '}
                                                        &bull; Linked {formatDate(account.linked_at)}
                                                    </div>
                                                </div>
                                            </div>
                                            <button
                                                onClick={() => handleUnlinkProvider(account.provider_id)}
                                                disabled={accounts.length <= 1}
                                                className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                                                    accounts.length <= 1
                                                        ? 'text-slate-500 cursor-not-allowed'
                                                        : 'text-red-400 hover:bg-red-500/20'
                                                }`}
                                                title={
                                                    accounts.length <= 1
                                                        ? 'Cannot unlink your only account'
                                                        : 'Unlink account'
                                                }
                                            >
                                                Unlink
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* Link new account */}
                            <div>
                                <h3
                                    className="text-xs font-medium uppercase tracking-wide mb-3"
                                    style={{ color: 'var(--text-muted)' }}
                                >
                                    Link Another Account
                                </h3>
                                <div className="space-y-2">
                                    <button
                                        onClick={() => handleLinkProvider('google')}
                                        className="w-full flex items-center gap-3 p-3 rounded-lg hover:bg-white/5 transition-colors"
                                        style={{
                                            background: 'var(--bg-canvas)',
                                            border: '1px solid var(--border-panel)',
                                            color: 'var(--text-primary)',
                                        }}
                                    >
                                        {providerIcons.google}
                                        <span className="text-sm">Link Google Account</span>
                                    </button>
                                    <button
                                        onClick={() => handleLinkProvider('microsoft')}
                                        className="w-full flex items-center gap-3 p-3 rounded-lg hover:bg-white/5 transition-colors"
                                        style={{
                                            background: 'var(--bg-canvas)',
                                            border: '1px solid var(--border-panel)',
                                            color: 'var(--text-primary)',
                                        }}
                                    >
                                        {providerIcons.microsoft}
                                        <span className="text-sm">Link Microsoft Account</span>
                                    </button>
                                </div>
                            </div>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}
