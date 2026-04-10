"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useUser } from "@clerk/nextjs";
import { getHistory, getMistakes, getExams } from "@/lib/api";

interface Stats {
  totalScans: number;
  totalMistakes: number;
  totalExams: number;
  masteredCount: number;
}

const quickActions = [
  {
    href: "/solve",
    label: "Upload & Solve",
    description: "Upload a photo of your homework and get AI solutions",
    icon: (
      <svg className="w-8 h-8 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5-5m0 0l5 5m-5-5v12" />
      </svg>
    ),
    color: "bg-indigo-50 border-indigo-100 hover:border-indigo-300",
  },
  {
    href: "/exams",
    label: "Exam Practice",
    description: "Practice with real NZQA exam papers and check your answers",
    icon: (
      <svg className="w-8 h-8 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15a2.25 2.25 0 012.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25zM6.75 12h.008v.008H6.75V12zm0 3h.008v.008H6.75V15zm0 3h.008v.008H6.75V18z" />
      </svg>
    ),
    color: "bg-purple-50 border-purple-100 hover:border-purple-300",
  },
  {
    href: "/mistakes",
    label: "Mistake Book",
    description: "Review your mistakes and track what you've mastered",
    icon: (
      <svg className="w-8 h-8 text-rose-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
      </svg>
    ),
    color: "bg-rose-50 border-rose-100 hover:border-rose-300",
  },
  {
    href: "/formulas",
    label: "Formula Library",
    description: "Browse and search formulas across all subjects",
    icon: (
      <svg className="w-8 h-8 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M4.745 3A23.933 23.933 0 003 12c0 3.183.62 6.22 1.745 9M19.5 3c.967 2.78 1.5 5.817 1.5 9s-.533 6.22-1.5 9M8.25 8.885l1.444-.89a.75.75 0 011.105.402l2.402 7.206a.75.75 0 001.104.401l1.445-.889" />
      </svg>
    ),
    color: "bg-amber-50 border-amber-100 hover:border-amber-300",
  },
];

export default function DashboardPage() {
  const { user, isSignedIn } = useUser();
  const [stats, setStats] = useState<Stats>({
    totalScans: 0,
    totalMistakes: 0,
    totalExams: 0,
    masteredCount: 0,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchStats() {
      try {
        const [historyData, mistakeData, examData] = await Promise.allSettled([
          getHistory({ page: 1, limit: 1 }),
          getMistakes({ page: 1, limit: 1 }),
          getExams({ page: 1, limit: 1 }),
        ]);

        setStats({
          totalScans:
            historyData.status === "fulfilled" ? historyData.value.total : 0,
          totalMistakes:
            mistakeData.status === "fulfilled" ? mistakeData.value.total : 0,
          totalExams:
            examData.status === "fulfilled" ? examData.value.total : 0,
          masteredCount: 0,
        });
      } catch {
        // Stats are optional
      } finally {
        setLoading(false);
      }
    }
    fetchStats();
  }, []);

  const greeting = (() => {
    const hour = new Date().getHours();
    if (hour < 12) return "Good morning";
    if (hour < 18) return "Good afternoon";
    return "Good evening";
  })();

  const displayName = user?.firstName || "Student";

  return (
    <div className="space-y-8">
      {/* Welcome header */}
      <div className="pt-4 lg:pt-0">
        <h1 className="text-2xl font-bold text-gray-900">
          {greeting}
          {isSignedIn ? `, ${displayName}` : ""}!
        </h1>
        <p className="text-gray-500 mt-1">
          What would you like to study today?
        </p>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
          <p className="text-xs text-gray-500 font-medium">Problems Solved</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">
            {loading ? "-" : stats.totalScans}
          </p>
        </div>
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
          <p className="text-xs text-gray-500 font-medium">Exam Papers</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">
            {loading ? "-" : stats.totalExams}
          </p>
        </div>
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
          <p className="text-xs text-gray-500 font-medium">In Mistake Book</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">
            {loading ? "-" : stats.totalMistakes}
          </p>
        </div>
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
          <p className="text-xs text-gray-500 font-medium">Formulas</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">
            <Link
              href="/formulas"
              className="text-indigo-600 hover:text-indigo-700"
            >
              Browse
            </Link>
          </p>
        </div>
      </div>

      {/* Quick actions */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Quick Actions
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {quickActions.map((action) => (
            <Link
              key={action.href}
              href={action.href}
              className={`flex items-start gap-4 p-5 rounded-xl border transition-all ${action.color}`}
            >
              <div className="flex-shrink-0 mt-0.5">{action.icon}</div>
              <div>
                <h3 className="text-sm font-semibold text-gray-900">
                  {action.label}
                </h3>
                <p className="text-xs text-gray-500 mt-1">
                  {action.description}
                </p>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
