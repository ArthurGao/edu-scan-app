"use client";

import { useEffect, useState } from "react";
import { getTiers, createTier, updateTier, deleteTier, TierInfo } from "@/lib/admin-api";

type TierWithCount = TierInfo & { user_count?: number };

const emptyTier: Partial<TierInfo> = {
  name: "",
  display_name: "",
  description: "",
  daily_question_limit: 5,
  allowed_ai_models: ["claude"],
  features: {},
  max_image_size_mb: 5,
  is_default: false,
  is_active: true,
  sort_order: 0,
};

export default function AdminTiersPage() {
  const [tiers, setTiers] = useState<TierWithCount[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editingTier, setEditingTier] = useState<Partial<TierInfo> | null>(null);
  const [formData, setFormData] = useState<Partial<TierInfo>>(emptyTier);

  const fetchTiers = async () => {
    setLoading(true);
    try {
      const data = await getTiers();
      setTiers(data);
    } catch {
      setError("Failed to load tiers.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTiers();
  }, []);

  const handleCreate = async () => {
    try {
      setError(null);
      await createTier(formData);
      setShowForm(false);
      setFormData(emptyTier);
      fetchTiers();
    } catch {
      setError("Failed to create tier.");
    }
  };

  const handleUpdate = async () => {
    if (!editingTier?.id) return;
    try {
      setError(null);
      await updateTier(editingTier.id, formData);
      setEditingTier(null);
      setFormData(emptyTier);
      fetchTiers();
    } catch {
      setError("Failed to update tier.");
    }
  };

  const handleDelete = async (tierId: number) => {
    if (!confirm("Delete this tier? Users assigned to it will lose their tier.")) return;
    try {
      setError(null);
      await deleteTier(tierId);
      fetchTiers();
    } catch {
      setError("Failed to delete tier. It may still have users assigned.");
    }
  };

  const startEdit = (tier: TierWithCount) => {
    setEditingTier(tier);
    setFormData({
      name: tier.name,
      display_name: tier.display_name,
      description: tier.description,
      daily_question_limit: tier.daily_question_limit,
      allowed_ai_models: tier.allowed_ai_models,
      max_image_size_mb: tier.max_image_size_mb,
      is_default: tier.is_default,
      is_active: tier.is_active,
      sort_order: tier.sort_order,
    });
    setShowForm(false);
  };

  const cancelForm = () => {
    setShowForm(false);
    setEditingTier(null);
    setFormData(emptyTier);
  };

  const isFormOpen = showForm || editingTier !== null;

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-semibold text-gray-900">Subscription Tiers</h2>
        {!isFormOpen && (
          <button
            onClick={() => { setShowForm(true); setFormData(emptyTier); }}
            className="px-4 py-2 bg-indigo-500 text-white text-sm font-medium rounded-lg hover:bg-indigo-600"
          >
            Add Tier
          </button>
        )}
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-3">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Form */}
      {isFormOpen && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 space-y-4">
          <h3 className="font-medium text-gray-900">
            {editingTier ? `Edit: ${editingTier.display_name}` : "New Tier"}
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Name (slug)</label>
              <input
                value={formData.name || ""}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                placeholder="e.g. basic"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Display Name</label>
              <input
                value={formData.display_name || ""}
                onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                placeholder="e.g. Basic Plan"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Daily Question Limit (0 = unlimited)</label>
              <input
                type="number"
                value={formData.daily_question_limit ?? 5}
                onChange={(e) => setFormData({ ...formData, daily_question_limit: parseInt(e.target.value) || 0 })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Max Image Size (MB)</label>
              <input
                type="number"
                value={formData.max_image_size_mb ?? 5}
                onChange={(e) => setFormData({ ...formData, max_image_size_mb: parseInt(e.target.value) || 5 })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">AI Models (comma-separated)</label>
              <input
                value={(formData.allowed_ai_models || []).join(", ")}
                onChange={(e) => setFormData({ ...formData, allowed_ai_models: e.target.value.split(",").map((s) => s.trim()).filter(Boolean) })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                placeholder="claude, gpt, gemini"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Sort Order</label>
              <input
                type="number"
                value={formData.sort_order ?? 0}
                onChange={(e) => setFormData({ ...formData, sort_order: parseInt(e.target.value) || 0 })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
              />
            </div>
          </div>
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={formData.is_default || false}
                onChange={(e) => setFormData({ ...formData, is_default: e.target.checked })}
                className="rounded"
              />
              Default tier
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={formData.is_active !== false}
                onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                className="rounded"
              />
              Active
            </label>
          </div>
          <div className="flex gap-2">
            <button
              onClick={editingTier ? handleUpdate : handleCreate}
              className="px-4 py-2 bg-indigo-500 text-white text-sm font-medium rounded-lg hover:bg-indigo-600"
            >
              {editingTier ? "Save Changes" : "Create Tier"}
            </button>
            <button onClick={cancelForm} className="px-4 py-2 text-gray-600 text-sm hover:bg-gray-100 rounded-lg">
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Tiers List */}
      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 animate-pulse">
              <div className="bg-gray-200 rounded h-5 w-32 mb-2" />
              <div className="bg-gray-200 rounded h-4 w-48" />
            </div>
          ))}
        </div>
      ) : (
        <div className="space-y-3">
          {tiers.map((tier) => (
            <div key={tier.id} className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-medium text-gray-900">{tier.display_name}</h3>
                    {tier.is_default && (
                      <span className="px-2 py-0.5 bg-indigo-100 text-indigo-700 text-xs font-medium rounded-full">
                        Default
                      </span>
                    )}
                    {!tier.is_active && (
                      <span className="px-2 py-0.5 bg-gray-100 text-gray-500 text-xs font-medium rounded-full">
                        Inactive
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-gray-500 mt-1">
                    {tier.daily_question_limit === 0 ? "Unlimited" : tier.daily_question_limit} questions/day
                    {" | "}Models: {tier.allowed_ai_models.join(", ")}
                    {" | "}Max image: {tier.max_image_size_mb}MB
                    {tier.user_count !== undefined && ` | ${tier.user_count} users`}
                  </p>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => startEdit(tier)}
                    className="text-xs px-3 py-1 text-indigo-600 hover:bg-indigo-50 rounded"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => handleDelete(tier.id)}
                    className="text-xs px-3 py-1 text-red-600 hover:bg-red-50 rounded"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
