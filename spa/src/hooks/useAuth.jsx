import { useState, useEffect, useCallback, createContext, useContext } from 'react';
import { api, getLoginUrl } from '../api/client';

/**
 * Auth context for sharing auth state across components
 */
const AuthContext = createContext(null);

/**
 * Auth provider component
 */
export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // Check auth status on mount
    useEffect(() => {
        checkAuth();
    }, []);

    const checkAuth = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await api.getMe();
            if (response && response.user) {
                setUser(response.user);
            } else {
                setUser(null);
            }
        } catch (err) {
            console.error('Auth check failed:', err);
            setError(err.message);
            setUser(null);
        } finally {
            setLoading(false);
        }
    }, []);

    const login = useCallback((provider) => {
        // Redirect to OAuth login
        window.location.href = getLoginUrl(provider);
    }, []);

    const logout = useCallback(async () => {
        try {
            await api.logout();
            setUser(null);
            // Redirect to home or refresh
            window.location.href = '/';
        } catch (err) {
            console.error('Logout failed:', err);
            // Still clear local state even if server logout fails
            setUser(null);
        }
    }, []);

    const value = {
        user,
        loading,
        error,
        isAuthenticated: !!user,
        isAdmin: user?.is_admin || false,
        login,
        logout,
        checkAuth,
    };

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
}

/**
 * Hook to access auth context
 */
export function useAuth() {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
}
