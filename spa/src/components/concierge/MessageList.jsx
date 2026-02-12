import { useRef, useEffect } from 'react';

/**
 * Chat message display component.
 * User messages on right (emerald), assistant on left (violet).
 * Optional introContent renders at top and scrolls with conversation.
 */
export default function MessageList({ messages, pendingPrompt, introContent }) {
    const endRef = useRef(null);

    useEffect(() => {
        endRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, pendingPrompt]);

    return (
        <div className="flex-1 overflow-y-auto p-4 space-y-3" onWheel={(e) => e.stopPropagation()}>
            {introContent}

            {messages.map((msg, idx) => (
                <div
                    key={idx}
                    className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                    <div
                        className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
                            msg.role === 'user'
                                ? 'bg-emerald-500/20 text-emerald-100 rounded-br-sm'
                                : 'bg-violet-500/20 text-violet-100 rounded-bl-sm'
                        }`}
                    >
                        {msg.content}
                    </div>
                </div>
            ))}

            {pendingPrompt && (
                <div className="flex justify-start">
                    <div className="max-w-[85%] rounded-lg px-3 py-2 text-sm bg-violet-500/20 text-violet-100 rounded-bl-sm">
                        {pendingPrompt}
                    </div>
                </div>
            )}

            <div ref={endRef} />
        </div>
    );
}
