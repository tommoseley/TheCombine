import { useAuth } from '../hooks';

/**
 * Login page shown to unauthenticated users
 * Displays branding and OAuth login options
 */
export default function LoginPage() {
    const { login, loading } = useAuth();

    return (
        <div
            className="min-h-screen flex flex-col"
            style={{ background: 'var(--bg-canvas)' }}
        >
            {/* Tier 1 Header - Logged Out (64px) */}
            <header
                className="h-16 flex items-center justify-between px-6 border-b"
                style={{
                    background: 'var(--bg-panel)',
                    borderColor: 'var(--border-panel)',
                }}
            >
                <div className="flex items-center gap-3">
                    <img
                        src="/logo-256.png"
                        alt="The Combine"
                        className="h-8 w-8"
                    />
                    <div>
                        <h1
                            className="text-lg font-bold tracking-wide"
                            style={{ color: 'var(--text-primary)' }}
                        >
                            THE COMBINE
                        </h1>
                        <p
                            className="text-xs"
                            style={{ color: 'var(--text-muted)' }}
                        >
                            Industrial AI for Knowledge Work
                        </p>
                    </div>
                </div>
            </header>

            {/* Main content */}
            <main className="flex-1 flex items-center justify-center p-8">
                <div
                    className="max-w-md w-full p-8 rounded-xl"
                    style={{
                        background: 'var(--bg-panel)',
                        border: '1px solid var(--border-panel)',
                    }}
                >
                    <div className="text-center mb-8">
                        <img
                            src="/logo-light.png"
                            alt="The Combine"
                            className="h-16 mx-auto mb-6"
                        />
                        <h2
                            className="text-2xl font-bold mb-2"
                            style={{ color: 'var(--text-primary)' }}
                        >
                            Welcome
                        </h2>
                        <p
                            className="text-sm"
                            style={{ color: 'var(--text-muted)' }}
                        >
                            Sign in to access your production line
                        </p>
                    </div>

                    <div className="space-y-3">
                        <button
                            onClick={() => login('google')}
                            disabled={loading}
                            className="w-full flex items-center justify-center gap-3 px-4 py-3 rounded-lg font-medium transition-colors"
                            style={{
                                background: '#ffffff',
                                color: '#1f2937',
                            }}
                        >
                            <svg className="w-5 h-5" viewBox="0 0 24 24">
                                <path
                                    fill="#4285F4"
                                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                                />
                                <path
                                    fill="#34A853"
                                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                                />
                                <path
                                    fill="#FBBC05"
                                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                                />
                                <path
                                    fill="#EA4335"
                                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                                />
                            </svg>
                            Continue with Google
                        </button>

                        <button
                            onClick={() => login('microsoft')}
                            disabled={loading}
                            className="w-full flex items-center justify-center gap-3 px-4 py-3 rounded-lg font-medium transition-colors"
                            style={{
                                background: '#2f2f2f',
                                color: '#ffffff',
                            }}
                        >
                            <svg className="w-5 h-5" viewBox="0 0 23 23">
                                <path fill="#f35325" d="M1 1h10v10H1z" />
                                <path fill="#81bc06" d="M12 1h10v10H12z" />
                                <path fill="#05a6f0" d="M1 12h10v10H1z" />
                                <path fill="#ffba08" d="M12 12h10v10H12z" />
                            </svg>
                            Continue with Microsoft
                        </button>
                    </div>

                    <p
                        className="text-xs text-center mt-6"
                        style={{ color: 'var(--text-muted)' }}
                    >
                        By signing in, you agree to our Terms of Service and Privacy Policy
                    </p>
                </div>
            </main>

            {/* Footer */}
            <footer
                className="py-4 text-center text-xs"
                style={{ color: 'var(--text-muted)' }}
            >
                &copy; 2026 The Combine. All rights reserved.
            </footer>
        </div>
    );
}
