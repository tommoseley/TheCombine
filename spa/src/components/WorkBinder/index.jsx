/**
 * WorkBinder — Work Package management screen with vertical WP Index and per-WP sub-views.
 *
 * Layout: left panel (WP Index) + center (WP Content Area).
 * URL-addressable when the Work Binder node is selected in the Pipeline Rail.
 *
 * WS-WB-007: Dedicated screen replacing the flat WorkBinder.jsx.
 * WS-WB-009: Candidate listing, import, and promotion.
 * WS-WB-030: Studio layout — WS state lifted to orchestrator.
 */
import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { api } from '../../api/client';
import {
    fetchWorkStatements, createWorkStatement,
    stabilizeWorkStatement, reorderWorkStatements,
    formatWsForClipboard,
} from './wsUtils';
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

/**
 * Fetch candidates from backend (read-only, no side effects).
 */
async function fetchCandidates(projectId) {
    try {
        const res = await api.getCandidates(projectId);
        return res || { candidates: [], count: 0, import_available: false, source_ip_id: null };
    } catch (e) {
        console.warn('WorkBinder: candidate fetch failed:', e.message);
        return { candidates: [], count: 0, import_available: false, source_ip_id: null };
    }
}

export default function WorkBinder({ projectId, projectCode }) {
    const { displayId: urlDisplayId } = useParams();
    const navigate = useNavigate();
    const location = useLocation();
    const [wps, setWps] = useState([]);
    const [candidates, setCandidates] = useState([]);
    const [importAvailable, setImportAvailable] = useState(false);
    const [sourceIpId, setSourceIpId] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [selectedWpId, setSelectedWpId] = useState(null);
    const [selectedCandidateId, setSelectedCandidateId] = useState(null);
    const [activeSubView, setActiveSubView] = useState('WORK');
    const [wpDetail, setWpDetail] = useState(null);
    const [initialResolved, setInitialResolved] = useState(!urlDisplayId);

    // WS-WB-030: Lifted WS state
    const [selectedWsId, setSelectedWsId] = useState(null);
    const [statements, setStatements] = useState([]);
    const [statementsLoading, setStatementsLoading] = useState(false);

    const refresh = useCallback(async () => {
        setLoading(true);
        setError(null);
        setWpDetail(null);
        try {
            const [wpData, candData] = await Promise.all([
                fetchWorkPackages(projectId),
                fetchCandidates(projectId),
            ]);
            setWps(wpData);
            setCandidates(candData.candidates || []);
            setImportAvailable(candData.import_available || false);
            setSourceIpId(candData.source_ip_id || null);
            // Auto-select first WP if none selected and no candidate selected
            if (!selectedWpId && !selectedCandidateId && wpData.length > 0) {
                setSelectedWpId(wpData[0].id);
            }
            return wpData;
        } catch (e) {
            setError(e.message);
            return null;
        } finally {
            setLoading(false);
        }
    }, [projectId, selectedWpId, selectedCandidateId]);

    useEffect(() => { refresh(); }, [projectId]);

    // ADR-056: Resolve URL display_id to initial selection after data loads
    useEffect(() => {
        if (initialResolved || loading || !urlDisplayId) return;
        if (wps.length === 0 && candidates.length === 0) return;

        const prefix = urlDisplayId.split('-')[0];
        if (prefix === 'WP') {
            // Direct WP selection
            const wp = wps.find(w => w.display_id === urlDisplayId || w.wp_id === urlDisplayId);
            if (wp) {
                setSelectedWpId(wp.id);
                setSelectedCandidateId(null);
                setActiveSubView('WORK');
            }
        } else if (prefix === 'WS') {
            // WS: find parent WP via API, then select parent and the WS
            api.getDocumentByDisplayId(projectCode, urlDisplayId)
                .then(doc => {
                    if (doc?.content?.parent_wp_id) {
                        const parentWp = wps.find(w => w.wp_id === doc.content.parent_wp_id);
                        if (parentWp) {
                            setSelectedWpId(parentWp.id);
                            setSelectedCandidateId(null);
                            setActiveSubView('WORK');
                            // Also select the specific WS
                            setSelectedWsId(doc.content.ws_id || urlDisplayId);
                        }
                    }
                })
                .catch(() => {});
        } else if (prefix === 'WPC') {
            // Direct candidate selection
            const cand = candidates.find(c => c.wpc_id === urlDisplayId || c.display_id === urlDisplayId);
            if (cand) {
                setSelectedCandidateId(cand.wpc_id);
                setSelectedWpId(null);
            }
        }
        setInitialResolved(true);
    }, [loading, wps, candidates, urlDisplayId, initialResolved, projectCode]);

    // ADR-056: Update URL when WP/WS/WPC selection changes
    const updateUrlForSelection = useCallback((displayId) => {
        if (!projectCode) return;
        const basePath = `/projects/${projectCode}/work-binder`;
        const targetPath = displayId ? `${basePath}/${displayId}` : basePath;
        if (location.pathname !== targetPath) {
            navigate(targetPath, { replace: true });
        }
    }, [projectCode, navigate, location.pathname]);

    const handleSelectWp = useCallback((wpId) => {
        setSelectedWpId(wpId);
        setSelectedCandidateId(null);
        setSelectedWsId(null); // Clear WS selection on WP change
        setActiveSubView('WORK');
        const wp = wps.find(w => w.id === wpId);
        if (wp) updateUrlForSelection(wp.display_id || wp.wp_id);
    }, [wps, updateUrlForSelection]);

    const handleSelectCandidate = useCallback((wpcId) => {
        setSelectedCandidateId(wpcId);
        setSelectedWpId(null);
        setSelectedWsId(null);
        const cand = candidates.find(c => c.wpc_id === wpcId);
        if (cand) updateUrlForSelection(cand.display_id || cand.wpc_id);
    }, [candidates, updateUrlForSelection]);

    // WS-WB-030: WS selection handler
    const handleSelectWs = useCallback((wsId) => {
        if (!wsId) {
            setSelectedWsId(null);
            // Revert URL to WP display_id
            const wp = wps.find(w => w.id === selectedWpId);
            if (wp) updateUrlForSelection(wp.display_id || wp.wp_id);
            return;
        }
        setSelectedWsId(wsId);
        const ws = statements.find(s => s.ws_id === wsId);
        if (ws) updateUrlForSelection(ws.ws_id);
    }, [statements, wps, selectedWpId, updateUrlForSelection]);

    const handleImportCandidates = useCallback(async () => {
        if (!sourceIpId) return;
        try {
            await api.importCandidates(sourceIpId);
            await refresh();
        } catch (e) {
            setError('Failed to import candidates: ' + e.message);
        }
    }, [sourceIpId, refresh]);

    const handlePromote = useCallback(async (wpcId) => {
        try {
            const result = await api.promoteCandidate(wpcId, projectId, 'kept', 'Promoted as-is from IP candidate.');
            const freshWps = await refresh();
            // Auto-navigate to the newly promoted WP's WORK tab
            if (result?.wp_id && freshWps) {
                const promotedWp = freshWps.find(wp => wp.wp_id === result.wp_id);
                if (promotedWp) {
                    setSelectedWpId(promotedWp.id);
                    setSelectedCandidateId(null);
                    setActiveSubView('WORK');
                }
            }
        } catch (e) {
            setError('Failed to promote candidate: ' + e.message);
        }
    }, [refresh]);

    const handleViewCandidate = useCallback((wpcId) => {
        const cand = candidates.find(c => c.wpc_id === wpcId);
        if (cand) {
            setSelectedCandidateId(wpcId);
            setSelectedWpId(null);
            setSelectedWsId(null);
        }
    }, [candidates]);

    const handleProposeStatements = useCallback(async (wpId) => {
        try {
            await api.proposeWorkStatements(projectId, wpId);
            await refresh();
        } catch (e) {
            setError(e.message || 'Failed to propose work statements');
        }
    }, [projectId, refresh]);

    // WS-WB-030: Lifted WS action callbacks
    const loadStatements = useCallback(async (wpContentId) => {
        setStatementsLoading(true);
        const data = await fetchWorkStatements(projectId, wpContentId);
        setStatements(data);
        setStatementsLoading(false);
        return data;
    }, [projectId]);

    const handleCreateWs = useCallback(async (intent) => {
        const wp = wps.find(w => w.id === selectedWpId);
        const wpContentId = wp?.wp_id;
        if (!wpContentId) return;
        try {
            await createWorkStatement(wpContentId, intent);
            await loadStatements(wpContentId);
        } catch (e) {
            setError('Create failed: ' + e.message);
        }
    }, [wps, selectedWpId, loadStatements]);

    const handleStabilize = useCallback(async (wsId) => {
        const wp = wps.find(w => w.id === selectedWpId);
        const wpContentId = wp?.wp_id;
        if (!wpContentId) return;
        try {
            await stabilizeWorkStatement(wsId);
            await loadStatements(wpContentId);
        } catch (e) {
            setError('Stabilize failed: ' + e.message);
        }
    }, [wps, selectedWpId, loadStatements]);

    const handleMoveWs = useCallback(async (wsId, direction) => {
        const idx = statements.findIndex(ws => ws.ws_id === wsId);
        if (idx < 0) return;
        const newIdx = direction === 'up' ? idx - 1 : idx + 1;
        if (newIdx < 0 || newIdx >= statements.length) return;
        const wp = wps.find(w => w.id === selectedWpId);
        const wpContentId = wp?.wp_id;
        if (!wpContentId) return;
        // Optimistic swap
        const newOrder = [...statements];
        [newOrder[idx], newOrder[newIdx]] = [newOrder[newIdx], newOrder[idx]];
        setStatements(newOrder);
        try {
            await reorderWorkStatements(
                wpContentId,
                newOrder.map(ws => ({ ws_id: ws.ws_id, order_key: ws.order_key || '' })),
            );
        } catch (e) {
            await loadStatements(wpContentId);
            setError('Reorder failed: ' + e.message);
        }
    }, [statements, wps, selectedWpId, loadStatements]);

    const handleCopyWs = useCallback((ws) => {
        const text = formatWsForClipboard(ws);
        navigator.clipboard.writeText(text).catch(() => {
            console.warn('WorkBinder: clipboard write failed');
        });
    }, []);

    const selectedWp = wps.find(wp => wp.id === selectedWpId) || null;
    const selectedCandidate = candidates.find(c => c.wpc_id === selectedCandidateId) || null;

    // Fetch full WP content + WS list when a WP is selected
    useEffect(() => {
        if (!selectedWpId) {
            setWpDetail(null);
            setStatements([]);
            return;
        }
        const wp = wps.find(w => w.id === selectedWpId);
        const contentWpId = wp?.wp_id;
        if (!contentWpId) {
            setWpDetail(null);
            setStatements([]);
            return;
        }
        let cancelled = false;
        setStatementsLoading(true);
        Promise.all([
            api.getWorkPackageDetail(contentWpId),
            fetchWorkStatements(projectId, contentWpId),
        ]).then(([detail, wsList]) => {
            if (!cancelled) {
                setWpDetail(detail);
                setStatements(wsList);
                setStatementsLoading(false);
            }
        }).catch(e => {
            console.warn('WP/WS fetch failed:', e.message);
            if (!cancelled) {
                setWpDetail(null);
                setStatements([]);
                setStatementsLoading(false);
            }
        });
        return () => { cancelled = true; };
    }, [selectedWpId, wps, projectId]);

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
                {/* Left Panel: WP Index + nested WS rows */}
                <WPIndex
                    wps={wps}
                    selectedWpId={selectedWpId}
                    onSelectWp={handleSelectWp}
                    candidates={candidates}
                    selectedCandidateId={selectedCandidateId}
                    onSelectCandidate={handleSelectCandidate}
                    importAvailable={importAvailable}
                    onImportCandidates={handleImportCandidates}
                    statements={statements}
                    selectedWsId={selectedWsId}
                    onSelectWs={handleSelectWs}
                    statementsLoading={statementsLoading}
                />

                {/* Center: WP Content Area or Candidate Detail */}
                <WPContentArea
                    wp={wpDetail || selectedWp}
                    candidate={selectedCandidate}
                    projectId={projectId}
                    activeSubView={activeSubView}
                    onChangeSubView={setActiveSubView}
                    onRefresh={refresh}
                    onPromote={handlePromote}
                    onProposeStatements={handleProposeStatements}
                    onViewCandidate={handleViewCandidate}
                    statements={statements}
                    selectedWsId={selectedWsId}
                    onSelectWs={handleSelectWs}
                    onCreateWs={handleCreateWs}
                    onStabilize={handleStabilize}
                    onMoveUp={(wsId) => handleMoveWs(wsId, 'up')}
                    onMoveDown={(wsId) => handleMoveWs(wsId, 'down')}
                    onCopyWs={handleCopyWs}
                />
            </div>
        </div>
    );
}
