"use client";

interface PaginationProps {
  page: number;
  pages: number;
  total: number;
  limit: number;
  label?: string;
  onPageChange: (page: number) => void;
}

export default function Pagination({ page, pages, total, limit, label = "results", onPageChange }: PaginationProps) {
  if (pages <= 1) return null;

  const getPageNumbers = (): (number | "...")[] => {
    if (pages <= 5) return Array.from({ length: pages }, (_, i) => i + 1);
    const nums: (number | "...")[] = [1];
    let start = Math.max(2, page - 1);
    let end = Math.min(pages - 1, page + 1);
    if (page <= 3) { start = 2; end = 4; }
    else if (page >= pages - 2) { start = pages - 3; end = pages - 1; }
    if (start > 2) nums.push("...");
    for (let i = start; i <= end; i++) nums.push(i);
    if (end < pages - 1) nums.push("...");
    nums.push(pages);
    return nums;
  };

  const from = (page - 1) * limit + 1;
  const to = Math.min(page * limit, total);

  return (
    <div className="flex items-center justify-between px-4 py-3">
      <p className="text-sm text-gray-500">
        {from}-{to} of {total} {label}
      </p>
      <div className="flex gap-1">
        <button onClick={() => onPageChange(page - 1)} disabled={page === 1}
          className="px-2.5 py-1 rounded text-sm border border-gray-200 text-gray-600 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed">
          Prev
        </button>
        {getPageNumbers().map((num, idx) =>
          num === "..." ? (
            <span key={`e-${idx}`} className="px-2 py-1 text-sm text-gray-400">...</span>
          ) : (
            <button key={num} onClick={() => onPageChange(num)}
              className={`px-2.5 py-1 rounded text-sm font-medium ${page === num ? "bg-purple-500 text-white" : "border border-gray-200 text-gray-600 hover:bg-gray-50"}`}>
              {num}
            </button>
          )
        )}
        <button onClick={() => onPageChange(page + 1)} disabled={page === pages}
          className="px-2.5 py-1 rounded text-sm border border-gray-200 text-gray-600 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed">
          Next
        </button>
      </div>
    </div>
  );
}
