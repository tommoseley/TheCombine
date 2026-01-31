import { useState, useEffect } from 'react';
import { ReactFlowProvider } from 'reactflow';

import ProjectTree from './components/ProjectTree';
import Floor from './components/Floor';
import ConciergeIntakeSidecar from './components/ConciergeIntakeSidecar';
import { useProjects, useTheme } from './hooks';
import { api } from './api/client';

export default function App() {
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
        // Open the concierge intake sidecar
        setShowIntakeSidecar(true);
    };

    const handleIntakeComplete = async (project) => {
        // Refresh projects list and select the new project
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
            // Select next available project if not showing archived
            if (!showArchived) {
                // Sort projects the same way ProjectTree does (by name, then projectId)
                const sorted = Object.values(projects).sort((a, b) => {
                    const nameCompare = (a.name || '').localeCompare(b.name || '');
                    if (nameCompare !== 0) return nameCompare;
                    return (a.projectId || '').localeCompare(b.projectId || '');
                });
                const currentIndex = sorted.findIndex(p => p.id === projectId);
                // Prefer the next project (takes its place), fallback to previous
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
            // Sort projects the same way ProjectTree does (by name, then projectId)
            const sorted = Object.values(projects).sort((a, b) => {
                const nameCompare = (a.name || '').localeCompare(b.name || '');
                if (nameCompare !== 0) return nameCompare;
                return (a.projectId || '').localeCompare(b.projectId || '');
            });
            const currentIndex = sorted.findIndex(p => p.id === projectId);
            // Prefer the next project (takes its place), fallback to previous
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
                    <div className="w-8 h-8 border-2 border-t-emerald-500 border-r-transparent border-b-transparent border-l-transparent rounded-full animate-spin mx-auto mb-4" />
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
        <div className={`flex h-screen theme-${theme}`}>
            <ProjectTree
                projects={projects}
                selectedId={activeProjectId}
                onSelectProject={handleSelectProject}
                onNewProject={handleNewProject}
                showArchived={showArchived}
                onToggleShowArchived={() => setShowArchived(prev => !prev)}
            />
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
    );
}
