/**
 * LearnPage - The "Convince Me" Page
 *
 * This page exists for evaluators who clicked "Learn how The Combine works"
 * from the Lobby. It's still outside the factory - no production UI elements.
 *
 * Tone: Calm, authoritative, no hype. Let the substance speak.
 */

import { useAuth } from '../hooks';

// Same color palette as Lobby - consistency matters
const colors = {
    bg: '#0f172a',
    bgElevated: '#1e293b',
    border: '#334155',
    textPrimary: '#f8fafc',
    textSecondary: '#94a3b8',
    textMuted: '#64748b',
    textSubtle: '#475569',
    accent: '#3b82f6',
    accentHover: '#2563eb',
};

/**
 * Page Header - Same as Lobby but with back navigation
 */
function LearnHeader() {
    return (
        <header
            className="h-16 flex items-center justify-between px-6 border-b"
            style={{
                background: colors.bg,
                borderColor: colors.border,
            }}
        >
            <a
                href="/"
                className="flex items-center gap-3 transition-colors"
                style={{ color: colors.textMuted }}
                onMouseOver={(e) => e.currentTarget.style.color = colors.textSecondary}
                onMouseOut={(e) => e.currentTarget.style.color = colors.textMuted}
            >
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M19 12H5M12 19l-7-7 7-7" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                <span className="text-sm">Back</span>
            </a>
            <div className="flex items-center gap-3">
                <img
                    src="/logo-dark.png"
                    alt="The Combine"
                    className="h-6"
                />
                <span
                    className="text-sm font-bold tracking-[0.15em]"
                    style={{ color: colors.textPrimary }}
                >
                    THE COMBINE
                </span>
            </div>
            <div className="w-16" /> {/* Spacer for centering */}
        </header>
    );
}

/**
 * Section component for consistent styling
 */
function Section({ title, children }) {
    return (
        <section className="mb-16">
            {title && (
                <h2
                    className="text-xl font-semibold mb-6"
                    style={{ color: colors.textPrimary }}
                >
                    {title}
                </h2>
            )}
            {children}
        </section>
    );
}

/**
 * Paragraph with consistent styling
 */
function P({ children, className = '' }) {
    return (
        <p
            className={`text-base leading-relaxed mb-4 ${className}`}
            style={{ color: colors.textSecondary }}
        >
            {children}
        </p>
    );
}

/**
 * Emphasized text block
 */
function Emphasis({ children }) {
    return (
        <p
            className="text-base leading-relaxed mb-4 pl-4"
            style={{
                color: colors.textPrimary,
                borderLeft: `2px solid ${colors.border}`,
            }}
        >
            {children}
        </p>
    );
}

/**
 * List with consistent styling
 */
function List({ items }) {
    return (
        <ul className="space-y-2 mb-4">
            {items.map((item, index) => (
                <li
                    key={index}
                    className="text-base flex items-start gap-3"
                    style={{ color: colors.textSecondary }}
                >
                    <span style={{ color: colors.textMuted }}>-</span>
                    {item}
                </li>
            ))}
        </ul>
    );
}

/**
 * Numbered step
 */
function Step({ number, title, children }) {
    return (
        <div className="mb-6">
            <div className="flex items-baseline gap-3 mb-2">
                <span
                    className="text-sm font-mono"
                    style={{ color: colors.textMuted }}
                >
                    {number}.
                </span>
                <h3
                    className="text-base font-medium"
                    style={{ color: colors.textPrimary }}
                >
                    {title}
                </h3>
            </div>
            <div className="pl-7">
                <P>{children}</P>
            </div>
        </div>
    );
}

/**
 * Feature block (title + description)
 */
function Feature({ title, children }) {
    return (
        <div className="mb-6">
            <h3
                className="text-base font-medium mb-2"
                style={{ color: colors.textPrimary }}
            >
                {title}
            </h3>
            <P className="mb-0">{children}</P>
        </div>
    );
}

/**
 * CTA Section
 */
function ReadySection({ onLogin }) {
    return (
        <section
            className="text-center py-12 rounded-lg"
            style={{
                background: colors.bgElevated,
                border: `1px solid ${colors.border}`,
            }}
        >
            <h2
                className="text-xl font-semibold mb-4"
                style={{ color: colors.textPrimary }}
            >
                When You're Ready
            </h2>
            <P className="max-w-md mx-auto mb-2">You don't need to prepare anything.</P>
            <P className="max-w-md mx-auto mb-2">You don't need to know the workflow in advance.</P>
            <P className="max-w-md mx-auto mb-8">You start by stating intent — the system handles the rest.</P>

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
 * Footer
 */
function LearnFooter() {
    return (
        <footer className="py-8 text-center">
            <p
                className="text-sm mb-6"
                style={{ color: colors.textMuted }}
            >
                The Combine does not replace human judgment. It makes it visible.
            </p>
            <div className="flex items-center justify-center gap-6">
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
            </div>
        </footer>
    );
}

/**
 * Main LearnPage Component
 */
export default function LearnPage() {
    const { login } = useAuth();

    return (
        <div
            className="min-h-screen flex flex-col"
            style={{ background: colors.bg }}
        >
            <LearnHeader />

            <main className="flex-1 px-6 py-12">
                <article className="max-w-2xl mx-auto">
                    {/* Page Title */}
                    <h1
                        className="text-3xl font-semibold mb-12 text-center"
                        style={{ color: colors.textPrimary }}
                    >
                        Learn More
                    </h1>

                    {/* What The Combine Is */}
                    <Section title="What The Combine Is">
                        <P>The Combine is an AI-assisted production system for knowledge work.</P>
                        <P>
                            It applies manufacturing discipline to work that is normally informal,
                            fragile, and difficult to audit — system design, architecture, requirements,
                            analysis, and planning.
                        </P>
                        <Emphasis>Instead of prompts and chat history, The Combine produces governed artifacts.</Emphasis>
                        <Emphasis>Instead of experimentation without memory, it runs repeatable production lines.</Emphasis>
                    </Section>

                    {/* Why It Exists */}
                    <Section title="Why It Exists">
                        <P>Most AI tools optimize for speed and creativity. That works well for drafts and exploration.</P>
                        <P>It breaks down when the work must be:</P>
                        <List items={[
                            'Auditable',
                            'Traceable',
                            'Reviewed',
                            'Approved',
                            'Reused',
                            'Defended',
                        ]} />
                        <P>
                            The Combine exists for situations where quality, accountability, and
                            repeatability matter more than cleverness.
                        </P>
                    </Section>

                    {/* Why "The Combine" */}
                    <Section title='Why "The Combine"'>
                        <P>
                            The Combine takes its name from the combine harvester — one of the most
                            important industrial inventions of the 20th century.
                        </P>
                        <P>
                            Before the combine, harvesting was fragmented, manual, and inconsistent.
                            Separate steps. Separate tools. High variability. Heavy dependence on individual skill.
                        </P>
                        <P>
                            The combine harvester changed that by integrating many steps into a single,
                            governed production line — increasing consistency, traceability, and scale
                            without removing human oversight.
                        </P>
                        <P>The Combine applies the same philosophy to AI-driven knowledge work.</P>
                        <P>
                            Instead of scattered prompts, fragile documents, and unrepeatable decisions,
                            it assembles intent through a structured line:
                        </P>
                        <List items={[
                            'Inputs are clarified',
                            'Work moves through defined stations',
                            'Quality gates enforce discipline',
                            'Outputs stabilize into reusable artifacts',
                        ]} />
                        <P>This is not automation for speed. It is industrialization for reliability.</P>
                        <Emphasis>As with the original combine, the breakthrough is not intelligence, but integration.</Emphasis>
                    </Section>

                    {/* How It Works */}
                    <Section title="How It Works">
                        <Step number={1} title="You express intent">
                            You describe what you want to build. The system listens, asks clarifying
                            questions, and confirms scope and constraints.
                        </Step>
                        <Step number={2} title="A production line is assembled">
                            Based on your intent, The Combine configures a sequence of specialized
                            stations — each responsible for producing a specific artifact.
                        </Step>
                        <Step number={3} title="Quality gates enforce discipline">
                            Artifacts move forward only when they meet defined criteria. Nothing
                            proceeds without validation.
                        </Step>
                        <Step number={4} title="Outputs stabilize">
                            Approved artifacts are versioned, bound, and ready for use — not just
                            today, but later.
                        </Step>
                    </Section>

                    {/* What Makes It Different */}
                    <Section title="What Makes It Different">
                        <Feature title="Production over prompting">
                            Work progresses through defined stages, not conversations.
                        </Feature>
                        <Feature title="Human accountability remains central">
                            AI assists, but humans approve. Nothing ships without oversight.
                        </Feature>
                        <Feature title="Every decision is traceable">
                            Why something exists, who approved it, and what assumptions were made
                            are always visible.
                        </Feature>
                        <Feature title="Designed for real-world constraints">
                            Compliance, audits, handoffs, and change management are first-class concerns.
                        </Feature>
                    </Section>

                    {/* What The Combine Is Not */}
                    <Section title="What The Combine Is Not">
                        <List items={[
                            'A chat interface',
                            'A creative writing tool',
                            'An autonomous agent that acts without approval',
                            'A system that hides its reasoning or decisions',
                        ]} />
                        <P>If you want improvisation, there are better tools.</P>
                        <Emphasis>If you need defensible outcomes, this is what The Combine is built for.</Emphasis>
                    </Section>

                    {/* Who It's For */}
                    <Section title="Who It's For">
                        <P>The Combine is designed for people responsible for outcomes, including:</P>
                        <List items={[
                            'Architects and technical leaders',
                            'Product and delivery leaders',
                            'Compliance-conscious teams',
                            'Organizations that need repeatable, explainable AI support',
                        ]} />
                        <Emphasis>
                            If the phrase "nothing ships without validation" resonates, you're in the right place.
                        </Emphasis>
                    </Section>

                    {/* CTA */}
                    <ReadySection onLogin={login} />
                </article>
            </main>

            <LearnFooter />
        </div>
    );
}
