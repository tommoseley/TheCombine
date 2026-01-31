import { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { transformProjectsList } from '../api/transformers';

/**
 * Hook for managing projects list
 * Fetches from real API
 *
 * @param {Object} options
 * @param {boolean} options.includeArchived - Whether to include archived projects
 */
export function useProjects({ includeArchived = false } = {}) {
    const [projects, setProjects] = useState({});
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // Fetch projects from API
    const fetchProjects = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await api.getProjects({ includeArchived });
            const transformed = transformProjectsList(response);
            setProjects(transformed);
        } catch (err) {
            setError(err.message);
            console.error('Failed to fetch projects:', err);
        } finally {
            setLoading(false);
        }
    }, [includeArchived]);

    // Create new project
    const addProject = useCallback(async (name) => {
        try {
            const newProject = await api.createProject({ name, description: '' });
            setProjects(prev => ({
                ...prev,
                [newProject.id]: {
                    id: newProject.id,
                    projectId: newProject.project_id,
                    name: newProject.name,
                    description: newProject.description || '',
                    status: 'active',
                    icon: newProject.icon,
                    createdAt: newProject.created_at,
                },
            }));
            return newProject;
        } catch (err) {
            setError(err.message);
            console.error('Failed to create project:', err);
            throw err;
        }
    }, []);

    useEffect(() => {
        fetchProjects();
    }, [fetchProjects]);

    return {
        projects,
        loading,
        error,
        addProject,
        refresh: fetchProjects,
    };
}
