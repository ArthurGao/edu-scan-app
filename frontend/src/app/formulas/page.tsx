"use client";

import { useEffect, useState, useCallback } from "react";
import katex from "katex";
import { getFormulas, getFormula } from "@/lib/api";
import { Formula, FormulaDetail, PaginatedResponse } from "@/lib/types";
import Pagination from "@/components/Pagination";

const subjectTabs = ["All", "Math", "Physics", "Chemistry", "Biology", "English", "Chinese"];

const subjectColors: Record<string, string> = {
  math: "bg-indigo-100 text-indigo-700",
  physics: "bg-blue-100 text-blue-700",
  chemistry: "bg-emerald-100 text-emerald-700",
  biology: "bg-orange-100 text-orange-700",
  english: "bg-rose-100 text-rose-700",
  chinese: "bg-amber-100 text-amber-700",
};

function renderLatex(latex: string): string {
  try {
    return katex.renderToString(latex, {
      throwOnError: false,
      displayMode: true,
    });
  } catch {
    return latex;
  }
}

export default function FormulasPage() {
  const [formulas, setFormulas] = useState<Formula[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [activeTab, setActiveTab] = useState("All");
  const [keyword, setKeyword] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedFormula, setExpandedFormula] = useState<FormulaDetail | null>(
    null
  );
  const [expandLoading, setExpandLoading] = useState(false);
  const limit = 12;

  const fetchFormulas = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: {
        subject?: string;
        keyword?: string;
        page: number;
        limit: number;
      } = { page, limit };
      if (activeTab !== "All") {
        params.subject = activeTab.toLowerCase();
      }
      if (keyword) {
        params.keyword = keyword;
      }
      const data: PaginatedResponse<Formula> = await getFormulas(params);
      setFormulas(data.items);
      setTotal(data.total);
      setPages(data.pages);
    } catch {
      setError(
        "Failed to load formulas. Make sure the backend is running."
      );
    } finally {
      setLoading(false);
    }
  }, [page, activeTab, keyword]);

  useEffect(() => {
    fetchFormulas();
  }, [fetchFormulas]);

  const handleTabChange = (tab: string) => {
    setActiveTab(tab);
    setPage(1);
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setKeyword(searchInput);
    setPage(1);
  };

  const handleExpandFormula = async (id: string) => {
    if (expandedFormula?.id === id) {
      setExpandedFormula(null);
      return;
    }
    setExpandLoading(true);
    try {
      const detail: FormulaDetail = await getFormula(id);
      setExpandedFormula(detail);
    } catch {
      setError("Failed to load formula details.");
    } finally {
      setExpandLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="pt-4 lg:pt-0">
        <h1 className="text-2xl font-bold text-gray-900">Formula Library</h1>
        <p className="text-gray-500 mt-1">
          Browse and search formulas across subjects
        </p>
      </div>

      {/* Search bar */}
      <form onSubmit={handleSearch} className="flex gap-2">
        <div className="relative flex-1">
          <svg
            className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z"
            />
          </svg>
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search formulas by name or keyword..."
            className="w-full rounded-lg border border-gray-300 bg-white pl-10 pr-4 py-2.5 text-sm text-gray-900 placeholder-gray-400 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
          />
        </div>
        <button
          type="submit"
          className="px-5 py-2.5 bg-indigo-500 text-white rounded-lg text-sm font-medium hover:bg-indigo-600 transition-colors"
        >
          Search
        </button>
      </form>

      {/* Subject tabs */}
      <div className="flex gap-2">
        {subjectTabs.map((tab) => (
          <button
            key={tab}
            onClick={() => handleTabChange(tab)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeTab === tab
                ? "bg-indigo-500 text-white"
                : "bg-white text-gray-600 border border-gray-200 hover:bg-gray-50"
            }`}
          >
            {tab}
          </button>
        ))}
        {!loading && (
          <span className="ml-auto flex items-center text-sm text-gray-400">
            {total} formulas
          </span>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 animate-pulse"
            >
              <div className="bg-gray-200 rounded h-4 w-2/3 mb-3" />
              <div className="bg-gray-200 rounded h-10 w-full mb-3" />
              <div className="bg-gray-200 rounded h-3 w-1/3" />
            </div>
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && formulas.length === 0 && (
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
                d="M4.745 3A23.933 23.933 0 003 12c0 3.183.62 6.22 1.745 9M19.5 3c.967 2.78 1.5 5.817 1.5 9s-.533 6.22-1.5 9M8.25 8.885l1.444-.89a.75.75 0 011.105.402l2.402 7.206a.75.75 0 001.104.401l1.445-.889"
              />
            </svg>
          </div>
          <p className="text-gray-700 font-medium">No formulas found</p>
          <p className="text-gray-500 text-sm mt-1">
            {keyword
              ? "Try a different search term"
              : "Formulas will appear here once available"}
          </p>
        </div>
      )}

      {/* Formula grid */}
      {!loading && formulas.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {formulas.map((formula) => (
            <div key={formula.id}>
              <button
                onClick={() => handleExpandFormula(formula.id)}
                className={`w-full text-left bg-white rounded-xl shadow-sm border transition-all hover:shadow-md ${
                  expandedFormula?.id === formula.id
                    ? "border-indigo-300 ring-1 ring-indigo-200"
                    : "border-gray-100"
                }`}
              >
                <div className="p-5">
                  {/* Name and subject */}
                  <div className="flex items-start justify-between gap-2 mb-3">
                    <h3 className="text-sm font-semibold text-gray-900 line-clamp-1">
                      {formula.name}
                    </h3>
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium flex-shrink-0 ${
                        subjectColors[formula.subject.toLowerCase()] ||
                        "bg-gray-100 text-gray-700"
                      }`}
                    >
                      {formula.subject}
                    </span>
                  </div>

                  {/* LaTeX formula */}
                  <div
                    className="bg-gray-50 rounded-lg p-3 mb-3 overflow-x-auto katex-container"
                    dangerouslySetInnerHTML={{
                      __html: renderLatex(formula.latex),
                    }}
                  />

                  {/* Description */}
                  {formula.description && (
                    <p className="text-xs text-gray-500 line-clamp-2">
                      {formula.description}
                    </p>
                  )}

                  {/* Grade levels */}
                  {formula.grade_levels && formula.grade_levels.length > 0 && (
                    <div className="flex gap-1 mt-2 flex-wrap">
                      {formula.grade_levels.map((grade) => (
                        <span
                          key={grade}
                          className="text-xs text-gray-400 bg-gray-100 rounded px-1.5 py-0.5"
                        >
                          {grade}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </button>

              {/* Expanded detail */}
              {expandedFormula?.id === formula.id && (
                <div className="mt-2 bg-indigo-50 rounded-xl border border-indigo-200 p-5 space-y-3">
                  {expandLoading ? (
                    <div className="text-center py-4">
                      <svg
                        className="animate-spin w-6 h-6 text-indigo-500 mx-auto"
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
                  ) : (
                    <>
                      {/* Keywords */}
                      {expandedFormula.keywords &&
                        expandedFormula.keywords.length > 0 && (
                          <div>
                            <p className="text-xs font-semibold text-indigo-700 mb-1">
                              Keywords
                            </p>
                            <div className="flex flex-wrap gap-1">
                              {expandedFormula.keywords.map((kw) => (
                                <span
                                  key={kw}
                                  className="text-xs bg-white text-indigo-600 rounded-full px-2 py-0.5 border border-indigo-200"
                                >
                                  {kw}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                      {/* Related formulas */}
                      {expandedFormula.related_formulas &&
                        expandedFormula.related_formulas.length > 0 && (
                          <div>
                            <p className="text-xs font-semibold text-indigo-700 mb-1">
                              Related Formulas
                            </p>
                            <div className="space-y-2">
                              {expandedFormula.related_formulas.map((rf) => (
                                <div
                                  key={rf.id}
                                  className="bg-white rounded-lg p-3 border border-indigo-100"
                                >
                                  <p className="text-xs font-medium text-gray-800">
                                    {rf.name}
                                  </p>
                                  <div
                                    className="mt-1 katex-container text-sm"
                                    dangerouslySetInnerHTML={{
                                      __html: renderLatex(rf.latex),
                                    }}
                                  />
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                      {/* Full description */}
                      {expandedFormula.description && (
                        <div>
                          <p className="text-xs font-semibold text-indigo-700 mb-1">
                            Description
                          </p>
                          <p className="text-xs text-gray-600">
                            {expandedFormula.description}
                          </p>
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {!loading && (
        <Pagination
          page={page}
          pages={pages}
          total={total}
          limit={limit}
          label="formulas"
          onPageChange={setPage}
        />
      )}
    </div>
  );
}
