"use client";

import { useState, useEffect, useCallback } from "react";
import { generatePractice, getPracticeQuestions } from "@/lib/api";
import type { PracticeQuestionGenerated } from "@/lib/types";
import PracticeCard from "./PracticeCard";

interface PracticeSectionProps {
  scanId: string;
}

export default function PracticeSection({ scanId }: PracticeSectionProps) {
  const [questions, setQuestions] = useState<PracticeQuestionGenerated[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadQuestions = useCallback(async () => {
    try {
      const res = await getPracticeQuestions(scanId);
      if (res.status === "ready" && res.questions.length > 0) {
        setQuestions(res.questions);
        setLoading(false);
        return true;
      }
      return false;
    } catch {
      return false;
    }
  }, [scanId]);

  useEffect(() => {
    let cancelled = false;

    async function init() {
      const found = await loadQuestions();
      if (found || cancelled) {
        setLoading(false);
        return;
      }

      try {
        const res = await generatePractice(scanId);
        if (!cancelled) {
          if (res.status === "ready") {
            setQuestions(res.questions);
          } else if (res.status === "error") {
            setError(res.message || "Failed to generate questions");
          }
        }
      } catch {
        if (!cancelled) setError("Failed to generate practice questions");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    init();
    return () => { cancelled = true; };
  }, [scanId, loadQuestions]);

  const handleGenerateMore = async () => {
    setGenerating(true);
    setError(null);
    try {
      const res = await generatePractice(scanId, true);
      if (res.status === "ready") {
        setQuestions(res.questions);
      } else if (res.status === "error") {
        setError(res.message || "Failed to generate more questions");
      }
    } catch {
      setError("Failed to generate more questions");
    } finally {
      setGenerating(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <h3 className="text-base font-semibold text-gray-900 mb-4">Practice Similar Questions</h3>
        <div className="space-y-4">
          {[0, 1, 2].map((i) => (
            <div key={i} className="animate-pulse">
              <div className="h-4 bg-gray-200 rounded w-24 mb-2" />
              <div className="h-3 bg-gray-200 rounded w-full mb-1" />
              <div className="h-3 bg-gray-200 rounded w-3/4" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error && questions.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <h3 className="text-base font-semibold text-gray-900 mb-2">Practice Similar Questions</h3>
        <p className="text-sm text-gray-500">{error}</p>
        <button
          onClick={handleGenerateMore}
          className="mt-3 px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700"
        >
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
      <h3 className="text-base font-semibold text-gray-900 mb-4">Practice Similar Questions</h3>

      <div className="space-y-4">
        {questions.map((q) => (
          <PracticeCard
            key={q.id}
            question={q}
            onAnswered={() => loadQuestions()}
          />
        ))}
      </div>

      {error && <p className="mt-3 text-sm text-red-500">{error}</p>}

      <button
        onClick={handleGenerateMore}
        disabled={generating}
        className="mt-4 w-full px-4 py-2 border border-gray-200 text-gray-700 text-sm rounded-lg hover:bg-gray-50 disabled:opacity-50"
      >
        {generating ? "Generating..." : "Generate More Questions"}
      </button>
    </div>
  );
}
