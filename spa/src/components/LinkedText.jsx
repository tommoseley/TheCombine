/**
 * LinkedText — auto-links document references in text (ADR-071).
 *
 * Parses text for display_id patterns (e.g., WS-142, TA-001, PD-001)
 * and renders them as clickable DocumentLink components.
 *
 * Usage:
 *   <LinkedText text="See WS-142 for details" projectId={projectId} />
 */

import { useMemo } from 'react';
import DocumentLink from './DocumentLink.jsx';
import { useProjectId } from './ProjectContext.jsx';

// Match display_id patterns: 2-4 uppercase letters, hyphen, 3+ digits
// e.g., WS-142, TA-001, WPC-001, PD-001, SD-A1B2C3D4
const DISPLAY_ID_REGEX = /\b([A-Z]{2,4}-\d{3,})\b/g;

export default function LinkedText({ text, projectId: propProjectId }) {
  const contextProjectId = useProjectId();
  const projectId = propProjectId || contextProjectId;
  const parts = useMemo(() => {
    if (!text || !projectId) return [text];

    const result = [];
    let lastIndex = 0;

    for (const match of text.matchAll(DISPLAY_ID_REGEX)) {
      // Add text before the match
      if (match.index > lastIndex) {
        result.push(text.slice(lastIndex, match.index));
      }
      // Add the linked reference
      result.push({ displayId: match[1], index: match.index });
      lastIndex = match.index + match[0].length;
    }

    // Add remaining text
    if (lastIndex < text.length) {
      result.push(text.slice(lastIndex));
    }

    return result;
  }, [text, projectId]);

  if (!text) return null;

  // No matches — return plain text
  if (parts.length === 1 && typeof parts[0] === 'string') {
    return <>{text}</>;
  }

  return (
    <>
      {parts.map((part, i) => {
        if (typeof part === 'string') {
          return <span key={i}>{part}</span>;
        }
        return (
          <DocumentLink
            key={`${part.displayId}-${part.index}`}
            displayId={part.displayId}
            projectId={projectId}
          />
        );
      })}
    </>
  );
}
