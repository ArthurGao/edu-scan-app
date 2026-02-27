"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import SolutionDisplay from "@/components/SolutionDisplay";
import ConversationThread from "@/components/ConversationThread";
import {
  getScanResult,
  getConversation,
  addToMistakes,
} from "@/lib/api";
import { ScanResponse, ConversationMessage } from "@/lib/types";

export default function HistoryDetailPage() {
  const params = useParams();
  const router = useRouter();
  const scanId = params.scanId as string;

  const [result, setResult] = useState<ScanResponse | null>(null);
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [scanData, convData] = await Promise.all([
        getScanResult(scanId),
        getConversation(scanId).catch(() => ({ messages: [] })),
      ]);
      setResult(scanData);
      setMessages(convData.messages || []);
    } catch {
      setError("Failed to load scan result. It may have been deleted.");
    } finally {
      setLoading(false);
    }
  }, [scanId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleNewMessage = (msg: ConversationMessage) => {
    setMessages((prev) => [...prev, msg]);
  };

  const handleSaveToMistakes = async () => {
    if (!result) return;
    setIsSaving(true);
    try {
      await addToMistakes(result.scan_id);
      setSaved(true);
    } catch {
      setError("Failed to save to mistake book.");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Back button + header */}
      <div className="pt-4 lg:pt-0 flex items-center gap-4">
        <button
          onClick={() => router.push("/history")}
          className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors"
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
              d="M15.75 19.5L8.25 12l7.5-7.5"
            />
          </svg>
          Back to History
        </button>
      </div>

      {/* Loading */}
      {loading && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-12 text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-indigo-50 rounded-full mb-4">
            <svg
              className="animate-spin w-8 h-8 text-indigo-500"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
              />
            </svg>
          </div>
          <p className="text-gray-700 font-medium">Loading solution...</p>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-center gap-3">
          <svg
            className="w-5 h-5 text-red-500 flex-shrink-0"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z"
            />
          </svg>
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Solution */}
      {result && (
        <>
          {/* Problem text */}
          {result.ocr_text && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
              <h3 className="text-base font-semibold text-gray-900 mb-2">
                Problem
              </h3>
              <p className="text-sm text-gray-700 whitespace-pre-wrap">
                {result.ocr_text}
              </p>
            </div>
          )}

          <SolutionDisplay
            data={result}
            onSaveToMistakes={saved ? undefined : handleSaveToMistakes}
            isSaving={isSaving}
          />

          {saved && (
            <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 flex items-center gap-3">
              <svg
                className="w-5 h-5 text-emerald-500 flex-shrink-0"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M4.5 12.75l6 6 9-13.5"
                />
              </svg>
              <p className="text-sm text-emerald-700">
                Saved to your Mistake Book for review
              </p>
            </div>
          )}

          {/* Conversation */}
          <ConversationThread
            scanId={scanId}
            messages={messages}
            onNewMessage={handleNewMessage}
          />
        </>
      )}
    </div>
  );
}
