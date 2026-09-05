"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { ListFilter, Loader2, ExternalLink } from "lucide-react";
import { api } from "@/lib/api";

export default function AdminTasksPage() {
  const [loading, setLoading] = useState(true);
  const [tasks, setTasks] = useState<any[]>([]);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");

  useEffect(() => {
    async function loadTasks() {
      try {
        setLoading(true);
        const data = await api.getAdminTasks();
        setTasks(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    loadTasks();
  }, []);

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

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 text-orange-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
            <ListFilter className="h-6 w-6 text-orange-500" /> System-Wide Scraping Tasks
          </h1>
          <p className="text-sm text-gray-500">Monitor all scraping tasks initialized across users.</p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search tasks by user, keyword, location..."
            className="bg-white border border-gray-200 text-xs rounded-xl px-3.5 py-2.5 w-64 focus:outline-none focus:border-orange-500"
          />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-white border border-gray-200 text-xs font-semibold rounded-xl px-3 py-2.5 focus:outline-none focus:border-orange-500"
          >
            <option value="ALL">All Statuses</option>
            <option value="COMPLETED">Completed</option>
            <option value="RUNNING">Running</option>
            <option value="PENDING">Pending</option>
            <option value="FAILED">Failed</option>
          </select>
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
        {/* Desktop Table View */}
        <div className="hidden md:block overflow-x-auto">
          <table className="w-full text-left text-sm text-gray-600">
            <thead className="bg-gray-50 text-xs uppercase font-bold text-gray-500 border-b border-gray-200">
              <tr>
                <th className="px-6 py-4">Task ID</th>
                <th className="px-6 py-4">User</th>
                <th className="px-6 py-4">Keyword & Location</th>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4">Discovered</th>
                <th className="px-6 py-4">Crawled</th>
                <th className="px-6 py-4">Leads Created</th>
                <th className="px-6 py-4">Created Date</th>
                <th className="px-6 py-4 text-right">View</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filteredTasks.map((t) => (
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
              ))}
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
                <span className="font-bold text-orange-600">{t.lead_count} Leads</span>
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
