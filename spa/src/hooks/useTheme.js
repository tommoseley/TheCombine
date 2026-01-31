import { useState, useEffect, useCallback } from 'react';
import { THEMES } from '../utils/constants';

const STORAGE_KEY = 'combine-theme';

/**
 * Hook for theme management with localStorage persistence
 */
export function useTheme(defaultTheme = 'industrial') {
    const [theme, setThemeState] = useState(() => {
        if (typeof window === 'undefined') return defaultTheme;
        const stored = localStorage.getItem(STORAGE_KEY);
        return stored && THEMES.includes(stored) ? stored : defaultTheme;
    });

    // Persist theme to localStorage
    useEffect(() => {
        localStorage.setItem(STORAGE_KEY, theme);
    }, [theme]);

    // Set theme
    const setTheme = useCallback((newTheme) => {
        if (THEMES.includes(newTheme)) {
            setThemeState(newTheme);
        }
    }, []);

    // Cycle to next theme
    const cycleTheme = useCallback(() => {
        setThemeState(current => {
            const idx = THEMES.indexOf(current);
            return THEMES[(idx + 1) % THEMES.length];
        });
    }, []);

    return { theme, setTheme, cycleTheme };
}
