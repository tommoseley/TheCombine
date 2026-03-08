import { useState, useEffect, useCallback, useMemo, useRef } from 'react';

import ContentPanel from './ContentPanel';
import { api } from '../api/client';
import { THEMES } from '../utils/constants';
import { useProductionStatus } from '../hooks';

/**
 * BinderDownloadDropdown — compact download button with standard/evidence options.
 */
function BinderDownloadDropdown({ projectId, projectCode }) {
    const [open, setOpen] = useState(false);
    const [downloading, setDownloading] = useState(null);
    const ref = useRef(null);

    useEffect(() => {
        if (!open) return;
        function close(e) { if (ref.current && !ref.current.contains(e.target)) setOpen(false); }
        document.addEventListener('mousedown', close);
        return () => document.removeEventListener('mousedown', close);
    }, [open]);

    const handleDownload = async (mode) => {
        setDownloading(mode);
        try {
            const blob = await api.renderProjectBinder(projectId, { mode });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            const suffix = mode === 'evidence' ? '-evidence' : '';
            a.download = `${projectCode || projectId}-binder${suffix}.md`;
            a.click();
            URL.revokeObjectURL(url);
        } catch (err) {
            if (err.status === 409) {
                alert(`Binder render blocked: ${err.data?.message || 'IA verification failed'}`);
            } else {
                console.error('Binder download failed:', err);
            }
        } finally {
            setDownloading(null);
            setOpen(false);
        }
    };

    return (
        <div ref={ref} className="relative flex-shrink-0">
            <button
                onClick={() => setOpen(!open)}
                className="p-1 rounded hover:bg-white/10 transition-colors"
                style={{ color: 'var(--text-muted)' }}
                title="Download Project Binder"
            >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                    <polyline points="7 10 12 15 17 10" />
                    <line x1="12" y1="15" x2="12" y2="3" />
                </svg>
            </button>
            {open && (
                <div
                    className="absolute right-0 top-full mt-1 z-50 rounded-lg border shadow-lg py-1"
                    style={{ background: 'var(--bg-panel)', borderColor: 'var(--border-panel)', minWidth: 220 }}
                >
                    <button
                        onClick={() => handleDownload('standard')}
                        disabled={!!downloading}
                        className="w-full text-left px-3 py-2 text-[10px] hover:bg-white/10 transition-colors"
                        style={{ color: 'var(--text-primary)', background: 'transparent', border: 'none', cursor: 'pointer' }}
                    >
                        {downloading === 'standard' ? 'Downloading...' : 'Download Binder'}
                    </button>
                    <button
                        onClick={() => handleDownload('evidence')}
                        disabled={!!downloading}
                        className="w-full text-left px-3 py-2 text-[10px] hover:bg-white/10 transition-colors"
                        style={{ color: 'var(--text-primary)', background: 'transparent', border: 'none', cursor: 'pointer' }}
                    >
                        {downloading === 'evidence' ? 'Downloading...' : 'Download Binder (With Evidence)'}
                    </button>
                </div>
            )}
        </div>
    );
}

const THEME_LABELS = { industrial: 'Industrial', light: 'Light', blueprint: 'Blueprint' };

/* Shared artifact-state helpers (same logic as PipelineRail) */
function getArtifactState(rawState) {
    if (['produced', 'stabilized', 'ready', 'complete'].includes(rawState)) return 'stabilized';
    if (['requirements_not_met', 'blocked', 'halted', 'failed'].includes(rawState)) return 'blocked';
    if (['in_production', 'active', 'queued', 'awaiting_operator'].includes(rawState)) return 'in_progress';
    if (['ready_for_production', 'waiting', 'pending_acceptance'].includes(rawState)) return 'ready';
    return 'ready';
}

const ARTIFACT_COLORS = {
    blocked: 'var(--state-blocked-bg)',
    in_progress: 'var(--state-active-bg)',
    ready: 'var(--state-ready-bg)',
    stabilized: 'var(--state-stabilized-bg)',
};

const DOC_TYPE_NAMES = {
    concierge_intake: 'Concierge Intake',
    project_discovery: 'Project Discovery',
    implementation_plan: 'Implementation Plan',
    technical_architecture: 'Technical Architecture',
    work_package: 'Work Binder',
};

function docName(id) {
    return DOC_TYPE_NAMES[id] || id.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
}

const LINE_STATE_LABELS = {
    active: { text: 'Active', color: '#f59e0b' },
    stopped: { text: 'Stopped', color: '#ef4444' },
    complete: { text: 'Complete', color: '#10b981' },
    idle: { text: 'Idle', color: 'var(--text-muted)' },
};

/**
 * ProjectEditPanel — dropdown panel for project management actions.
 * Appears below the edit button in the breadcrumb bar.
 */
function ProjectEditPanel({ projectId, projectName, isArchived, onUpdate, onArchive, onUnarchive, onDelete, onClose }) {
    const [name, setName] = useState(projectName || '');
    const [saving, setSaving] = useState(false);
    const [confirmDelete, setConfirmDelete] = useState(false);
    const panelRef = useRef(null);

    useEffect(() => {
        function handleClickOutside(e) {
            if (panelRef.current && !panelRef.current.contains(e.target)) onClose();
        }
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, [onClose]);

    const handleSave = async () => {
        if (!name.trim() || name === projectName) return;
        setSaving(true);
        try {
            await onUpdate(projectId, { name: name.trim() });
            onClose();
        } catch { setSaving(false); }
    };

    const handleArchiveToggle = async () => {
        try {
            if (isArchived) await onUnarchive(projectId);
            else await onArchive(projectId);
            onClose();
        } catch {}
    };

    const handleDelete = async () => {
        try {
            await onDelete(projectId);
            onClose();
        } catch {}
    };

    return (
        <div
            ref={panelRef}
            className="absolute top-full right-0 mt-1 z-50 rounded-lg border shadow-xl"
            style={{
                background: 'var(--bg-panel)',
                borderColor: 'var(--border-panel)',
                width: 280,
            }}
        >
            <div className="p-3">
                <label
                    className="text-[10px] font-medium uppercase tracking-wider block mb-1"
                    style={{ color: 'var(--text-muted)' }}
                >
                    Project Name
                </label>
                <div className="flex gap-2">
                    <input
                        type="text"
                        value={name}
                        onChange={e => setName(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && handleSave()}
                        className="flex-1 text-sm px-2 py-1.5 rounded border"
                        style={{
                            background: 'var(--bg-canvas)',
                            borderColor: 'var(--border-panel)',
                            color: 'var(--text-primary)',
                            outline: 'none',
                        }}
                    />
                    <button
                        onClick={handleSave}
                        disabled={saving || !name.trim() || name === projectName}
                        className="text-xs px-3 py-1.5 rounded font-medium transition-colors"
                        style={{
                            background: name !== projectName && name.trim() ? '#10b981' : 'var(--bg-canvas)',
                            color: name !== projectName && name.trim() ? 'white' : 'var(--text-muted)',
                        }}
                    >
                        {saving ? '...' : 'Save'}
                    </button>
                </div>
            </div>
            <div className="border-t px-3 py-2 flex items-center gap-2" style={{ borderColor: 'var(--border-panel)' }}>
                <button
                    onClick={handleArchiveToggle}
                    className="text-xs px-3 py-1.5 rounded hover:bg-white/10 transition-colors"
                    style={{ color: 'var(--text-muted)' }}
                >
                    {isArchived ? 'Unarchive' : 'Archive'}
                </button>
                <div className="flex-1" />
                {!confirmDelete ? (
                    <button
                        onClick={() => setConfirmDelete(true)}
                        className="text-xs px-3 py-1.5 rounded hover:bg-red-500/10 transition-colors"
                        style={{ color: '#ef4444' }}
                    >
                        Delete
                    </button>
                ) : (
                    <button
                        onClick={handleDelete}
                        className="text-xs px-3 py-1.5 rounded font-medium"
                        style={{ background: '#ef4444', color: 'white' }}
                    >
                        Confirm Delete
                    </button>
                )}
            </div>
        </div>
    );
}

/**
 * PipelineBreadcrumb — persistent horizontal status bar for the production line.
 */
function PipelineBreadcrumb({ data, selectedNodeId, onSelectNode, projectId, projectCode, projectName, isArchived, lineState, theme, onCycleTheme, onProjectUpdate, onProjectArchive, onProjectUnarchive, onProjectDelete }) {
    const l1Items = data.filter(d => (d.level || 1) === 1);
    const ls = LINE_STATE_LABELS[lineState] || LINE_STATE_LABELS.idle;
    const [showEdit, setShowEdit] = useState(false);

    return (
        <div
            className="flex items-center gap-4 px-4 border-b flex-shrink-0"
            style={{
                height: 40,
                background: 'var(--bg-canvas)',
                borderColor: 'var(--border-panel)',
            }}
        >
            {/* Project identity */}
            <span
                className="text-xs font-mono flex-shrink-0"
                style={{ color: 'var(--text-muted)' }}
            >
                {projectCode}
            </span>
            <span
                className="text-xs font-semibold truncate flex-shrink-0"
                style={{ color: 'var(--text-primary)', maxWidth: 240 }}
            >
                {projectName || 'Untitled'}
            </span>

            {/* Edit button */}
            <div className="relative flex-shrink-0">
                <button
                    onClick={() => setShowEdit(!showEdit)}
                    className="p-1 rounded hover:bg-white/10 transition-colors"
                    style={{ color: showEdit ? 'var(--text-primary)' : 'var(--text-muted)' }}
                    title="Edit project"
                >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                        <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                    </svg>
                </button>
                {showEdit && (
                    <ProjectEditPanel
                        projectId={projectId}
                        projectName={projectName}
                        isArchived={isArchived}
                        onUpdate={onProjectUpdate}
                        onArchive={onProjectArchive}
                        onUnarchive={onProjectUnarchive}
                        onDelete={onProjectDelete}
                        onClose={() => setShowEdit(false)}
                    />
                )}
            </div>

            {/* Divider */}
            <div style={{ width: 1, height: 16, background: 'var(--border-panel)', flexShrink: 0 }} />

            {/* Line state */}
            <span className="flex items-center gap-1.5 flex-shrink-0">
                <span
                    className="inline-block w-2 h-2 rounded-full"
                    style={{ background: ls.color }}
                />
                <span className="text-[10px] font-medium" style={{ color: ls.color }}>
                    {ls.text}
                </span>
            </span>

            {/* Divider */}
            <div style={{ width: 1, height: 16, background: 'var(--border-panel)', flexShrink: 0 }} />

            {/* Pipeline stages */}
            <div className="flex items-center gap-1 flex-1 overflow-x-auto min-w-0">
                {l1Items.map((item, idx) => {
                    const state = getArtifactState(item.state || 'ready_for_production');
                    const color = ARTIFACT_COLORS[state];
                    const isSelected = item.id === selectedNodeId;
                    return (
                        <button
                            key={item.id}
                            onClick={() => onSelectNode(item.id)}
                            className="flex items-center gap-1.5 px-2 py-1 rounded transition-colors flex-shrink-0"
                            style={{
                                background: isSelected ? 'var(--bg-panel)' : 'transparent',
                                border: 'none',
                                cursor: 'pointer',
                            }}
                            title={docName(item.id)}
                        >
                            <span
                                className={`inline-block w-2 h-2 rounded-full flex-shrink-0${state === 'in_progress' ? ' breadcrumb-pulse' : ''}`}
                                style={{ background: color }}
                            />
                            <span
                                className="text-[10px] font-medium whitespace-nowrap"
                                style={{
                                    color: isSelected ? 'var(--text-primary)' : 'var(--text-muted)',
                                }}
                            >
                                {docName(item.id)}
                            </span>
                            {idx < l1Items.length - 1 && (
                                <span
                                    className="text-[10px] ml-1"
                                    style={{ color: 'var(--text-muted)', opacity: 0.4 }}
                                >
                                    ›
                                </span>
                            )}
                        </button>
                    );
                })}
            </div>

            {/* Download binder */}
            <BinderDownloadDropdown projectId={projectId} projectCode={projectCode} />

            {/* Theme toggle */}
            <button
                onClick={onCycleTheme}
                className="text-[10px] font-medium px-2 py-1 rounded hover:bg-white/10 transition-colors flex-shrink-0"
                style={{ color: 'var(--text-muted)' }}
            >
                {THEME_LABELS[theme]}
            </button>
        </div>
    );
}

export default function Floor({ projectId, projectCode, projectName, isArchived, savedLayout, autoExpandNodeId, theme, onThemeChange, onProjectUpdate, onProjectArchive, onProjectUnarchive, onProjectDelete }) {
    const {
        data: productionData,
        lineState,
        loading,
        error,
        notification,
        dismissNotification,
        resolveInterrupt,
        startProduction,
    } = useProductionStatus(projectId);

    const [data, setData] = useState([]);
    const [selectedNodeId, setSelectedNodeId] = useState(null);

    // Update data when productionData changes
    useEffect(() => {
        if (productionData.length > 0) {
            setData(productionData);
        }
    }, [productionData]);

    // Auto-select node: prefer autoExpandNodeId (deep linking), then first node
    useEffect(() => {
        if (data.length > 0 && !selectedNodeId) {
            if (autoExpandNodeId) {
                const target = data.find(d => d.id === autoExpandNodeId);
                if (target) { setSelectedNodeId(target.id); return; }
            }
            const firstL1 = data.find(d => (d.level || 1) === 1);
            if (firstL1) setSelectedNodeId(firstL1.id);
        }
    }, [data, selectedNodeId, autoExpandNodeId]);

    // Reset selection when project changes
    useEffect(() => {
        setSelectedNodeId(null);
    }, [projectId]);

    const cycleTheme = useCallback(() => {
        const idx = THEMES.indexOf(theme);
        onThemeChange(THEMES[(idx + 1) % THEMES.length]);
    }, [theme, onThemeChange]);

    // Production callbacks used by ContentPanel
    const handleStartProduction = useCallback(async (docTypeId) => {
        console.log('Starting production for:', docTypeId);

        // Optimistic update: immediately show as in_production
        setData(prev => prev.map(item => {
            if (item.id === docTypeId) {
                return {
                    ...item,
                    _prevState: item.state,
                    state: 'in_production',
                };
            }
            return item;
        }));

        try {
            await startProduction(docTypeId);
        } catch (err) {
            // Revert optimistic update
            setData(prev => prev.map(item =>
                item.id === docTypeId
                    ? { ...item, state: item._prevState || 'ready_for_production', stations: null }
                    : item
            ));
        }
    }, [startProduction]);

    const handleSubmitQuestions = useCallback(async (id, answers) => {
        console.log('Submitted:', id, answers);

        // Optimistically update local state - mark PGC complete, ASM active
        setData(prev => {
            const update = (items) => items.map(item => {
                if (item.id === id && item.stations) {
                    return {
                        ...item,
                        state: 'in_production',
                        stations: item.stations.map(s =>
                            s.id === 'pgc' ? { ...s, state: 'complete', needs_input: false } :
                                s.id === 'asm' ? { ...s, state: 'active' } : s
                        )
                    };
                }
                if (item.children) return { ...item, children: update(item.children) };
                return item;
            });
            return update(prev);
        });

        // Find the document to get its interruptId and submit
        const doc = data.find(d => d.id === id);
        if (doc?.interruptId) {
            try {
                await resolveInterrupt(doc.interruptId, answers);
            } catch (err) {
                console.error('Failed to submit answers:', err);
            }
        }
    }, [data, resolveInterrupt]);

    // Auto-import flag for Work Binder (set when navigating from "Produce Next")
    const [autoImport, setAutoImport] = useState(false);

    // Navigate to a step and immediately start production (or import for Work Binder)
    const handleProduceNext = useCallback(async (docTypeId) => {
        setSelectedNodeId(docTypeId);
        if (docTypeId === 'work_package') {
            // Work Binder: navigate + trigger auto-import (no startProduction)
            setAutoImport(true);
        } else {
            // Document: navigate + start production
            setTimeout(() => handleStartProduction(docTypeId), 100);
        }
    }, [handleStartProduction]);

    // Find the selected step data for ContentPanel
    const selectedStep = useMemo(() => {
        if (!selectedNodeId) return null;
        const l1 = data.find(d => d.id === selectedNodeId && (d.level || 1) === 1);
        if (l1) return l1;
        for (const item of data) {
            const child = item.children?.find(c => c.id === selectedNodeId);
            if (child) return child;
        }
        return null;
    }, [data, selectedNodeId]);

    if (loading && data.length === 0) {
        return (
            <div className="flex items-center justify-center h-full" style={{ background: 'var(--bg-canvas)' }}>
                <div className="text-center">
                    <img
                        src="/logo-light.png"
                        alt="The Combine"
                        className="h-12 mx-auto mb-4 animate-pulse"
                    />
                    <p style={{ color: 'var(--text-muted)' }}>Loading production line...</p>
                </div>
            </div>
        );
    }

    if (error && data.length === 0) {
        return (
            <div className="flex items-center justify-center h-full" style={{ background: 'var(--bg-canvas)' }}>
                <div className="text-center p-6 rounded-lg" style={{ background: 'var(--bg-panel)' }}>
                    <p className="text-red-500 mb-4">{error}</p>
                </div>
            </div>
        );
    }

    return (
        <div className="w-full h-full flex flex-col">
            {/* Production Line — always horizontal, always visible */}
            <PipelineBreadcrumb
                data={data}
                selectedNodeId={selectedNodeId}
                onSelectNode={setSelectedNodeId}
                projectId={projectId}
                projectCode={projectCode}
                projectName={projectName}
                isArchived={isArchived}
                lineState={lineState}
                theme={theme}
                onCycleTheme={cycleTheme}
                onProjectUpdate={onProjectUpdate}
                onProjectArchive={onProjectArchive}
                onProjectUnarchive={onProjectUnarchive}
                onProjectDelete={onProjectDelete}
            />

            {/* Station Workspace — full width below the line */}
            <div className="flex-1 overflow-hidden">
                <ContentPanel
                    step={selectedStep}
                    projectId={projectId}
                    projectCode={projectCode}
                    onStartProduction={handleStartProduction}
                    onSubmitQuestions={handleSubmitQuestions}
                    pipelineData={data}
                    onProduceNext={handleProduceNext}
                    autoImport={autoImport}
                />
            </div>

            {/* Notification Toast */}
            {notification && (
                <div
                    className="fixed top-6 left-1/2 -translate-x-1/2 z-50 flex items-center gap-3 px-5 py-3 rounded-lg shadow-lg border"
                    style={{
                        background: notification.type === 'error' ? '#fef2f2' : '#f0fdf4',
                        borderColor: notification.type === 'error' ? '#fecaca' : '#bbf7d0',
                        maxWidth: 500,
                        animation: 'fadeIn 0.2s ease-out',
                    }}
                >
                    <span style={{
                        fontSize: 18,
                        color: notification.type === 'error' ? '#dc2626' : '#16a34a',
                        flexShrink: 0,
                    }}>
                        {notification.type === 'error' ? '\u26A0' : '\u2714'}
                    </span>
                    <span style={{ fontSize: 13, color: '#1f2937', lineHeight: 1.4 }}>
                        {notification.message}
                    </span>
                    <button
                        onClick={dismissNotification}
                        style={{
                            marginLeft: 'auto',
                            background: 'none',
                            border: 'none',
                            color: '#9ca3af',
                            fontSize: 18,
                            cursor: 'pointer',
                            padding: '0 2px',
                            lineHeight: 1,
                            flexShrink: 0,
                        }}
                    >
                        &times;
                    </button>
                </div>
            )}

        </div>
    );
}
