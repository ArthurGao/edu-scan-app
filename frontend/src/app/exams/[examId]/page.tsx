"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { getExams, getExamQuestions, revealAnswer, explainQuestion } from "@/lib/api";
import {
  ExamPaper,
  PracticeQuestion,
  QuestionAnswer,
  PaginatedResponse,
} from "@/lib/types";
import Pagination from "@/components/Pagination";
import { renderRichText } from "@/lib/renderMath";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";

interface SubGroup {
  sub: string;
  items: PracticeQuestion[];
}

interface QuestionGroup {
  questionNumber: string;
  passages: PracticeQuestion[];
  subGroups: SubGroup[];
}

function groupQuestions(questions: PracticeQuestion[]): QuestionGroup[] {
  const map = new Map<
    string,
    { passages: PracticeQuestion[]; subMap: Map<string, PracticeQuestion[]> }
  >();

  for (const q of questions) {
    if (!map.has(q.question_number)) {
      map.set(q.question_number, { passages: [], subMap: new Map() });
    }
    const entry = map.get(q.question_number)!;

    if (q.sub_question.startsWith("passage-")) {
      entry.passages.push(q);
    } else {
      const existing = entry.subMap.get(q.sub_question) || [];
      existing.push(q);
      entry.subMap.set(q.sub_question, existing);
    }
  }

  return Array.from(map.entries()).map(([questionNumber, { passages, subMap }]) => ({
    questionNumber,
    passages,
    subGroups: Array.from(subMap.entries()).map(([sub, items]) => ({
      sub,
      items,
    })),
  }));
}

export default function ExamDetailPage() {
  const params = useParams();
  const examId = params.examId as string;

  const [exam, setExam] = useState<ExamPaper | null>(null);
  const [questions, setQuestions] = useState<PracticeQuestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [questionsLoading, setQuestionsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [questionPage, setQuestionPage] = useState(1);
  const [questionPages, setQuestionPages] = useState(1);
  const [totalQuestions, setTotalQuestions] = useState(0);
  const [revealedAnswers, setRevealedAnswers] = useState<
    Record<string, QuestionAnswer>
  >({});
  const [revealingId, setRevealingId] = useState<string | null>(null);
  const [studentAnswers, setStudentAnswers] = useState<Record<string, string>>(
    {}
  );
  // Self-assessment: "correct" | "incorrect" | undefined
  const [selfAssessment, setSelfAssessment] = useState<
    Record<string, "correct" | "incorrect">
  >({});
  // AI explanation
  const [aiExplanations, setAiExplanations] = useState<Record<string, string>>({});
  const [aiLoading, setAiLoading] = useState<string | null>(null);
  const [aiErrors, setAiErrors] = useState<Record<string, string>>({});

  const questionLimit = 50;

  // Fetch exam metadata
  useEffect(() => {
    async function fetchExam() {
      try {
        const data: PaginatedResponse<ExamPaper> = await getExams({
          page: 1,
          limit: 100,
        });
        const found = data.items.find((e) => String(e.id) === String(examId));
        if (found) setExam(found);
        else setError("Exam not found.");
      } catch {
        setError("Failed to load exam.");
      } finally {
        setLoading(false);
      }
    }
    fetchExam();
  }, [examId]);

  const fetchQuestions = useCallback(
    async (page: number) => {
      setQuestionsLoading(true);
      try {
        const data: PaginatedResponse<PracticeQuestion> =
          await getExamQuestions(examId, { page, limit: questionLimit });
        setQuestions(data.items);
        setTotalQuestions(data.total);
        setQuestionPages(data.pages);
      } catch {
        setError("Failed to load questions.");
      } finally {
        setQuestionsLoading(false);
      }
    },
    [examId]
  );

  useEffect(() => {
    if (examId) fetchQuestions(1);
  }, [examId, fetchQuestions]);

  const handleQuestionPageChange = (page: number) => {
    setQuestionPage(page);
    fetchQuestions(page);
  };

  const handleRevealAnswer = async (questionId: string) => {
    if (revealedAnswers[questionId]) return;
    setRevealingId(questionId);
    try {
      const answer: QuestionAnswer = await revealAnswer(examId, questionId);
      setRevealedAnswers((prev) => ({ ...prev, [questionId]: answer }));
    } catch {
      setError("Failed to reveal answer.");
    } finally {
      setRevealingId(null);
    }
  };

  const handleAskAI = async (q: PracticeQuestion) => {
    if (aiExplanations[q.id] || aiLoading === q.id) return;

    setAiLoading(q.id);
    setAiErrors((prev) => { const next = { ...prev }; delete next[q.id]; return next; });

    try {
      const result = await explainQuestion(examId, q.id);
      setAiExplanations((prev) => ({ ...prev, [q.id]: result.explanation }));
    } catch (err) {
      setAiErrors((prev) => ({
        ...prev,
        [q.id]: err instanceof Error ? err.message : "AI explanation failed",
      }));
    } finally {
      setAiLoading(null);
    }
  };

  if (loading) {
    return (
      <div className="space-y-4 pt-4 lg:pt-0">
        <div className="bg-gray-200 rounded h-8 w-2/3 animate-pulse" />
        <div className="bg-gray-200 rounded h-4 w-1/3 animate-pulse" />
        <div className="space-y-4 mt-6">
          {Array.from({ length: 3 }).map((_, i) => (
            <div
              key={i}
              className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 animate-pulse"
            >
              <div className="bg-gray-200 rounded h-4 w-1/4 mb-3" />
              <div className="bg-gray-200 rounded h-20 w-full" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (!exam) {
    return (
      <div className="pt-4 lg:pt-0">
        <Link
          href="/exams"
          className="flex items-center gap-1 text-sm text-indigo-600 hover:text-indigo-700 mb-3"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
          </svg>
          Back to exams
        </Link>
        <p className="text-gray-700">{error || "Exam not found."}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="pt-4 lg:pt-0">
        <Link
          href="/exams"
          className="flex items-center gap-1 text-sm text-indigo-600 hover:text-indigo-700 mb-3"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
          </svg>
          Back to exams
        </Link>
        <h1 className="text-2xl font-bold text-gray-900">{exam.title}</h1>
        <div className="flex items-center gap-3 mt-1">
          <span className="text-sm text-gray-500">
            {exam.year} &middot; Level {exam.level}
          </span>
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-700">
            {exam.subject}
          </span>
          <span className="text-sm text-gray-400">
            {exam.total_questions} questions
          </span>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Questions */}
      {questionsLoading ? (
        <div className="space-y-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div
              key={i}
              className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 animate-pulse"
            >
              <div className="bg-gray-200 rounded h-4 w-1/4 mb-3" />
              <div className="bg-gray-200 rounded h-20 w-full mb-3" />
              <div className="bg-gray-200 rounded h-8 w-32" />
            </div>
          ))}
        </div>
      ) : questions.length === 0 ? (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-12 text-center">
          <p className="text-gray-700 font-medium">No questions found</p>
          <p className="text-gray-500 text-sm mt-1">
            This exam has no parsed questions yet.
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          {groupQuestions(questions).map((group) => (
            <div
              key={group.questionNumber}
              className="bg-white rounded-xl shadow-sm border border-gray-100 p-6"
            >
              {/* Question number header */}
              <div className="flex items-center gap-2 mb-4">
                <span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-indigo-500 text-white text-sm font-bold">
                  {group.questionNumber}
                </span>
                <span className="text-sm font-semibold text-gray-700">
                  Question {group.questionNumber}
                </span>
              </div>

              {/* Passage/reading context images */}
              {group.passages.map((q) => (
                <div key={q.id} className="mb-4">
                  <img
                    src={`${API_BASE_URL}/exams/questions/${q.id}/image?v=3`}
                    alt={`Reading passage for Question ${group.questionNumber}`}
                    className="max-w-full h-auto rounded-lg border border-gray-200"
                    loading="lazy"
                  />
                </div>
              ))}

              {/* Sub-question groups */}
              <div className="space-y-5">
                {group.subGroups.map((sg) => (
                  <div key={sg.sub} className="border-l-2 border-gray-200 pl-4">
                    {/* Sub-question label */}
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-sm font-semibold text-gray-700">
                        ({sg.sub})
                      </span>
                      {sg.items[0]?.question_type && (
                        <span className="ml-auto text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-600">
                          {sg.items[0].question_type}
                        </span>
                      )}
                    </div>

                    {/* Show image ONCE for the sub-group (first item with image) */}
                    {sg.items[0]?.has_image && (
                      <div className="mb-3">
                        <img
                          src={`${API_BASE_URL}/exams/questions/${sg.items[0].id}/image?v=3`}
                          alt={`Question ${group.questionNumber}(${sg.sub})`}
                          className="max-w-full h-auto rounded-lg border border-gray-200"
                          loading="lazy"
                        />
                      </div>
                    )}

                    {/* Render each sub-sub-question within this sub-group */}
                    {sg.items.map((q, qIdx) => {
                    const revealed = revealedAnswers[q.id];
                    // For single-item sub-groups, don't repeat the sub label
                    const showSubLabel = sg.items.length > 1;
                    return (
                      <div
                        key={q.id}
                        className={sg.items.length > 1 ? "border-l border-indigo-200 pl-3 py-2" : ""}
                      >
                        {/* Show brief label for sub-sub-questions */}
                        {showSubLabel && q.question_text && (
                          <p className="text-gray-800 text-sm mb-2">
                            {q.question_text.length > 200
                              ? q.question_text.slice(0, 200) + "..."
                              : q.question_text}
                          </p>
                        )}

                        {/* For single-item groups without image already shown, show text */}
                        {!showSubLabel && !sg.items[0]?.has_image && q.question_text && (
                          <p className="text-gray-800 whitespace-pre-wrap mb-3 text-sm">
                            {q.question_text}
                          </p>
                        )}

                        {/* Before reveal: clickable options or text input */}
                        {!revealed && (
                          <div className="mb-3">
                            {q.options && q.options.length > 0 ? (
                              /* Clickable multichoice options */
                              <div className="space-y-2 mb-3">
                                {q.options.map((opt, idx) => {
                                  const selected =
                                    studentAnswers[q.id] === opt;
                                  return (
                                    <button
                                      key={idx}
                                      onClick={() =>
                                        setStudentAnswers((prev) => ({
                                          ...prev,
                                          [q.id]: opt,
                                        }))
                                      }
                                      className={`w-full text-left flex items-center gap-3 px-4 py-2.5 rounded-lg border text-sm transition-all ${
                                        selected
                                          ? "border-indigo-500 bg-indigo-50 text-indigo-900 ring-1 ring-indigo-500"
                                          : "border-gray-200 bg-white text-gray-700 hover:border-gray-300 hover:bg-gray-50"
                                      }`}
                                    >
                                      <span
                                        className={`flex-shrink-0 w-6 h-6 rounded-full border-2 flex items-center justify-center text-xs font-bold ${
                                          selected
                                            ? "border-indigo-500 bg-indigo-500 text-white"
                                            : "border-gray-300 text-gray-400"
                                        }`}
                                      >
                                        {String.fromCharCode(65 + idx)}
                                      </span>
                                      <span>{opt}</span>
                                    </button>
                                  );
                                })}
                                <button
                                  onClick={() => handleRevealAnswer(q.id)}
                                  disabled={
                                    revealingId === q.id ||
                                    !studentAnswers[q.id]
                                  }
                                  className="mt-2 px-4 py-2 text-xs font-medium rounded-lg bg-indigo-500 text-white hover:bg-indigo-600 transition-colors disabled:opacity-50"
                                >
                                  {revealingId === q.id
                                    ? "Checking..."
                                    : "Check Answer"}
                                </button>
                              </div>
                            ) : q.question_type === "numeric" ? (
                              /* Text input for numeric */
                              <div className="flex items-center gap-2">
                                <input
                                  type="text"
                                  value={studentAnswers[q.id] || ""}
                                  onChange={(e) =>
                                    setStudentAnswers((prev) => ({
                                      ...prev,
                                      [q.id]: e.target.value,
                                    }))
                                  }
                                  placeholder="Type your answer..."
                                  className="flex-1 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
                                />
                                <button
                                  onClick={() => handleRevealAnswer(q.id)}
                                  disabled={revealingId === q.id}
                                  className="px-4 py-2 text-xs font-medium rounded-lg bg-indigo-500 text-white hover:bg-indigo-600 transition-colors disabled:opacity-50 whitespace-nowrap"
                                >
                                  {revealingId === q.id
                                    ? "Checking..."
                                    : "Check Answer"}
                                </button>
                              </div>
                            ) : (
                              /* Fallback: show answer button */
                              <button
                                onClick={() => handleRevealAnswer(q.id)}
                                disabled={revealingId === q.id}
                                className="px-4 py-2 text-xs font-medium rounded-lg bg-indigo-500 text-white hover:bg-indigo-600 transition-colors disabled:opacity-50"
                              >
                                {revealingId === q.id
                                  ? "Revealing..."
                                  : "Show Answer"}
                              </button>
                            )}
                          </div>
                        )}

                        {/* After reveal: correct answer + self-assessment */}
                        {revealed && (() => {
                          const myAnswer = (studentAnswers[q.id] || "").trim().toLowerCase();
                          const correct = (revealed.correct_answer || "").trim().toLowerCase();
                          const accepted = (revealed.accepted_answers || []).map(a => a.trim().toLowerCase());
                          const hasOptions = q.options && q.options.length > 0;
                          const autoCorrect = myAnswer !== "" && (
                            myAnswer === correct ||
                            accepted.includes(myAnswer) ||
                            (hasOptions && revealed.correct_answer && myAnswer === revealed.correct_answer.trim().toLowerCase())
                          );
                          const canAutoCheck = myAnswer !== "" && (q.question_type === "numeric" || hasOptions);
                          const assessment = selfAssessment[q.id];

                          return (
                            <div className={`rounded-lg p-3 ${
                              (canAutoCheck && autoCorrect) || assessment === "correct"
                                ? "bg-emerald-50 border border-emerald-200"
                                : (canAutoCheck && !autoCorrect) || assessment === "incorrect"
                                ? "bg-red-50 border border-red-200"
                                : "bg-gray-50 border border-gray-200"
                            }`}>
                              {/* Auto-check result */}
                              {canAutoCheck && (
                                <div className="flex items-center gap-2 mb-2">
                                  {autoCorrect ? (
                                    <span className="inline-flex items-center gap-1 text-sm font-semibold text-emerald-700">
                                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2.5}>
                                        <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                                      </svg>
                                      Correct!
                                    </span>
                                  ) : (
                                    <span className="inline-flex items-center gap-1 text-sm font-semibold text-red-700">
                                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2.5}>
                                        <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                                      </svg>
                                      Incorrect
                                    </span>
                                  )}
                                  <span className="text-xs text-gray-500">
                                    Your answer: {studentAnswers[q.id]}
                                  </span>
                                </div>
                              )}

                              {/* Self-assessment result */}
                              {!canAutoCheck && assessment && (
                                <div className="flex items-center gap-2 mb-2">
                                  {assessment === "correct" ? (
                                    <span className="inline-flex items-center gap-1 text-sm font-semibold text-emerald-700">
                                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2.5}>
                                        <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                                      </svg>
                                      You got it right!
                                    </span>
                                  ) : (
                                    <span className="inline-flex items-center gap-1 text-sm font-semibold text-red-700">
                                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2.5}>
                                        <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                                      </svg>
                                      Review this one
                                    </span>
                                  )}
                                </div>
                              )}

                              {/* Correct answer (only show if available) */}
                              {revealed.correct_answer ? (
                                <>
                                  <p className="text-xs font-semibold text-gray-600 mb-1">
                                    Correct Answer
                                  </p>
                                  <p className="text-sm font-medium text-gray-900">
                                    {revealed.correct_answer}
                                  </p>
                                  {revealed.accepted_answers &&
                                    revealed.accepted_answers.length > 0 && (
                                      <p className="text-xs text-gray-500 mt-1">
                                        Also accepted:{" "}
                                        {revealed.accepted_answers.join(", ")}
                                      </p>
                                    )}
                                  {revealed.answer_explanation && (
                                    <p className="text-xs text-gray-600 mt-2">
                                      {revealed.answer_explanation}
                                    </p>
                                  )}
                                  {revealed.marks && (
                                    <p className="text-xs text-gray-500 mt-1">
                                      Marks: {revealed.marks}
                                    </p>
                                  )}

                                  {/* Self-assessment buttons */}
                                  {!canAutoCheck && !assessment && (
                                    <div className="flex items-center gap-2 mt-3 pt-3 border-t border-gray-200">
                                      <span className="text-xs text-gray-500">
                                        Did you get it right?
                                      </span>
                                      <button
                                        onClick={() =>
                                          setSelfAssessment((prev) => ({
                                            ...prev,
                                            [q.id]: "correct",
                                          }))
                                        }
                                        className="px-3 py-1 text-xs font-medium rounded-lg bg-emerald-100 text-emerald-700 hover:bg-emerald-200 transition-colors"
                                      >
                                        Yes
                                      </button>
                                      <button
                                        onClick={() =>
                                          setSelfAssessment((prev) => ({
                                            ...prev,
                                            [q.id]: "incorrect",
                                          }))
                                        }
                                        className="px-3 py-1 text-xs font-medium rounded-lg bg-red-100 text-red-700 hover:bg-red-200 transition-colors"
                                      >
                                        No
                                      </button>
                                    </div>
                                  )}
                                </>
                              ) : (
                                <p className="text-xs text-gray-400 italic">
                                  No marking schedule for this exam. Use &quot;Ask AI to Explain&quot; below for the solution.
                                </p>
                              )}
                            </div>
                          );
                        })()}

                        {/* Ask AI button and explanation */}
                        <div className="mt-3">
                          {!aiExplanations[q.id] && aiLoading !== q.id && (
                            <button
                              onClick={() => handleAskAI(q)}
                              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-gradient-to-r from-purple-500 to-indigo-500 text-white hover:from-purple-600 hover:to-indigo-600 transition-all"
                            >
                              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
                              </svg>
                              Ask AI to Explain
                            </button>
                          )}

                          {aiLoading === q.id && (
                            <div className="flex items-center gap-2 py-2 text-sm text-purple-600">
                              <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                              </svg>
                              AI is analyzing...
                            </div>
                          )}

                          {aiErrors[q.id] && (
                            <div className="bg-red-50 border border-red-200 rounded-lg p-2 text-xs text-red-700 mt-2">
                              {aiErrors[q.id]}
                            </div>
                          )}

                          {aiExplanations[q.id] && (
                            <div className="mt-3 border border-purple-200 rounded-xl overflow-hidden">
                              <div className="bg-purple-50 px-4 py-2 flex items-center gap-2 border-b border-purple-200">
                                <svg className="w-4 h-4 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                                  <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
                                </svg>
                                <span className="text-xs font-semibold text-purple-700">AI Explanation</span>
                              </div>
                              {/* AI-generated content rendered with math + markdown support.
                                  Content is from our own backend AI, non-math text is HTML-escaped by renderRichText. */}
                              <div
                                className="p-4 text-sm text-gray-700 leading-relaxed [&_strong]:font-semibold [&_strong]:text-gray-900 [&_ul]:my-2 [&_li]:mb-1"
                                dangerouslySetInnerHTML={{
                                  __html: renderRichText(aiExplanations[q.id]),
                                }}
                              />
                            </div>
                          )}
                        </div>
                      </div>
                    );
                    })}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {!questionsLoading && (
        <Pagination
          page={questionPage}
          pages={questionPages}
          total={totalQuestions}
          limit={questionLimit}
          label="questions"
          onPageChange={handleQuestionPageChange}
        />
      )}
    </div>
  );
}
