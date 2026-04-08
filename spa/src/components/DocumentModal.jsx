/**
 * DocumentModal — ADR-071 modal document viewer.
 *
 * Opens a document in a modal overlay using the existing FullDocumentViewer,
 * which handles all rendering paths (IA config, render model, raw fallback).
 * Preserves the user's navigation context — closing returns them to where
 * they were.
 */

import { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client.js';
import FullDocumentViewer from './FullDocumentViewer.jsx';

export default function DocumentModal({ projectId, displayId, onClose }) {
  const [docTypeId, setDocTypeId] = useState(null);
  const [instanceId, setInstanceId] = useState(null);
  const [docTitle, setDocTitle] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currentDisplayId, setCurrentDisplayId] = useState(displayId);

  const resolveDoc = useCallback(async (refId) => {
    setLoading(true);
    setError(null);
    setDocTypeId(null);
    setDocTitle(null);
    try {
      const resolved = await api.resolveReferences(projectId, [refId]);
      const ref = resolved.resolved?.[refId];
      if (!ref) {
        setError(`Document "${refId}" not found`);
        setLoading(false);
        return;
      }
      // Use doc_type_id for render model (IA config lookup needs the real type).
      // For multi-instance types, pass instance_id from the document's own
      // instance_id field to disambiguate — but we don't have that here.
      // FullDocumentViewer will find the right doc: for single-instance types
      // (TA, PD, IP) doc_type_id alone is unique; for multi-instance types
      // the render-model may return a generic view, but getDocument fallback
      // uses display_id which is always unique.
      setDocTypeId(ref.doc_type_id);
      setInstanceId(null);
      setDocTitle(ref.title);
      setCurrentDisplayId(refId);
    } catch (err) {
      setError(err.message || 'Failed to resolve document');
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    resolveDoc(displayId);
  }, [displayId, resolveDoc]);

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
          maxWidth: 1100,
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
          padding: '10px 16px',
          borderBottom: '1px solid var(--border, #333)',
          background: 'var(--bg-canvas, #0f0f23)',
          flexShrink: 0,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{
              fontSize: 11,
              fontWeight: 700,
              color: 'var(--accent-primary, #3b82f6)',
              letterSpacing: '0.05em',
            }}>
              {currentDisplayId}
            </span>
            {docTitle && (
              <span style={{
                fontSize: 14,
                fontWeight: 600,
                color: 'var(--text-primary, #eee)',
              }}>
                {docTitle}
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

          {!loading && !error && docTypeId && (
            <FullDocumentViewer
              projectId={projectId}
              projectCode=""
              docTypeId={docTypeId}
              instanceId={instanceId}
              onClose={onClose}
              inline
            />
          )}
        </div>
      </div>
    </div>
  );
}
