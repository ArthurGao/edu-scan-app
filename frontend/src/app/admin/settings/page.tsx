"use client";

import { useEffect, useState } from "react";
import { getSettings, updateSettings, SystemSettingItem } from "@/lib/admin-api";

export default function AdminSettingsPage() {
  const [settings, setSettings] = useState<SystemSettingItem[]>([]);
  const [editValues, setEditValues] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await getSettings();
        setSettings(data);
        const vals: Record<string, string> = {};
        data.forEach((s) => {
          vals[s.key] = typeof s.value === "object" ? JSON.stringify(s.value) : String(s.value);
        });
        setEditValues(vals);
      } catch {
        setError("Failed to load settings.");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const payload: Record<string, unknown> = {};
      settings.forEach((s) => {
        const newVal = editValues[s.key];
        const currentVal = typeof s.value === "object" ? JSON.stringify(s.value) : String(s.value);
        if (newVal !== currentVal) {
          // Try to parse as JSON, fall back to string
          try {
            payload[s.key] = JSON.parse(newVal);
          } catch {
            payload[s.key] = newVal;
          }
        }
      });

      if (Object.keys(payload).length === 0) {
        setSuccess("No changes to save.");
        setSaving(false);
        return;
      }

      await updateSettings(payload);
      setSuccess("Settings saved successfully.");
      // Reload
      const data = await getSettings();
      setSettings(data);
    } catch {
      setError("Failed to save settings.");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 space-y-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="animate-pulse">
            <div className="bg-gray-200 rounded h-4 w-32 mb-2" />
            <div className="bg-gray-200 rounded h-10 w-full" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-semibold text-gray-900">System Settings</h2>
        <button
          onClick={handleSave}
          disabled={saving}
          className="px-4 py-2 bg-indigo-500 text-white text-sm font-medium rounded-lg hover:bg-indigo-600 disabled:opacity-50"
        >
          {saving ? "Saving..." : "Save Changes"}
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-3">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {success && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3">
          <p className="text-sm text-emerald-700">{success}</p>
        </div>
      )}

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 divide-y divide-gray-100">
        {settings.map((setting) => (
          <div key={setting.key} className="p-4">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <label className="block text-sm font-medium text-gray-900">
                  {setting.key}
                </label>
                {setting.description && (
                  <p className="text-xs text-gray-500 mt-0.5">{setting.description}</p>
                )}
              </div>
              <input
                value={editValues[setting.key] || ""}
                onChange={(e) =>
                  setEditValues({ ...editValues, [setting.key]: e.target.value })
                }
                className="w-64 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            <p className="text-xs text-gray-400 mt-1">
              Last updated: {new Date(setting.updated_at).toLocaleString()}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
