"use client";

import { renderMathText } from "@/lib/renderMath";

interface MathPreviewProps {
  text: string;
}

export default function MathPreview({ text }: MathPreviewProps) {
  if (!text.trim()) return null;

  // Only show preview if text contains LaTeX delimiters
  if (!text.includes("$")) return null;

  return (
    <div className="mt-2 rounded-lg border border-indigo-100 bg-indigo-50/50 px-3 py-2">
      <div className="flex items-center gap-1.5 mb-1.5">
        <svg
          className="w-3.5 h-3.5 text-indigo-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z"
          />
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
          />
        </svg>
        <span className="text-xs font-medium text-indigo-400">
          Formula Preview
        </span>
      </div>
      <div
        className="text-sm text-gray-800 leading-relaxed katex-container"
        dangerouslySetInnerHTML={{ __html: renderMathText(text) }}
      />
    </div>
  );
}
