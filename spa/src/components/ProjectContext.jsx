/**
 * ProjectContext — provides projectId to deeply nested components (ADR-071).
 *
 * Used by LinkedText/DocumentLink to know which project to resolve
 * document references against, without threading projectId through
 * every component in the render tree.
 */

import { createContext, useContext } from 'react';

const ProjectContext = createContext(null);

export function ProjectProvider({ projectId, children }) {
  return (
    <ProjectContext.Provider value={projectId}>
      {children}
    </ProjectContext.Provider>
  );
}

export function useProjectId() {
  return useContext(ProjectContext);
}
