"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { getHistory, deleteHistoryItem } from "@/lib/api";
import { ScanRecord, PaginatedResponse } from "@/lib/types";

const subjectTabs = ["All", "Math", "Physics", "Chemistry", "Biology", "English", "Chinese"];

const subjectColors: Record<string, string> = {
  math: "bg-indigo-100 text-indigo-700",
  physics: "bg-blue-100 text-blue-700",
  chemistry: "bg-emerald-100 text-emerald-700",
  biology: "bg-orange-100 text-orange-700",
  english: "bg-rose-100 text-rose-700",
  chinese: "bg-amber-100 text-amber-700",
};

function formatDate(dateStr: string) {
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function HistoryPage() {
  const router = useRouter();
  const [records, setRecords] = useState<ScanRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [activeTab, setActiveTab] = useState("All");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const limit = 12;

  const fetchHistory = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: { subject?: string; page: number; limit: number } = {
        page,
        limit,
      };
      if (activeTab !== "All") {
        params.subject = activeTab.toLowerCase();
      }
      const data: PaginatedResponse<ScanRecord> = await getHistory(params);
      setRecords(data.items);
      setTotal(data.total);
      setPages(data.pages);
    } catch {
      setError("Failed to load history. Make sure the backend is running.");
    } finally {
      setLoading(false);
    }
  }, [page, activeTab]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const handleDelete = async (scanId: string) => {
    try {
      await deleteHistoryItem(scanId);
      setRecords((prev) => prev.filter((r) => r.id !== scanId));
      setTotal((prev) => prev - 1);
    } catch {
      setError("Failed to delete item.");
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
        <h1 className="text-2xl font-bold text-gray-900">History</h1>
        <p className="text-gray-500 mt-1">
          Browse your previously solved problems
        </p>
      </div>

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
              className="bg-white rounded-xl shadow-sm border border-gray-100 p-4 animate-pulse"
            >
              <div className="bg-gray-200 rounded-lg h-32 mb-3" />
              <div className="bg-gray-200 rounded h-4 w-3/4 mb-2" />
              <div className="bg-gray-200 rounded h-3 w-1/2" />
            </div>
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && records.length === 0 && (
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
                d="M12 6v6l4 2m6-2a10 10 0 11-20 0 10 10 0 0120 0z"
              />
            </svg>
          </div>
          <p className="text-gray-700 font-medium">No history yet</p>
          <p className="text-gray-500 text-sm mt-1">
            Upload and solve a problem to see it here
          </p>
        </div>
      )}

      {/* Records grid */}
      {!loading && records.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {records.map((record) => (
            <div
              key={record.id}
              onClick={() => router.push(`/history/${record.id}`)}
              className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden hover:shadow-md transition-shadow group cursor-pointer"
            >
              {/* Image / Placeholder */}
              <div className="h-36 bg-gray-100 relative overflow-hidden">
                {record.image_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={record.image_url}
                    alt="Problem"
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <svg
                      className="w-10 h-10 text-gray-300"
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
                {/* Delete button */}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDelete(record.id);
                  }}
                  className="absolute top-2 right-2 bg-white/90 text-gray-500 hover:text-red-500 rounded-full p-1.5 opacity-0 group-hover:opacity-100 transition-opacity shadow-sm"
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

              {/* Content */}
              <div className="p-4">
                {record.ocr_text && (
                  <p className="text-sm text-gray-800 line-clamp-2 mb-2">
                    {record.ocr_text}
                  </p>
                )}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {record.subject && (
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                          subjectColors[record.subject.toLowerCase()] ||
                          "bg-gray-100 text-gray-700"
                        }`}
                      >
                        {record.subject}
                      </span>
                    )}
                    {record.difficulty && (
                      <span className="text-xs text-gray-400">
                        {record.difficulty}
                      </span>
                    )}
                  </div>
                  <span className="text-xs text-gray-400">
                    {formatDate(record.created_at)}
                  </span>
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
            Showing {(page - 1) * limit + 1}-
            {Math.min(page * limit, total)} of {total} results
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-3 py-1.5 rounded-lg text-sm border border-gray-200 text-gray-600 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            {Array.from({ length: Math.min(pages, 5) }, (_, i) => {
              const pageNum = i + 1;
              return (
                <button
                  key={pageNum}
                  onClick={() => setPage(pageNum)}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium ${
                    page === pageNum
                      ? "bg-indigo-500 text-white"
                      : "border border-gray-200 text-gray-600 hover:bg-gray-50"
                  }`}
                >
                  {pageNum}
                </button>
              );
            })}
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
