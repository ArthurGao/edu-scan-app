"use client";

import { useState, useCallback } from "react";
import UploadZone from "@/components/UploadZone";
import SolutionDisplay from "@/components/SolutionDisplay";
import ConversationThread from "@/components/ConversationThread";
import { solveImage, solveText, addToMistakes } from "@/lib/api";
import { ScanResponse, ConversationMessage } from "@/lib/types";

type InputMode = "image" | "text";

const subjects = [
  { value: "", label: "Auto-detect" },
  { value: "math", label: "Math" },
  { value: "physics", label: "Physics" },
  { value: "chemistry", label: "Chemistry" },
];

export default function UploadSolvePage() {
  const [inputMode, setInputMode] = useState<InputMode>("image");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [problemText, setProblemText] = useState("");
  const [subject, setSubject] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ScanResponse | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [messages, setMessages] = useState<ConversationMessage[]>([]);

  const handleFileSelected = useCallback((file: File) => {
    setSelectedFile(file);
    setPreviewUrl(URL.createObjectURL(file));
    setResult(null);
    setError(null);
    setSaved(false);
  }, []);

  const handleTabSwitch = (mode: InputMode) => {
    setInputMode(mode);
    setResult(null);
    setError(null);
    setSaved(false);
  };

  const canSolve =
    inputMode === "image"
      ? !!selectedFile
      : problemText.trim().length > 0;

  const handleSolve = async () => {
    if (!canSolve) return;
    setLoading(true);
    setError(null);
    setResult(null);
    setMessages([]);
    try {
      const data =
        inputMode === "image"
          ? await solveImage(selectedFile!, subject || undefined, undefined)
          : await solveText(problemText.trim(), subject || undefined, undefined);
      setResult(data);
    } catch (err: unknown) {
      const message =
        err instanceof Error
          ? err.message
          : "Failed to solve. Please try again.";
      setError(message);
    } finally {
      setLoading(false);
    }
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
    <div className="space-y-8">
      {/* Page header */}
      <div className="pt-4 lg:pt-0">
        <h1 className="text-2xl font-bold text-gray-900">Upload & Solve</h1>
        <p className="text-gray-500 mt-1">
          Upload a photo or type your homework problem to get an AI-powered
          solution
        </p>
      </div>

      {/* Input mode tabs */}
      <div className="flex border-b border-gray-200">
        <button
          onClick={() => handleTabSwitch("image")}
          className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
            inputMode === "image"
              ? "border-indigo-500 text-indigo-600"
              : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
          }`}
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
              d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0022.5 18.75V5.25A2.25 2.25 0 0020.25 3H3.75A2.25 2.25 0 001.5 5.25v13.5A2.25 2.25 0 003.75 21z"
            />
          </svg>
          Upload Image
        </button>
        <button
          onClick={() => handleTabSwitch("text")}
          className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
            inputMode === "text"
              ? "border-indigo-500 text-indigo-600"
              : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
          }`}
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
              d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L6.832 19.82a4.5 4.5 0 01-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 011.13-1.897L16.863 4.487zm0 0L19.5 7.125"
            />
          </svg>
          Type Text
        </button>
      </div>

      {/* Input area */}
      {inputMode === "image" ? (
        <UploadZone
          onFileSelected={handleFileSelected}
          selectedFile={selectedFile}
          previewUrl={previewUrl}
        />
      ) : (
        <textarea
          value={problemText}
          onChange={(e) => {
            setProblemText(e.target.value);
            setResult(null);
            setError(null);
            setSaved(false);
          }}
          placeholder="Type or paste your homework problem here...&#10;&#10;Example: Solve for x: 2x + 5 = 15"
          rows={6}
          className="w-full rounded-xl border-2 border-dashed border-gray-300 bg-gray-50 px-4 py-3 text-sm text-gray-900 placeholder-gray-400 focus:border-indigo-500 focus:bg-white focus:outline-none transition-colors resize-y"
        />
      )}

      {/* Options & Solve button */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
        <div className="flex-1 w-full sm:w-auto">
          <label
            htmlFor="subject"
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            Subject (optional)
          </label>
          <select
            id="subject"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            className="w-full sm:w-48 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
          >
            {subjects.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </div>
        <button
          onClick={handleSolve}
          disabled={!canSolve || loading}
          className="mt-auto px-6 py-2.5 bg-indigo-500 text-white rounded-lg font-medium text-sm hover:bg-indigo-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          {loading ? (
            <>
              <svg
                className="animate-spin w-4 h-4"
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
              Solving...
            </>
          ) : (
            <>
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
                  d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z"
                />
              </svg>
              Solve
            </>
          )}
        </button>
      </div>

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

      {/* Loading state */}
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
          <p className="text-gray-700 font-medium">
            Analyzing your problem...
          </p>
          <p className="text-gray-500 text-sm mt-1">
            This may take a few seconds
          </p>
        </div>
      )}

      {/* Result */}
      {result && (
        <SolutionDisplay
          data={result}
          onSaveToMistakes={saved ? undefined : handleSaveToMistakes}
          isSaving={isSaving}
        />
      )}

      {/* Saved confirmation */}
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

      {/* Follow-up conversation */}
      {result && (
        <ConversationThread
          scanId={result.scan_id}
          messages={messages}
          onNewMessage={(msg) => setMessages((prev) => [...prev, msg])}
        />
      )}
    </div>
  );
}
