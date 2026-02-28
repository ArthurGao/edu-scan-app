"use client";

interface PaginationProps {
  page: number;
  pages: number;
  total: number;
  limit: number;
  label?: string;
  onPageChange: (page: number) => void;
}

export default function Pagination({
  page,
  pages,
  total,
  limit,
  label = "results",
  onPageChange,
}: PaginationProps) {
  if (pages <= 1) return null;

  // Build page numbers with sliding window
  const getPageNumbers = (): (number | "...")[] => {
    const maxVisible = 5;
    if (pages <= maxVisible) {
      return Array.from({ length: pages }, (_, i) => i + 1);
    }

    const nums: (number | "...")[] = [];
    // Always show first page
    nums.push(1);

    let start = Math.max(2, page - 1);
    let end = Math.min(pages - 1, page + 1);

    // Adjust window to always show 3 middle pages when possible
    if (page <= 3) {
      start = 2;
      end = 4;
    } else if (page >= pages - 2) {
      start = pages - 3;
      end = pages - 1;
    }

    if (start > 2) nums.push("...");
    for (let i = start; i <= end; i++) {
      nums.push(i);
    }
    if (end < pages - 1) nums.push("...");

    // Always show last page
    nums.push(pages);
    return nums;
  };

  const from = (page - 1) * limit + 1;
  const to = Math.min(page * limit, total);

  return (
    <div className="flex items-center justify-between bg-white rounded-xl shadow-sm border border-gray-100 px-6 py-3">
      <p className="text-sm text-gray-500">
        Showing {from}-{to} of {total} {label}
      </p>
      <div className="flex gap-1.5">
        <button
          onClick={() => onPageChange(page - 1)}
          disabled={page === 1}
          className="px-3 py-1.5 rounded-lg text-sm border border-gray-200 text-gray-600 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Previous
        </button>
        {getPageNumbers().map((num, idx) =>
          num === "..." ? (
            <span
              key={`ellipsis-${idx}`}
              className="px-2 py-1.5 text-sm text-gray-400"
            >
              ...
            </span>
          ) : (
            <button
              key={num}
              onClick={() => onPageChange(num)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium ${
                page === num
                  ? "bg-indigo-500 text-white"
                  : "border border-gray-200 text-gray-600 hover:bg-gray-50"
              }`}
            >
              {num}
            </button>
          )
        )}
        <button
          onClick={() => onPageChange(page + 1)}
          disabled={page === pages}
          className="px-3 py-1.5 rounded-lg text-sm border border-gray-200 text-gray-600 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Next
        </button>
      </div>
    </div>
  );
}
