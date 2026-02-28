"use client";

import { useEffect, useState } from "react";
import { getStatsOverview, getDailyStats, StatsOverview, DailyStat } from "@/lib/admin-api";

export default function AdminDashboard() {
  const [stats, setStats] = useState<StatsOverview | null>(null);
  const [dailyStats, setDailyStats] = useState<DailyStat[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const [overview, daily] = await Promise.all([
          getStatsOverview(),
          getDailyStats(7),
        ]);
        setStats(overview);
        setDailyStats(daily);
      } catch {
        setError("Failed to load dashboard data. Make sure you have admin access.");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 animate-pulse">
            <div className="bg-gray-200 rounded h-4 w-20 mb-2" />
            <div className="bg-gray-200 rounded h-8 w-16" />
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-xl p-4">
        <p className="text-sm text-red-700">{error}</p>
      </div>
    );
  }

  if (!stats) return null;

  const kpis = [
    { label: "Total Users", value: stats.total_users, color: "text-indigo-600" },
    { label: "Active Today", value: stats.active_today, color: "text-emerald-600" },
    { label: "Questions Today", value: stats.questions_today, color: "text-blue-600" },
    {
      label: "Tier Breakdown",
      value: Object.keys(stats.tier_distribution).length + " tiers",
      color: "text-amber-600",
    },
  ];

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {kpis.map((kpi) => (
          <div key={kpi.label} className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
            <p className="text-sm text-gray-500">{kpi.label}</p>
            <p className={`text-2xl font-bold mt-1 ${kpi.color}`}>{kpi.value}</p>
          </div>
        ))}
      </div>

      {/* Tier Distribution */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Tier Distribution</h2>
        <div className="space-y-3">
          {Object.entries(stats.tier_distribution).map(([tier, count]) => {
            const total = stats.total_users || 1;
            const pct = Math.round((count / total) * 100);
            return (
              <div key={tier}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-700 capitalize">{tier}</span>
                  <span className="text-gray-500">{count} users ({pct}%)</span>
                </div>
                <div className="w-full bg-gray-100 rounded-full h-2">
                  <div
                    className="bg-indigo-500 h-2 rounded-full transition-all"
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Daily Activity */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Daily Activity (Last 7 Days)</h2>
        {dailyStats.length === 0 ? (
          <p className="text-gray-500 text-sm">No activity data available yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-2 font-medium text-gray-500">Date</th>
                  <th className="text-right py-2 font-medium text-gray-500">Active Users</th>
                  <th className="text-right py-2 font-medium text-gray-500">Questions</th>
                </tr>
              </thead>
              <tbody>
                {dailyStats.map((day) => (
                  <tr key={day.date} className="border-b border-gray-50">
                    <td className="py-2 text-gray-700">{day.date}</td>
                    <td className="py-2 text-right text-gray-700">{day.active_users}</td>
                    <td className="py-2 text-right text-gray-700">{day.questions}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
