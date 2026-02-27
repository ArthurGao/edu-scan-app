"use client";

import { useEffect, useState, useCallback } from "react";
import { getMistakes, updateMistake, deleteMistake } from "@/lib/api";
import { MistakeRecord, PaginatedResponse } from "@/lib/types";

const filterTabs = ["All", "Unmastered", "Mastered"];

function formatDate(dateStr: string) {
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

const subjectColors: Record<string, string> = {
  math: "bg-indigo-100 text-indigo-700",
  physics: "bg-blue-100 text-blue-700",
  chemistry: "bg-emerald-100 text-emerald-700",
};

export default function MistakesPage() {
  const [mistakes, setMistakes] = useState<MistakeRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [activeTab, setActiveTab] = useState("All");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingNotes, setEditingNotes] = useState<string | null>(null);
  const [notesText, setNotesText] = useState("");
  const limit = 10;

  const fetchMistakes = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: {
        mastered?: boolean;
        page: number;
        limit: number;
      } = { page, limit };
      if (activeTab === "Mastered") params.mastered = true;
      if (activeTab === "Unmastered") params.mastered = false;
      const data: PaginatedResponse<MistakeRecord> =
        await getMistakes(params);
      setMistakes(data.items);
      setTotal(data.total);
      setPages(data.pages);
    } catch {
      setError(
        "Failed to load mistake book. Make sure the backend is running."
      );
    } finally {
      setLoading(false);
    }
  }, [page, activeTab]);

  useEffect(() => {
    fetchMistakes();
  }, [fetchMistakes]);

  const handleToggleMastered = async (mistake: MistakeRecord) => {
    try {
      await updateMistake(mistake.id, { mastered: !mistake.mastered });
      setMistakes((prev) =>
        prev.map((m) =>
          m.id === mistake.id ? { ...m, mastered: !m.mastered } : m
        )
      );
    } catch {
      setError("Failed to update status.");
    }
  };

  const handleSaveNotes = async (id: string) => {
    try {
      await updateMistake(id, { notes: notesText });
      setMistakes((prev) =>
        prev.map((m) => (m.id === id ? { ...m, notes: notesText } : m))
      );
      setEditingNotes(null);
    } catch {
      setError("Failed to save notes.");
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteMistake(id);
      setMistakes((prev) => prev.filter((m) => m.id !== id));
      setTotal((prev) => prev - 1);
    } catch {
      setError("Failed to delete mistake.");
    }
  };

  const handleTabChange = (tab: string) => {
    setActiveTab(tab);
    setPage(1);
  };

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="pt-4 lg:pt-0">
        <h1 className="text-2xl font-bold text-gray-900">Mistake Book</h1>
        <p className="text-gray-500 mt-1">
          Review and track your problem areas for improvement
        </p>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-2">
        {filterTabs.map((tab) => (
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
            {total} items
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
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div
              key={i}
              className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 animate-pulse"
            >
              <div className="flex gap-4">
                <div className="bg-gray-200 rounded-lg w-24 h-24 flex-shrink-0" />
                <div className="flex-1">
                  <div className="bg-gray-200 rounded h-4 w-3/4 mb-2" />
                  <div className="bg-gray-200 rounded h-3 w-1/2 mb-4" />
                  <div className="bg-gray-200 rounded h-3 w-full" />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && mistakes.length === 0 && (
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
                d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25"
              />
            </svg>
          </div>
          <p className="text-gray-700 font-medium">No mistakes saved yet</p>
          <p className="text-gray-500 text-sm mt-1">
            Save problems from the solution page to review later
          </p>
        </div>
      )}

      {/* Mistake cards */}
      {!loading && mistakes.length > 0 && (
        <div className="space-y-4">
          {mistakes.map((mistake) => (
            <div
              key={mistake.id}
              className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 hover:shadow-md transition-shadow"
            >
              <div className="flex gap-4">
                {/* Thumbnail */}
                <div className="w-24 h-24 bg-gray-100 rounded-lg flex-shrink-0 overflow-hidden">
                  {mistake.scan_record.image_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={mistake.scan_record.image_url}
                      alt="Problem"
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center">
                      <svg
                        className="w-8 h-8 text-gray-300"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                        strokeWidth={1.5}
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0022.5 18.75V5.25A2.25 2.25 0 0020.25 3H3.75A2.25 2.25 0 001.5 5.25v13.5A2.25 2.25 0 003.75 21z"
                        />
                      </svg>
                    </div>
                  )}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      {mistake.scan_record.ocr_text && (
                        <p className="text-sm font-medium text-gray-800 line-clamp-2">
                          {mistake.scan_record.ocr_text}
                        </p>
                      )}
                      <div className="flex items-center gap-2 mt-1.5">
                        {mistake.scan_record.subject && (
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                              subjectColors[
                                mistake.scan_record.subject.toLowerCase()
                              ] || "bg-gray-100 text-gray-700"
                            }`}
                          >
                            {mistake.scan_record.subject}
                          </span>
                        )}
                        <span className="text-xs text-gray-400">
                          Reviewed {mistake.review_count} times
                        </span>
                        <span className="text-xs text-gray-400">
                          {formatDate(mistake.created_at)}
                        </span>
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2 flex-shrink-0">
                      {/* Mastered toggle */}
                      <button
                        onClick={() => handleToggleMastered(mistake)}
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                          mistake.mastered
                            ? "bg-emerald-100 text-emerald-700 hover:bg-emerald-200"
                            : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                        }`}
                      >
                        <svg
                          className="w-3.5 h-3.5"
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
                        {mistake.mastered ? "Mastered" : "Not Mastered"}
                      </button>
                      {/* Delete */}
                      <button
                        onClick={() => handleDelete(mistake.id)}
                        className="p-1.5 text-gray-400 hover:text-red-500 rounded-lg hover:bg-red-50 transition-colors"
                        title="Delete"
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
                            d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0"
                          />
                        </svg>
                      </button>
                    </div>
                  </div>

                  {/* Notes section */}
                  <div className="mt-3">
                    {editingNotes === mistake.id ? (
                      <div className="flex gap-2">
                        <textarea
                          value={notesText}
                          onChange={(e) => setNotesText(e.target.value)}
                          className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-700 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none resize-none"
                          rows={2}
                          placeholder="Add your notes..."
                        />
                        <div className="flex flex-col gap-1">
                          <button
                            onClick={() => handleSaveNotes(mistake.id)}
                            className="px-3 py-1.5 bg-indigo-500 text-white rounded-lg text-xs font-medium hover:bg-indigo-600"
                          >
                            Save
                          </button>
                          <button
                            onClick={() => setEditingNotes(null)}
                            className="px-3 py-1.5 bg-gray-100 text-gray-600 rounded-lg text-xs font-medium hover:bg-gray-200"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : (
                      <button
                        onClick={() => {
                          setEditingNotes(mistake.id);
                          setNotesText(mistake.notes || "");
                        }}
                        className="text-sm text-gray-500 hover:text-indigo-500 transition-colors"
                      >
                        {mistake.notes ? (
                          <span className="italic">&quot;{mistake.notes}&quot;</span>
                        ) : (
                          <span className="flex items-center gap-1">
                            <svg
                              className="w-3.5 h-3.5"
                              fill="none"
                              stroke="currentColor"
                              viewBox="0 0 24 24"
                              strokeWidth={2}
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10"
                              />
                            </svg>
                            Add notes
                          </span>
                        )}
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {!loading && pages > 1 && (
        <div className="flex items-center justify-between bg-white rounded-xl shadow-sm border border-gray-100 px-6 py-3">
          <p className="text-sm text-gray-500">
            Page {page} of {pages} ({total} total)
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-3 py-1.5 rounded-lg text-sm border border-gray-200 text-gray-600 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            <button
              onClick={() => setPage((p) => Math.min(pages, p + 1))}
              disabled={page === pages}
              className="px-3 py-1.5 rounded-lg text-sm border border-gray-200 text-gray-600 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
