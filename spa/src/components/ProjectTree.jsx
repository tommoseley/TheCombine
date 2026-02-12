import { useState, useCallback, useRef, useEffect, useMemo } from 'react';

const STATUS_COLORS = {
    active: '#f59e0b',
    complete: '#10b981',
    queued: '#64748b'
};

const MIN_WIDTH = 180;
const MAX_WIDTH = 400;
const DEFAULT_WIDTH = 260;
const COLLAPSED_WIDTH = 48;

/**
 * Format ISO date string to short display format
 */
function formatDate(isoString) {
    if (!isoString) return '';
    try {
        const date = new Date(isoString);
        return date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: date.getFullYear() !== new Date().getFullYear() ? 'numeric' : undefined
        });
    } catch {
        return '';
    }
}

export default function ProjectTree({ projects, selectedId, onSelectProject, onNewProject, showArchived, onToggleShowArchived, userSection }) {
    const [collapsed, setCollapsed] = useState(false);
    const [width, setWidth] = useState(DEFAULT_WIDTH);
    const [isDragging, setIsDragging] = useState(false);
    const containerRef = useRef(null);
    const selectedRef = useRef(null);

    // Scroll selected project into view when selection changes
    useEffect(() => {
        if (selectedRef.current) {
            selectedRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }, [selectedId]);

    // Sort projects by name, then by projectId
    const sortedProjects = useMemo(() => {
        return Object.values(projects).sort((a, b) => {
            const nameCompare = (a.name || '').localeCompare(b.name || '');
            if (nameCompare !== 0) return nameCompare;
            return (a.projectId || '').localeCompare(b.projectId || '');
        });
    }, [projects]);

    const handleNewProject = () => {
        onNewProject();
    };

    const handleMouseDown = useCallback((e) => {
        e.preventDefault();
        setIsDragging(true);
    }, []);

    const handleMouseMove = useCallback((e) => {
        if (!isDragging) return;
        const newWidth = Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, e.clientX));
        setWidth(newWidth);
    }, [isDragging]);

    const handleMouseUp = useCallback(() => {
        setIsDragging(false);
    }, []);

    useEffect(() => {
        if (isDragging) {
            document.addEventListener('mousemove', handleMouseMove);
            document.addEventListener('mouseup', handleMouseUp);
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';
        } else {
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
        }
        return () => {
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
        };
    }, [isDragging, handleMouseMove, handleMouseUp]);

    const currentWidth = collapsed ? COLLAPSED_WIDTH : width;

    return (
        <div
            ref={containerRef}
            className="h-full flex flex-col relative"
            onWheel={(e) => e.stopPropagation()}
            style={{
                width: currentWidth,
                minWidth: currentWidth,
                background: 'var(--bg-panel)',
                borderRight: '1px solid var(--border-panel)',
                transition: isDragging ? 'none' : 'width 0.2s ease'
            }}
        >
            {/* Header */}
            <div
                className="p-3 border-b flex items-center justify-between"
                style={{ borderColor: 'var(--border-panel)' }}
            >
                {!collapsed && (
                    <div className="flex items-center gap-2">
                        <h2
                            className="text-sm font-semibold"
                            style={{ color: 'var(--text-primary)' }}
                        >
                            Projects
                        </h2>
                        <button
                            onClick={onToggleShowArchived}
                            className="p-1 rounded hover:bg-white/10 transition-colors"
                            style={{ color: showArchived ? '#f59e0b' : 'var(--text-muted)' }}
                            title={showArchived ? 'Hide archived' : 'Show archived'}
                        >
                            <svg
                                width="14"
                                height="14"
                                viewBox="0 0 24 24"
                                fill="none"
                                stroke="currentColor"
                                strokeWidth="2"
                            >
                                <path d="M21 8v13H3V8M1 3h22v5H1zM10 12h4" />
                            </svg>
                        </button>
                    </div>
                )}
                <button
                    onClick={() => setCollapsed(!collapsed)}
                    className="p-1.5 rounded hover:bg-white/10 transition-colors"
                    style={{ color: 'var(--text-muted)' }}
                    title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
                >
                    <svg
                        width="16"
                        height="16"
                        viewBox="0 0 16 16"
                        fill="none"
                        style={{
                            transform: collapsed ? 'rotate(180deg)' : 'rotate(0deg)',
                            transition: 'transform 0.2s ease'
                        }}
                    >
                        <path
                            d="M10 12L6 8L10 4"
                            stroke="currentColor"
                            strokeWidth="1.5"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                        />
                    </svg>
                </button>
            </div>

            {/* Project list */}
            {!collapsed && (
                <div className="flex-1 overflow-y-auto p-2">
                    {sortedProjects.map(project => {
                        const isSelected = selectedId === project.id;
                        return (
                        <div
                            key={project.id}
                            ref={isSelected ? selectedRef : null}
                            onClick={() => onSelectProject(project.id)}
                            className="p-3 rounded-lg mb-2 cursor-pointer transition-all"
                            style={{
                                background: isSelected ? 'var(--state-active-bg)' : 'transparent',
                                border: isSelected
                                    ? '1px solid var(--state-active-bg)'
                                    : '1px solid transparent',
                                boxShadow: isSelected ? '0 0 12px rgba(245, 158, 11, 0.3)' : 'none'
                            }}
                        >
                            <div className="flex items-center gap-2">
                                <div
                                    className="w-2 h-2 rounded-full flex-shrink-0"
                                    style={{
                                        background: isSelected ? '#ffffff' : (STATUS_COLORS[project.status] || STATUS_COLORS.queued)
                                    }}
                                />
                                <span
                                    className="text-sm font-medium truncate flex-1"
                                    style={{ color: isSelected ? '#ffffff' : 'var(--text-primary)' }}
                                >
                                    {project.name}
                                </span>
                                {project.isArchived && (
                                    <svg
                                        className="w-3.5 h-3.5 flex-shrink-0"
                                        style={{ color: isSelected ? 'rgba(255,255,255,0.7)' : 'var(--text-muted)' }}
                                        viewBox="0 0 24 24"
                                        fill="none"
                                        stroke="currentColor"
                                        strokeWidth="2"
                                        title="Archived"
                                    >
                                        <path d="M21 8v13H3V8M1 3h22v5H1zM10 12h4" />
                                    </svg>
                                )}
                            </div>
                            <div className="flex items-center justify-between mt-0.5 ml-4">
                                <span
                                    className="text-[10px] font-mono"
                                    style={{ color: isSelected ? 'rgba(255,255,255,0.8)' : 'var(--text-muted)' }}
                                >
                                    {project.projectId}
                                </span>
                                <span
                                    className="text-[10px]"
                                    style={{ color: isSelected ? 'rgba(255,255,255,0.8)' : 'var(--text-muted)' }}
                                >
                                    {formatDate(project.createdAt)}
                                </span>
                            </div>
                        </div>
                    );
                    })}
                </div>
            )}

            {/* Collapsed project icons */}
            {collapsed && (
                <div className="flex-1 overflow-y-auto py-2">
                    {sortedProjects.map(project => (
                        <div
                            key={project.id}
                            onClick={() => onSelectProject(project.id)}
                            className="flex items-center justify-center py-2 cursor-pointer hover:bg-white/5"
                            title={project.name}
                        >
                            <div
                                className="w-3 h-3 rounded-full"
                                style={{
                                    background: STATUS_COLORS[project.status] || STATUS_COLORS.queued,
                                    boxShadow: selectedId === project.id
                                        ? '0 0 0 2px var(--bg-panel), 0 0 0 4px var(--border-node)'
                                        : 'none'
                                }}
                            />
                        </div>
                    ))}
                </div>
            )}

            {/* New project button */}
            {!collapsed && (
                <div
                    className="p-3 border-t"
                    style={{ borderColor: 'var(--border-panel)' }}
                >
                    <button
                        onClick={handleNewProject}
                        className="w-full py-2.5 rounded-lg text-sm font-medium flex items-center justify-center gap-2 transition-colors"
                        style={{ background: '#10b981', color: 'white' }}
                    >
                        <span style={{ fontSize: 18, lineHeight: 1 }}>+</span>
                        <span>New Project</span>
                    </button>
                </div>
            )}

            {/* Collapsed new project button */}
            {collapsed && (
                <div
                    className="p-2 border-t flex justify-center"
                    style={{ borderColor: 'var(--border-panel)' }}
                >
                    <button
                        onClick={handleNewProject}
                        className="w-8 h-8 rounded-lg flex items-center justify-center"
                        style={{ background: '#10b981', color: 'white' }}
                        title="New Project"
                    >
                        <span style={{ fontSize: 18, lineHeight: 1 }}>+</span>
                    </button>
                </div>
            )}

            {/* User section (passed from parent) */}
            {userSection}

            {/* Drag handle */}
            {!collapsed && (
                <div
                    onMouseDown={handleMouseDown}
                    className="absolute top-0 right-0 w-1 h-full cursor-col-resize hover:bg-emerald-500/50 transition-colors"
                    style={{
                        background: isDragging ? 'var(--state-active-bg)' : 'transparent'
                    }}
                />
            )}
        </div>
    );
}
