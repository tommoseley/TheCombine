import { useState, useEffect } from 'react';
import { useAuth } from '../hooks';

/**
 * UserSidecar - Operator control panel
 *
 * This is the user's control booth - identity plumbing, not production actions.
 * Opens to the right of the sidebar, floor remains visible.
 *
 * Rules:
 * - No canvas interaction disabled underneath
 * - Floor remains visible (dimmed slightly)
 * - Close = back to work instantly
 * - No production actions (Generate, Run, Approve) - those belong to the line
 */
export default function UserSidecar({ onClose }) {
    const { user, logout } = useAuth();
    const [expandedSection, setExpandedSection] = useState(null);
    const [linkedAccounts, setLinkedAccounts] = useState([]);
    const [loadingAccounts, setLoadingAccounts] = useState(false);
    const [message, setMessage] = useState(null);

    // Load linked accounts when that section expands
    useEffect(() => {
        if (expandedSection === 'linked') {
            loadLinkedAccounts();
        }
    }, [expandedSection]);

    const loadLinkedAccounts = async () => {
        try {
            setLoadingAccounts(true);
            const response = await fetch('/auth/accounts', { credentials: 'include' });
            if (response.ok) {
                const data = await response.json();
                setLinkedAccounts(data.identities || []);
            }
        } catch (err) {
            console.error('Failed to load accounts:', err);
        } finally {
            setLoadingAccounts(false);
        }
    };

    const handleLinkProvider = (provider) => {
        window.location.href = `/auth/accounts/link/${provider}`;
    };

    const handleUnlinkProvider = async (provider) => {
        if (linkedAccounts.length <= 1) {
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
                headers: { 'X-CSRF-Token': csrfToken || '' },
            });

            if (response.ok) {
                setMessage({ type: 'success', text: 'Account unlinked' });
                await loadLinkedAccounts();
            } else {
                const data = await response.json();
                throw new Error(data.detail || 'Failed to unlink');
            }
        } catch (err) {
            setMessage({ type: 'error', text: err.message });
        }
    };

    const handleSignOut = async () => {
        await logout();
        onClose();
    };

    const toggleSection = (section) => {
        setExpandedSection(expandedSection === section ? null : section);
        setMessage(null);
    };

    const providerIcons = {
        google: (
            <svg className="w-4 h-4" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
            </svg>
        ),
        microsoft: (
            <svg className="w-4 h-4" viewBox="0 0 23 23">
                <path fill="#f35325" d="M1 1h10v10H1z" />
                <path fill="#81bc06" d="M12 1h10v10H12z" />
                <path fill="#05a6f0" d="M1 12h10v10H1z" />
                <path fill="#ffba08" d="M12 12h10v10H12z" />
            </svg>
        ),
    };

    const sections = [
        { id: 'account', label: 'Account', icon: 'user', future: false },
        { id: 'linked', label: 'Linked Accounts', icon: 'link', future: false },
        { id: 'team', label: 'Team / Org', icon: 'users', future: true },
        { id: 'billing', label: 'Billing', icon: 'credit-card', future: true },
        { id: 'preferences', label: 'Preferences', icon: 'settings', future: true },
    ];

    const getIcon = (icon) => {
        const icons = {
            user: (
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                    <circle cx="12" cy="7" r="4" />
                </svg>
            ),
            link: (
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
                    <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
                </svg>
            ),
            users: (
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                    <circle cx="9" cy="7" r="4" />
                    <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                    <path d="M16 3.13a4 4 0 0 1 0 7.75" />
                </svg>
            ),
            'credit-card': (
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <rect x="1" y="4" width="22" height="16" rx="2" ry="2" />
                    <line x1="1" y1="10" x2="23" y2="10" />
                </svg>
            ),
            settings: (
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="3" />
                    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
                </svg>
            ),
        };
        return icons[icon] || icons.user;
    };

    const renderSectionContent = (sectionId) => {
        switch (sectionId) {
            case 'account':
                return (
                    <div className="px-4 py-3 space-y-3">
                        <div>
                            <label
                                className="text-xs uppercase tracking-wide"
                                style={{ color: 'var(--text-muted)' }}
                            >
                                Email
                            </label>
                            <p
                                className="text-sm mt-1"
                                style={{ color: 'var(--text-primary)' }}
                            >
                                {user?.email || '-'}
                            </p>
                        </div>
                        <div>
                            <label
                                className="text-xs uppercase tracking-wide"
                                style={{ color: 'var(--text-muted)' }}
                            >
                                Member since
                            </label>
                            <p
                                className="text-sm mt-1"
                                style={{ color: 'var(--text-primary)' }}
                            >
                                {user?.user_created_at
                                    ? new Date(user.user_created_at).toLocaleDateString('en-US', {
                                          month: 'long',
                                          year: 'numeric',
                                      })
                                    : '-'}
                            </p>
                        </div>
                    </div>
                );

            case 'linked':
                return (
                    <div className="px-4 py-3">
                        {message && (
                            <div
                                className={`mb-3 px-3 py-2 rounded text-xs ${
                                    message.type === 'error'
                                        ? 'bg-red-500/20 text-red-300'
                                        : 'bg-emerald-500/20 text-emerald-300'
                                }`}
                            >
                                {message.text}
                            </div>
                        )}

                        {loadingAccounts ? (
                            <div className="flex items-center justify-center py-4">
                                <div className="w-5 h-5 border-2 border-t-blue-500 border-r-transparent border-b-transparent border-l-transparent rounded-full animate-spin" />
                            </div>
                        ) : (
                            <>
                                {/* Current accounts */}
                                <div className="space-y-2 mb-4">
                                    {linkedAccounts.map((account) => (
                                        <div
                                            key={account.provider_id}
                                            className="flex items-center justify-between p-2 rounded"
                                            style={{
                                                background: 'var(--bg-canvas)',
                                                border: '1px solid var(--border-panel)',
                                            }}
                                        >
                                            <div className="flex items-center gap-2">
                                                {providerIcons[account.provider_id]}
                                                <span
                                                    className="text-xs"
                                                    style={{ color: 'var(--text-primary)' }}
                                                >
                                                    {account.provider_email}
                                                </span>
                                            </div>
                                            <button
                                                onClick={() => handleUnlinkProvider(account.provider_id)}
                                                disabled={linkedAccounts.length <= 1}
                                                className={`text-xs px-2 py-1 rounded ${
                                                    linkedAccounts.length <= 1
                                                        ? 'text-slate-600 cursor-not-allowed'
                                                        : 'text-red-400 hover:bg-red-500/20'
                                                }`}
                                            >
                                                Unlink
                                            </button>
                                        </div>
                                    ))}
                                </div>

                                {/* Link new */}
                                <div className="space-y-2">
                                    <p
                                        className="text-xs uppercase tracking-wide mb-2"
                                        style={{ color: 'var(--text-muted)' }}
                                    >
                                        Link another
                                    </p>
                                    <button
                                        onClick={() => handleLinkProvider('google')}
                                        className="w-full flex items-center gap-2 p-2 rounded text-xs hover:bg-white/5"
                                        style={{
                                            background: 'var(--bg-canvas)',
                                            border: '1px solid var(--border-panel)',
                                            color: 'var(--text-primary)',
                                        }}
                                    >
                                        {providerIcons.google}
                                        Google
                                    </button>
                                    <button
                                        onClick={() => handleLinkProvider('microsoft')}
                                        className="w-full flex items-center gap-2 p-2 rounded text-xs hover:bg-white/5"
                                        style={{
                                            background: 'var(--bg-canvas)',
                                            border: '1px solid var(--border-panel)',
                                            color: 'var(--text-primary)',
                                        }}
                                    >
                                        {providerIcons.microsoft}
                                        Microsoft
                                    </button>
                                </div>
                            </>
                        )}
                    </div>
                );

            default:
                return (
                    <div
                        className="px-4 py-3 text-xs"
                        style={{ color: 'var(--text-muted)' }}
                    >
                        Coming soon
                    </div>
                );
        }
    };

    return (
        <>
            {/* Subtle backdrop - click to close, floor still visible */}
            <div
                className="fixed inset-0 z-40"
                style={{ background: 'rgba(0, 0, 0, 0.3)' }}
                onClick={onClose}
            />

            {/* Sidecar panel - positioned to the right of sidebar */}
            <div
                className="fixed top-12 bottom-0 z-50 w-72 flex flex-col shadow-2xl"
                style={{
                    left: '240px', // Width of ProjectTree sidebar
                    background: 'var(--bg-panel)',
                    borderRight: '1px solid var(--border-panel)',
                }}
            >
                {/* User header */}
                <div
                    className="px-4 py-4 border-b"
                    style={{ borderColor: 'var(--border-panel)' }}
                >
                    <div className="flex items-center gap-3 mb-3">
                        {user?.avatar_url ? (
                            <img
                                src={user.avatar_url}
                                alt={user.name}
                                className="w-10 h-10 rounded-full"
                            />
                        ) : (
                            <div
                                className="w-10 h-10 rounded-full flex items-center justify-center"
                                style={{ background: 'var(--bg-canvas)' }}
                            >
                                <svg
                                    className="w-5 h-5"
                                    viewBox="0 0 24 24"
                                    fill="none"
                                    stroke="currentColor"
                                    strokeWidth="2"
                                    style={{ color: 'var(--text-muted)' }}
                                >
                                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                                    <circle cx="12" cy="7" r="4" />
                                </svg>
                            </div>
                        )}
                        <div className="flex-1 overflow-hidden">
                            <div
                                className="text-sm font-medium truncate"
                                style={{ color: 'var(--text-primary)' }}
                            >
                                {user?.name || 'User'}
                            </div>
                            <div
                                className="text-xs truncate"
                                style={{ color: 'var(--text-muted)' }}
                            >
                                {user?.email || ''}
                            </div>
                        </div>
                        <button
                            onClick={onClose}
                            className="p-1.5 rounded hover:bg-white/10 transition-colors"
                            style={{ color: 'var(--text-muted)' }}
                        >
                            <svg
                                className="w-4 h-4"
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
                    <div
                        className="text-xs px-2 py-1 rounded inline-block"
                        style={{
                            background: 'var(--bg-canvas)',
                            color: 'var(--text-muted)',
                        }}
                    >
                        Plan: Individual
                    </div>
                </div>

                {/* Sections */}
                <div className="flex-1 overflow-y-auto">
                    {sections.map((section) => (
                        <div
                            key={section.id}
                            style={{ borderBottom: '1px solid var(--border-panel)' }}
                        >
                            <button
                                onClick={() => !section.future && toggleSection(section.id)}
                                className={`w-full flex items-center gap-3 px-4 py-3 transition-colors ${
                                    section.future
                                        ? 'cursor-not-allowed opacity-50'
                                        : 'hover:bg-white/5'
                                }`}
                                style={{ color: 'var(--text-primary)' }}
                                disabled={section.future}
                            >
                                <span style={{ color: 'var(--text-muted)' }}>
                                    {getIcon(section.icon)}
                                </span>
                                <span className="flex-1 text-sm text-left">
                                    {section.label}
                                </span>
                                {section.future ? (
                                    <span
                                        className="text-[10px] px-1.5 py-0.5 rounded"
                                        style={{
                                            background: 'var(--bg-canvas)',
                                            color: 'var(--text-muted)',
                                        }}
                                    >
                                        Soon
                                    </span>
                                ) : (
                                    <svg
                                        className="w-4 h-4 transition-transform"
                                        style={{
                                            color: 'var(--text-muted)',
                                            transform:
                                                expandedSection === section.id
                                                    ? 'rotate(90deg)'
                                                    : 'rotate(0deg)',
                                        }}
                                        viewBox="0 0 24 24"
                                        fill="none"
                                        stroke="currentColor"
                                        strokeWidth="2"
                                    >
                                        <polyline points="9 18 15 12 9 6" />
                                    </svg>
                                )}
                            </button>
                            {expandedSection === section.id && !section.future && (
                                <div
                                    style={{
                                        background: 'var(--bg-canvas)',
                                        borderTop: '1px solid var(--border-panel)',
                                    }}
                                >
                                    {renderSectionContent(section.id)}
                                </div>
                            )}
                        </div>
                    ))}
                </div>

                {/* Sign Out */}
                <div
                    className="p-4 border-t"
                    style={{ borderColor: 'var(--border-panel)' }}
                >
                    <button
                        onClick={handleSignOut}
                        className="w-full flex items-center justify-center gap-2 px-4 py-2 rounded text-sm transition-colors hover:bg-white/5"
                        style={{ color: 'var(--text-muted)' }}
                    >
                        <svg
                            className="w-4 h-4"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2"
                        >
                            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                            <polyline points="16 17 21 12 16 7" />
                            <line x1="21" y1="12" x2="9" y2="12" />
                        </svg>
                        Sign Out
                    </button>
                </div>
            </div>
        </>
    );
}
