"use client";

import { useEffect, useState, useCallback, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { getExamPapers, getQuestionsAdmin, type ExamPaper, type PracticeQuestion, type PaginatedResponse } from "@/lib/api";
import Pagination from "@/components/Pagination";

function QuestionsContent() {
  const searchParams = useSearchParams();
  const initialExamId = searchParams.get("exam_id") || "";

  const [allExams, setAllExams] = useState<ExamPaper[]>([]);
  const [levelFilter, setLevelFilter] = useState("");
  const [subjectFilter, setSubjectFilter] = useState("");
  const [selectedExam, setSelectedExam] = useState(initialExamId);
  const [typeFilter, setTypeFilter] = useState("");
  const [questionNumFilter, setQuestionNumFilter] = useState("");
  const [data, setData] = useState<PaginatedResponse<PracticeQuestion> | null>(null);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  // Load exam list
  useEffect(() => {
    getExamPapers({ limit: 100 }).then((r) => setAllExams(r.items)).catch(() => {});
  }, []);

  // Derive unique levels and subjects
  const levels = [...new Set(allExams.map((e) => e.level))].sort();
  const subjects = [...new Set(allExams.map((e) => e.subject))].sort();

  // Filter exams by level and subject
  const filteredExams = allExams.filter((e) => {
    if (levelFilter && e.level !== Number(levelFilter)) return false;
    if (subjectFilter && e.subject !== subjectFilter) return false;
    return true;
  });

  // Load questions
  const load = useCallback(async () => {
    if (!selectedExam) { setData(null); return; }
    setLoading(true);
    try {
      const res = await getQuestionsAdmin(selectedExam, {
        page,
        limit: 20,
        question_type: typeFilter || undefined,
        question_number: questionNumFilter || undefined,
      });
      setData(res);
    } catch { /* ignore */ }
    finally { setLoading(false); }
  }, [selectedExam, page, typeFilter, questionNumFilter]);

  useEffect(() => { load(); }, [load]);

  // image_url from API is like "/api/v1/exams/questions/1/image", so use origin only
  const apiBase = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1").replace(/\/api\/v1\/?$/, "");

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Question Bank</h1>

      {/* Filters row 1: Level, Subject, Exam */}
      <div className="flex flex-wrap gap-3">
        <select
          value={levelFilter}
          onChange={(e) => { setLevelFilter(e.target.value); setSelectedExam(""); setPage(1); }}
          className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-purple-500"
        >
          <option value="">All levels</option>
          {levels.map((l) => (
            <option key={l} value={l}>Level {l}</option>
          ))}
        </select>
        <select
          value={subjectFilter}
          onChange={(e) => { setSubjectFilter(e.target.value); setSelectedExam(""); setPage(1); }}
          className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-purple-500"
        >
          <option value="">All subjects</option>
          {subjects.map((s) => (
            <option key={s} value={s} className="capitalize">{s}</option>
          ))}
        </select>
        <select
          value={selectedExam}
          onChange={(e) => { setSelectedExam(e.target.value); setPage(1); }}
          className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-purple-500 min-w-[280px]"
        >
          <option value="">Select an exam paper ({filteredExams.length})...</option>
          {filteredExams.map((e) => (
            <option key={e.id} value={e.id}>
              L{e.level} {e.subject} — {e.title} ({e.year}) [{e.total_questions}q]
            </option>
          ))}
        </select>
      </div>

      {/* Filters row 2: Question type, Question number */}
      {selectedExam && (
        <div className="flex flex-wrap gap-3">
          <select
            value={typeFilter}
            onChange={(e) => { setTypeFilter(e.target.value); setPage(1); }}
            className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-purple-500"
          >
            <option value="">All types</option>
            <option value="numeric">Numeric</option>
            <option value="multichoice">Multiple choice</option>
            <option value="explanation">Explanation</option>
          </select>
          <select
            value={questionNumFilter}
            onChange={(e) => { setQuestionNumFilter(e.target.value); setPage(1); }}
            className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-purple-500"
          >
            <option value="">All questions</option>
            {["1", "2", "3", "4", "5"].map((n) => (
              <option key={n} value={n}>Question {n}</option>
            ))}
          </select>
        </div>
      )}

      {!selectedExam ? (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-12 text-center text-gray-400">
          Select an exam paper to view its questions
        </div>
      ) : loading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="bg-white rounded-xl border border-gray-100 shadow-sm p-5 h-24 animate-pulse" />
          ))}
        </div>
      ) : data?.items.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-12 text-center text-gray-400">
          No questions match the current filters
        </div>
      ) : (
        <div className="space-y-3">
          {data?.items.map((q) => (
            <QuestionCard
              key={q.id}
              question={q}
              apiBase={apiBase}
              expanded={expandedId === q.id}
              onToggle={() => setExpandedId(expandedId === q.id ? null : q.id)}
            />
          ))}
        </div>
      )}

      {data && (
        <Pagination page={data.page} pages={data.pages} total={data.total} limit={data.limit} label="questions" onPageChange={setPage} />
      )}
    </div>
  );
}

function QuestionCard({ question: q, apiBase, expanded, onToggle }: {
  question: PracticeQuestion;
  apiBase: string;
  expanded: boolean;
  onToggle: () => void;
}) {
  const typeColors: Record<string, string> = {
    numeric: "bg-blue-50 text-blue-700",
    multichoice: "bg-amber-50 text-amber-700",
    explanation: "bg-emerald-50 text-emerald-700",
  };

  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
      {/* Header — always visible */}
      <button onClick={onToggle} className="w-full px-5 py-4 flex items-center gap-4 text-left hover:bg-gray-50/50 transition-colors">
        <div className="flex items-center gap-2 min-w-[80px]">
          <span className="text-lg font-bold text-gray-900">Q{q.question_number}</span>
          <span className="text-lg text-gray-400">({q.sub_question})</span>
        </div>
        {q.question_type && (
          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${typeColors[q.question_type] || "bg-gray-50 text-gray-600"}`}>
            {q.question_type}
          </span>
        )}
        {q.marks && (
          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${q.marks === "H" ? "bg-purple-50 text-purple-700" : "bg-gray-100 text-gray-600"}`}>
            {q.marks === "H" ? "Holistic" : "Achieved"}
          </span>
        )}
        <p className="flex-1 text-sm text-gray-600 truncate">{q.question_text.slice(0, 100)}</p>
        <svg className={`w-5 h-5 text-gray-400 transition-transform ${expanded ? "rotate-180" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
        </svg>
      </button>

      {/* Body — expanded */}
      {expanded && (
        <div className="px-5 pb-5 border-t border-gray-100 pt-4 space-y-4">
          {/* Question image */}
          {q.has_image && q.image_url && (
            <div className="border border-gray-200 rounded-lg overflow-hidden bg-gray-50">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={`${apiBase}${q.image_url}`}
                alt={`Q${q.question_number}(${q.sub_question})`}
                className="max-w-full h-auto"
              />
            </div>
          )}

          {/* Question text */}
          <div>
            <h3 className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1">Question Text</h3>
            <p className="text-sm text-gray-800 whitespace-pre-wrap">{q.question_text}</p>
          </div>

          {/* Answer section */}
          <div className="bg-emerald-50/50 border border-emerald-100 rounded-lg p-4 space-y-2">
            <h3 className="text-xs font-medium text-emerald-700 uppercase tracking-wider">Answer</h3>
            {q.correct_answer ? (
              <>
                <p className="text-sm font-medium text-emerald-800">{q.correct_answer}</p>
                {q.accepted_answers && q.accepted_answers.length > 0 && (
                  <div>
                    <span className="text-xs text-emerald-600">Also accept: </span>
                    <span className="text-xs text-emerald-700">{q.accepted_answers.join(", ")}</span>
                  </div>
                )}
                {q.answer_explanation && (
                  <p className="text-xs text-emerald-700 mt-1">{q.answer_explanation}</p>
                )}
              </>
            ) : (
              <p className="text-sm text-gray-400 italic">No answer available — upload a marking schedule</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default function QuestionsPage() {
  return (
    <Suspense fallback={<div className="max-w-6xl mx-auto"><div className="h-8 bg-gray-200 rounded w-48 animate-pulse" /></div>}>
      <QuestionsContent />
    </Suspense>
  );
}
