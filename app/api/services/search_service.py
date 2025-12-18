"""
Search service for web UI - Document-centric version.
Handles full-text search across projects and documents.
"""

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Set
from dataclasses import dataclass

from app.api.models import Project, Document


@dataclass
class SearchResults:
    """Container for search results across all entity types"""
    projects: List[Dict[str, Any]]
    epics: List[Dict[str, Any]]
    stories: List[Dict[str, Any]]
    documents: List[Dict[str, Any]]  # Generic documents
    
    def get_tree_paths(self) -> List[str]:
        """
        Generate tree paths for highlighting matched nodes
        Returns list of data-node-id values to highlight
        """
        paths: Set[str] = set()
        
        # Add project paths
        for project in self.projects:
            paths.add(f"project-{project['project_uuid']}")
        
        # Add epic paths (include parent project)
        for epic in self.epics:
            paths.add(f"project-{epic['project_uuid']}")
            paths.add(f"epic-{epic['epic_uuid']}")
        
        # Add story paths (include parent epic and project)
        for story in self.stories:
            paths.add(f"project-{story['project_uuid']}")
            if story.get('epic_uuid'):
                paths.add(f"epic-{story['epic_uuid']}")
            paths.add(f"story-{story['story_uuid']}")
        
        # Add generic document paths
        for doc in self.documents:
            paths.add(f"project-{doc['project_uuid']}")
            paths.add(f"document-{doc['document_uuid']}")
        
        return list(paths)


class SearchService:
    """Service for search operations using Document model."""
    
    async def search_all(
        self,
        db: AsyncSession,
        query: str,
        limit: int = 10
    ) -> SearchResults:
        """
        Search across all entities (projects, documents)
        Returns structured results with parent relationships
        """
        search_term = f"%{query}%"
        
        # Search projects
        projects = await self._search_projects(db, search_term, limit)
        
        # Search epics (documents with doc_type_id='epic')
        epics = await self._search_documents_by_type(db, search_term, 'epic', limit)
        
        # Search stories (documents with doc_type_id='story')
        stories = await self._search_documents_by_type(db, search_term, 'story', limit)
        
        # Search all other documents
        documents = await self._search_documents(db, search_term, limit)
        
        return SearchResults(
            projects=projects,
            epics=epics,
            stories=stories,
            documents=documents
        )
    
    async def _search_projects(
        self,
        db: AsyncSession,
        search_term: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Search projects by name or description"""
        query = (
            select(Project)
            .where(
                or_(
                    Project.name.ilike(search_term),
                    Project.description.ilike(search_term)
                )
            )
            .order_by(Project.updated_at.desc())
            .limit(limit)
        )
        
        result = await db.execute(query)
        projects = result.scalars().all()
        
        return [
            {
                "project_uuid": str(project.id),
                "name": project.name or "Untitled Project",
                "description": project.description or "",
                "status": project.status or "active"
            }
            for project in projects
        ]
    
    async def _search_documents_by_type(
        self,
        db: AsyncSession,
        search_term: str,
        doc_type: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Search documents of a specific type."""
        query = (
            select(Document)
            .where(Document.doc_type_id == doc_type)
            .where(Document.is_latest == True)
            .where(
                or_(
                    Document.title.ilike(search_term),
                    Document.summary.ilike(search_term)
                )
            )
            .order_by(Document.updated_at.desc())
            .limit(limit)
        )
        
        result = await db.execute(query)
        docs = result.scalars().all()
        
        # Get project names
        doc_results = []
        for doc in docs:
            project = await db.get(Project, doc.space_id) if doc.space_type == 'project' else None
            
            if doc_type == 'epic':
                doc_results.append({
                    "epic_uuid": str(doc.id),
                    "name": doc.title,
                    "description": doc.summary or "",
                    "status": doc.status,
                    "project_uuid": str(doc.space_id),
                    "project_name": project.name if project else "Unknown Project"
                })
            elif doc_type == 'story':
                doc_results.append({
                    "story_uuid": str(doc.id),
                    "title": doc.title,
                    "description": doc.summary or "",
                    "status": doc.status,
                    "epic_uuid": None,  # Would need to query relations to get this
                    "epic_name": "Unknown Epic",
                    "project_uuid": str(doc.space_id),
                    "project_name": project.name if project else "Unknown Project"
                })
        
        return doc_results
    
    async def _search_documents(
        self,
        db: AsyncSession,
        search_term: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Search all documents (excluding epics and stories which have their own handlers)."""
        query = (
            select(Document)
            .where(Document.is_latest == True)
            .where(Document.doc_type_id.notin_(['epic', 'story']))
            .where(
                or_(
                    Document.title.ilike(search_term),
                    Document.summary.ilike(search_term)
                )
            )
            .order_by(Document.updated_at.desc())
            .limit(limit)
        )
        
        result = await db.execute(query)
        docs = result.scalars().all()
        
        doc_results = []
        for doc in docs:
            project = await db.get(Project, doc.space_id) if doc.space_type == 'project' else None
            
            doc_results.append({
                "document_uuid": str(doc.id),
                "doc_type_id": doc.doc_type_id,
                "title": doc.title,
                "description": doc.summary or "",
                "status": doc.status,
                "is_stale": doc.is_stale,
                "project_uuid": str(doc.space_id) if doc.space_type == 'project' else None,
                "project_name": project.name if project else None,
                "space_type": doc.space_type
            })
        
        return doc_results


# Singleton instance
search_service = SearchService()