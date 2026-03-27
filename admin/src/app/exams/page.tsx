"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import Link from "next/link";
import {
  getExamPapers, uploadExamPdf, crawlExams, deleteExamPaper, uploadSchedule,
  type ExamPaper, type PaginatedResponse, type CrawlResponse,
} from "@/lib/api";
import Pagination from "@/components/Pagination";

export default function ExamsPage() {
  const [data, setData] = useState<PaginatedResponse<ExamPaper> | null>(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [yearFilter, setYearFilter] = useState("");
  const [levelFilter, setLevelFilter] = useState("");
  const [showUpload, setShowUpload] = useState(false);
  const [showCrawl, setShowCrawl] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getExamPapers({
        page,
        limit: 20,
        year: yearFilter ? Number(yearFilter) : undefined,
        level: levelFilter ? Number(levelFilter) : undefined,
      });
      setData(res);
    } catch { /* ignore */ }
    finally { setLoading(false); }
  }, [page, yearFilter, levelFilter]);

  useEffect(() => { load(); }, [load]);

  const handleUploadSchedule = async (examId: string, file: File) => {
    try {
      const res = await uploadSchedule(examId, file);
      alert(`Updated ${res.answers_updated} of ${res.total_questions} questions with answers (${res.answers_parsed} answers parsed from schedule)`);
      load();
    } catch {
      alert("Failed to upload schedule");
    }
  };

  const handleDelete = async (exam: ExamPaper) => {
    if (!confirm(`Delete "${exam.title}" and all its questions?`)) return;
    try {
      await deleteExamPaper(exam.id);
      load();
    } catch { /* ignore */ }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Exam Papers</h1>
        <div className="flex gap-2">
          <button
            onClick={() => setShowCrawl(!showCrawl)}
            className="px-4 py-2 text-sm font-medium bg-white border border-gray-200 rounded-lg hover:bg-gray-50"
          >
            Crawl NZQA
          </button>
          <button
            onClick={() => setShowUpload(!showUpload)}
            className="px-4 py-2 text-sm font-medium bg-purple-500 text-white rounded-lg hover:bg-purple-600"
          >
            Upload PDF
          </button>
        </div>
      </div>

      {/* Upload Panel */}
      {showUpload && <UploadPanel onDone={() => { setShowUpload(false); load(); }} />}

      {/* Crawl Panel */}
      {showCrawl && <CrawlPanel onDone={() => { setShowCrawl(false); load(); }} />}

      {/* Filters */}
      <div className="flex gap-3">
        <select
          value={levelFilter}
          onChange={(e) => { setLevelFilter(e.target.value); setPage(1); }}
          className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-purple-500"
        >
          <option value="">All levels</option>
          <option value="1">Level 1</option>
          <option value="2">Level 2</option>
          <option value="3">Level 3</option>
        </select>
        <select
          value={yearFilter}
          onChange={(e) => { setYearFilter(e.target.value); setPage(1); }}
          className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-purple-500"
        >
          <option value="">All years</option>
          {[2025, 2024, 2023, 2022, 2021].map((y) => (
            <option key={y} value={y}>{y}</option>
          ))}
        </select>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr className="text-left text-gray-500">
                <th className="px-4 py-3 font-medium">Title</th>
                <th className="px-4 py-3 font-medium">Level</th>
                <th className="px-4 py-3 font-medium">Year</th>
                <th className="px-4 py-3 font-medium">Subject</th>
                <th className="px-4 py-3 font-medium">Language</th>
                <th className="px-4 py-3 font-medium">Questions</th>
                <th className="px-4 py-3 font-medium">Created</th>
                <th className="px-4 py-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i} className="border-t border-gray-50">
                    <td colSpan={8} className="px-4 py-3"><div className="h-5 bg-gray-100 rounded animate-pulse" /></td>
                  </tr>
                ))
              ) : data?.items.length === 0 ? (
                <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">No exam papers found</td></tr>
              ) : (
                data?.items.map((exam) => (
                  <tr key={exam.id} className="border-t border-gray-50 hover:bg-gray-50/50">
                    <td className="px-4 py-3 font-medium text-gray-900">{exam.title}</td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-purple-50 text-purple-700">L{exam.level}</span>
                    </td>
                    <td className="px-4 py-3 text-gray-600">{exam.year}</td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700 capitalize">{exam.subject}</span>
                    </td>
                    <td className="px-4 py-3 text-gray-600 capitalize">{exam.language}</td>
                    <td className="px-4 py-3">
                      <span className="font-medium text-gray-900">{exam.total_questions}</span>
                    </td>
                    <td className="px-4 py-3 text-gray-500">{new Date(exam.created_at).toLocaleDateString()}</td>
                    <td className="px-4 py-3">
                      <div className="flex gap-2 flex-wrap">
                        <Link
                          href={`/questions?exam_id=${exam.id}`}
                          className="px-2 py-1 rounded text-xs font-medium bg-purple-50 text-purple-600 hover:bg-purple-100"
                        >
                          Questions
                        </Link>
                        <label className="px-2 py-1 rounded text-xs font-medium bg-emerald-50 text-emerald-600 hover:bg-emerald-100 cursor-pointer">
                          + Schedule
                          <input
                            type="file"
                            accept=".pdf"
                            className="hidden"
                            onChange={(e) => {
                              const file = e.target.files?.[0];
                              if (file) handleUploadSchedule(exam.id, file);
                              e.target.value = "";
                            }}
                          />
                        </label>
                        <button
                          onClick={() => handleDelete(exam)}
                          className="px-2 py-1 rounded text-xs font-medium bg-red-50 text-red-600 hover:bg-red-100"
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        {data && (
          <Pagination page={data.page} pages={data.pages} total={data.total} limit={data.limit} label="papers" onPageChange={setPage} />
        )}
      </div>
    </div>
  );
}

function UploadPanel({ onDone }: { onDone: () => void }) {
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const examRef = useRef<HTMLInputElement>(null);
  const schedRef = useRef<HTMLInputElement>(null);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = e.currentTarget;
    const fd = new FormData();

    const examFile = examRef.current?.files?.[0];
    if (!examFile) return;
    fd.append("exam_pdf", examFile);

    const schedFile = schedRef.current?.files?.[0];
    if (schedFile) fd.append("schedule_pdf", schedFile);

    fd.append("title", (form.elements.namedItem("title") as HTMLInputElement).value);
    fd.append("year", (form.elements.namedItem("year") as HTMLInputElement).value);
    fd.append("subject", (form.elements.namedItem("subject") as HTMLSelectElement).value);
    fd.append("level", (form.elements.namedItem("level") as HTMLSelectElement).value);
    fd.append("language", (form.elements.namedItem("language") as HTMLSelectElement).value);

    setUploading(true);
    setError(null);
    try {
      const res = await uploadExamPdf(fd);
      setResult(`Parsed ${res.total_questions_parsed} questions from "${res.exam_paper.title}"`);
      setTimeout(onDone, 1500);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Upload failed";
      setError(msg);
    } finally {
      setUploading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-gray-100 shadow-sm p-6 space-y-4">
      <h2 className="text-lg font-semibold text-gray-900">Upload Exam PDF</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Title *</label>
          <input name="title" required className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-purple-500" placeholder="Numeracy 2025 Week 1" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Year *</label>
          <input name="year" type="number" required defaultValue={2025} className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-purple-500" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Subject</label>
          <select name="subject" defaultValue="numeracy" className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-purple-500">
            <option value="numeracy">Numeracy</option>
            <option value="literacy">Literacy</option>
            <option value="mathematics">Mathematics</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">NCEA Level</label>
          <select name="level" defaultValue="1" className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-purple-500">
            <option value="1">Level 1</option>
            <option value="2">Level 2</option>
            <option value="3">Level 3</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Language</label>
          <select name="language" defaultValue="english" className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-purple-500">
            <option value="english">English</option>
            <option value="te_reo_maori">Te Reo Maori</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Exam PDF *</label>
          <input ref={examRef} type="file" accept=".pdf" required className="w-full text-sm text-gray-500 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-purple-50 file:text-purple-600 hover:file:bg-purple-100" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Marking Schedule (optional)</label>
          <input ref={schedRef} type="file" accept=".pdf" className="w-full text-sm text-gray-500 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-gray-50 file:text-gray-600 hover:file:bg-gray-100" />
        </div>
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}
      {result && <p className="text-sm text-emerald-600">{result}</p>}
      <div className="flex gap-2">
        <button type="submit" disabled={uploading}
          className="px-4 py-2 text-sm font-medium bg-purple-500 text-white rounded-lg hover:bg-purple-600 disabled:opacity-50">
          {uploading ? "Uploading & Parsing..." : "Upload & Parse"}
        </button>
        <button type="button" onClick={onDone} className="px-4 py-2 text-sm font-medium bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200">
          Cancel
        </button>
      </div>
    </form>
  );
}

function CrawlPanel({ onDone }: { onDone: () => void }) {
  const [crawling, setCrawling] = useState(false);
  const [crawlResult, setCrawlResult] = useState<CrawlResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = e.currentTarget;
    const url = (form.elements.namedItem("url") as HTMLInputElement).value;
    const language = (form.elements.namedItem("language") as HTMLSelectElement).value;
    const level = Number((form.elements.namedItem("crawl_level") as HTMLSelectElement).value);

    setCrawling(true);
    setError(null);
    setCrawlResult(null);
    try {
      const res = await crawlExams({ url, language, level });
      setCrawlResult(res);
      if (res.total_papers_imported > 0) {
        setTimeout(onDone, 3000);
      }
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Crawl failed";
      setError(msg);
    } finally {
      setCrawling(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-gray-100 shadow-sm p-6 space-y-4">
      <h2 className="text-lg font-semibold text-gray-900">Crawl NZQA Page</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="sm:col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-1">NZQA Page URL *</label>
          <input name="url" required placeholder="https://www2.nzqa.govt.nz/ncea/subjects/past-exams-and-exemplars/litnum/32406/"
            className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-purple-500" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">NCEA Level</label>
          <select name="crawl_level" defaultValue="1" className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-purple-500">
            <option value="1">Level 1</option>
            <option value="2">Level 2</option>
            <option value="3">Level 3</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Language</label>
          <select name="language" defaultValue="english" className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-purple-500">
            <option value="english">English</option>
            <option value="te_reo_maori">Te Reo Maori</option>
          </select>
        </div>
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}

      {/* Crawl results */}
      {crawlResult && (
        <div className="space-y-3 text-sm">
          <p className="text-emerald-600 font-medium">
            Discovered {crawlResult.total_pdfs_discovered} PDFs.
            Imported {crawlResult.total_papers_imported} papers ({crawlResult.total_questions_parsed} questions).
            {crawlResult.total_skipped > 0 && ` Skipped ${crawlResult.total_skipped} existing.`}
          </p>

          {crawlResult.skipped.length > 0 && (
            <div className="bg-gray-50 rounded-lg p-3">
              <p className="font-medium text-gray-600 mb-1">Skipped (already imported):</p>
              <ul className="list-disc list-inside text-gray-500 space-y-0.5">
                {crawlResult.skipped.map((s, i) => <li key={i}>{s}</li>)}
              </ul>
            </div>
          )}

          {crawlResult.failed.length > 0 && (
            <div className="bg-red-50 rounded-lg p-3">
              <p className="font-medium text-red-700 mb-1">Failed (need manual import):</p>
              <ul className="list-disc list-inside text-red-600 space-y-0.5">
                {crawlResult.failed.map((f, i) => <li key={i}>{f}</li>)}
              </ul>
            </div>
          )}

          {crawlResult.errors.length > 0 && (
            <div className="bg-amber-50 rounded-lg p-3">
              <p className="font-medium text-amber-700 mb-1">Warnings:</p>
              <ul className="list-disc list-inside text-amber-600 space-y-0.5">
                {crawlResult.errors.map((e, i) => <li key={i}>{e}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}

      <div className="flex gap-2">
        <button type="submit" disabled={crawling}
          className="px-4 py-2 text-sm font-medium bg-purple-500 text-white rounded-lg hover:bg-purple-600 disabled:opacity-50">
          {crawling ? "Crawling..." : "Start Crawl"}
        </button>
        <button type="button" onClick={onDone} className="px-4 py-2 text-sm font-medium bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200">
          Cancel
        </button>
      </div>
    </form>
  );
}
