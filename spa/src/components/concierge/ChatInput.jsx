import { useState, useRef, useEffect } from 'react';

/**
 * Chat input textarea with Enter-to-send.
 * Shift+Enter for newline.
 */
export default function ChatInput({ onSubmit, disabled, placeholder }) {
    const [value, setValue] = useState('');
    const textareaRef = useRef(null);

    useEffect(() => {
        if (!disabled) {
            textareaRef.current?.focus();
        }
    }, [disabled]);

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (value.trim() && !disabled) {
                onSubmit(value.trim());
                setValue('');
            }
        }
    };

    const handleSubmit = () => {
        if (value.trim() && !disabled) {
            onSubmit(value.trim());
            setValue('');
        }
    };

    return (
        <div
            className="p-3 border-t"
            style={{ borderColor: 'var(--border-panel)' }}
        >
            <div className="flex gap-2">
                <textarea
                    ref={textareaRef}
                    value={value}
                    onChange={(e) => setValue(e.target.value)}
                    onKeyDown={handleKeyDown}
                    disabled={disabled}
                    placeholder={placeholder || 'Type your message...'}
                    rows={2}
                    className="flex-1 rounded-lg px-3 py-2 text-sm resize-none"
                    style={{
                        background: 'var(--bg-input)',
                        border: '1px solid var(--border-input)',
                        color: 'var(--text-primary)',
                    }}
                />
                <button
                    onClick={handleSubmit}
                    disabled={disabled || !value.trim()}
                    className={`px-4 rounded-lg font-medium text-sm transition-colors ${
                        disabled || !value.trim()
                            ? 'bg-slate-600 text-slate-400 cursor-not-allowed'
                            : 'bg-violet-500 text-white hover:bg-violet-400'
                    }`}
                >
                    Send
                </button>
            </div>
            <p
                className="text-[10px] mt-1"
                style={{ color: 'var(--text-muted)' }}
            >
                Press Enter to send, Shift+Enter for newline
            </p>
        </div>
    );
}
