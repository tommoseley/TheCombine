/**
 * DocumentModal — ADR-071 modal document viewer.
 *
 * Opens a document in a modal overlay using the existing RenderModelViewer.
 * Preserves the user's navigation context — closing returns them to where
 * they were. Internal links replace modal content (no stacking).
 */

import { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client.js';
import RenderModelViewer from './RenderModelViewer.jsx';

export default function DocumentModal({ projectId, displayId, onClose }) {
  const [renderModel, setRenderModel] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currentDisplayId, setCurrentDisplayId] = useState(displayId);
  const [history, setHistory] = useState([]);

  const loadDocument = useCallback(async (refId) => {
    setLoading(true);
    setError(null);
    try {
      // First resolve the display_id to get doc_type_id
      const resolved = await api.resolveReferences(projectId, [refId]);
      const ref = resolved.resolved?.[refId];
      if (!ref) {
        setError(`Document "${refId}" not found`);
        setLoading(false);
        return;
      }

      // Fetch render model using doc_type_id
      const rm = await api.getDocumentRenderModel(projectId, ref.doc_type_id);
      setRenderModel(rm);
      setCurrentDisplayId(refId);
    } catch (err) {
      setError(err.message || 'Failed to load document');
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadDocument(displayId);
  }, [displayId, loadDocument]);

  // Navigate to a different document within the modal (no stacking)
  const navigateToRef = useCallback((refId) => {
    setHistory(prev => [...prev, currentDisplayId]);
    loadDocument(refId);
  }, [currentDisplayId, loadDocument]);

  const navigateBack = useCallback(() => {
    if (history.length > 0) {
      const prev = history[history.length - 1];
      setHistory(h => h.slice(0, -1));
      loadDocument(prev);
    }
  }, [history, loadDocument]);

  // Close on Escape
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed',
        top: 0, left: 0, right: 0, bottom: 0,
        background: 'rgba(0, 0, 0, 0.7)',
        zIndex: 1000,
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'flex-start',
        paddingTop: 40,
        overflow: 'auto',
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: '90%',
          maxWidth: 1000,
          maxHeight: 'calc(100vh - 80px)',
          background: 'var(--bg-surface, #1a1a2e)',
          border: '1px solid var(--border, #333)',
          borderRadius: 8,
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {/* Header */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '12px 16px',
          borderBottom: '1px solid var(--border, #333)',
          background: 'var(--bg-canvas, #0f0f23)',
          flexShrink: 0,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            {history.length > 0 && (
              <button
                onClick={navigateBack}
                style={{
                  background: 'transparent',
                  border: '1px solid var(--border, #444)',
                  borderRadius: 4,
                  color: 'var(--text-muted, #888)',
                  cursor: 'pointer',
                  padding: '2px 8px',
                  fontSize: 12,
                }}
                title="Go back"
              >
                &larr;
              </button>
            )}
            <span style={{
              fontSize: 11,
              fontWeight: 700,
              color: 'var(--accent-primary, #3b82f6)',
              letterSpacing: '0.05em',
            }}>
              {currentDisplayId}
            </span>
            {renderModel && (
              <span style={{
                fontSize: 14,
                fontWeight: 600,
                color: 'var(--text-primary, #eee)',
              }}>
                {renderModel.title}
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted, #888)',
              fontSize: 18,
              cursor: 'pointer',
              padding: '0 4px',
              lineHeight: 1,
            }}
            title="Close (Esc)"
          >
            &times;
          </button>
        </div>

        {/* Body */}
        <div style={{
          flex: 1,
          overflow: 'auto',
          padding: '16px 20px',
        }}>
          {loading && (
            <div style={{
              padding: 40,
              textAlign: 'center',
              color: 'var(--text-muted, #888)',
              fontSize: 13,
            }}>
              Loading {currentDisplayId}...
            </div>
          )}

          {error && (
            <div style={{
              padding: 20,
              color: '#e53935',
              fontSize: 13,
            }}>
              {error}
            </div>
          )}

          {!loading && !error && renderModel && (
            <RenderModelViewer
              renderModel={renderModel}
              variant="full"
              hideHeader={true}
            />
          )}

          {!loading && !error && !renderModel && (
            <div style={{
              padding: 40,
              textAlign: 'center',
              color: 'var(--text-muted, #888)',
              fontSize: 13,
            }}>
              No render model available for this document.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * Context for document link navigation within modals.
 * Components can use this to trigger modal navigation.
 */
export const DocumentModalContext = {
  _navigateFn: null,

  setNavigate(fn) {
    this._navigateFn = fn;
  },

  navigate(displayId) {
    if (this._navigateFn) {
      this._navigateFn(displayId);
    }
  },

  clear() {
    this._navigateFn = null;
  },
};
