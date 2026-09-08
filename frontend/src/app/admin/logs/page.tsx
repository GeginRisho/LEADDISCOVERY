"use client";

import React, { useState, useEffect } from "react";
import { FileText, Search } from "lucide-react";
import { api, ScrapingLog } from "@/lib/api";

export default function AdminLogsPage() {
  const [loading, setLoading] = useState(true);
  const [logs, setLogs] = useState<ScrapingLog[]>([]);
  const [taskIdInput, setTaskIdInput] = useState("");
  const [eventTypeFilter, setEventTypeFilter] = useState("");

  const loadLogs = async () => {
    try {
      setLoading(true);
      const data = await api.getAdminLogs(taskIdInput.trim() || undefined, eventTypeFilter || undefined);
      setLogs(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLogs();
  }, []);

  const handleFilterSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadLogs();
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
            <FileText className="h-6 w-6 text-orange-500" /> Scraping Logs & Event Inspector
          </h1>
          <p className="text-sm text-gray-500">Inspect real-time event logs across discovery, crawling, extraction, and deduplication.</p>
        </div>

        <form onSubmit={handleFilterSubmit} className="flex flex-wrap items-center gap-2">
          <input
            type="text"
            placeholder="Filter Task ID..."
            value={taskIdInput}
            onChange={(e) => setTaskIdInput(e.target.value)}
            className="px-3.5 py-2 border border-gray-300 rounded-xl text-xs font-semibold focus:outline-none focus:border-orange-500"
          />
          <select
            value={eventTypeFilter}
            onChange={(e) => setEventTypeFilter(e.target.value)}
            className="px-3.5 py-2 border border-gray-300 rounded-xl text-xs font-semibold focus:outline-none focus:border-orange-500"
          >
            <option value="">All Event Types</option>
            <option value="DISCOVERY_STARTED">DISCOVERY_STARTED</option>
            <option value="WEBSITE_FOUND">WEBSITE_FOUND</option>
            <option value="CRAWL_START">CRAWL_START</option>
            <option value="CRAWL_SUCCESS">CRAWL_SUCCESS</option>
            <option value="CRAWL_FAILED">CRAWL_FAILED</option>
            <option value="ROBOTS_BLOCKED">ROBOTS_BLOCKED</option>
            <option value="DATABASE_SAVING">DATABASE_SAVING</option>
          </select>
          <button
            type="submit"
            className="px-4 py-2 bg-orange-500 text-white rounded-xl text-xs font-bold hover:bg-orange-600 flex items-center gap-1.5"
          >
            <Search className="h-3.5 w-3.5" /> Filter
          </button>
        </form>
      </div>

      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-gray-50 text-[11px] uppercase font-bold text-gray-500 border-b border-gray-200">
              <tr>
                <th className="px-6 py-3.5">Timestamp</th>
                <th className="px-6 py-3.5">Task ID</th>
                <th className="px-6 py-3.5">Event</th>
                <th className="px-6 py-3.5">Message Log</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 font-mono">
              {loading && logs.length === 0 ? (
                [...Array(4)].map((_, i) => (
                  <tr key={i} className="animate-pulse">
                    <td className="px-6 py-3"><div className="h-3 bg-gray-200 rounded w-16"></div></td>
                    <td className="px-6 py-3"><div className="h-3 bg-gray-200 rounded w-20"></div></td>
                    <td className="px-6 py-3"><div className="h-3 bg-gray-200 rounded w-24"></div></td>
                    <td className="px-6 py-3"><div className="h-3 bg-gray-200 rounded w-64"></div></td>
                  </tr>
                ))
              ) : (
                logs.map((log) => (
                  <tr key={log.id} className="hover:bg-gray-50/80 transition-colors">
                    <td className="px-6 py-3 text-gray-500 whitespace-nowrap">
                      {new Date(log.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </td>
                    <td className="px-6 py-3 font-bold text-gray-900">{log.task_id}</td>
                    <td className="px-6 py-3">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        log.event_type.includes("SUCCESS") ? "bg-emerald-100 text-emerald-800" :
                        log.event_type.includes("FAILED") || log.event_type.includes("BLOCKED") ? "bg-red-100 text-red-800" :
                        "bg-orange-100 text-orange-800"
                      }`}>
                        {log.event_type}
                      </span>
                    </td>
                    <td className="px-6 py-3 text-gray-800 break-words">{log.message}</td>
                  </tr>
                ))
              )}
              {logs.length === 0 && !loading && (
                <tr>
                  <td colSpan={4} className="text-center py-8 text-xs text-gray-400 font-sans">
                    No scraping logs match the specified criteria.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
