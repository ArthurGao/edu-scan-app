"use client";

import { useEffect, useState, useCallback } from "react";
import { getUsers, updateUser, type UserInfo, type PaginatedResponse } from "@/lib/api";
import Pagination from "@/components/Pagination";

export default function UsersPage() {
  const [data, setData] = useState<PaginatedResponse<UserInfo> | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [page, setPage] = useState(1);
  const limit = 20;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getUsers({
        page,
        limit,
        search: search || undefined,
        role: roleFilter || undefined,
      });
      setData(res);
    } catch (err) {
      console.error("Failed to load users:", err);
    } finally {
      setLoading(false);
    }
  }, [page, search, roleFilter]);

  useEffect(() => { load(); }, [load]);

  const handleToggleActive = async (user: UserInfo) => {
    try {
      await updateUser(user.id, { is_active: !user.is_active });
      load();
    } catch {
      /* ignore */
    }
  };

  const handleToggleRole = async (user: UserInfo) => {
    const newRole = user.role === "admin" ? "user" : "admin";
    if (!confirm(`Change ${user.email} role to "${newRole}"?`)) return;
    try {
      await updateUser(user.id, { role: newRole });
      load();
    } catch {
      /* ignore */
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">User Management</h1>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <input
          type="text"
          placeholder="Search email or name..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-purple-500 w-64"
        />
        <select
          value={roleFilter}
          onChange={(e) => { setRoleFilter(e.target.value); setPage(1); }}
          className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-purple-500"
        >
          <option value="">All roles</option>
          <option value="user">User</option>
          <option value="admin">Admin</option>
        </select>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr className="text-left text-gray-500">
                <th className="px-4 py-3 font-medium">User</th>
                <th className="px-4 py-3 font-medium">Role</th>
                <th className="px-4 py-3 font-medium">Grade</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Today</th>
                <th className="px-4 py-3 font-medium">Joined</th>
                <th className="px-4 py-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i} className="border-t border-gray-50">
                    <td colSpan={7} className="px-4 py-3"><div className="h-5 bg-gray-100 rounded animate-pulse" /></td>
                  </tr>
                ))
              ) : data?.items.length === 0 ? (
                <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">No users found</td></tr>
              ) : (
                data?.items.map((user) => (
                  <tr key={user.id} className="border-t border-gray-50 hover:bg-gray-50/50">
                    <td className="px-4 py-3">
                      <div>
                        <p className="font-medium text-gray-900">{user.nickname || user.email.split("@")[0]}</p>
                        <p className="text-xs text-gray-400">{user.email}</p>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${
                        user.role === "admin" ? "bg-purple-100 text-purple-700" : "bg-gray-100 text-gray-600"
                      }`}>
                        {user.role}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-600">{user.grade_level || "-"}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-block w-2 h-2 rounded-full ${user.is_active ? "bg-emerald-400" : "bg-gray-300"}`} />
                      <span className="ml-1.5 text-gray-600">{user.is_active ? "Active" : "Disabled"}</span>
                    </td>
                    <td className="px-4 py-3 text-gray-600">{user.today_usage ?? 0}</td>
                    <td className="px-4 py-3 text-gray-500">{new Date(user.created_at).toLocaleDateString()}</td>
                    <td className="px-4 py-3">
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleToggleActive(user)}
                          className={`px-2 py-1 rounded text-xs font-medium ${
                            user.is_active
                              ? "bg-red-50 text-red-600 hover:bg-red-100"
                              : "bg-emerald-50 text-emerald-600 hover:bg-emerald-100"
                          }`}
                        >
                          {user.is_active ? "Disable" : "Enable"}
                        </button>
                        <button
                          onClick={() => handleToggleRole(user)}
                          className="px-2 py-1 rounded text-xs font-medium bg-gray-50 text-gray-600 hover:bg-gray-100"
                        >
                          {user.role === "admin" ? "Demote" : "Promote"}
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
          <Pagination page={data.page} pages={data.pages} total={data.total} limit={data.limit} label="users" onPageChange={setPage} />
        )}
      </div>
    </div>
  );
}
