/**
 * Spinner shown during document generation phase.
 */
export default function GeneratingIndicator() {
    return (
        <div className="flex flex-col items-center justify-center py-8 px-4">
            <div className="relative w-16 h-16 mb-4">
                {/* Outer ring */}
                <div
                    className="absolute inset-0 rounded-full border-4 border-violet-500/20"
                />
                {/* Spinning arc */}
                <div
                    className="absolute inset-0 rounded-full border-4 border-t-violet-500 border-r-transparent border-b-transparent border-l-transparent animate-spin"
                />
                {/* Inner pulse */}
                <div
                    className="absolute inset-3 rounded-full bg-violet-500/20 animate-pulse"
                />
            </div>

            <h3
                className="text-sm font-medium mb-1"
                style={{ color: 'var(--text-primary)' }}
            >
                Generating Project
            </h3>

            <p
                className="text-xs text-center max-w-[200px]"
                style={{ color: 'var(--text-muted)' }}
            >
                Creating intake document and running quality checks...
            </p>

            <div className="flex gap-1 mt-4">
                <div
                    className="w-2 h-2 rounded-full bg-violet-500 animate-bounce"
                    style={{ animationDelay: '0ms' }}
                />
                <div
                    className="w-2 h-2 rounded-full bg-violet-500 animate-bounce"
                    style={{ animationDelay: '150ms' }}
                />
                <div
                    className="w-2 h-2 rounded-full bg-violet-500 animate-bounce"
                    style={{ animationDelay: '300ms' }}
                />
            </div>
        </div>
    );
}
