"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { ListFilter, ExternalLink } from "lucide-react";
import { api } from "@/lib/api";

import { useToast } from "@/components/AppLayout";

export default function AdminTasksPage() {
  const { showToast, backendStatus } = useToast();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isWaking, setIsWaking] = useState(false);
  const [tasks, setTasks] = useState<any[]>([]);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");

  const loadTasks = React.useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getAdminTasks();
      setTasks(data);
      setError(null);
      setIsWaking(false);
    } catch (err: any) {
      const waking = err?.isBackendWaking || err?.code === "BACKEND_WAKING" || err?.message?.includes("waking up");
      setIsWaking(!!waking);
      const msg = waking 
        ? "Server is waking up. Your data is safe. Retrying automatically..." 
        : (err.message || "Failed to load system tasks.");
      setError(msg);
      showToast(msg, waking ? "info" : "error");
    } finally {
      setLoading(false);
    }
  }, [showToast]);

  useEffect(() => {
    loadTasks();
  }, [loadTasks]);

  // Auto-retry when backend finishes waking
  useEffect(() => {
    if (error && !backendStatus.isWaking && !loading) {
      loadTasks();
    }
  }, [backendStatus.isWaking, error, loading, loadTasks]);

  const filteredTasks = tasks.filter((t) => {
    const query = search.toLowerCase();
    const matchesSearch =
      (t.user_email || "").toLowerCase().includes(query) ||
      (t.keyword || "").toLowerCase().includes(query) ||
      (t.location || "").toLowerCase().includes(query) ||
      (t.public_task_id || "").toLowerCase().includes(query);
    const matchesStatus = statusFilter === "ALL" || t.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
            <ListFilter className="h-6 w-6 text-orange-500" /> Admin Tasks Directory
          </h1>
          <p className="text-sm text-gray-500">Monitor all search & scraping tasks across all system users.</p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <input
            type="text"
            placeholder="Search tasks, users, keywords..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-xl text-xs font-semibold focus:outline-none focus:border-orange-500 w-64"
          />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-xl text-xs font-semibold focus:outline-none focus:border-orange-500"
          >
            <option value="ALL">All Statuses</option>
            <option value="COMPLETED">Completed</option>
            <option value="RUNNING">Running</option>
            <option value="FAILED">Failed</option>
          </select>
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="hidden md:block overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-gray-50 text-xs font-bold text-gray-500 uppercase border-b border-gray-200">
              <tr>
                <th className="px-6 py-3.5">Task ID</th>
                <th className="px-6 py-3.5">User</th>
                <th className="px-6 py-3.5">Target</th>
                <th className="px-6 py-3.5">Status</th>
                <th className="px-6 py-3.5" title="Number of raw candidates discovered before verification.">Raw Candidates</th>
                <th className="px-6 py-3.5">Crawled</th>
                <th className="px-6 py-3.5" title="Verified organizations that passed the validation pipeline.">Verified Leads</th>
                <th className="px-6 py-3.5">Created</th>
                <th className="px-6 py-3.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {loading && tasks.length === 0 ? (
                [...Array(4)].map((_, i) => (
                  <tr key={i} className="animate-pulse">
                    <td className="px-6 py-4"><div className="h-4 bg-gray-200 rounded w-20"></div></td>
                    <td className="px-6 py-4"><div className="h-4 bg-gray-200 rounded w-32"></div></td>
                    <td className="px-6 py-4"><div className="h-4 bg-gray-200 rounded w-36"></div></td>
                    <td className="px-6 py-4"><div className="h-4 bg-gray-200 rounded w-16"></div></td>
                    <td className="px-6 py-4"><div className="h-4 bg-gray-200 rounded w-12"></div></td>
                    <td className="px-6 py-4"><div className="h-4 bg-gray-200 rounded w-12"></div></td>
                    <td className="px-6 py-4"><div className="h-4 bg-gray-200 rounded w-12"></div></td>
                    <td className="px-6 py-4"><div className="h-4 bg-gray-200 rounded w-24"></div></td>
                    <td className="px-6 py-4"><div className="h-4 bg-gray-200 rounded w-8 ml-auto"></div></td>
                  </tr>
                ))
              ) : error ? (
                <tr>
                  <td colSpan={9} className="px-6 py-12 text-center">
                    <p className="font-bold text-gray-900 text-sm">{isWaking ? "Server is waking up" : "Failed to load admin tasks"}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{error}</p>
                    <button
                      onClick={() => loadTasks()}
                      className="mt-3 inline-flex items-center gap-2 px-3 py-1.5 bg-white border border-gray-300 rounded-lg text-xs font-bold hover:bg-gray-50 shadow-xs"
                    >
                      Retry Loading Tasks
                    </button>
                  </td>
                </tr>
              ) : tasks.length === 0 ? (
                <tr>
                  <td colSpan={9} className="px-6 py-12 text-center text-gray-400 font-semibold text-xs">
                    No system tasks found.
                  </td>
                </tr>
              ) : filteredTasks.length === 0 ? (
                <tr>
                  <td colSpan={9} className="px-6 py-12 text-center text-gray-400 font-semibold text-xs">
                    No tasks match query filters.
                  </td>
                </tr>
              ) : (
                filteredTasks.map((t) => (
                  <tr key={t.id} className="hover:bg-gray-50/80 transition-colors">
                    <td className="px-6 py-4 font-mono text-xs font-bold text-gray-900">{t.public_task_id}</td>
                    <td className="px-6 py-4 font-medium text-gray-800">{t.user_email}</td>
                    <td className="px-6 py-4">
                      <span className="font-semibold text-gray-900">{t.keyword}</span>
                      <span className="text-xs text-gray-400 block">{t.location}</span>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`px-2.5 py-1 rounded-full text-xs font-bold ${
                        t.status === "COMPLETED" ? "bg-emerald-100 text-emerald-800" :
                        t.status === "RUNNING" ? "bg-amber-100 text-amber-800 animate-pulse" :
                        t.status === "FAILED" ? "bg-red-100 text-red-800" : "bg-gray-100 text-gray-800"
                      }`}>
                        {t.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 font-semibold text-gray-800">{t.discovered_count}</td>
                    <td className="px-6 py-4 font-semibold text-gray-800">{t.websites_crawled}</td>
                    <td className="px-6 py-4 font-bold text-orange-600">{t.lead_count}</td>
                    <td className="px-6 py-4 text-xs text-gray-500">
                      {new Date(t.created_at).toLocaleDateString()} {new Date(t.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <Link
                        href={`/tasks/${t.public_task_id}`}
                        className="p-2 text-gray-400 hover:text-orange-600 inline-block"
                      >
                        <ExternalLink className="h-4 w-4" />
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Mobile Card Layout */}
        <div className="md:hidden divide-y divide-gray-100">
          {filteredTasks.map((t) => (
            <div key={t.id} className="p-4 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-mono font-bold text-xs text-gray-900">{t.public_task_id}</span>
                <span className={`px-2 py-0.5 rounded-full text-[11px] font-bold ${
                  t.status === "COMPLETED" ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"
                }`}>
                  {t.status}
                </span>
              </div>
              <div className="text-sm font-bold text-gray-900">{t.keyword} <span className="font-normal text-gray-500">in {t.location}</span></div>
              <div className="flex items-center justify-between text-xs text-gray-500 pt-1">
                <span>User: {t.user_email}</span>
                <span className="font-semibold text-gray-600">Raw Candidates: {t.discovered_count}</span>
                <span className="font-bold text-orange-600">Verified Leads: {t.lead_count}</span>
              </div>
              <Link
                href={`/tasks/${t.public_task_id}`}
                className="mt-2 block w-full text-center py-2 bg-orange-50 text-orange-600 rounded-xl text-xs font-bold"
              >
                View Task Details
              </Link>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
