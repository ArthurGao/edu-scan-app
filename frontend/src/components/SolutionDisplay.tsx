"use client";

import { ScanResponse } from "@/lib/types";
import { renderLatex, renderMathText } from "@/lib/renderMath";

interface SolutionDisplayProps {
  data: ScanResponse;
  onSaveToMistakes?: () => void;
  isSaving?: boolean;
}

function SubjectBadge({ label }: { label: string }) {
  const colorMap: Record<string, string> = {
    math: "bg-indigo-100 text-indigo-700",
    physics: "bg-blue-100 text-blue-700",
    chemistry: "bg-emerald-100 text-emerald-700",
  };
  const color =
    colorMap[label.toLowerCase()] || "bg-gray-100 text-gray-700";
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${color}`}
    >
      {label}
    </span>
  );
}

function VerificationBadge({
  status,
  confidence,
}: {
  status?: string;
  confidence?: number;
}) {
  if (!status || status === "unverified") return null;

  if (status === "verified") {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-100 text-emerald-700">
        <svg
          className="w-3.5 h-3.5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          strokeWidth={2.5}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
        已验证{confidence ? ` ${Math.round(confidence * 100)}%` : ""}
      </span>
    );
  }

  if (status === "caution") {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-100 text-amber-700">
        <svg
          className="w-3.5 h-3.5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          strokeWidth={2.5}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
          />
        </svg>
        建议核实
      </span>
    );
  }

  return null;
}

export default function SolutionDisplay({
  data,
  onSaveToMistakes,
  isSaving,
}: SolutionDisplayProps) {
  const { solution, related_formulas } = data;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-lg font-semibold text-gray-900">Solution</h2>
              <VerificationBadge
                status={solution.verification_status}
                confidence={solution.verification_confidence}
              />
            </div>
            <div className="flex items-center gap-2 mt-2 flex-wrap">
              <SubjectBadge label={solution.question_type} />
              {solution.knowledge_points.map((point, i) => (
                <span
                  key={i}
                  className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-700"
                >
                  {point}
                </span>
              ))}
            </div>
          </div>
          {onSaveToMistakes && (
            <button
              onClick={onSaveToMistakes}
              disabled={isSaving}
              className="flex items-center gap-2 px-4 py-2 bg-amber-50 text-amber-700 rounded-lg text-sm font-medium hover:bg-amber-100 transition-colors disabled:opacity-50"
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
                  d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25"
                />
              </svg>
              {isSaving ? "Saving..." : "Save to Mistake Book"}
            </button>
          )}
        </div>
      </div>

      {/* Steps */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <h3 className="text-base font-semibold text-gray-900 mb-4">
          Step-by-Step Solution
        </h3>
        <div className="space-y-5">
          {solution.steps.map((step) => (
            <div key={step.step} className="flex gap-4">
              <div className="flex-shrink-0 w-8 h-8 bg-indigo-500 text-white rounded-full flex items-center justify-center text-sm font-bold">
                {step.step}
              </div>
              <div className="flex-1 pt-0.5 min-w-0">
                {/* Description — supports inline math with $...$ */}
                <div
                  className="text-gray-800 text-sm leading-relaxed"
                  dangerouslySetInnerHTML={{
                    __html: renderMathText(step.description),
                  }}
                />
                {/* Formula — rendered as display math */}
                {step.formula && (
                  <div
                    className="mt-2 bg-indigo-50 rounded-lg px-4 py-3 katex-container overflow-x-auto"
                    dangerouslySetInnerHTML={{
                      __html: renderLatex(step.formula, true),
                    }}
                  />
                )}
                {/* Calculation — rendered with math support */}
                {step.calculation && (
                  <div
                    className="mt-2 bg-gray-50 rounded-lg px-4 py-3 text-sm text-gray-700 overflow-x-auto leading-relaxed katex-container"
                    dangerouslySetInnerHTML={{
                      __html: renderMathText(step.calculation),
                    }}
                  />
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Final Answer */}
      <div className="bg-emerald-50 rounded-xl border border-emerald-200 p-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-emerald-500 text-white rounded-full flex items-center justify-center flex-shrink-0">
            <svg
              className="w-5 h-5"
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
          </div>
          <div className="min-w-0">
            <p className="text-sm font-medium text-emerald-700">Final Answer</p>
            <div
              className="text-lg font-semibold text-emerald-900 mt-0.5 katex-container"
              dangerouslySetInnerHTML={{
                __html: renderMathText(solution.final_answer),
              }}
            />
          </div>
        </div>
      </div>

      {/* Explanation */}
      {solution.explanation && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <h3 className="text-base font-semibold text-gray-900 mb-2">
            Explanation
          </h3>
          <div
            className="text-sm text-gray-600 leading-relaxed"
            dangerouslySetInnerHTML={{
              __html: renderMathText(solution.explanation),
            }}
          />
        </div>
      )}

      {/* Tips */}
      {solution.tips && (
        <div className="bg-amber-50 rounded-xl border border-amber-200 p-6">
          <div className="flex items-start gap-3">
            <svg
              className="w-5 h-5 text-amber-500 mt-0.5 flex-shrink-0"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 18v-5.25m0 0a6.01 6.01 0 001.5-.189m-1.5.189a6.01 6.01 0 01-1.5-.189m3.75 7.478a12.06 12.06 0 01-4.5 0m3.75 2.383a14.406 14.406 0 01-3 0M14.25 18v-.192c0-.983.658-1.823 1.508-2.316a7.5 7.5 0 10-7.517 0c.85.493 1.509 1.333 1.509 2.316V18"
              />
            </svg>
            <div>
              <p className="text-sm font-medium text-amber-800">Tip</p>
              <div
                className="text-sm text-amber-700 mt-1"
                dangerouslySetInnerHTML={{
                  __html: renderMathText(solution.tips),
                }}
              />
            </div>
          </div>
        </div>
      )}

      {/* Related Formulas */}
      {related_formulas && related_formulas.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <h3 className="text-base font-semibold text-gray-900 mb-4">
            Related Formulas
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {related_formulas.map((formula) => (
              <div
                key={formula.id}
                className="bg-gray-50 rounded-lg p-4 border border-gray-100"
              >
                <p className="text-sm font-medium text-gray-800">
                  {formula.name}
                </p>
                <div
                  className="mt-2 katex-container overflow-x-auto"
                  dangerouslySetInnerHTML={{
                    __html: renderLatex(formula.latex, true),
                  }}
                />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
