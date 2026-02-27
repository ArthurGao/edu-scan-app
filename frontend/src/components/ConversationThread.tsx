"use client";

import { useState, useRef, useEffect } from "react";
import { ConversationMessage } from "@/lib/types";
import { sendFollowUp } from "@/lib/api";

interface ConversationThreadProps {
  scanId: string;
  messages: ConversationMessage[];
  onNewMessage?: (msg: ConversationMessage) => void;
}

export default function ConversationThread({
  scanId,
  messages,
  onNewMessage,
}: ConversationThreadProps) {
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || sending) return;

    // Optimistically add user message
    const userMsg: ConversationMessage = {
      id: `temp-${Date.now()}`,
      role: "user",
      content: text,
      created_at: new Date().toISOString(),
    };
    onNewMessage?.(userMsg);
    setInput("");
    setSending(true);
    setError(null);

    try {
      const res = await sendFollowUp(scanId, text);
      const assistantMsg: ConversationMessage = {
        id: `temp-${Date.now() + 1}`,
        role: "assistant",
        content: res.reply,
        created_at: new Date().toISOString(),
      };
      onNewMessage?.(assistantMsg);
    } catch {
      setError("Failed to send. Please try again.");
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Filter out the system message and the initial assistant summary
  // (the solution is already shown via SolutionDisplay)
  const visibleMessages = messages.filter((m, i) => {
    if (m.role === "system") return false;
    // Skip the first assistant message (initial solution summary)
    if (m.role === "assistant" && i <= 1) return false;
    return true;
  });

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-100">
        <h3 className="text-base font-semibold text-gray-900">Conversation</h3>
        <p className="text-xs text-gray-500 mt-0.5">
          Ask follow-up questions about this problem
        </p>
      </div>

      {/* Messages */}
      <div className="px-6 py-4 space-y-4 max-h-96 overflow-y-auto">
        {visibleMessages.length === 0 && (
          <p className="text-sm text-gray-400 text-center py-4">
            No conversation yet. Ask a question below.
          </p>
        )}
        {visibleMessages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[80%] rounded-xl px-4 py-2.5 text-sm leading-relaxed ${
                msg.role === "user"
                  ? "bg-indigo-500 text-white"
                  : "bg-gray-100 text-gray-800"
              }`}
            >
              <p className="whitespace-pre-wrap">{msg.content}</p>
            </div>
          </div>
        ))}
        {sending && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-xl px-4 py-2.5">
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:0.15s]" />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:0.3s]" />
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Error */}
      {error && (
        <div className="px-6 pb-2">
          <p className="text-xs text-red-500">{error}</p>
        </div>
      )}

      {/* Input */}
      <div className="px-6 py-4 border-t border-gray-100">
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a follow-up question..."
            rows={1}
            className="flex-1 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-indigo-500 focus:outline-none resize-none"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || sending}
            className="px-4 py-2 bg-indigo-500 text-white rounded-lg text-sm font-medium hover:bg-indigo-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex-shrink-0"
          >
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5"
              />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
