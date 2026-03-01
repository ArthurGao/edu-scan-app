"use client";

import { useState, useCallback, useRef } from "react";
import dynamic from "next/dynamic";
import { useUser } from "@clerk/nextjs";
import UploadZone from "@/components/UploadZone";
import SolutionDisplay from "@/components/SolutionDisplay";
import ConversationThread from "@/components/ConversationThread";
import MathPreview from "@/components/MathPreview";
import LandingPage from "@/components/LandingPage";
import { extractText, solveText, addToMistakes } from "@/lib/api";
import { ScanResponse, ConversationMessage } from "@/lib/types";

const MathInput = dynamic(() => import("@/components/MathInput"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-40 rounded-xl border-2 border-dashed border-gray-300 bg-gray-50 animate-pulse" />
  ),
});

type InputMode = "image" | "text";

const subjects = [
  { value: "", label: "Auto-detect" },
  { value: "math", label: "Math" },
  { value: "physics", label: "Physics" },
  { value: "chemistry", label: "Chemistry" },
  { value: "biology", label: "Biology" },
  { value: "english", label: "English" },
  { value: "chinese", label: "Chinese" },
];

export default function UploadSolvePage() {
  const { isSignedIn, isLoaded } = useUser();
  const [inputMode, setInputMode] = useState<InputMode>("image");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [problemText, setProblemText] = useState("");
  const [subject, setSubject] = useState("");
  const [extracting, setExtracting] = useState(false);
  const [solving, setSolving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ScanResponse | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [ocrText, setOcrText] = useState("");
  const [ocrReady, setOcrReady] = useState(false);
  const [refImages, setRefImages] = useState<{ file: File; url: string }[]>([]);
  const refImageInputRef = useRef<HTMLInputElement>(null);
  const [resultTab, setResultTab] = useState<"solution" | "chat">("solution");

  const loading = extracting || solving;

  // Wrap plain OCR text in \text{} so MathLive renders it as normal text
  const wrapOcrForMathLive = (raw: string): string => {
    if (!raw.trim()) return "";
    // If it already contains LaTeX commands, return as-is
    if (raw.includes("\\")) return raw;
    // Wrap each line in \text{} and join with newlines
    return raw
      .split("\n")
      .map((line) => (line.trim() ? `\\text{${line.trim()}}` : ""))
      .filter(Boolean)
      .join(" \\\\ ");
  };

  // Auto-extract text when file is selected
  const handleFileSelected = useCallback(async (file: File) => {
    setSelectedFile(file);
    setPreviewUrl(URL.createObjectURL(file));
    setResult(null);
    setError(null);
    setSaved(false);
    setOcrText("");
    setOcrReady(false);

    // Auto-trigger OCR
    setExtracting(true);
    try {
      const data = await extractText(file);
      setOcrText(wrapOcrForMathLive(data.ocr_text));
      setOcrReady(true);
    } catch (err: unknown) {
      const message =
        err instanceof Error
          ? err.message
          : "Failed to extract text. Please try again.";
      setError(message);
    } finally {
      setExtracting(false);
    }
  }, []);

  const handleRetryExtract = async () => {
    if (!selectedFile) return;
    setExtracting(true);
    setError(null);
    setOcrText("");
    setOcrReady(false);
    try {
      const data = await extractText(selectedFile);
      setOcrText(wrapOcrForMathLive(data.ocr_text));
      setOcrReady(true);
    } catch (err: unknown) {
      const message =
        err instanceof Error
          ? err.message
          : "Failed to extract text. Please try again.";
      setError(message);
    } finally {
      setExtracting(false);
    }
  };

  const handleTabSwitch = (mode: InputMode) => {
    setInputMode(mode);
    setResult(null);
    setError(null);
    setSaved(false);
    setOcrText("");
    setOcrReady(false);
  };

  const handleAddRefImages = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (!files) return;
      const newImages = Array.from(files)
        .filter((f) => f.type.startsWith("image/"))
        .map((f) => ({ file: f, url: URL.createObjectURL(f) }));
      setRefImages((prev) => [...prev, ...newImages]);
      e.target.value = "";
    },
    []
  );

  const handleRemoveRefImage = useCallback((index: number) => {
    setRefImages((prev) => {
      URL.revokeObjectURL(prev[index].url);
      return prev.filter((_, i) => i !== index);
    });
  }, []);

  const handleSolve = async () => {
    const text = inputMode === "image" ? ocrText.trim() : problemText.trim();
    if (!text) return;
    const solveInput =
      inputMode === "text" && text && !text.includes("$")
        ? `$${text}$`
        : text;
    setSolving(true);
    setError(null);
    setResult(null);
    setMessages([]);
    try {
      const data = await solveText(solveInput, subject || undefined, undefined);
      setResult(data);
    } catch (err: unknown) {
      const message =
        err instanceof Error
          ? err.message
          : "Failed to solve. Please try again.";
      setError(message);
    } finally {
      setSolving(false);
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

  const canSolve =
    inputMode === "image"
      ? ocrReady && ocrText.trim().length > 0
      : problemText.trim().length > 0;

  if (!isLoaded) return null;
  if (!isSignedIn) return <LandingPage />;

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
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0022.5 18.75V5.25A2.25 2.25 0 0020.25 3H3.75A2.25 2.25 0 001.5 5.25v13.5A2.25 2.25 0 003.75 21z" />
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
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L6.832 19.82a4.5 4.5 0 01-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 011.13-1.897L16.863 4.487zm0 0L19.5 7.125" />
          </svg>
          Type Text
        </button>
      </div>

      {/* Image mode */}
      {inputMode === "image" && (
        <>
          {/* Upload zone — always visible in image mode for re-upload */}
          {!ocrReady && !extracting && (
            <UploadZone
              onFileSelected={handleFileSelected}
              selectedFile={selectedFile}
              previewUrl={previewUrl}
            />
          )}

          {/* Extracting state */}
          {extracting && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-8 text-center">
              <div className="inline-flex items-center justify-center w-12 h-12 bg-indigo-50 rounded-full mb-3">
                <svg className="animate-spin w-6 h-6 text-indigo-500" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
              </div>
              <p className="text-gray-700 font-medium">Extracting text from image...</p>
              <p className="text-gray-500 text-sm mt-1">This may take a few seconds</p>
            </div>
          )}

          {/* Image panel + MathLive OCR editor */}
          {ocrReady && (
            <div className="space-y-4">
              {/* Image reference + MathLive editor */}
              {previewUrl && (
                <div className="space-y-3">
                  {/* Uploaded image — full width, larger display */}
                  <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={previewUrl}
                      alt="Uploaded problem"
                      className="w-full object-contain bg-gray-50"
                      style={{ maxHeight: "360px" }}
                    />
                    <div className="px-3 py-2 flex items-center justify-between border-t border-gray-100">
                      <span className="text-xs font-medium text-gray-500">Uploaded Image</span>
                      <button
                        onClick={() => {
                          setOcrReady(false);
                          setOcrText("");
                          setResult(null);
                        }}
                        className="text-xs font-medium text-indigo-600 hover:text-indigo-700 transition-colors"
                      >
                        Change
                      </button>
                    </div>
                  </div>

                  {/* MathLive editor — below image (unmount when result exists to remove keyboard container) */}
                  {!result && (
                    <div>
                      <div className="flex items-center justify-between mb-1.5">
                        <div className="flex items-center gap-1.5">
                          <span className="text-sm font-medium text-gray-700">Recognized Text</span>
                          <span className="text-xs text-gray-400 hidden sm:inline">(edit if needed)</span>
                        </div>
                        <button
                          onClick={handleRetryExtract}
                          className="text-xs font-medium text-gray-500 hover:text-gray-700 transition-colors"
                        >
                          Re-extract
                        </button>
                      </div>
                      <MathInput
                        value={ocrText}
                        onChange={(latex: string) => setOcrText(latex)}
                      />
                    </div>
                  )}
                </div>
              )}

              {/* Subject + Solve button */}
              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
                <div className="flex-1 w-full sm:w-auto">
                  <label htmlFor="subject-img" className="block text-sm font-medium text-gray-700 mb-1">
                    Subject (optional)
                  </label>
                  <select
                    id="subject-img"
                    value={subject}
                    onChange={(e) => setSubject(e.target.value)}
                    className="w-full sm:w-48 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
                  >
                    {subjects.map((s) => (
                      <option key={s.value} value={s.value}>{s.label}</option>
                    ))}
                  </select>
                </div>
                <button
                  onClick={handleSolve}
                  disabled={!canSolve || loading}
                  className="mt-auto px-6 py-2.5 bg-indigo-500 text-white rounded-lg font-medium text-sm hover:bg-indigo-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {solving ? (
                    <>
                      <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                      Solving...
                    </>
                  ) : (
                    <>
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
                      </svg>
                      Solve
                    </>
                  )}
                </button>
              </div>
            </div>
          )}
        </>
      )}

      {/* Text mode */}
      {inputMode === "text" && (
        <>
          {/* Reference images + MathLive editor */}
          <div className="space-y-3">
            {/* Reference image panels */}
            {refImages.length > 0 && (
              <div className="flex flex-wrap gap-3">
                {refImages.map((img, i) => (
                  <div
                    key={img.url}
                    className="relative group rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden w-28 md:w-44"
                  >
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={img.url}
                      alt={`Reference ${i + 1}`}
                      className="w-full h-24 md:h-32 object-contain bg-gray-50"
                    />
                    <button
                      onClick={() => handleRemoveRefImage(i)}
                      className="absolute top-1.5 right-1.5 w-6 h-6 bg-red-500 text-white rounded-full flex items-center justify-center text-xs opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      &times;
                    </button>
                    <div className="px-2 py-1 text-xs text-gray-500 truncate text-center">
                      {img.file.name}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Add image button */}
            <input
              ref={refImageInputRef}
              type="file"
              accept="image/*"
              multiple
              onChange={handleAddRefImages}
              className="hidden"
            />
            <button
              type="button"
              onClick={() => refImageInputRef.current?.click()}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0022.5 18.75V5.25A2.25 2.25 0 0020.25 3H3.75A2.25 2.25 0 001.5 5.25v13.5A2.25 2.25 0 003.75 21z" />
              </svg>
              Attach Reference Image
            </button>

            {/* MathLive editor — unmount when result exists to remove keyboard container */}
            {!result && (
              <MathInput
                value={problemText}
                onChange={(latex: string) => {
                  setProblemText(latex);
                  setResult(null);
                  setError(null);
                  setSaved(false);
                }}
              />
            )}
          </div>
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
            <div className="flex-1 w-full sm:w-auto">
              <label htmlFor="subject-text" className="block text-sm font-medium text-gray-700 mb-1">
                Subject (optional)
              </label>
              <select
                id="subject-text"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                className="w-full sm:w-48 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
              >
                {subjects.map((s) => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>
            </div>
            <button
              onClick={handleSolve}
              disabled={!canSolve || loading}
              className="mt-auto px-6 py-2.5 bg-indigo-500 text-white rounded-lg font-medium text-sm hover:bg-indigo-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {solving ? (
                <>
                  <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Solving...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
                  </svg>
                  Solve
                </>
              )}
            </button>
          </div>
        </>
      )}

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-center gap-3">
          <svg className="w-5 h-5 text-red-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
          </svg>
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Solving state */}
      {solving && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-12 text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-indigo-50 rounded-full mb-4">
            <svg className="animate-spin w-8 h-8 text-indigo-500" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
          </div>
          <p className="text-gray-700 font-medium">Analyzing your problem...</p>
          <p className="text-gray-500 text-sm mt-1">This may take a few seconds</p>
        </div>
      )}

      {/* Result + Conversation */}
      {result && (
        <>
          {/* Mobile: tab switcher */}
          <div className="flex border-b border-gray-200 lg:hidden">
            <button
              onClick={() => setResultTab("solution")}
              className={`flex-1 flex items-center justify-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                resultTab === "solution"
                  ? "border-indigo-500 text-indigo-600"
                  : "border-transparent text-gray-500 hover:text-gray-700"
              }`}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
              </svg>
              Solution
            </button>
            <button
              onClick={() => setResultTab("chat")}
              className={`flex-1 flex items-center justify-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                resultTab === "chat"
                  ? "border-indigo-500 text-indigo-600"
                  : "border-transparent text-gray-500 hover:text-gray-700"
              }`}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z" />
              </svg>
              Chat
              {messages.length > 0 && (
                <span className="ml-1 inline-flex items-center justify-center w-5 h-5 text-xs font-bold bg-indigo-100 text-indigo-600 rounded-full">
                  {messages.length}
                </span>
              )}
            </button>
          </div>

          {/* Two-column on desktop, tabbed on mobile */}
          <div className="lg:grid lg:grid-cols-[1fr_380px] lg:gap-6 lg:items-start">
            {/* Left: Solution */}
            <div className={`space-y-6 ${resultTab === "chat" ? "hidden lg:block" : ""}`}>
              <SolutionDisplay
                data={result}
                onSaveToMistakes={saved ? undefined : handleSaveToMistakes}
                isSaving={isSaving}
              />
              {saved && (
                <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 flex items-center gap-3">
                  <svg className="w-5 h-5 text-emerald-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                  </svg>
                  <p className="text-sm text-emerald-700">
                    Saved to your Mistake Book for review
                  </p>
                </div>
              )}
            </div>

            {/* Right: Conversation (sticky on desktop) */}
            <div className={`lg:sticky lg:top-4 ${resultTab === "solution" ? "hidden lg:block" : "mt-4 lg:mt-0"}`}>
              <ConversationThread
                scanId={result.scan_id}
                messages={messages}
                onNewMessage={(msg) => setMessages((prev) => [...prev, msg])}
              />
            </div>
          </div>
        </>
      )}
    </div>
  );
}
