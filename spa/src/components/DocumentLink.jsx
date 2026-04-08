/**
 * DocumentLink — clickable document reference (ADR-071).
 *
 * Renders a display_id as a styled, clickable element that opens
 * a DocumentModal. Shows resolved title on hover if available.
 */

import { useState, useCallback } from 'react';
import DocumentModal from './DocumentModal.jsx';

export default function DocumentLink({ displayId, title, projectId }) {
  const [showModal, setShowModal] = useState(false);

  const handleClick = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setShowModal(true);
  }, []);

  return (
    <>
      <span
        onClick={handleClick}
        title={title ? `${displayId}: ${title}` : displayId}
        style={{
          color: 'var(--accent-primary, #3b82f6)',
          cursor: 'pointer',
          fontWeight: 500,
          borderBottom: '1px dotted rgba(59, 130, 246, 0.4)',
        }}
      >
        {displayId}
      </span>
      {showModal && (
        <DocumentModal
          projectId={projectId}
          displayId={displayId}
          onClose={() => setShowModal(false)}
        />
      )}
    </>
  );
}
