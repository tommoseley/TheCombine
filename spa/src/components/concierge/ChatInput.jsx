import { useState, useRef, useEffect } from 'react';

const ALLOWED_TYPES = ['image/png', 'image/jpeg', 'application/pdf'];
const MAX_IMAGE_SIZE = 10 * 1024 * 1024; // 10MB
const MAX_PDF_SIZE = 20 * 1024 * 1024; // 20MB

function formatSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

/**
 * Chat input textarea with Enter-to-send and optional file attachments.
 * Shift+Enter for newline.
 *
 * Props:
 *   onSubmit(text)       - called when user sends a message
 *   disabled             - disables input
 *   placeholder          - textarea placeholder
 *   enableAttachments    - show paperclip button for buffering files
 *   bufferedFiles        - array of { file, label, id } from parent state
 *   onFilesChange(files) - called when buffered files change
 */
export default function ChatInput({
    onSubmit,
    disabled,
    placeholder,
    enableAttachments = false,
    bufferedFiles = [],
    onFilesChange,
}) {
    const [value, setValue] = useState('');
    const [fileError, setFileError] = useState(null);
    const [editingLabelId, setEditingLabelId] = useState(null);
    const textareaRef = useRef(null);
    const fileInputRef = useRef(null);

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

    const handleFileSelect = (e) => {
        setFileError(null);
        const file = e.target.files?.[0];
        if (!file) return;

        // Validate type
        if (!ALLOWED_TYPES.includes(file.type)) {
            setFileError('Only PNG, JPEG, and PDF files are accepted.');
            e.target.value = '';
            return;
        }

        // Validate size
        const maxSize = file.type === 'application/pdf' ? MAX_PDF_SIZE : MAX_IMAGE_SIZE;
        if (file.size > maxSize) {
            const limitStr = file.type === 'application/pdf' ? '20MB' : '10MB';
            setFileError(`File too large. Max ${limitStr} for ${file.type === 'application/pdf' ? 'PDF' : 'images'}.`);
            e.target.value = '';
            return;
        }

        // Default label: filename without extension
        const label = file.name.replace(/\.[^.]+$/, '');
        const id = Date.now() + '-' + Math.random().toString(36).slice(2, 8);

        if (onFilesChange) {
            onFilesChange([...bufferedFiles, { file, label, id }]);
        }
        e.target.value = '';
    };

    const handleRemoveFile = (id) => {
        if (onFilesChange) {
            onFilesChange(bufferedFiles.filter((f) => f.id !== id));
        }
    };

    const handleLabelChange = (id, newLabel) => {
        if (onFilesChange) {
            onFilesChange(
                bufferedFiles.map((f) =>
                    f.id === id ? { ...f, label: newLabel } : f
                )
            );
        }
    };

    // Generate thumbnail preview URL
    const getThumbnailUrl = (buffered) => {
        if (buffered.file.type === 'application/pdf') return null;
        if (!buffered._objectUrl) {
            buffered._objectUrl = URL.createObjectURL(buffered.file);
        }
        return buffered._objectUrl;
    };

    return (
        <div
            className="p-3 border-t"
            style={{ borderColor: 'var(--border-panel)' }}
        >
            {/* Buffered file chips */}
            {enableAttachments && bufferedFiles.length > 0 && (
                <div className="flex flex-wrap gap-2 mb-2">
                    {bufferedFiles.map((bf) => {
                        const thumbUrl = getThumbnailUrl(bf);
                        return (
                            <div
                                key={bf.id}
                                className="flex items-center gap-2 px-2 py-1.5 rounded-lg border"
                                style={{
                                    background: 'var(--bg-canvas)',
                                    borderColor: 'var(--border-panel)',
                                }}
                            >
                                {/* Thumbnail or PDF icon */}
                                {thumbUrl ? (
                                    <img
                                        src={thumbUrl}
                                        alt={bf.label}
                                        className="w-8 h-8 rounded object-cover flex-shrink-0"
                                    />
                                ) : (
                                    <div
                                        className="w-8 h-8 rounded flex items-center justify-center flex-shrink-0"
                                        style={{ background: 'var(--bg-panel)' }}
                                    >
                                        <svg
                                            className="w-4 h-4"
                                            viewBox="0 0 24 24"
                                            fill="none"
                                            stroke="currentColor"
                                            strokeWidth="2"
                                            style={{ color: 'var(--text-muted)' }}
                                        >
                                            <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
                                            <polyline points="14 2 14 8 20 8" />
                                        </svg>
                                    </div>
                                )}

                                {/* Label (click to edit) */}
                                {editingLabelId === bf.id ? (
                                    <input
                                        type="text"
                                        value={bf.label}
                                        onChange={(e) => handleLabelChange(bf.id, e.target.value)}
                                        onBlur={() => setEditingLabelId(null)}
                                        onKeyDown={(e) => e.key === 'Enter' && setEditingLabelId(null)}
                                        autoFocus
                                        className="text-[11px] px-1 py-0.5 rounded border"
                                        style={{
                                            background: 'var(--bg-input)',
                                            borderColor: 'var(--border-input)',
                                            color: 'var(--text-primary)',
                                            width: 100,
                                            outline: 'none',
                                        }}
                                    />
                                ) : (
                                    <span
                                        className="text-[11px] cursor-pointer max-w-[100px] truncate"
                                        style={{ color: 'var(--text-secondary)' }}
                                        title="Click to edit label"
                                        onClick={() => setEditingLabelId(bf.id)}
                                    >
                                        {bf.label}
                                    </span>
                                )}

                                {/* Size */}
                                <span
                                    className="text-[10px]"
                                    style={{ color: 'var(--text-muted)' }}
                                >
                                    {formatSize(bf.file.size)}
                                </span>

                                {/* Remove button */}
                                <button
                                    onClick={() => handleRemoveFile(bf.id)}
                                    className="p-0.5 rounded hover:bg-white/10 transition-colors"
                                    style={{ color: 'var(--text-muted)' }}
                                    title="Remove"
                                >
                                    <svg
                                        className="w-3 h-3"
                                        viewBox="0 0 24 24"
                                        fill="none"
                                        stroke="currentColor"
                                        strokeWidth="2"
                                    >
                                        <line x1="18" y1="6" x2="6" y2="18" />
                                        <line x1="6" y1="6" x2="18" y2="18" />
                                    </svg>
                                </button>
                            </div>
                        );
                    })}
                </div>
            )}

            {/* File validation error */}
            {fileError && (
                <p className="text-[11px] text-red-400 mb-2">{fileError}</p>
            )}

            <div className="flex gap-2">
                {/* Attachment button */}
                {enableAttachments && (
                    <>
                        <input
                            ref={fileInputRef}
                            type="file"
                            accept="image/png,image/jpeg,application/pdf"
                            onChange={handleFileSelect}
                            className="hidden"
                        />
                        <button
                            onClick={() => fileInputRef.current?.click()}
                            disabled={disabled}
                            className="flex-shrink-0 p-2 rounded-lg transition-colors hover:bg-white/10"
                            style={{
                                color: disabled ? 'var(--text-muted)' : 'var(--text-secondary)',
                                opacity: disabled ? 0.5 : 1,
                            }}
                            title="Attach mockup (PNG, JPEG, PDF)"
                        >
                            <svg
                                className="w-5 h-5"
                                viewBox="0 0 24 24"
                                fill="none"
                                stroke="currentColor"
                                strokeWidth="2"
                                strokeLinecap="round"
                                strokeLinejoin="round"
                            >
                                <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                                <circle cx="8.5" cy="8.5" r="1.5" />
                                <polyline points="21 15 16 10 5 21" />
                            </svg>
                        </button>
                    </>
                )}

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
