import { useState, useEffect } from 'react';
import { ReactFlowProvider } from 'reactflow';

import ProjectTree from './components/ProjectTree';
import Floor from './components/Floor';
import ConciergeIntakeSidecar from './components/ConciergeIntakeSidecar';
import { useProjects, useTheme, useAuth, AuthProvider } from './hooks';
import { api } from './api/client';

/**
 * Main app content (shown when authenticated)
 */
function AppContent() {
    const { user, logout } = useAuth();
    const [showArchived, setShowArchived] = useState(false);
    const { projects, loading, error, refresh: refreshProjects } = useProjects({ includeArchived: showArchived });
    const [selectedProjectId, setSelectedProjectId] = useState(null);
    const [autoExpandNode, setAutoExpandNode] = useState(null);
    const [showIntakeSidecar, setShowIntakeSidecar] = useState(false);
    const { theme, setTheme } = useTheme();

    // Select first project when loaded
    const projectIds = Object.keys(projects);
    const activeProjectId = selectedProjectId && projects[selectedProjectId]
        ? selectedProjectId
        : projectIds[0] || null;

    // Update document title when project changes
    useEffect(() => {
        if (activeProjectId && projects[activeProjectId]) {
            const project = projects[activeProjectId];
            document.title = `${project.projectId} - The Combine`;
        } else {
            document.title = 'The Combine';
        }
    }, [activeProjectId, projects]);

    const handleSelectProject = (projectId) => {
        setSelectedProjectId(projectId);
        setAutoExpandNode(null);
    };

    const handleNewProject = () => {
        setShowIntakeSidecar(true);
    };

    const handleIntakeComplete = async (project) => {
        await refreshProjects();
        if (project && project.id) {
            setSelectedProjectId(project.id);
            setAutoExpandNode('concierge_intake');
        }
        setShowIntakeSidecar(false);
    };

    const handleIntakeClose = () => {
        setShowIntakeSidecar(false);
    };

    const handleProjectUpdate = async (projectId, updates) => {
        try {
            await api.updateProject(projectId, updates);
            await refreshProjects();
        } catch (err) {
            console.error('Failed to update project:', err);
            throw err;
        }
    };

    const handleProjectArchive = async (projectId) => {
        try {
            await api.archiveProject(projectId);
            if (!showArchived) {
                const sorted = Object.values(projects).sort((a, b) => {
                    const nameCompare = (a.name || '').localeCompare(b.name || '');
                    if (nameCompare !== 0) return nameCompare;
                    return (a.projectId || '').localeCompare(b.projectId || '');
                });
                const currentIndex = sorted.findIndex(p => p.id === projectId);
                const nextProject = sorted[currentIndex + 1] || sorted[currentIndex - 1] || null;
                setSelectedProjectId(nextProject?.id || null);
            }
            await refreshProjects();
        } catch (err) {
            console.error('Failed to archive project:', err);
            throw err;
        }
    };

    const handleProjectUnarchive = async (projectId) => {
        try {
            await api.unarchiveProject(projectId);
            await refreshProjects();
        } catch (err) {
            console.error('Failed to unarchive project:', err);
            throw err;
        }
    };

    const handleProjectDelete = async (projectId) => {
        try {
            await api.deleteProject(projectId);
            const sorted = Object.values(projects).sort((a, b) => {
                const nameCompare = (a.name || '').localeCompare(b.name || '');
                if (nameCompare !== 0) return nameCompare;
                return (a.projectId || '').localeCompare(b.projectId || '');
            });
            const currentIndex = sorted.findIndex(p => p.id === projectId);
            const nextProject = sorted[currentIndex + 1] || sorted[currentIndex - 1] || null;
            setSelectedProjectId(nextProject?.id || null);
            await refreshProjects();
        } catch (err) {
            console.error('Failed to delete project:', err);
            throw err;
        }
    };

    if (loading) {
        return (
            <div className={`flex h-screen items-center justify-center theme-${theme}`}
                 style={{ background: 'var(--bg-canvas)' }}>
                <div className="text-center">
                    <img
                        src="/logo-light.png"
                        alt="The Combine"
                        className="h-16 mx-auto mb-4 animate-pulse"
                    />
                    <p style={{ color: 'var(--text-muted)' }}>Loading projects...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className={`flex h-screen items-center justify-center theme-${theme}`}
                 style={{ background: 'var(--bg-canvas)' }}>
                <div className="text-center p-6 rounded-lg" style={{ background: 'var(--bg-panel)' }}>
                    <p className="text-red-500 mb-4">Failed to load projects: {error}</p>
                    <button
                        onClick={() => window.location.reload()}
                        className="px-4 py-2 bg-emerald-500 text-white rounded hover:bg-emerald-600"
                    >
                        Retry
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className={`flex flex-col h-screen theme-${theme}`}>
            {/* Tier 1 Header - Logged In (48px) */}
            <header
                className="h-12 flex items-center justify-between px-4 border-b flex-shrink-0"
                style={{
                    background: 'var(--bg-panel)',
                    borderColor: 'var(--border-panel)',
                }}
            >
                <div className="flex items-center gap-3">
                    <img
                        src="/logo-256.png"
                        alt="The Combine"
                        className="h-7 w-7"
                    />
                    <span
                        className="text-sm font-bold tracking-wide"
                        style={{ color: 'var(--text-primary)' }}
                    >
                        THE COMBINE
                    </span>
                </div>
                {/* Help button */}
                <button
                    className="p-2 rounded hover:bg-white/10 transition-colors"
                    style={{ color: 'var(--text-muted)' }}
                    title="Help"
                >
                    <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <circle cx="12" cy="12" r="10" />
                        <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
                        <path d="M12 17h.01" />
                    </svg>
                </button>
            </header>

            {/* Main content area */}
            <div className="flex flex-1 overflow-hidden">
                {/* Left sidebar with projects and user */}
                <div className="flex flex-col" style={{ background: 'var(--bg-panel)' }}>
                    <ProjectTree
                        projects={projects}
                        selectedId={activeProjectId}
                        onSelectProject={handleSelectProject}
                        onNewProject={handleNewProject}
                        showArchived={showArchived}
                        onToggleShowArchived={() => setShowArchived(prev => !prev)}
                    />
                    {/* User section at bottom left */}
                    <div
                        className="p-3 border-t flex items-center gap-3"
                        style={{ borderColor: 'var(--border-panel)' }}
                    >
                        <button
                            onClick={logout}
                            className="flex items-center gap-3 flex-1 p-2 rounded-lg hover:bg-white/10 transition-colors"
                            style={{ color: 'var(--text-primary)' }}
                            title="Sign out"
                        >
                            {user?.avatar_url ? (
                                <img
                                    src={user.avatar_url}
                                    alt={user.name}
                                    className="w-8 h-8 rounded-full"
                                />
                            ) : (
                                <div
                                    className="w-8 h-8 rounded-full flex items-center justify-center"
                                    style={{ background: 'var(--bg-canvas)' }}
                                >
                                    <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                                        <circle cx="12" cy="7" r="4" />
                                    </svg>
                                </div>
                            )}
                            <div className="flex-1 text-left overflow-hidden">
                                <div className="text-sm font-medium truncate">
                                    {user?.name || 'User'}
                                </div>
                                <div className="text-xs truncate" style={{ color: 'var(--text-muted)' }}>
                                    {user?.email || ''}
                                </div>
                            </div>
                        </button>
                    </div>
                </div>
                <div className="flex-1">
                    {activeProjectId ? (
                        <ReactFlowProvider key={activeProjectId}>
                            <Floor
                                projectId={activeProjectId}
                                projectCode={projects[activeProjectId]?.projectId}
                                projectName={projects[activeProjectId]?.name}
                                isArchived={projects[activeProjectId]?.isArchived}
                                autoExpandNodeId={autoExpandNode}
                                theme={theme}
                                onThemeChange={setTheme}
                                onProjectUpdate={handleProjectUpdate}
                                onProjectArchive={handleProjectArchive}
                                onProjectUnarchive={handleProjectUnarchive}
                                onProjectDelete={handleProjectDelete}
                            />
                        </ReactFlowProvider>
                    ) : (
                        <div className="flex items-center justify-center h-full"
                             style={{ background: 'var(--bg-canvas)' }}>
                            <div className="text-center">
                                <p style={{ color: 'var(--text-muted)' }}>
                                    No projects yet. Create one to get started.
                                </p>
                            </div>
                        </div>
                    )}
                </div>

                {/* Concierge Intake Sidecar */}
                {showIntakeSidecar && (
                    <ConciergeIntakeSidecar
                        onClose={handleIntakeClose}
                        onComplete={handleIntakeComplete}
                    />
                )}
            </div>
        </div>
    );
}

/**
 * Factory Gates - Entry Terminal
 * Industrial landing page for unauthenticated users
 */
function FactoryGates() {
    const { login } = useAuth();

    return (
        <div
            className="min-h-screen flex flex-col"
            style={{
                background: 'linear-gradient(180deg, #0f172a 0%, #1e293b 50%, #0f172a 100%)',
            }}
        >
            {/* Ambient grid overlay */}
            <div
                className="fixed inset-0 pointer-events-none opacity-5"
                style={{
                    backgroundImage: `
                        linear-gradient(rgba(148, 163, 184, 0.1) 1px, transparent 1px),
                        linear-gradient(90deg, rgba(148, 163, 184, 0.1) 1px, transparent 1px)
                    `,
                    backgroundSize: '64px 64px',
                }}
            />

            {/* Main content */}
            <main className="flex-1 flex items-center justify-center p-8 relative z-10">
                <div className="text-center max-w-lg">
                    {/* The Manifold C - Glow Logo */}
                    <div className="mb-12">
                        <img
                            src="/logo-dark.png"
                            alt="The Combine"
                            className="h-32 mx-auto"
                            style={{
                                filter: 'drop-shadow(0 0 40px rgba(16, 185, 129, 0.3))',
                            }}
                        />
                    </div>

                    {/* Wordmark */}
                    <h1
                        className="text-4xl font-bold tracking-[0.3em] mb-3"
                        style={{
                            color: '#f8fafc',
                            fontFamily: 'system-ui, -apple-system, sans-serif',
                        }}
                    >
                        THE COMBINE
                    </h1>
                    <p
                        className="text-sm tracking-[0.2em] uppercase mb-16"
                        style={{ color: '#64748b' }}
                    >
                        Industrial AI for Knowledge Work
                    </p>

                    {/* Entry Terminal */}
                    <div
                        className="p-8 rounded-lg mx-auto max-w-sm"
                        style={{
                            background: 'rgba(30, 41, 59, 0.8)',
                            border: '1px solid #334155',
                            boxShadow: '0 0 60px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.05)',
                        }}
                    >
                        <div
                            className="text-xs tracking-[0.15em] uppercase mb-6"
                            style={{ color: '#64748b' }}
                        >
                            Authorized Personnel Only
                        </div>

                        <div className="space-y-3">
                            <button
                                onClick={() => login('google')}
                                className="w-full flex items-center justify-center gap-3 px-4 py-3 rounded font-medium transition-all hover:scale-[1.02]"
                                style={{
                                    background: '#1e293b',
                                    border: '1px solid #334155',
                                    color: '#e2e8f0',
                                }}
                            >
                                <svg className="w-5 h-5" viewBox="0 0 24 24">
                                    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                                    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                                    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                                    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                                </svg>
                                Enter with Google
                            </button>

                            <button
                                onClick={() => login('microsoft')}
                                className="w-full flex items-center justify-center gap-3 px-4 py-3 rounded font-medium transition-all hover:scale-[1.02]"
                                style={{
                                    background: '#1e293b',
                                    border: '1px solid #334155',
                                    color: '#e2e8f0',
                                }}
                            >
                                <svg className="w-5 h-5" viewBox="0 0 23 23">
                                    <path fill="#f35325" d="M1 1h10v10H1z" />
                                    <path fill="#81bc06" d="M12 1h10v10H12z" />
                                    <path fill="#05a6f0" d="M1 12h10v10H1z" />
                                    <path fill="#ffba08" d="M12 12h10v10H12z" />
                                </svg>
                                Enter with Microsoft
                            </button>
                        </div>
                    </div>

                    {/* Terminology introduction */}
                    <p
                        className="mt-12 text-xs"
                        style={{ color: '#475569' }}
                    >
                        Access the Production Line for stabilized outputs
                    </p>
                </div>
            </main>

            {/* System Status Footer */}
            <footer className="p-6 flex items-center justify-between relative z-10">
                <div className="flex items-center gap-2">
                    <div
                        className="w-2 h-2 rounded-full animate-pulse"
                        style={{ background: '#10b981' }}
                    />
                    <span
                        className="text-xs tracking-wider uppercase"
                        style={{ color: '#475569' }}
                    >
                        System Online
                    </span>
                </div>
                <span
                    className="text-xs"
                    style={{ color: '#334155' }}
                >
                    &copy; 2026 The Combine
                </span>
            </footer>
        </div>
    );
}

/**
 * App wrapper that handles auth state
 */
function AppWithAuth() {
    const { isAuthenticated, loading } = useAuth();
    const { theme } = useTheme();

    // Show loading while checking auth
    if (loading) {
        return (
            <div className={`flex h-screen items-center justify-center theme-${theme}`}
                 style={{ background: 'var(--bg-canvas)' }}>
                <div className="text-center">
                    <img
                        src="/logo-light.png"
                        alt="The Combine"
                        className="h-16 mx-auto mb-4 animate-pulse"
                    />
                    <p style={{ color: 'var(--text-muted)' }}>Loading...</p>
                </div>
            </div>
        );
    }

    // Show Factory Gates if not authenticated
    if (!isAuthenticated) {
        return <FactoryGates />;
    }

    // Show main app if authenticated
    return <AppContent />;
}

/**
 * Root App component with providers
 */
export default function App() {
    return (
        <AuthProvider>
            <AppWithAuth />
        </AuthProvider>
    );
}
