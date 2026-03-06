import { useState, useEffect } from 'react';
import { Routes, Route, useParams, useNavigate, useLocation, useMatch } from 'react-router-dom';

import ProjectTree from './components/ProjectTree';
import Floor from './components/Floor';
import ConciergeIntakeSidecar from './components/ConciergeIntakeSidecar';
import UserSidecar from './components/UserSidecar';
import Lobby from './components/Lobby';
import LearnPage from './components/LearnPage';
import AdminWorkbench from './components/admin/AdminWorkbench';
import AdminPanel from './components/admin/AdminPanel';
import { useProjects, useTheme, useAuth, AuthProvider } from './hooks';
import { api } from './api/client';

/**
 * User button - Opens the user sidecar
 * Simple, invisible when not interacted with
 */
function UserButton({ user, onClick }) {
    return (
        <div
            className="p-3 border-t"
            style={{ borderColor: 'var(--border-panel)' }}
        >
            <button
                onClick={onClick}
                className="flex items-center gap-3 w-full p-2 rounded-lg hover:bg-white/10 transition-colors"
                style={{ color: 'var(--text-primary)' }}
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
    );
}

/**
 * Main app content (shown when authenticated)
 * Reads optional projectId and displayId from URL params for deep linking.
 * WS-DEEPLINK-001: Cold-load resolution for all deep link routes.
 */
function AppContent() {
    const { user } = useAuth();
    const { projectId: urlProjectId, displayId: urlDisplayId } = useParams();
    const navigate = useNavigate();
    const location = useLocation();
    // Phase 1: Replace pathname.includes with declarative route matching
    const workBinderMatch = useMatch('/projects/:projectId/work-binder/*');
    const docsMatch = useMatch('/projects/:projectId/docs/:displayId');
    const [showArchived, setShowArchived] = useState(false);
    const { projects, loading, error, refresh: refreshProjects } = useProjects({ includeArchived: showArchived });
    const [selectedProjectId, setSelectedProjectId] = useState(null);
    // Auto-expand work_package node when route matches /work-binder
    const [autoExpandNode, setAutoExpandNode] = useState(
        workBinderMatch ? 'work_package' : null
    );
    // Phase 2: Deep-link document resolution state
    const [deepLinkDocNode, setDeepLinkDocNode] = useState(
        docsMatch ? urlDisplayId : null
    );
    const [projectNotFound, setProjectNotFound] = useState(false);
    const [docNotFound, setDocNotFound] = useState(false);
    const [showIntakeSidecar, setShowIntakeSidecar] = useState(false);
    const [showUserSidecar, setShowUserSidecar] = useState(false);
    const { theme, setTheme } = useTheme();

    // Resolve URL projectId (project_id like HWCA-001) to internal UUID
    useEffect(() => {
        if (urlProjectId && Object.keys(projects).length > 0) {
            const entry = Object.entries(projects).find(
                ([, p]) => p.projectId === urlProjectId
            );
            if (entry) {
                setSelectedProjectId(entry[0]); // internal UUID key
                setProjectNotFound(false);
            } else {
                // Phase 4: Project not found in loaded project list
                setProjectNotFound(true);
            }
        } else if (urlProjectId && Object.keys(projects).length === 0 && !loading) {
            // Projects loaded but empty — project cannot exist
            setProjectNotFound(true);
        }
    }, [urlProjectId, projects, loading]);

    // Phase 2: Resolve /docs/:displayId to a pipeline node on cold load
    useEffect(() => {
        if (!docsMatch || !urlDisplayId || !urlProjectId) return;
        // Validate the display_id by fetching the document
        api.getDocumentByDisplayId(urlProjectId, urlDisplayId)
            .then(doc => {
                if (doc) {
                    // Determine the pipeline node from the document type
                    const docType = doc.document_type || doc.doc_type_id;
                    if (docType) {
                        setAutoExpandNode(docType);
                        setDeepLinkDocNode(docType);
                    }
                    setDocNotFound(false);
                }
            })
            .catch(() => {
                setDocNotFound(true);
                setDeepLinkDocNode(null);
            });
    }, [docsMatch, urlDisplayId, urlProjectId]);

    // Select first project when loaded and no URL projectId
    const projectIds = Object.keys(projects);
    const activeProjectId = selectedProjectId && projects[selectedProjectId]
        ? selectedProjectId
        : (urlProjectId ? null : projectIds[0] || null);

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
        setDeepLinkDocNode(null);
        setProjectNotFound(false);
        setDocNotFound(false);
        // Update URL to reflect selected project
        const project = projects[projectId];
        if (project?.projectId) {
            navigate(`/projects/${project.projectId}`, { replace: true });
        }
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
                if (nextProject) {
                    navigate(`/projects/${nextProject.projectId}`, { replace: true });
                } else {
                    navigate('/', { replace: true });
                }
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
            if (nextProject) {
                navigate(`/projects/${nextProject.projectId}`, { replace: true });
            } else {
                navigate('/', { replace: true });
            }
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

    // Phase 4: Project not found — show 404 within the app shell
    if (projectNotFound && urlProjectId) {
        return (
            <div className={`flex h-screen items-center justify-center theme-${theme}`}
                 style={{ background: 'var(--bg-canvas)' }}>
                <div className="text-center">
                    <h1 className="text-4xl font-bold mb-2" style={{ color: 'var(--text-primary)' }}>404</h1>
                    <p className="mb-2" style={{ color: 'var(--text-muted)' }}>
                        Project not found: <code style={{ color: 'var(--text-secondary)' }}>{urlProjectId}</code>
                    </p>
                    <p className="mb-4" style={{ color: 'var(--text-muted)', fontSize: 13 }}>
                        The project may have been deleted or the URL may be incorrect.
                    </p>
                    <button
                        onClick={() => navigate('/')}
                        className="px-4 py-2 bg-emerald-500 text-white rounded hover:bg-emerald-600"
                    >
                        Back to Lobby
                    </button>
                </div>
            </div>
        );
    }

    // Phase 4: Document not found — show 404 within the app shell
    if (docNotFound && urlDisplayId) {
        return (
            <div className={`flex h-screen items-center justify-center theme-${theme}`}
                 style={{ background: 'var(--bg-canvas)' }}>
                <div className="text-center">
                    <h1 className="text-4xl font-bold mb-2" style={{ color: 'var(--text-primary)' }}>404</h1>
                    <p className="mb-2" style={{ color: 'var(--text-muted)' }}>
                        Document not found: <code style={{ color: 'var(--text-secondary)' }}>{urlDisplayId}</code>
                    </p>
                    <p className="mb-4" style={{ color: 'var(--text-muted)', fontSize: 13 }}>
                        The document may not exist in project <code>{urlProjectId}</code>.
                    </p>
                    <button
                        onClick={() => navigate(urlProjectId ? `/projects/${urlProjectId}` : '/')}
                        className="px-4 py-2 bg-emerald-500 text-white rounded hover:bg-emerald-600"
                    >
                        Back to Project
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
                <ProjectTree
                    projects={projects}
                    selectedId={activeProjectId}
                    onSelectProject={handleSelectProject}
                    onNewProject={handleNewProject}
                    showArchived={showArchived}
                    onToggleShowArchived={() => setShowArchived(prev => !prev)}
                    userSection={<UserButton user={user} onClick={() => setShowUserSidecar(true)} />}
                    autoCollapse={!!activeProjectId}
                />
                <div className="flex-1">
                    {activeProjectId ? (
                        <Floor
                            key={activeProjectId}
                            projectId={activeProjectId}
                            projectCode={projects[activeProjectId]?.projectId}
                            projectName={projects[activeProjectId]?.name}
                            isArchived={projects[activeProjectId]?.isArchived}
                            savedLayout={projects[activeProjectId]?.metadata?.floor_layout}
                            autoExpandNodeId={autoExpandNode || deepLinkDocNode}
                            theme={theme}
                            onThemeChange={setTheme}
                            onProjectUpdate={handleProjectUpdate}
                            onProjectArchive={handleProjectArchive}
                            onProjectUnarchive={handleProjectUnarchive}
                            onProjectDelete={handleProjectDelete}
                        />
                    ) : urlProjectId ? (
                        /* Phase 3: Loading state while resolving project from URL */
                        <div className="flex items-center justify-center h-full"
                             style={{ background: 'var(--bg-canvas)' }}>
                            <div className="text-center">
                                <img
                                    src="/logo-light.png"
                                    alt="The Combine"
                                    className="h-12 mx-auto mb-4 animate-pulse"
                                />
                                <p style={{ color: 'var(--text-muted)' }}>
                                    Loading project...
                                </p>
                            </div>
                        </div>
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

                {/* User Sidecar */}
                {showUserSidecar && (
                    <UserSidecar
                        onClose={() => setShowUserSidecar(false)}
                    />
                )}
            </div>
        </div>
    );
}

/**
 * Loading screen shown while checking auth state
 */
function LoadingScreen() {
    const { theme } = useTheme();
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

/**
 * 404 page for unmatched routes
 */
function NotFound() {
    const { theme } = useTheme();
    const navigate = useNavigate();
    return (
        <div className={`flex h-screen items-center justify-center theme-${theme}`}
             style={{ background: 'var(--bg-canvas)' }}>
            <div className="text-center">
                <h1 className="text-4xl font-bold mb-2" style={{ color: 'var(--text-primary)' }}>404</h1>
                <p className="mb-4" style={{ color: 'var(--text-muted)' }}>Page not found</p>
                <button
                    onClick={() => navigate('/')}
                    className="px-4 py-2 bg-emerald-500 text-white rounded hover:bg-emerald-600"
                >
                    Back to Home
                </button>
            </div>
        </div>
    );
}

/**
 * Admin wrapper with theme
 */
function AdminRoute({ children }) {
    const { theme } = useTheme();
    return <div className={`h-screen theme-${theme}`}>{children}</div>;
}

/**
 * App wrapper that handles auth state and routing (ADR-056)
 */
function AppWithAuth() {
    const { isAuthenticated, loading } = useAuth();

    if (loading) {
        return <LoadingScreen />;
    }

    // Unauthenticated routes
    if (!isAuthenticated) {
        return (
            <Routes>
                <Route path="/learn" element={<LearnPage />} />
                <Route path="*" element={<Lobby />} />
            </Routes>
        );
    }

    // Authenticated routes
    return (
        <Routes>
            <Route path="/admin/workbench" element={<AdminRoute><AdminWorkbench /></AdminRoute>} />
            <Route path="/admin/executions/:executionId" element={<AdminRoute><AdminPanel /></AdminRoute>} />
            <Route path="/admin" element={<AdminRoute><AdminPanel /></AdminRoute>} />
            <Route path="/projects/:projectId/docs/:displayId" element={<AppContent />} />
            <Route path="/projects/:projectId/work-binder/:displayId" element={<AppContent />} />
            <Route path="/projects/:projectId/work-binder" element={<AppContent />} />
            <Route path="/projects/:projectId/production" element={<AppContent />} />
            <Route path="/projects/:projectId" element={<AppContent />} />
            <Route path="/" element={<AppContent />} />
            <Route path="*" element={<NotFound />} />
        </Routes>
    );
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
