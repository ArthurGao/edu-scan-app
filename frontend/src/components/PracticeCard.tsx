"use client";

import { useState, useRef } from "react";
import { submitPracticeAnswer } from "@/lib/api";
import type { PracticeQuestionGenerated, SubmitPracticeAnswerResponse } from "@/lib/types";
import { renderMathText } from "@/lib/renderMath";

const DIFFICULTY_LABELS: Record<number, { label: string; color: string }> = {
  0: { label: "Same Level", color: "bg-blue-100 text-blue-700" },
  1: { label: "Harder", color: "bg-orange-100 text-orange-700" },
  2: { label: "Hardest", color: "bg-red-100 text-red-700" },
};

interface PracticeCardProps {
  question: PracticeQuestionGenerated;
  onAnswered?: () => void;
}

export default function PracticeCard({ question, onAnswered }: PracticeCardProps) {
  const [answer, setAnswer] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<SubmitPracticeAnswerResponse | null>(null);
  const [showExplanation, setShowExplanation] = useState(false);
  const [alreadyAnswered] = useState(question.answered);
  const startTime = useRef(Date.now());

  const diffInfo = DIFFICULTY_LABELS[question.difficulty_offset] || DIFFICULTY_LABELS[0];

  const handleSubmit = async () => {
    if (!answer.trim() || submitting) return;
    setSubmitting(true);
    try {
      const timeSpent = Math.round((Date.now() - startTime.current) / 1000);
      const res = await submitPracticeAnswer(question.id, answer.trim(), timeSpent);
      setResult(res);
      onAnswered?.();
    } catch (err: unknown) {
      const error = err as { response?: { status?: number } };
      if (error?.response?.status === 409) {
        // Already answered — ignore
      }
    } finally {
      setSubmitting(false);
    }
  };

  // renderMathText produces safe KaTeX HTML from LaTeX (trusted AI backend content)

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <span className={`px-2 py-0.5 rounded text-xs font-medium ${diffInfo.color}`}>
          {diffInfo.label}
        </span>
        {question.difficulty && (
          <span className="px-2 py-0.5 rounded text-xs bg-gray-100 text-gray-600">
            {question.difficulty}
          </span>
        )}
        {question.knowledge_points?.map((kp) => (
          <span key={kp} className="px-2 py-0.5 rounded text-xs bg-indigo-50 text-indigo-600">
            {kp}
          </span>
        ))}
      </div>

      {/* Question text */}
      <div
        className="text-sm text-gray-800 leading-relaxed mb-4"
        dangerouslySetInnerHTML={{ __html: renderMathText(question.question_text) }}
      />

      {/* Answer area */}
      {!result && !alreadyAnswered ? (
        <div className="flex gap-2">
          <input
            type="text"
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
            placeholder="Enter your answer..."
            className="flex-1 px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            disabled={submitting}
          />
          <button
            onClick={handleSubmit}
            disabled={!answer.trim() || submitting}
            className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitting ? "Grading..." : "Submit"}
          </button>
        </div>
      ) : null}

      {/* Result */}
      {result && (
        <div className={`mt-3 p-4 rounded-lg ${result.is_correct ? "bg-emerald-50 border border-emerald-200" : "bg-red-50 border border-red-200"}`}>
          <div className="flex items-center gap-2 mb-2">
            <span className={`text-lg ${result.is_correct ? "text-emerald-600" : "text-red-600"}`}>
              {result.is_correct ? "Correct!" : "Incorrect"}
            </span>
          </div>

          {!result.is_correct && result.correct_answer && (
            <p className="text-sm text-gray-700 mb-2">
              <span className="font-medium">Correct answer: </span>
              <span dangerouslySetInnerHTML={{ __html: renderMathText(result.correct_answer) }} />
            </p>
          )}

          {result.ai_feedback && (
            <p className="text-sm text-gray-600 mb-2">{result.ai_feedback}</p>
          )}

          {result.answer_explanation && (
            <div className="mt-2">
              <button
                onClick={() => setShowExplanation(!showExplanation)}
                className="text-sm text-indigo-600 hover:text-indigo-800 font-medium"
              >
                {showExplanation ? "Hide Explanation" : "View Explanation"}
              </button>
              {showExplanation && (
                <div
                  className="mt-2 text-sm text-gray-700 leading-relaxed"
                  dangerouslySetInnerHTML={{ __html: renderMathText(result.answer_explanation) }}
                />
              )}
            </div>
          )}
        </div>
      )}

      {/* Already answered indicator */}
      {alreadyAnswered && !result && (
        <div className={`mt-3 p-3 rounded-lg ${question.is_correct ? "bg-emerald-50" : "bg-red-50"}`}>
          <span className="text-sm">
            {question.is_correct ? "Answered correctly" : "Answered incorrectly"}
          </span>
        </div>
      )}
    </div>
  );
}
