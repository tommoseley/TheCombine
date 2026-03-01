/**
 * WorkBinder — Work Package management screen with vertical WP Index and per-WP sub-views.
 *
 * Layout: left panel (WP Index) + center (WP Content Area).
 * URL-addressable when the Work Binder node is selected in the Pipeline Rail.
 *
 * WS-WB-007: Dedicated screen replacing the flat WorkBinder.jsx.
 */
import { useState, useEffect, useCallback } from 'react';
import { api } from '../../api/client';
import WPIndex from './WPIndex';
import WPContentArea from './WPContentArea';
import './WorkBinder.css';

/**
 * Fetch work packages from backend.
 * Falls back gracefully when the endpoint is not yet available.
 */
async function fetchWorkPackages(projectId) {
    try {
        const res = await api.getWorkPackages
            ? await api.getWorkPackages(projectId)
            : await fetch(`/api/v1/work-binder/wp?project_id=${encodeURIComponent(projectId)}`).then(r => {
                if (!r.ok) throw new Error(`${r.status}`);
                return r.json();
            });
        return Array.isArray(res) ? res : (res?.items || []);
    } catch (e) {
        console.warn('WorkBinder: WP fetch failed, endpoint may not exist yet:', e.message);
        return [];
    }
}

export default function WorkBinder({ projectId, projectCode }) {
    const [wps, setWps] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [selectedWpId, setSelectedWpId] = useState(null);
    const [activeSubView, setActiveSubView] = useState('WORK');

    const refresh = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await fetchWorkPackages(projectId);
            setWps(data);
            // Auto-select first WP if none selected
            if (!selectedWpId && data.length > 0) {
                setSelectedWpId(data[0].id);
            }
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    }, [projectId, selectedWpId]);

    useEffect(() => { refresh(); }, [projectId]);

    const handleSelectWp = useCallback((wpId) => {
        setSelectedWpId(wpId);
        setActiveSubView('WORK');
    }, []);

    const handleInsertPackage = useCallback(async (title) => {
        try {
            const res = await fetch(`/api/v1/work-binder/wp`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ project_id: projectId, title }),
            });
            if (!res.ok) throw new Error(`Failed to create WP: ${res.status}`);
            const newWp = await res.json();
            await refresh();
            setSelectedWpId(newWp.id);
        } catch (e) {
            setError('Failed to insert package: ' + e.message);
        }
    }, [projectId, refresh]);

    const selectedWp = wps.find(wp => wp.id === selectedWpId) || null;

    if (loading) {
        return (
            <div className="wb-root">
                <div className="wb-loading">
                    <p style={{ fontSize: 14, color: 'var(--text-muted)' }}>Loading work binder...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="wb-root">
            {/* Header */}
            <div className="wb-header">
                <h2 className="wb-header-title">Work Binder</h2>
                <span className="wb-header-project">{projectCode || 'No Project'}</span>
            </div>

            {error && (
                <div className="wb-error-banner">
                    <p>{error}</p>
                    <button onClick={() => setError(null)} className="wb-error-dismiss">&times;</button>
                </div>
            )}

            <div className="wb-layout">
                {/* Left Panel: WP Index */}
                <WPIndex
                    wps={wps}
                    selectedWpId={selectedWpId}
                    onSelectWp={handleSelectWp}
                    onInsertPackage={handleInsertPackage}
                />

                {/* Center: WP Content Area */}
                <WPContentArea
                    wp={selectedWp}
                    projectId={projectId}
                    activeSubView={activeSubView}
                    onChangeSubView={setActiveSubView}
                    onRefresh={refresh}
                />
            </div>
        </div>
    );
}
