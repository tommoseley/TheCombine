/**
 * Lobby - The Entry Terminal
 *
 * The Lobby is outside the factory. Nothing is moving. Nothing is being built.
 * It exists only to explain the nature of the system and to control entry.
 * Crossing the login boundary is crossing into production.
 *
 * Design Principles (from lobby-spec.md):
 * - Separation of Worlds: No production UI elements
 * - Orientation Over Demonstration: Explains how the system works, not how to use it
 * - Calm Authority: No hype, animations, or gimmicks
 * - Single Primary Action: All interaction funnels toward authentication
 * - Irreversibility: Once authenticated, the Lobby is no longer visible
 *
 * Layout Principle:
 * - Never more than two vertical anchors before the primary fork
 * - The fork: "Start a Production Line" (sign in) vs "Learn More" (evaluate)
 * - "Learn More" is an alternative primary action, not an afterthought
 */

import { useAuth } from '../hooks';

// Color palette - lower contrast than production, calm and authoritative
const colors = {
    bg: '#0f172a',           // Deep slate
    bgElevated: '#1e293b',   // Elevated panels
    border: '#334155',       // Subtle borders
    textPrimary: '#f8fafc',  // High contrast text
    textSecondary: '#94a3b8', // Body text
    textMuted: '#64748b',    // Subdued text
    textSubtle: '#475569',   // Footer text
    accent: '#3b82f6',       // Blue accent for CTA
    accentHover: '#2563eb',  // CTA hover
};

/**
 * Lobby Header - Fixed, persistent
 * Brand mark + tagline only. No user controls.
 */
function LobbyHeader() {
    return (
        <header
            className="h-16 flex items-center justify-center border-b"
            style={{
                background: colors.bg,
                borderColor: colors.border,
            }}
        >
            <div className="flex items-center gap-3">
                <img
                    src="/logo-dark.png"
                    alt="The Combine"
                    className="h-8"
                />
                <div>
                    <span
                        className="text-sm font-bold tracking-[0.2em]"
                        style={{ color: colors.textPrimary }}
                    >
                        THE COMBINE
                    </span>
                    <span
                        className="text-xs tracking-wide ml-4"
                        style={{ color: colors.textMuted }}
                    >
                        Industrial AI for Knowledge Work
                    </span>
                </div>
            </div>
        </header>
    );
}

/**
 * Hero Section: Identity & Value Proposition + Learn More link
 * The fork happens here: evaluators can branch to Learn More before scrolling.
 */
function Hero() {
    return (
        <section className="text-center max-w-2xl mx-auto">
            <h1
                className="text-3xl font-semibold mb-6 leading-tight"
                style={{ color: colors.textPrimary }}
            >
                Turn complex intent into governed, repeatable artifacts.
            </h1>
            <p
                className="text-lg leading-relaxed mb-6"
                style={{ color: colors.textSecondary }}
            >
                The Combine applies manufacturing discipline to AI knowledge work.
                Every output is traceable. Every decision is auditable.
                Production over prompting.
            </p>
            {/* Learn More - catches evaluators before they scroll */}
            <a
                href="/learn"
                className="text-sm transition-colors inline-flex items-center gap-1"
                style={{ color: colors.textMuted }}
                onMouseOver={(e) => e.currentTarget.style.color = colors.textSecondary}
                onMouseOut={(e) => e.currentTarget.style.color = colors.textMuted}
            >
                Learn how The Combine works
                <span aria-hidden="true">&rarr;</span>
            </a>
        </section>
    );
}

/**
 * Conceptual Flow - Single horizontal row
 * Compressed: Icon + label + description on hover
 */
function ConceptualFlow() {
    const steps = [
        {
            icon: (
                <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
            ),
            title: 'Express Intent',
            description: 'Describe what you need',
        },
        {
            icon: (
                <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M19.5 12c0-1.232-.046-2.453-.138-3.662a4.006 4.006 0 00-3.7-3.7 48.678 48.678 0 00-7.324 0 4.006 4.006 0 00-3.7 3.7c-.017.22-.032.441-.046.662M19.5 12l3-3m-3 3l-3-3m-12 3c0 1.232.046 2.453.138 3.662a4.006 4.006 0 003.7 3.7 48.656 48.656 0 007.324 0 4.006 4.006 0 003.7-3.7c.017-.22.032-.441.046-.662M4.5 12l3 3m-3-3l-3 3" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
            ),
            title: 'Line Assembles',
            description: 'Stations configure',
        },
        {
            icon: (
                <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
            ),
            title: 'Gates Enforce',
            description: 'Validation required',
        },
        {
            icon: (
                <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5M10 11.25h4M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
            ),
            title: 'Artifacts Stabilize',
            description: 'Versioned, ready',
        },
    ];

    return (
        <section className="max-w-4xl mx-auto">
            <div className="flex items-start justify-between gap-4">
                {steps.map((step, index) => (
                    <div key={index} className="flex-1 text-center group">
                        <div
                            className="inline-flex items-center justify-center w-10 h-10 rounded-full mb-3"
                            style={{
                                background: colors.bgElevated,
                                border: `1px solid ${colors.border}`,
                                color: colors.textMuted,
                            }}
                        >
                            {step.icon}
                        </div>
                        <h3
                            className="text-sm font-medium mb-1"
                            style={{ color: colors.textPrimary }}
                        >
                            {step.title}
                        </h3>
                        <p
                            className="text-xs"
                            style={{ color: colors.textMuted }}
                        >
                            {step.description}
                        </p>
                        {/* Connector arrow (except last) */}
                        {index < steps.length - 1 && (
                            <div
                                className="absolute top-5 -right-2 hidden md:block"
                                style={{ color: colors.border }}
                            >
                            </div>
                        )}
                    </div>
                ))}
            </div>
        </section>
    );
}

/**
 * Trust Signals - Compact, inline
 */
function TrustSignals() {
    const signals = [
        'Auditable outputs',
        'Traceable decisions',
        'Validated delivery',
        'Human accountability',
    ];

    return (
        <section className="text-center">
            <div className="flex flex-wrap justify-center gap-x-6 gap-y-2">
                {signals.map((signal, index) => (
                    <span
                        key={index}
                        className="text-xs"
                        style={{ color: colors.textMuted }}
                    >
                        {signal}
                    </span>
                ))}
            </div>
        </section>
    );
}

/**
 * Sign In Section - Optional feeling, not pushy
 * "Ready?" signals this is for users who've decided
 */
function SignIn({ onLogin }) {
    return (
        <section className="text-center">
            <p
                className="text-sm font-medium mb-4"
                style={{ color: colors.textSecondary }}
            >
                Ready?
            </p>
            <div className="inline-flex flex-col gap-3">
                <button
                    onClick={() => onLogin('google')}
                    className="w-64 flex items-center justify-center gap-3 px-4 py-3 rounded font-medium transition-colors"
                    style={{
                        background: colors.accent,
                        color: '#ffffff',
                    }}
                    onMouseOver={(e) => e.currentTarget.style.background = colors.accentHover}
                    onMouseOut={(e) => e.currentTarget.style.background = colors.accent}
                >
                    <svg className="w-5 h-5" viewBox="0 0 24 24">
                        <path fill="#ffffff" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                        <path fill="#ffffff" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                        <path fill="#ffffff" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                        <path fill="#ffffff" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                    </svg>
                    Continue with Google
                </button>

                <button
                    onClick={() => onLogin('microsoft')}
                    className="w-64 flex items-center justify-center gap-3 px-4 py-3 rounded font-medium transition-colors"
                    style={{
                        background: colors.bg,
                        border: `1px solid ${colors.border}`,
                        color: colors.textPrimary,
                    }}
                    onMouseOver={(e) => e.currentTarget.style.background = colors.bgElevated}
                    onMouseOut={(e) => e.currentTarget.style.background = colors.bg}
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
        </section>
    );
}

/**
 * Lobby Footer - Minimal and quiet
 * Copyright + legal links only.
 */
function LobbyFooter() {
    return (
        <footer className="py-6 flex items-center justify-center gap-6">
            <a
                href="/terms"
                className="text-xs transition-colors"
                style={{ color: colors.textSubtle }}
                onMouseOver={(e) => e.currentTarget.style.color = colors.textMuted}
                onMouseOut={(e) => e.currentTarget.style.color = colors.textSubtle}
            >
                Terms
            </a>
            <a
                href="/privacy"
                className="text-xs transition-colors"
                style={{ color: colors.textSubtle }}
                onMouseOver={(e) => e.currentTarget.style.color = colors.textMuted}
                onMouseOut={(e) => e.currentTarget.style.color = colors.textSubtle}
            >
                Privacy
            </a>
            <span
                className="text-xs"
                style={{ color: colors.border }}
            >
                &copy; 2026 The Combine
            </span>
        </footer>
    );
}

/**
 * Main Lobby Component
 * The quiet space before heavy machinery.
 */
export default function Lobby() {
    const { login } = useAuth();

    return (
        <div
            className="min-h-screen flex flex-col"
            style={{ background: colors.bg }}
        >
            <LobbyHeader />

            {/* Main content - compressed vertical rhythm */}
            <main className="flex-1 flex flex-col justify-center px-8 py-12">
                <div className="space-y-12">
                    <Hero />
                    <ConceptualFlow />
                    <TrustSignals />
                    <SignIn onLogin={login} />
                </div>
            </main>

            <LobbyFooter />
        </div>
    );
}
