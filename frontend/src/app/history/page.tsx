"use client";

import React, { useEffect, useState, useRef } from "react";
import Link from "next/link";
import { 
  Sparkles, Search, History, Calendar, MapPin, Tag, ArrowRight,
  Download, FileSpreadsheet, Play, Loader2, CheckCircle
} from "lucide-react";
import { api, ScrapingTask } from "@/lib/api";
import { useToast } from "@/components/AppLayout";

export default function HistoryPage() {
  const { showToast } = useToast();
  const [tasks, setTasks] = useState<ScrapingTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState<string | null>(null);

  // Search & Filter state
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");

  const isFetchingRef = useRef(false);

  useEffect(() => {
    let isCurrent = true;
    async function loadTasks() {
      if (isFetchingRef.current) return;
      isFetchingRef.current = true;
      try {
        const data = await api.getTasks();
        if (isCurrent) {
          setTasks(data);
        }
      } catch (err: any) {
        if (isCurrent) {
          showToast(err.message || "Failed to load task history.", "error");
        }
      } finally {
        if (isCurrent) {
          setLoading(false);
          isFetchingRef.current = false;
        }
      }
    }
    loadTasks();
    return () => {
      isCurrent = false;
      isFetchingRef.current = false;
    };
  }, []);

  const handleSecureExport = async (taskId: string, format: "csv" | "excel") => {
    setExporting(`${taskId}_${format}`);
    try {
      const blob = await api.downloadExport(taskId, format);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${taskId}_leads.${format === "csv" ? "csv" : "xlsx"}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      showToast(`Exported ${taskId} leads to ${format.toUpperCase()}.`, "success");
    } catch (err: any) {
      showToast(err.message || `Failed to export ${format.toUpperCase()}.`, "error");
    } finally {
      setExporting(null);
    }
  };

  const filteredTasks = tasks.filter((task) => {
    const matchesSearch = 
      task.public_task_id.toLowerCase().includes(search.toLowerCase()) ||
      task.keyword.toLowerCase().includes(search.toLowerCase()) ||
      task.location.toLowerCase().includes(search.toLowerCase());
      
    const matchesStatus = statusFilter === "ALL" || task.status === statusFilter;
    
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="space-y-6">
      
      {/* Page Title */}
      <div className="border-b border-gray-200 pb-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl md:text-2xl font-extrabold text-gray-900">Scraping Sessions History</h1>
          <p className="text-xs text-gray-500 mt-1">Review, search, and download historical prospect extraction sessions</p>
        </div>
        <Link
          href="/scrape"
          className="flex items-center justify-center gap-2 bg-orange-500 hover:bg-orange-600 text-white px-4 py-2.5 rounded-xl text-xs font-bold transition-all shadow-md shadow-orange-500/20 active:scale-[0.98]"
        >
          <Play className="h-3.5 w-3.5 fill-white" /> New Scrape Task
        </Link>
      </div>

      {/* Query Filter Section */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-4 rounded-2xl border border-gray-200 shadow-xs">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3.5 top-3.5 h-4 w-4 text-gray-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search sessions by Task ID, keyword, location..."
            className="w-full bg-white border border-gray-200 focus:border-orange-500 focus:ring-2 focus:ring-orange-100 focus:outline-none rounded-xl py-2.5 pl-10 pr-4 text-xs text-gray-900 placeholder-gray-400 transition-colors"
          />
        </div>

        <div className="flex items-center gap-2">
          <label className="text-xs font-bold text-gray-600 uppercase tracking-wider">Status:</label>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-white border border-gray-200 text-gray-800 text-xs font-semibold rounded-xl px-4 py-2.5 focus:outline-none focus:border-orange-500"
          >
            <option value="ALL">All Statuses</option>
            <option value="COMPLETED">Completed</option>
            <option value="RUNNING">Running</option>
            <option value="PENDING">Pending</option>
            <option value="FAILED">Failed</option>
            <option value="CANCELLED">Cancelled</option>
          </select>
        </div>
      </div>

      {/* History List Table */}
      {loading && tasks.length === 0 ? (
        <div className="space-y-4">
          <div className="flex items-center justify-center gap-2 py-4 text-xs font-semibold text-gray-500">
            <Loader2 className="h-4 w-4 animate-spin text-orange-500" />
            Loading task history...
          </div>
          {[...Array(3)].map((_, i) => (
            <div key={i} className="p-5 bg-white border border-gray-200 rounded-2xl shadow-xs animate-pulse h-28"></div>
          ))}
        </div>
      ) : tasks.length === 0 ? (
        <div className="bg-white border border-gray-200 rounded-2xl py-16 flex flex-col items-center justify-center text-center shadow-xs">
          <History className="h-10 w-10 text-gray-300 mb-3" />
          <h4 className="text-sm font-bold text-gray-800">No scraping sessions yet.</h4>
          <p className="text-xs text-gray-500 mt-1 max-w-xs">
            Start a new scraping session to scan and index prospects.
          </p>
          <Link
            href="/scrape"
            className="mt-4 flex items-center justify-center gap-2 bg-orange-500 hover:bg-orange-600 text-white px-4 py-2 rounded-xl text-xs font-bold transition-all shadow-md shadow-orange-500/20 active:scale-[0.98]"
          >
            <Play className="h-3.5 w-3.5 fill-white" /> New Scrape Task
          </Link>
        </div>
      ) : filteredTasks.length === 0 ? (
        <div className="bg-white border border-gray-200 rounded-2xl py-16 flex flex-col items-center justify-center text-center shadow-xs">
          <History className="h-10 w-10 text-gray-300 mb-3" />
          <h4 className="text-sm font-bold text-gray-800">No sessions match query</h4>
          <p className="text-xs text-gray-500 mt-1 max-w-xs">
            Try adjusting your search terms or filter selection.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredTasks.map((task) => {
            const isCompleted = task.status === "COMPLETED";
            const isRunning = task.status === "RUNNING" || task.status === "PENDING";
            const isFailed = task.status === "FAILED";
            const totalHits = task.phone_count + task.email_count;

            return (
              <div 
                key={task.id}
                onMouseEnter={() => api.setTaskCache(task)}
                className="p-5 bg-white border border-gray-200 rounded-2xl shadow-xs flex flex-col lg:flex-row lg:items-center justify-between gap-6 hover:border-orange-200 hover:shadow-md transition-all group"
              >
                
                {/* Details info */}
                <div className="space-y-2 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-bold text-gray-500 bg-gray-100 px-2 py-0.5 rounded border border-gray-200">{task.public_task_id}</span>
                    <span className={`text-[9px] uppercase font-extrabold tracking-wider px-2 py-0.5 rounded border ${
                      isCompleted ? "bg-emerald-50 border-emerald-200 text-emerald-700" :
                      isRunning ? "bg-orange-50 border-orange-200 text-orange-700 animate-pulse" :
                      isFailed ? "bg-red-50 border-red-200 text-red-700" :
                      "bg-gray-100 border-gray-200 text-gray-600"
                    }`}>
                      {task.status}
                    </span>
                  </div>

                  <h3 className="text-sm font-bold text-gray-900 flex flex-wrap items-center gap-x-2 gap-y-1">
                    <span className="flex items-center gap-1"><Tag className="h-4 w-4 text-orange-500" /> {task.keyword}</span>
                    <span className="text-gray-400 font-normal">in</span>
                    <span className="flex items-center gap-1 text-orange-600"><MapPin className="h-4 w-4 text-orange-500" /> {task.location}</span>
                  </h3>

                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[10px] text-gray-500 font-semibold">
                    <span className="flex items-center gap-1">
                      <Calendar className="h-3.5 w-3.5 text-gray-400" /> Created: {new Date(task.created_at).toLocaleDateString()} at {new Date(task.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                    {task.completed_at && (
                      <span className="flex items-center gap-1 text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded">
                        <CheckCircle className="h-3 w-3 text-emerald-600" /> Done: {new Date(task.completed_at).toLocaleDateString()} at {new Date(task.completed_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    )}
                  </div>
                </div>

                {/* Target limit info */}
                <div className="w-full lg:w-36 space-y-1 text-xs text-gray-600 font-medium">
                  <div><span className="font-bold text-gray-800">Target Max:</span> {task.max_results} orgs</div>
                  <div><span className="font-bold text-gray-800">Depth:</span> {task.max_pages_per_site} pages/site</div>
                </div>

                {/* Hits stats */}
                <div className="flex flex-wrap items-center gap-2.5">
                  <div className="px-3 py-1.5 bg-orange-50 rounded-xl border border-orange-200 text-center min-w-[65px]">
                    <p className="text-[9px] text-orange-700 font-bold uppercase">Results</p>
                    <p className="text-xs font-black text-orange-900 mt-0.5">{task.lead_count ?? totalHits}</p>
                  </div>
                  <div className="px-3 py-1.5 bg-gray-50 rounded-xl border border-gray-200 text-center min-w-[60px]">
                    <p className="text-[9px] text-gray-500 font-bold uppercase">Domains</p>
                    <p className="text-xs font-black text-gray-900 mt-0.5">{task.websites_found}</p>
                  </div>
                  <div className="px-3 py-1.5 bg-gray-50 rounded-xl border border-gray-200 text-center min-w-[60px]">
                    <p className="text-[9px] text-gray-500 font-bold uppercase">Phones</p>
                    <p className="text-xs font-black text-indigo-600 mt-0.5">{task.phone_count}</p>
                  </div>
                  <div className="px-3 py-1.5 bg-gray-50 rounded-xl border border-gray-200 text-center min-w-[60px]">
                    <p className="text-[9px] text-gray-500 font-bold uppercase">Emails</p>
                    <p className="text-xs font-black text-blue-600 mt-0.5">{task.email_count}</p>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 border-t lg:border-t-0 border-gray-100 pt-4 lg:pt-0">
                  {isCompleted && totalHits > 0 && (
                    <>
                      <button
                        onClick={() => handleSecureExport(task.public_task_id, "csv")}
                        disabled={exporting !== null}
                        className="p-2.5 rounded-xl bg-white hover:bg-gray-50 border border-gray-200 text-gray-600 hover:text-gray-900 transition-colors disabled:opacity-50"
                        title="Export CSV"
                      >
                        <Download className="h-4 w-4 text-orange-500" />
                      </button>
                      <button
                        onClick={() => handleSecureExport(task.public_task_id, "excel")}
                        disabled={exporting !== null}
                        className="p-2.5 rounded-xl bg-white hover:bg-gray-50 border border-gray-200 text-gray-600 hover:text-gray-900 transition-colors disabled:opacity-50"
                        title="Export Excel"
                      >
                        <FileSpreadsheet className="h-4 w-4 text-emerald-600" />
                      </button>
                    </>
                  )}
                  <Link
                    href={`/tasks/${task.public_task_id}`}
                    className="flex items-center gap-1.5 bg-orange-50 hover:bg-orange-500 border border-orange-200 hover:border-transparent text-orange-700 hover:text-white px-4 py-2 rounded-xl text-xs font-bold transition-all"
                  >
                    View Task
                    <ArrowRight className="h-3.5 w-3.5 transform group-hover:translate-x-0.5 transition-transform" />
                  </Link>
                </div>

              </div>
            );
          })}
        </div>
      )}

    </div>
  );
}
