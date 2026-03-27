"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { getExams } from "@/lib/api";
import { ExamPaper, PaginatedResponse } from "@/lib/types";
import Pagination from "@/components/Pagination";

const levelTabs = [
  { label: "All Levels", value: undefined },
  { label: "Level 1", value: 1 },
  { label: "Level 2", value: 2 },
  { label: "Level 3", value: 3 },
];

export default function ExamsPage() {
  const [exams, setExams] = useState<ExamPaper[]>([]);
  const [totalExams, setTotalExams] = useState(0);
  const [examPage, setExamPage] = useState(1);
  const [examPages, setExamPages] = useState(1);
  const [activeLevel, setActiveLevel] = useState<number | undefined>(undefined);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const examLimit = 12;

  const fetchExams = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: { level?: number; page: number; limit: number } = {
        page: examPage,
        limit: examLimit,
      };
      if (activeLevel !== undefined) params.level = activeLevel;
      const data: PaginatedResponse<ExamPaper> = await getExams(params);
      setExams(data.items);
      setTotalExams(data.total);
      setExamPages(data.pages);
    } catch {
      setError("Failed to load exams. Make sure the backend is running.");
    } finally {
      setLoading(false);
    }
  }, [examPage, activeLevel]);

  useEffect(() => {
    fetchExams();
  }, [fetchExams]);

  const handleLevelChange = (level: number | undefined) => {
    setActiveLevel(level);
    setExamPage(1);
  };

  return (
    <div className="space-y-6">
      <div className="pt-4 lg:pt-0">
        <h1 className="text-2xl font-bold text-gray-900">Exam Practice</h1>
        <p className="text-gray-500 mt-1">
          Browse exam papers and practice questions
        </p>
      </div>

      <div className="flex gap-2 flex-wrap">
        {levelTabs.map((tab) => (
          <button
            key={tab.label}
            onClick={() => handleLevelChange(tab.value)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeLevel === tab.value
                ? "bg-indigo-500 text-white"
                : "bg-white text-gray-600 border border-gray-200 hover:bg-gray-50"
            }`}
          >
            {tab.label}
          </button>
        ))}
        {!loading && (
          <span className="ml-auto flex items-center text-sm text-gray-400">
            {totalExams} exams
          </span>
        )}
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {loading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 animate-pulse"
            >
              <div className="bg-gray-200 rounded h-4 w-3/4 mb-3" />
              <div className="bg-gray-200 rounded h-3 w-1/2 mb-2" />
              <div className="bg-gray-200 rounded h-3 w-1/3" />
            </div>
          ))}
        </div>
      )}

      {!loading && exams.length === 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-12 text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gray-100 rounded-full mb-4">
            <svg
              className="w-8 h-8 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
              />
            </svg>
          </div>
          <p className="text-gray-700 font-medium">No exams available</p>
          <p className="text-gray-500 text-sm mt-1">
            Exam papers will appear here once imported by an admin.
          </p>
        </div>
      )}

      {!loading && exams.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {exams.map((exam) => (
            <Link
              key={exam.id}
              href={`/exams/${exam.id}`}
              className="w-full text-left bg-white rounded-xl shadow-sm border border-gray-100 p-5 hover:shadow-md hover:border-indigo-200 transition-all"
            >
              <h3 className="text-sm font-semibold text-gray-900 line-clamp-2 mb-2">
                {exam.title}
              </h3>
              <div className="flex items-center gap-2 mb-3">
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-700">
                  {exam.subject}
                </span>
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
                  Level {exam.level}
                </span>
              </div>
              <div className="flex items-center justify-between text-xs text-gray-500">
                <span>{exam.year}</span>
                <span>{exam.total_questions} questions</span>
              </div>
            </Link>
          ))}
        </div>
      )}

      {!loading && (
        <Pagination
          page={examPage}
          pages={examPages}
          total={totalExams}
          limit={examLimit}
          label="exams"
          onPageChange={setExamPage}
        />
      )}
    </div>
  );
}
