"use client";

import { useState, useEffect, useCallback } from "react";
import { getPublicQuestions, submitPracticeAnswer } from "@/lib/api";
import { renderMathText } from "@/lib/renderMath";
import type { SubmitPracticeAnswerResponse } from "@/lib/types";

interface PublicQuestion {
  id: string;
  question_text: string;
  question_type: string | null;
  difficulty: string | null;
  knowledge_points: string[] | null;
  marks: string | null;
  usage_count: number;
  correct_rate: number | null;
}

export default function PracticePage() {
  const [questions, setQuestions] = useState<PublicQuestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [subject, setSubject] = useState("");
  const [difficulty, setDifficulty] = useState("");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [results, setResults] = useState<Record<string, SubmitPracticeAnswerResponse>>({});
  const [submitting, setSubmitting] = useState<Record<string, boolean>>({});
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  const loadQuestions = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string | number> = { page, limit: 20 };
      if (subject) params.subject = subject;
      if (difficulty) params.difficulty = difficulty;
      const res = await getPublicQuestions(params);
      setQuestions(res.items || []);
      setTotalPages(res.pages || 1);
    } catch {
      setQuestions([]);
    } finally {
      setLoading(false);
    }
  }, [subject, difficulty, page]);

  useEffect(() => {
    loadQuestions();
  }, [loadQuestions]);

  async function handleSubmit(questionId: string) {
    const ans = answers[questionId]?.trim();
    if (!ans) return;
    setSubmitting((s) => ({ ...s, [questionId]: true }));
    try {
      const res = await submitPracticeAnswer(questionId, ans);
      setResults((r) => ({ ...r, [questionId]: res }));
    } catch {
      // ignore
    } finally {
      setSubmitting((s) => ({ ...s, [questionId]: false }));
    }
  }

  const SUBJECTS = ["math", "physics", "chemistry", "biology", "english", "chinese"];
  const DIFFICULTIES = ["easy", "medium", "hard", "very_hard"];

  // renderMathText produces safe KaTeX HTML from LaTeX (trusted AI backend content)

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Practice Question Bank</h1>

      <div className="flex gap-3 mb-6 flex-wrap">
        <select
          value={subject}
          onChange={(e) => { setSubject(e.target.value); setPage(1); }}
          className="px-3 py-2 border border-gray-200 rounded-lg text-sm"
        >
          <option value="">All Subjects</option>
          {SUBJECTS.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <select
          value={difficulty}
          onChange={(e) => { setDifficulty(e.target.value); setPage(1); }}
          className="px-3 py-2 border border-gray-200 rounded-lg text-sm"
        >
          <option value="">All Difficulties</option>
          {DIFFICULTIES.map((d) => <option key={d} value={d}>{d}</option>)}
        </select>
      </div>

      {loading ? (
        <div className="space-y-4">
          {[0, 1, 2].map((i) => (
            <div key={i} className="bg-white rounded-xl p-6 border border-gray-100 animate-pulse">
              <div className="h-4 bg-gray-200 rounded w-1/3 mb-3" />
              <div className="h-3 bg-gray-200 rounded w-full mb-1" />
              <div className="h-3 bg-gray-200 rounded w-2/3" />
            </div>
          ))}
        </div>
      ) : questions.length === 0 ? (
        <p className="text-gray-500 text-center py-12">No public questions available yet.</p>
      ) : (
        <div className="space-y-4">
          {questions.map((q) => (
            <div key={q.id} className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
              <div className="flex items-center gap-2 mb-3 flex-wrap">
                {q.difficulty && (
                  <span className="px-2 py-0.5 rounded text-xs bg-gray-100 text-gray-600">{q.difficulty}</span>
                )}
                {q.marks && (
                  <span className="px-2 py-0.5 rounded text-xs bg-indigo-50 text-indigo-600">{q.marks} pts</span>
                )}
                {q.knowledge_points?.map((kp) => (
                  <span key={kp} className="px-2 py-0.5 rounded text-xs bg-blue-50 text-blue-600">{kp}</span>
                ))}
                {q.correct_rate != null && (
                  <span className="px-2 py-0.5 rounded text-xs bg-emerald-50 text-emerald-600">
                    {Math.round(q.correct_rate * 100)}% correct
                  </span>
                )}
              </div>

              <div
                className="text-sm text-gray-800 leading-relaxed mb-3"
                dangerouslySetInnerHTML={{ __html: renderMathText(q.question_text) }}
              />

              {!results[q.id] ? (
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={answers[q.id] || ""}
                    onChange={(e) => setAnswers((a) => ({ ...a, [q.id]: e.target.value }))}
                    onKeyDown={(e) => e.key === "Enter" && handleSubmit(q.id)}
                    placeholder="Your answer..."
                    className="flex-1 px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                  <button
                    onClick={() => handleSubmit(q.id)}
                    disabled={!answers[q.id]?.trim() || submitting[q.id]}
                    className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 disabled:opacity-50"
                  >
                    {submitting[q.id] ? "..." : "Submit"}
                  </button>
                </div>
              ) : (
                <div className={`p-3 rounded-lg ${results[q.id].is_correct ? "bg-emerald-50 border border-emerald-200" : "bg-red-50 border border-red-200"}`}>
                  <span className={`text-sm font-medium ${results[q.id].is_correct ? "text-emerald-700" : "text-red-700"}`}>
                    {results[q.id].is_correct ? "Correct!" : `Incorrect — Answer: ${results[q.id].correct_answer}`}
                  </span>
                  {results[q.id].answer_explanation && (
                    <div className="mt-2">
                      <button
                        onClick={() => setExpanded((e) => ({ ...e, [q.id]: !e[q.id] }))}
                        className="text-xs text-indigo-600 hover:text-indigo-800"
                      >
                        {expanded[q.id] ? "Hide" : "Explanation"}
                      </button>
                      {expanded[q.id] && (
                        <div
                          className="mt-1 text-sm text-gray-700"
                          dangerouslySetInnerHTML={{ __html: renderMathText(results[q.id].answer_explanation!) }}
                        />
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex justify-center gap-2 mt-6">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1 border rounded text-sm disabled:opacity-50"
          >
            Prev
          </button>
          <span className="px-3 py-1 text-sm text-gray-600">{page} / {totalPages}</span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-3 py-1 border rounded text-sm disabled:opacity-50"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
