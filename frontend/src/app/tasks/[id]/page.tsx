"use client";

import React, { useEffect, useState, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { 
  Sparkles, Globe, Mail, Phone, MapPin, Tag, ShieldAlert, Search,
  Loader2, Download, Trash2, Copy, ExternalLink, Calendar,
  ListRestart, Play, Ban, FileSpreadsheet, CheckCircle, AlertTriangle, Info, X
} from "lucide-react";
import { api, ScrapingTask, ScrapingLog, Lead } from "@/lib/api";
import { useToast } from "@/components/AppLayout";

export default function TaskDetailsPage() {
  const params = useParams();
  const router = useRouter();
  const { showToast } = useToast();
  const taskId = params.id as string;

  const [task, setTask] = useState<ScrapingTask | null>(null);
  const [logs, setLogs] = useState<ScrapingLog[]>([]);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState<string | null>(null);

  // Table states
  const [search, setSearch] = useState("");
  const [confidenceFilter, setConfidenceFilter] = useState("ALL");
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
  const pollingRef = useRef<NodeJS.Timeout | null>(null);

  const [taskError, setTaskError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function fetchInitialData() {
      try {
        setLoading(true);
        setTaskError(null);
        const t = await api.getTask(taskId);
        if (isMounted) setTask(t);

        try {
          const l = await api.getTaskLogs(taskId);
          if (isMounted) setLogs(l);
        } catch (logErr) {
          console.error("Failed to fetch logs", logErr);
        }

        try {
          const le = await api.getTaskLeads(taskId);
          if (isMounted) setLeads(le);
        } catch (leadErr) {
          console.error("Failed to fetch leads", leadErr);
        }

      } catch (err: any) {
        if (isMounted) {
          setTaskError(err.message || "Error loading scraping task details.");
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    fetchInitialData();

    return () => {
      isMounted = false;
    };
  }, [taskId]);

  // Safe Polling Loop
  useEffect(() => {
    if (!task) return;
    
    const isFinished = ["COMPLETED", "COMPLETED_BELOW_MINIMUM", "COMPLETED_WITH_NO_RESULTS", "FAILED", "CANCELLED"].includes(task.status);
    
    if (isFinished) {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
      return;
    }

    if (!pollingRef.current) {
      pollingRef.current = setInterval(async () => {
        try {
          const updatedTask = await api.getTask(taskId);
          setTask(updatedTask);
          
          try {
            const updatedLogs = await api.getTaskLogs(taskId);
            setLogs(updatedLogs);
          } catch (e) {}

          try {
            const updatedLeads = await api.getTaskLeads(taskId);
            setLeads(updatedLeads);
          } catch (e) {}
          
          if (["COMPLETED", "COMPLETED_BELOW_MINIMUM", "COMPLETED_WITH_NO_RESULTS", "FAILED", "CANCELLED"].includes(updatedTask.status)) {
            if (pollingRef.current) {
              clearInterval(pollingRef.current);
              pollingRef.current = null;
            }
          }
        } catch (err) {
          console.error("Silent polling error", err);
        }
      }, 1500);
    }

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [task?.status, taskId]);

  const handleCancel = async () => {
    if (!confirm("Are you sure you want to cancel this scraping task?")) return;
    try {
      await api.cancelTask(taskId);
      showToast("Cancellation request submitted.", "info");
      const updated = await api.getTask(taskId);
      setTask(updated);
    } catch (err: any) {
      showToast(err.message || "Failed to cancel task.", "error");
    }
  };

  const handleDeleteLead = async (leadId: number) => {
    if (!confirm("Are you sure you want to delete this lead?")) return;
    try {
      await api.deleteLead(leadId);
      showToast("Lead deleted successfully.", "success");
      setLeads((prev) => prev.filter((l) => l.id !== leadId));
      if (selectedLead?.id === leadId) setSelectedLead(null);
    } catch (err: any) {
      showToast("Failed to delete lead.", "error");
    }
  };

  const handleSecureExport = async (format: "csv" | "excel") => {
    setExporting(format);
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
      showToast(`Exported leads to ${format.toUpperCase()} successfully.`, "success");
    } catch (err: any) {
      showToast(err.message || `Failed to export ${format.toUpperCase()}.`, "error");
    } finally {
      setExporting(null);
    }
  };

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    showToast(`Copied ${label} to clipboard.`, "success");
  };

  // Filtered Leads list
  const filteredLeads = leads.filter((lead) => {
    const matchesSearch = 
      lead.name.toLowerCase().includes(search.toLowerCase()) ||
      (lead.city || "").toLowerCase().includes(search.toLowerCase()) ||
      lead.email_addresses.some(e => e.email.toLowerCase().includes(search.toLowerCase())) ||
      lead.phone_numbers.some(p => p.normalized_value.includes(search));
      
    const matchesConf = confidenceFilter === "ALL" || lead.confidence === confidenceFilter;
    
    return matchesSearch && matchesConf;
  });

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-4">
        <Loader2 className="h-10 w-10 text-orange-500 animate-spin" />
        <p className="text-sm font-semibold text-gray-600">Loading scraping session details...</p>
      </div>
    );
  }

  if (!task) return null;

  const isRunning = task.status === "RUNNING" || task.status === "PENDING";
  const isCompleted = task.status === "COMPLETED";
  const isBelowMinimum = task.status === "COMPLETED_BELOW_MINIMUM";
  const isZeroResults = task.status === "COMPLETED_WITH_NO_RESULTS";
  const isFailed = task.status === "FAILED";

  return (
    <div className="space-y-8 max-w-7xl">
      
      {/* HEADER SECTION */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 bg-white border border-gray-200 rounded-2xl p-6 shadow-sm">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono font-bold text-gray-500 bg-gray-100 px-2 py-0.5 rounded border border-gray-200">{task.public_task_id}</span>
            <span className={`text-[10px] uppercase font-extrabold tracking-wider px-2.5 py-0.5 rounded border ${
              isCompleted ? "bg-emerald-50 border-emerald-200 text-emerald-700" :
              isBelowMinimum ? "bg-amber-50 border-amber-300 text-amber-900" :
              isZeroResults ? "bg-amber-50 border-amber-200 text-amber-800" :
              isRunning ? "bg-orange-50 border-orange-200 text-orange-700 animate-pulse" :
              isFailed ? "bg-red-50 border-red-200 text-red-700" :
              "bg-gray-100 border-gray-200 text-gray-600"
            }`}>
              {task.status.replace(/_/g, " ")}
            </span>
          </div>
          <h1 className="text-xl md:text-2xl font-black text-gray-900 flex items-center gap-2">
            {task.keyword} <span className="text-gray-400 font-normal">in</span> {task.location}
          </h1>
          <div className="flex flex-wrap gap-x-6 gap-y-1.5 text-xs text-gray-500 font-semibold">
            <span className="flex items-center gap-1"><Calendar className="h-4 w-4 text-orange-500" /> Created: {new Date(task.created_at).toLocaleString()}</span>
            <span>Target Target: {Math.min(15, task.max_results)} min</span>
            <span>Max Results: {task.max_results}</span>
            <span>Max Pages/Site: {task.max_pages_per_site}</span>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {isRunning && (
            <button
              onClick={handleCancel}
              className="flex items-center gap-2 bg-red-50 hover:bg-red-100 border border-red-200 text-red-700 px-4 py-2.5 rounded-xl text-xs font-bold transition-all shadow-xs active:scale-[0.98]"
            >
              <Ban className="h-4 w-4" /> Cancel Task
            </button>
          )}

          {!isRunning && leads.length > 0 && (
            <>
              <button
                onClick={() => handleSecureExport("csv")}
                disabled={exporting !== null}
                className="flex items-center gap-2 bg-white hover:bg-gray-50 border border-gray-200 text-gray-700 px-4 py-2.5 rounded-xl text-xs font-bold transition-all shadow-xs disabled:opacity-50"
              >
                <Download className="h-4 w-4 text-orange-500" /> Export CSV
              </button>
              <button
                onClick={() => handleSecureExport("excel")}
                disabled={exporting !== null}
                className="flex items-center gap-2 bg-orange-500 hover:bg-orange-600 text-white px-4 py-2.5 rounded-xl text-xs font-bold transition-all shadow-md shadow-orange-500/20 active:scale-[0.98] disabled:opacity-50"
              >
                <FileSpreadsheet className="h-4 w-4" /> Export Excel
              </button>
            </>
          )}
        </div>
      </div>

      {/* BELOW MINIMUM DIAGNOSTIC ALERT */}
      {isBelowMinimum && (
        <div className="bg-amber-50/90 border border-amber-300 rounded-2xl p-5 flex items-start gap-4">
          <AlertTriangle className="h-6 w-6 text-amber-600 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <h3 className="text-sm font-bold text-amber-900">
              Completed Below Minimum Target ({leads.length} Verified Organizations Found, Target: {Math.min(15, task.max_results)})
            </h3>
            <p className="text-xs text-amber-800 font-medium">
              {task.error_info || `Discovery budget was exhausted. Found ${leads.length} verified organizations matching location and quality filters.`}
            </p>
            <p className="text-[11px] text-amber-700">
              Data Accuracy Priority: Missing organizations were NOT fabricated. Review the Live Monitor Logs for candidate filtering details.
            </p>
          </div>
        </div>
      )}

      {/* ZERO RESULT EXPLANATION ALERT */}
      {isZeroResults && (
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-5 flex items-start gap-4 justify-between">
          <div className="flex items-start gap-4">
            <AlertTriangle className="h-6 w-6 text-amber-600 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <h3 className="text-sm font-bold text-amber-900">NO QUALIFIED LEADS / NO VERIFIED ORGANIZATIONS DISCOVERED</h3>
              <p className="text-xs text-amber-800 font-medium">
                {task.error_info || "Discovery completed but no candidate organizations passed official website or location verification."}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* LIVE PROGRESS STATUS ROW */}
      <div className="space-y-2">
        <div className="flex justify-between items-center text-xs font-bold text-gray-700 px-1">
          <span>Overall Task Progress</span>
          <span className="text-orange-600 font-extrabold">{task.progress}%</span>
        </div>
        <div className="h-3 w-full bg-orange-50 rounded-full overflow-hidden border border-orange-200">
          <div 
            className={`h-full transition-all duration-500 ${isFailed ? "bg-red-500" : isZeroResults ? "bg-amber-500" : isBelowMinimum ? "bg-amber-500" : "bg-orange-500"}`}
            style={{ width: `${task.progress}%` }}
          ></div>
        </div>
      </div>

      {/* DETAILED STATS ROW */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
        
        <div className="bg-white border border-gray-200 p-4 rounded-2xl text-center space-y-1 shadow-xs">
          <p className="text-[10px] text-gray-500 font-bold uppercase tracking-wider">Discovered</p>
          <p className="text-2xl font-black text-gray-900">{task.discovered_count}</p>
        </div>
        
        <div className="bg-white border border-gray-200 p-4 rounded-2xl text-center space-y-1 shadow-xs">
          <p className="text-[10px] text-gray-500 font-bold uppercase tracking-wider">Websites Found</p>
          <p className="text-2xl font-black text-emerald-600">{task.websites_found}</p>
        </div>

        <div className="bg-white border border-gray-200 p-4 rounded-2xl text-center space-y-1 shadow-xs">
          <p className="text-[10px] text-gray-500 font-bold uppercase tracking-wider">Crawled</p>
          <p className="text-2xl font-black text-orange-600">{task.websites_crawled}</p>
        </div>

        <div className="bg-white border border-gray-200 p-4 rounded-2xl text-center space-y-1 shadow-xs">
          <p className="text-[10px] text-gray-500 font-bold uppercase tracking-wider">Emails</p>
          <p className="text-2xl font-black text-blue-600">{task.email_count}</p>
        </div>

        <div className="bg-white border border-gray-200 p-4 rounded-2xl text-center space-y-1 shadow-xs">
          <p className="text-[10px] text-gray-500 font-bold uppercase tracking-wider">Phones</p>
          <p className="text-2xl font-black text-indigo-600">{task.phone_count}</p>
        </div>

        <div className="bg-white border border-gray-200 p-4 rounded-2xl text-center space-y-1 shadow-xs">
          <p className="text-[10px] text-gray-500 font-bold uppercase tracking-wider">Duplicates</p>
          <p className="text-2xl font-black text-amber-600">{task.duplicate_count}</p>
        </div>

        <div className="bg-white border border-gray-200 p-4 rounded-2xl text-center space-y-1 shadow-xs col-span-2 md:col-span-1">
          <p className="text-[10px] text-gray-500 font-bold uppercase tracking-wider">Failures</p>
          <p className="text-2xl font-black text-red-600">{task.failed_count}</p>
        </div>

      </div>

      {/* MAIN CONTENT AREA: LEADS DATA TABLE */}
      <div className="space-y-4">
        
        {/* Filter and Search Bar */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-4 rounded-2xl border border-gray-200 shadow-xs">
              <div className="relative flex-1 max-w-md">
                <Search className="absolute left-3.5 top-3.5 h-4 w-4 text-gray-400" />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search leads by name, email, phone, city..."
                  className="w-full bg-white border border-gray-200 focus:border-orange-500 focus:ring-2 focus:ring-orange-100 focus:outline-none rounded-xl py-2.5 pl-10 pr-4 text-xs text-gray-900 placeholder-gray-400 transition-colors"
                />
              </div>

              <div className="flex items-center gap-2">
                <label className="text-xs font-bold text-gray-600 uppercase tracking-wider">Quality Score:</label>
                <select
                  value={confidenceFilter}
                  onChange={(e) => setConfidenceFilter(e.target.value)}
                  className="bg-white border border-gray-200 text-gray-800 text-xs font-semibold rounded-xl px-4 py-2.5 focus:outline-none focus:border-orange-500"
                >
                  <option value="ALL">All Scores</option>
                  <option value="HIGH">High Confidence</option>
                  <option value="MEDIUM">Medium Confidence</option>
                  <option value="LOW">Low Confidence</option>
                </select>
              </div>
            </div>

            {/* Table and Mobile Card Views */}
            {filteredLeads.length === 0 ? (
              <div className="bg-white border border-gray-200 rounded-2xl py-12 flex flex-col items-center justify-center text-center shadow-xs px-4">
                <Globe className="h-10 w-10 text-gray-300 mb-3" />
                <h4 className="text-sm font-bold text-gray-800">
                  {leads.length === 0 && (isCompleted || isBelowMinimum || isZeroResults)
                    ? "No qualified prospect leads"
                    : leads.length === 0 && isRunning
                    ? "Scraper engine is actively processing target pages..."
                    : "No matching leads found"}
                </h4>
                <p className="text-xs text-gray-500 mt-1 max-w-sm">
                  {leads.length === 0 && isRunning
                    ? "Discovered candidates and extracted contacts will populate automatically as pages are crawled."
                    : leads.length === 0 && (isZeroResults || isBelowMinimum)
                    ? "Discovery completed. Check Live Monitor Logs to review provider candidate evaluation details."
                    : "No leads matched your current search or confidence filter criteria."}
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {/* Desktop Table View */}
                <div className="hidden md:block bg-white border border-gray-200 rounded-2xl overflow-hidden shadow-xs">
                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                      <thead>
                        <tr className="bg-gray-50 text-[10px] text-gray-500 font-extrabold uppercase tracking-wider border-b border-gray-200">
                          <th className="py-4 px-6">Organization</th>
                          <th className="py-4 px-6">Confidence</th>
                          <th className="py-4 px-6">Phone Number</th>
                          <th className="py-4 px-6">Email Address</th>
                          <th className="py-4 px-6">Official Website</th>
                          <th className="py-4 px-6 text-center">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {filteredLeads.map((lead) => {
                          const hasPhone = lead.phone_numbers.length > 0;
                          const hasEmail = lead.email_addresses.length > 0;
                          const hasWeb = lead.website && lead.website.url;
                          
                          return (
                            <tr key={lead.id} className="text-xs text-gray-700 hover:bg-orange-50/40 transition-colors">
                              <td className="py-4 px-6 font-bold text-gray-900">
                                <div>{lead.name}</div>
                                {lead.category && <div className="text-[10px] text-gray-500 font-normal mt-0.5">{lead.category}</div>}
                              </td>
                              <td className="py-4 px-6">
                                <span className={`text-[10px] font-extrabold px-2.5 py-0.5 rounded border ${
                                  lead.confidence === "HIGH" ? "bg-emerald-50 border-emerald-200 text-emerald-700" :
                                  lead.confidence === "MEDIUM" ? "bg-amber-50 border-amber-200 text-amber-700" :
                                  "bg-gray-100 border-gray-200 text-gray-600"
                                }`}>
                                  {lead.confidence}
                                </span>
                              </td>
                              <td className="py-4 px-6 font-semibold">
                                {hasPhone ? (
                                  <div className="flex items-center gap-1">
                                    <span>{lead.phone_numbers[0].normalized_value}</span>
                                    <button 
                                      onClick={() => copyToClipboard(lead.phone_numbers[0].normalized_value, "phone")}
                                      className="p-1 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-600"
                                    >
                                      <Copy className="h-3 w-3" />
                                    </button>
                                  </div>
                                ) : (
                                  <span className="text-gray-400 font-normal italic">Not available</span>
                                )}
                              </td>
                              <td className="py-4 px-6 font-medium">
                                {hasEmail ? (
                                  <div className="flex items-center gap-1">
                                    <span className="truncate max-w-[160px] inline-block">{lead.email_addresses[0].email}</span>
                                    <button 
                                      onClick={() => copyToClipboard(lead.email_addresses[0].email, "email")}
                                      className="p-1 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-600"
                                    >
                                      <Copy className="h-3 w-3" />
                                    </button>
                                  </div>
                                ) : (
                                  <span className="text-gray-400 font-normal italic">Not available</span>
                                )}
                              </td>
                              <td className="py-4 px-6">
                                {hasWeb ? (
                                  <a 
                                    href={lead.website!.url!} 
                                    target="_blank" 
                                    rel="noopener noreferrer"
                                    className="text-orange-600 hover:text-orange-700 flex items-center gap-1 font-semibold group"
                                  >
                                    {lead.website!.domain || lead.website!.url}
                                    <ExternalLink className="h-3 w-3 opacity-0 group-hover:opacity-100" />
                                  </a>
                                ) : (
                                  <span className="text-gray-400 italic">Official website not found</span>
                                )}
                              </td>
                              <td className="py-4 px-6 text-center">
                                <div className="flex items-center justify-center gap-1">
                                  <button
                                    onClick={() => setSelectedLead(lead)}
                                    className="bg-orange-50 border border-orange-200 hover:bg-orange-100 text-orange-700 px-3 py-1.5 rounded-lg font-bold transition-colors text-xs"
                                  >
                                    View Card
                                  </button>
                                  <button
                                    onClick={() => handleDeleteLead(lead.id)}
                                    className="p-2 rounded-lg hover:bg-red-50 text-gray-400 hover:text-red-600 transition-colors"
                                  >
                                    <Trash2 className="h-4 w-4" />
                                  </button>
                                </div>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Mobile Responsive Cards View (< 768px) */}
                <div className="md:hidden space-y-3">
                  {filteredLeads.map((lead) => {
                    const hasPhone = lead.phone_numbers.length > 0;
                    const hasEmail = lead.email_addresses.length > 0;
                    const hasWeb = lead.website && lead.website.url;

                    return (
                      <div key={lead.id} className="bg-white border border-gray-200 rounded-2xl p-4 shadow-xs space-y-3">
                        <div className="flex items-start justify-between">
                          <div>
                            <h4 className="font-bold text-gray-900 text-sm">{lead.name}</h4>
                            {lead.category && <p className="text-xs text-orange-600 font-medium">{lead.category}</p>}
                          </div>
                          <span className={`text-[10px] font-extrabold px-2 py-0.5 rounded border ${
                            lead.confidence === "HIGH" ? "bg-emerald-50 border-emerald-200 text-emerald-700" :
                            lead.confidence === "MEDIUM" ? "bg-amber-50 border-amber-200 text-amber-700" :
                            "bg-gray-100 border-gray-200 text-gray-600"
                          }`}>
                            {lead.confidence} Score
                          </span>
                        </div>

                        <div className="space-y-1.5 text-xs text-gray-600 pt-1">
                          <div className="flex items-center justify-between">
                            <span className="text-gray-400 font-medium">Website:</span>
                            {hasWeb ? (
                              <a href={lead.website!.url!} target="_blank" rel="noopener noreferrer" className="font-semibold text-orange-600 truncate max-w-[180px]">
                                {lead.website!.domain || lead.website!.url}
                              </a>
                            ) : (
                              <span className="text-gray-400 italic">Official website not found</span>
                            )}
                          </div>

                          <div className="flex items-center justify-between">
                            <span className="text-gray-400 font-medium">Phone:</span>
                            <span className="font-semibold text-gray-900">
                              {hasPhone ? lead.phone_numbers[0].normalized_value : "Not available"}
                            </span>
                          </div>

                          <div className="flex items-center justify-between">
                            <span className="text-gray-400 font-medium">Email:</span>
                            <span className="font-semibold text-gray-900 truncate max-w-[180px]">
                              {hasEmail ? lead.email_addresses[0].email : "Not available"}
                            </span>
                          </div>
                        </div>

                        <div className="flex items-center gap-2 pt-2 border-t border-gray-100">
                          <button
                            onClick={() => setSelectedLead(lead)}
                            className="flex-1 py-2 bg-orange-50 text-orange-700 border border-orange-200 rounded-xl text-xs font-bold text-center"
                          >
                            View Card
                          </button>
                          <button
                            onClick={() => handleDeleteLead(lead.id)}
                            className="p-2 bg-red-50 text-red-600 border border-red-200 rounded-xl text-xs font-bold"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

      </div>

      {/* LEAD DETAILS CARD OVERLAY MODAL */}
      {selectedLead && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/50 backdrop-blur-xs p-4">
          <div className="bg-white border border-gray-200 rounded-2xl max-w-2xl w-full max-h-[85vh] overflow-y-auto shadow-2xl p-6 relative animate-in zoom-in-95 duration-150">
            
            <button 
              onClick={() => setSelectedLead(null)}
              className="absolute right-5 top-5 p-2 rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-500 hover:text-gray-800"
            >
              <X className="h-5 w-5" />
            </button>

            {/* Section 1: Organization Information */}
            <div className="border-b border-gray-100 pb-4 pr-12 space-y-1">
              <span className={`text-[10px] font-extrabold px-2.5 py-0.5 rounded border ${
                selectedLead.confidence === "HIGH" ? "bg-emerald-50 border-emerald-200 text-emerald-700" :
                selectedLead.confidence === "MEDIUM" ? "bg-amber-50 border-amber-200 text-amber-700" :
                "bg-gray-100 border-gray-200 text-gray-600"
              }`}>
                {selectedLead.confidence} Confidence Score
              </span>
              <h2 className="text-lg md:text-xl font-bold text-gray-900 mt-2">{selectedLead.name}</h2>
              <p className="text-xs text-orange-600 font-semibold">{selectedLead.category || "General Prospect"}</p>
            </div>

            <div className="py-5 space-y-5">
              
              {/* Section 2: Online Presence (Official Website) */}
              <div className="bg-gray-50 rounded-xl p-4 border border-gray-200 space-y-2">
                <h4 className="text-[10px] text-gray-500 font-bold uppercase tracking-wider">Official Web Domain</h4>
                {selectedLead.website && selectedLead.website.url ? (
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-gray-900">{selectedLead.website.url}</span>
                    <a 
                      href={selectedLead.website.url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="flex items-center gap-1.5 bg-orange-500 hover:bg-orange-600 text-white text-[11px] font-bold px-3 py-1.5 rounded-lg shadow-xs"
                    >
                      Visit Domain <ExternalLink className="h-3.5 w-3.5" />
                    </a>
                  </div>
                ) : (
                  <p className="text-xs text-gray-500 italic">Official website not found</p>
                )}
              </div>

              {/* Section 3: Contact Information */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <h4 className="text-[10px] text-gray-500 font-bold uppercase tracking-wider flex items-center gap-1.5">
                    <Phone className="h-4 w-4 text-orange-500" /> Extracted Phones
                  </h4>
                  {selectedLead.phone_numbers.length === 0 ? (
                    <p className="text-xs text-gray-400 italic">Not available</p>
                  ) : (
                    <div className="space-y-1.5">
                      {selectedLead.phone_numbers.map((p) => (
                        <div key={p.id} className="p-2.5 bg-gray-50 border border-gray-200 rounded-xl text-xs flex items-center justify-between">
                          <div>
                            <span className="font-bold text-gray-900">{p.normalized_value}</span>
                            <span className="text-[9px] uppercase px-1.5 py-0.5 rounded bg-gray-200 text-gray-700 ml-2 font-bold">{p.type}</span>
                            {p.source_page_url && (
                              <a href={p.source_page_url} target="_blank" rel="noopener noreferrer" className="block text-[9px] text-orange-600 hover:underline mt-0.5 truncate max-w-[160px]">
                                Source URL
                              </a>
                            )}
                          </div>
                          <button onClick={() => copyToClipboard(p.normalized_value, "phone")} className="p-1 text-gray-400 hover:text-gray-600">
                            <Copy className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div className="space-y-2">
                  <h4 className="text-[10px] text-gray-500 font-bold uppercase tracking-wider flex items-center gap-1.5">
                    <Mail className="h-4 w-4 text-orange-500" /> Extracted Emails
                  </h4>
                  {selectedLead.email_addresses.length === 0 ? (
                    <p className="text-xs text-gray-400 italic">Not available</p>
                  ) : (
                    <div className="space-y-1.5">
                      {selectedLead.email_addresses.map((e) => (
                        <div key={e.id} className="p-2.5 bg-gray-50 border border-gray-200 rounded-xl text-xs flex items-center justify-between">
                          <div className="truncate pr-2">
                            <span className="font-bold text-gray-900 truncate block">{e.email}</span>
                            {e.source_page_url && (
                              <a href={e.source_page_url} target="_blank" rel="noopener noreferrer" className="block text-[9px] text-orange-600 hover:underline mt-0.5 truncate max-w-[160px]">
                                Source URL
                              </a>
                            )}
                          </div>
                          <button onClick={() => copyToClipboard(e.email, "email")} className="p-1 text-gray-400 hover:text-gray-600">
                            <Copy className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Physical Address */}
              <div className="space-y-2 border-t border-gray-100 pt-4">
                <h4 className="text-[10px] text-gray-500 font-bold uppercase tracking-wider flex items-center gap-1.5">
                  <MapPin className="h-4 w-4 text-orange-500" /> Physical Address
                </h4>
                {selectedLead.address ? (
                  <div className="p-3 bg-gray-50 border border-gray-200 rounded-xl text-xs text-gray-800 font-medium">
                    {selectedLead.address}
                  </div>
                ) : (
                  <p className="text-xs text-gray-400 italic">Not available</p>
                )}
              </div>

              {/* Section 4: Discovery Source Information */}
              <div className="space-y-2 border-t border-gray-100 pt-4">
                <h4 className="text-[10px] text-gray-500 font-bold uppercase tracking-wider">Discovery Source Page</h4>
                {selectedLead.discovery_source_url ? (
                  <a 
                    href={selectedLead.discovery_source_url} 
                    target="_blank" 
                    rel="noopener noreferrer" 
                    className="text-xs text-orange-600 hover:underline font-mono truncate block"
                  >
                    {selectedLead.discovery_source_url}
                  </a>
                ) : (
                  <p className="text-xs text-gray-400 italic">Search Provider Candidate Discovery</p>
                )}
              </div>

            </div>

            <div className="border-t border-gray-100 pt-4 flex justify-between">
              <button
                onClick={() => handleDeleteLead(selectedLead.id)}
                className="flex items-center gap-1.5 bg-red-50 hover:bg-red-100 border border-red-200 text-red-700 px-4 py-2 rounded-xl text-xs font-bold"
              >
                <Trash2 className="h-4 w-4" /> Delete Lead
              </button>
              <button
                onClick={() => setSelectedLead(null)}
                className="bg-white border border-gray-200 hover:bg-gray-50 text-gray-700 px-4 py-2 rounded-xl text-xs font-bold"
              >
                Close Card
              </button>
            </div>

          </div>
        </div>
      )}

    </div>
  );
}
