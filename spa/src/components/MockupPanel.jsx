import { useState, useEffect, useRef, useCallback } from 'react';
import { api } from '../api/client';

const ALLOWED_TYPES = ['image/png', 'image/jpeg', 'application/pdf'];
const MAX_IMAGE_SIZE = 10 * 1024 * 1024;
const MAX_PDF_SIZE = 20 * 1024 * 1024;
const API_BASE = '/api/v1';

function formatSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function formatDate(dateStr) {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
}

/**
 * MockupPanel - displays uploaded mockups/artifacts for a project.
 *
 * Features:
 * - Thumbnail grid with label, date, size
 * - Lightbox overlay on click
 * - Delete with confirmation
 * - Upload button for adding new mockups
 */
export default function MockupPanel({ projectId }) {
    const [artifacts, setArtifacts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [uploading, setUploading] = useState(false);
    const [lightboxArtifact, setLightboxArtifact] = useState(null);
    const [confirmDeleteId, setConfirmDeleteId] = useState(null);
    const [collapsed, setCollapsed] = useState(false);
    const fileInputRef = useRef(null);

    const fetchArtifacts = useCallback(async () => {
        try {
            const data = await api.listArtifacts(projectId);
            setArtifacts(Array.isArray(data) ? data : data.artifacts || []);
            setError(null);
        } catch (err) {
            // 404 means no artifacts endpoint yet -- treat as empty
            if (err.status === 404) {
                setArtifacts([]);
            } else {
                setError(err.message || 'Failed to load mockups');
            }
        } finally {
            setLoading(false);
        }
    }, [projectId]);

    useEffect(() => {
        fetchArtifacts();
    }, [fetchArtifacts]);

    const handleFileSelect = async (e) => {
        const file = e.target.files?.[0];
        if (!file) return;

        if (!ALLOWED_TYPES.includes(file.type)) {
            setError('Only PNG, JPEG, and PDF files are accepted.');
            e.target.value = '';
            return;
        }

        const maxSize = file.type === 'application/pdf' ? MAX_PDF_SIZE : MAX_IMAGE_SIZE;
        if (file.size > maxSize) {
            const limitStr = file.type === 'application/pdf' ? '20MB' : '10MB';
            setError(`File too large. Max ${limitStr}.`);
            e.target.value = '';
            return;
        }

        setError(null);
        setUploading(true);
        try {
            const label = file.name.replace(/\.[^.]+$/, '');
            await api.uploadArtifact(projectId, file, label);
            await fetchArtifacts();
        } catch (err) {
            setError(err.message || 'Upload failed');
        } finally {
            setUploading(false);
            e.target.value = '';
        }
    };

    const handleDelete = async (artifactId) => {
        try {
            await api.deleteArtifact(projectId, artifactId);
            setArtifacts((prev) => prev.filter((a) => a.id !== artifactId));
            setConfirmDeleteId(null);
            if (lightboxArtifact?.id === artifactId) setLightboxArtifact(null);
        } catch (err) {
            setError(err.message || 'Delete failed');
        }
    };

    const thumbnailUrl = (artifact) =>
        `${API_BASE}/projects/${projectId}/artifacts/${artifact.id}/thumbnail`;

    const fullUrl = (artifact) =>
        `${API_BASE}/projects/${projectId}/artifacts/${artifact.id}`;

    return (
        <div
            className="rounded-lg border"
            style={{
                background: 'var(--bg-panel)',
                borderColor: 'var(--border-panel)',
            }}
        >
            {/* Header */}
            <button
                onClick={() => setCollapsed(!collapsed)}
                className="w-full flex items-center justify-between px-4 py-3 text-left"
                style={{ background: 'transparent', border: 'none', cursor: 'pointer' }}
            >
                <div className="flex items-center gap-2">
                    <svg
                        className="w-4 h-4"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        style={{ color: 'var(--text-muted)' }}
                    >
                        <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                        <circle cx="8.5" cy="8.5" r="1.5" />
                        <polyline points="21 15 16 10 5 21" />
                    </svg>
                    <span
                        className="text-xs font-semibold"
                        style={{ color: 'var(--text-primary)' }}
                    >
                        Mockups
                    </span>
                    {artifacts.length > 0 && (
                        <span
                            className="text-[10px] px-1.5 py-0.5 rounded-full"
                            style={{
                                background: 'var(--bg-canvas)',
                                color: 'var(--text-muted)',
                            }}
                        >
                            {artifacts.length}
                        </span>
                    )}
                </div>
                <svg
                    className="w-4 h-4 transition-transform"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    style={{
                        color: 'var(--text-muted)',
                        transform: collapsed ? 'rotate(-90deg)' : 'rotate(0deg)',
                    }}
                >
                    <polyline points="6 9 12 15 18 9" />
                </svg>
            </button>

            {!collapsed && (
                <div className="px-4 pb-4">
                    {/* Error */}
                    {error && (
                        <p className="text-[11px] text-red-400 mb-2">{error}</p>
                    )}

                    {/* Loading */}
                    {loading && (
                        <div className="flex items-center justify-center py-8">
                            <div className="w-6 h-6 border-2 border-t-violet-500 border-r-transparent border-b-transparent border-l-transparent rounded-full animate-spin" />
                        </div>
                    )}

                    {/* Empty state */}
                    {!loading && artifacts.length === 0 && (
                        <div className="text-center py-6">
                            <svg
                                className="w-8 h-8 mx-auto mb-2"
                                viewBox="0 0 24 24"
                                fill="none"
                                stroke="currentColor"
                                strokeWidth="1.5"
                                style={{ color: 'var(--text-muted)', opacity: 0.5 }}
                            >
                                <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                                <circle cx="8.5" cy="8.5" r="1.5" />
                                <polyline points="21 15 16 10 5 21" />
                            </svg>
                            <p
                                className="text-xs"
                                style={{ color: 'var(--text-muted)' }}
                            >
                                No mockups uploaded
                            </p>
                        </div>
                    )}

                    {/* Thumbnail grid */}
                    {!loading && artifacts.length > 0 && (
                        <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))' }}>
                            {artifacts.map((artifact) => (
                                <div
                                    key={artifact.id}
                                    className="rounded-lg border overflow-hidden group"
                                    style={{
                                        background: 'var(--bg-canvas)',
                                        borderColor: 'var(--border-panel)',
                                    }}
                                >
                                    {/* Thumbnail */}
                                    <div
                                        className="relative cursor-pointer"
                                        style={{ paddingTop: '75%' }}
                                        onClick={() => setLightboxArtifact(artifact)}
                                    >
                                        <img
                                            src={thumbnailUrl(artifact)}
                                            alt={artifact.label || 'Mockup'}
                                            className="absolute inset-0 w-full h-full object-cover"
                                            onError={(e) => {
                                                e.target.style.display = 'none';
                                            }}
                                        />
                                    </div>

                                    {/* Info */}
                                    <div className="px-2 py-1.5">
                                        <p
                                            className="text-[11px] font-medium truncate"
                                            style={{ color: 'var(--text-primary)' }}
                                            title={artifact.label}
                                        >
                                            {artifact.label || 'Untitled'}
                                        </p>
                                        <div className="flex items-center justify-between mt-0.5">
                                            <span
                                                className="text-[10px]"
                                                style={{ color: 'var(--text-muted)' }}
                                            >
                                                {artifact.file_size_bytes ? formatSize(artifact.file_size_bytes) : ''}
                                                {artifact.file_size_bytes && artifact.created_at ? ' \u00B7 ' : ''}
                                                {formatDate(artifact.created_at)}
                                            </span>

                                            {/* Delete */}
                                            {confirmDeleteId === artifact.id ? (
                                                <div className="flex gap-1">
                                                    <button
                                                        onClick={() => handleDelete(artifact.id)}
                                                        className="text-[10px] px-1.5 py-0.5 rounded font-medium"
                                                        style={{ background: '#ef4444', color: 'white' }}
                                                    >
                                                        Yes
                                                    </button>
                                                    <button
                                                        onClick={() => setConfirmDeleteId(null)}
                                                        className="text-[10px] px-1.5 py-0.5 rounded"
                                                        style={{ color: 'var(--text-muted)' }}
                                                    >
                                                        No
                                                    </button>
                                                </div>
                                            ) : (
                                                <button
                                                    onClick={() => setConfirmDeleteId(artifact.id)}
                                                    className="opacity-0 group-hover:opacity-100 p-0.5 rounded hover:bg-white/10 transition-all"
                                                    style={{ color: 'var(--text-muted)' }}
                                                    title="Delete mockup"
                                                >
                                                    <svg
                                                        className="w-3 h-3"
                                                        viewBox="0 0 24 24"
                                                        fill="none"
                                                        stroke="currentColor"
                                                        strokeWidth="2"
                                                    >
                                                        <polyline points="3 6 5 6 21 6" />
                                                        <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" />
                                                    </svg>
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Upload button */}
                    <div className="mt-3">
                        <input
                            ref={fileInputRef}
                            type="file"
                            accept="image/png,image/jpeg,application/pdf"
                            onChange={handleFileSelect}
                            className="hidden"
                        />
                        <button
                            onClick={() => fileInputRef.current?.click()}
                            disabled={uploading}
                            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors hover:bg-white/10"
                            style={{
                                color: 'var(--text-secondary)',
                                border: '1px dashed var(--border-panel)',
                                opacity: uploading ? 0.5 : 1,
                            }}
                        >
                            {uploading ? (
                                <div className="w-3 h-3 border border-t-violet-500 border-r-transparent border-b-transparent border-l-transparent rounded-full animate-spin" />
                            ) : (
                                <svg
                                    className="w-3 h-3"
                                    viewBox="0 0 24 24"
                                    fill="none"
                                    stroke="currentColor"
                                    strokeWidth="2"
                                >
                                    <line x1="12" y1="5" x2="12" y2="19" />
                                    <line x1="5" y1="12" x2="19" y2="12" />
                                </svg>
                            )}
                            {uploading ? 'Uploading...' : 'Add mockup'}
                        </button>
                    </div>
                </div>
            )}

            {/* Lightbox overlay */}
            {lightboxArtifact && (
                <div
                    className="fixed inset-0 z-[100] flex items-center justify-center"
                    style={{ background: 'rgba(0, 0, 0, 0.85)' }}
                    onClick={() => setLightboxArtifact(null)}
                >
                    <div
                        className="relative max-w-[90vw] max-h-[90vh]"
                        onClick={(e) => e.stopPropagation()}
                    >
                        <img
                            src={fullUrl(lightboxArtifact)}
                            alt={lightboxArtifact.label || 'Mockup'}
                            className="max-w-full max-h-[85vh] object-contain rounded-lg"
                        />
                        <div className="flex items-center justify-between mt-3">
                            <span
                                className="text-sm font-medium"
                                style={{ color: 'var(--text-primary)' }}
                            >
                                {lightboxArtifact.label}
                            </span>
                            <button
                                onClick={() => setLightboxArtifact(null)}
                                className="px-3 py-1.5 rounded-lg text-xs font-medium hover:bg-white/10 transition-colors"
                                style={{ color: 'var(--text-muted)' }}
                            >
                                Close
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
