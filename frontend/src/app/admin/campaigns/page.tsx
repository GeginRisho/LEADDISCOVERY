"use client";

import React, { useState, useEffect } from "react";
import { 
  Sparkles, Play, Pause, XCircle, RotateCw, CheckCircle2, 
  AlertCircle, Building2, MapPin, Layers, RefreshCw, Loader2, ArrowRight
} from "lucide-react";
import { api } from "@/lib/api";
import { useToast } from "@/components/AppLayout";

export default function AdminCampaignsPage() {
  const { showToast } = useToast();

  const [campaigns, setCampaigns] = useState<any[]>([]);
  const [selectedCampaign, setSelectedCampaign] = useState<any | null>(null);
  const [matrix, setMatrix] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);

  // Form states
  const [selectedCategory, setSelectedCategory] = useState("Colleges");
  const [maxResults, setMaxResults] = useState(15);
  const [activeTab, setActiveTab] = useState<"matrix" | "campaigns">("matrix");

  const loadData = async () => {
    try {
      setLoading(true);
      const [cmps, matData] = await Promise.all([
        api.getCampaigns(),
        api.getOrganizationMatrix()
      ]);
      setCampaigns(cmps);
      setMatrix(matData);
      if (selectedCampaign) {
        const updated = cmps.find((c: any) => c.id === selectedCampaign.id);
        if (updated) {
          const detail = await api.getCampaignDetail(updated.id);
          setSelectedCampaign(detail);
        }
      }
    } catch (err: any) {
      showToast(err.message || "Failed to load discovery campaigns.", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(() => {
      api.getCampaigns().then((cmps) => {
        setCampaigns(cmps);
        if (selectedCampaign) {
          api.getCampaignDetail(selectedCampaign.id).then(setSelectedCampaign).catch(() => {});
        }
      }).catch(() => {});
      api.getOrganizationMatrix().then(setMatrix).catch(() => {});
    }, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleRunTN = async () => {
    try {
      setActionLoading(true);
      const res = await api.runAllTamilNadu(selectedCategory, maxResults);
      showToast(res.message, "success");
      loadData();
      setActiveTab("campaigns");
    } catch (err: any) {
      showToast(err.message || "Failed to launch Tamil Nadu campaign.", "error");
    } finally {
      setActionLoading(false);
    }
  };

  const handleRunPuducherry = async () => {
    try {
      setActionLoading(true);
      const res = await api.runPuducherry(selectedCategory, maxResults);
      showToast(res.message, "success");
      loadData();
      setActiveTab("campaigns");
    } catch (err: any) {
      showToast(err.message || "Failed to launch Puducherry campaign.", "error");
    } finally {
      setActionLoading(false);
    }
  };

  const handleRunAllRegions = async () => {
    try {
      setActionLoading(true);
      const res = await api.runAllRegions(selectedCategory, maxResults);
      showToast(res.message, "success");
      loadData();
      setActiveTab("campaigns");
    } catch (err: any) {
      showToast(err.message || "Failed to launch All Regions campaign.", "error");
    } finally {
      setActionLoading(false);
    }
  };

  const handleResume = async (campaignId: number) => {
    try {
      setActionLoading(true);
      const res = await api.resumeCampaign(campaignId);
      showToast(res.message, "success");
      loadData();
    } catch (err: any) {
      showToast(err.message || "Failed to resume campaign.", "error");
    } finally {
      setActionLoading(false);
    }
  };

  const handlePause = async (campaignId: number) => {
    try {
      setActionLoading(true);
      const res = await api.pauseCampaign(campaignId);
      showToast(res.message, "info");
      loadData();
    } catch (err: any) {
      showToast(err.message || "Failed to pause campaign.", "error");
    } finally {
      setActionLoading(false);
    }
  };

  const handleCancel = async (campaignId: number) => {
    try {
      setActionLoading(true);
      const res = await api.cancelCampaign(campaignId);
      showToast(res.message, "info");
      loadData();
    } catch (err: any) {
      showToast(err.message || "Failed to cancel campaign.", "error");
    } finally {
      setActionLoading(false);
    }
  };

  const selectCampaign = async (cmpId: number) => {
    try {
      const detail = await api.getCampaignDetail(cmpId);
      setSelectedCampaign(detail);
      setActiveTab("campaigns");
    } catch (err: any) {
      showToast(err.message || "Failed to load campaign detail.", "error");
    }
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* HEADER SECTION */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-6 rounded-2xl border border-gray-200 shadow-sm">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-extrabold bg-orange-100 text-orange-700 uppercase tracking-wider flex items-center gap-1">
              <Sparkles className="h-3 w-3" /> Regional Discovery Engine
            </span>
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Regional Discovery Campaigns</h1>
          <p className="text-xs text-gray-500 font-semibold">
            Proactively populate Master Organization Database across 38 Tamil Nadu Districts + Puducherry.
          </p>
        </div>

        <button
          onClick={loadData}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 shadow-xs"
        >
          <RefreshCw className={`h-4 w-4 text-orange-500 ${loading ? "animate-spin" : ""}`} />
          Refresh Campaign Matrix
        </button>
      </div>

      {/* QUICK LAUNCH BULK CONTROL PANEL */}
      <div className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm space-y-4">
        <div className="flex items-center justify-between border-b border-gray-100 pb-3">
          <div>
            <h2 className="text-base font-bold text-gray-900">Bulk Campaign Dispatcher</h2>
            <p className="text-xs text-gray-500">Launch automated discovery campaigns across entire regions without manual district search.</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
          {/* Category Selector */}
          <div>
            <label className="block text-xs font-bold text-gray-700 mb-1">Target Organization Category</label>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="w-full px-3 py-2.5 text-xs font-bold border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500 bg-gray-50/50"
            >
              <option value="Colleges">Colleges & Universities</option>
              <option value="Hotels">Hotels & Hospitality</option>
              <option value="Hospitals">Hospitals & Healthcare</option>
              <option value="Companies">Companies & Corporations</option>
              <option value="IT Companies">IT & Software Companies</option>
              <option value="Schools">Schools & Institutions</option>
              <option value="CBSE Schools">CBSE Schools</option>
            </select>
          </div>

          {/* Max results per district */}
          <div>
            <label className="block text-xs font-bold text-gray-700 mb-1">Max Results Per District</label>
            <input
              type="number"
              min={5}
              max={100}
              value={maxResults}
              onChange={(e) => setMaxResults(Number(e.target.value))}
              className="w-full px-3 py-2.5 text-xs font-bold border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500 bg-gray-50/50"
            />
          </div>

          {/* Action buttons */}
          <div className="flex flex-wrap gap-2">
            <button
              onClick={handleRunTN}
              disabled={actionLoading}
              className="flex-1 px-3 py-2.5 bg-orange-500 hover:bg-orange-600 text-white rounded-xl text-xs font-extrabold shadow-sm flex items-center justify-center gap-1.5 transition-all"
            >
              <Play className="h-3.5 w-3.5 fill-current" />
              [ RUN ALL TAMIL NADU ]
            </button>
            <button
              onClick={handleRunPuducherry}
              disabled={actionLoading}
              className="px-3 py-2.5 bg-sky-600 hover:bg-sky-700 text-white rounded-xl text-xs font-extrabold shadow-sm flex items-center justify-center gap-1.5 transition-all"
            >
              <Play className="h-3.5 w-3.5 fill-current" />
              [ RUN PUDUCHERRY ]
            </button>
            <button
              onClick={handleRunAllRegions}
              disabled={actionLoading}
              className="w-full sm:w-auto px-3 py-2.5 bg-gray-900 hover:bg-black text-white rounded-xl text-xs font-extrabold shadow-sm flex items-center justify-center gap-1.5 transition-all"
            >
              <Sparkles className="h-3.5 w-3.5 text-orange-400" />
              [ RUN TAMIL NADU + PUDUCHERRY ]
            </button>
          </div>
        </div>
      </div>

      {/* NAVIGATION TABS */}
      <div className="flex items-center gap-2 border-b border-gray-200 pb-2">
        <button
          onClick={() => setActiveTab("matrix")}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 ${
            activeTab === "matrix"
              ? "bg-orange-500 text-white shadow-sm"
              : "bg-white text-gray-600 hover:bg-gray-100 border border-gray-200"
          }`}
        >
          <Layers className="h-4 w-4" /> Regional Coverage Matrix (PostgreSQL DB)
        </button>
        <button
          onClick={() => setActiveTab("campaigns")}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 ${
            activeTab === "campaigns"
              ? "bg-orange-500 text-white shadow-sm"
              : "bg-white text-gray-600 hover:bg-gray-100 border border-gray-200"
          }`}
        >
          <Building2 className="h-4 w-4" /> Active & Historical Campaigns ({campaigns.length})
        </button>
      </div>

      {/* TAB 1: REGIONAL MATRIX */}
      {activeTab === "matrix" && (
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden space-y-4 p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-gray-900">Regional Organization Database Matrix</h2>
              <p className="text-xs text-gray-500 font-semibold">
                Live cross-tabulation across 38 TN Districts + Puducherry. All numbers reflect actual records stored in PostgreSQL.
              </p>
            </div>
          </div>

          <div className="overflow-x-auto max-h-[600px] overflow-y-auto border border-gray-200 rounded-xl">
            <table className="w-full text-left text-xs border-collapse">
              <thead className="sticky top-0 bg-gray-900 text-white text-[10px] uppercase font-bold tracking-wider z-10">
                <tr>
                  <th className="py-3 px-4">Region / District</th>
                  <th className="py-3 px-4 text-center">Colleges</th>
                  <th className="py-3 px-4 text-center">Schools</th>
                  <th className="py-3 px-4 text-center">Hotels</th>
                  <th className="py-3 px-4 text-center">Hospitals</th>
                  <th className="py-3 px-4 text-center">Companies</th>
                  <th className="py-3 px-4 text-center">IT Companies</th>
                  <th className="py-3 px-4 text-right">Total Verified</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 font-semibold text-gray-800">
                {matrix.map((row) => (
                  <tr key={row.region} className={`hover:bg-orange-50/40 transition-colors ${row.region === "Puducherry" ? "bg-sky-50/50 font-bold" : ""}`}>
                    <td className="py-2.5 px-4 font-bold text-gray-900 flex items-center gap-1.5">
                      <MapPin className="h-3.5 w-3.5 text-orange-500" />
                      {row.region} {row.region === "Puducherry" && <span className="text-[10px] bg-sky-100 text-sky-800 px-1.5 py-0.5 rounded uppercase">UT</span>}
                    </td>
                    <td className="py-2.5 px-4 text-center">{row.colleges > 0 ? <span className="text-emerald-700 font-extrabold">{row.colleges}</span> : <span className="text-gray-400 font-normal">0</span>}</td>
                    <td className="py-2.5 px-4 text-center">{row.schools > 0 ? <span className="text-emerald-700 font-extrabold">{row.schools}</span> : <span className="text-gray-400 font-normal">0</span>}</td>
                    <td className="py-2.5 px-4 text-center">{row.hotels > 0 ? <span className="text-emerald-700 font-extrabold">{row.hotels}</span> : <span className="text-gray-400 font-normal">0</span>}</td>
                    <td className="py-2.5 px-4 text-center">{row.hospitals > 0 ? <span className="text-emerald-700 font-extrabold">{row.hospitals}</span> : <span className="text-gray-400 font-normal">0</span>}</td>
                    <td className="py-2.5 px-4 text-center">{row.companies > 0 ? <span className="text-emerald-700 font-extrabold">{row.companies}</span> : <span className="text-gray-400 font-normal">0</span>}</td>
                    <td className="py-2.5 px-4 text-center">{row.it_companies > 0 ? <span className="text-emerald-700 font-extrabold">{row.it_companies}</span> : <span className="text-gray-400 font-normal">0</span>}</td>
                    <td className="py-2.5 px-4 text-right font-black text-gray-900">{row.total}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 2: CAMPAIGN DETAILS & DISPATCH LOG */}
      {activeTab === "campaigns" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Campaign List */}
          <div className="bg-white p-5 rounded-2xl border border-gray-200 shadow-sm space-y-3">
            <h2 className="text-sm font-bold text-gray-900 uppercase tracking-wider text-[11px] text-gray-500">Discovery Campaign History</h2>
            
            <div className="space-y-2 max-h-[550px] overflow-y-auto pr-1">
              {campaigns.map((cmp) => (
                <div
                  key={cmp.id}
                  onClick={() => selectCampaign(cmp.id)}
                  className={`p-3.5 rounded-xl border cursor-pointer transition-all ${
                    selectedCampaign?.id === cmp.id
                      ? "bg-orange-50 border-orange-300 ring-2 ring-orange-400/30"
                      : "bg-gray-50/60 border-gray-200 hover:bg-gray-100"
                  }`}
                >
                  <div className="flex justify-between items-start mb-1">
                    <h3 className="font-bold text-xs text-gray-900 truncate pr-2">{cmp.name}</h3>
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-extrabold uppercase ${
                      cmp.status === "COMPLETED" ? "bg-emerald-100 text-emerald-800" :
                      cmp.status === "RUNNING" ? "bg-amber-100 text-amber-800 animate-pulse" :
                      cmp.status === "PAUSED" ? "bg-blue-100 text-blue-800" : "bg-gray-100 text-gray-800"
                    }`}>
                      {cmp.status}
                    </span>
                  </div>

                  <div className="flex justify-between text-[11px] text-gray-500 font-semibold mt-2">
                    <span>Districts: {cmp.completed_regions} / {cmp.total_regions}</span>
                    <span className="text-orange-600 font-bold">Discovered: {cmp.discovered_count}</span>
                  </div>
                </div>
              ))}

              {campaigns.length === 0 && (
                <p className="text-xs text-gray-400 italic text-center py-8">No campaigns launched yet.</p>
              )}
            </div>
          </div>

          {/* Selected Campaign Detail Panel */}
          <div className="lg:col-span-2 bg-white p-6 rounded-2xl border border-gray-200 shadow-sm space-y-6">
            {selectedCampaign ? (
              <>
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-gray-100 pb-4">
                  <div>
                    <span className="text-[10px] font-extrabold uppercase tracking-wider text-orange-600 bg-orange-50 px-2 py-0.5 rounded border border-orange-200">
                      Campaign #{selectedCampaign.id} ({selectedCampaign.region_scope})
                    </span>
                    <h2 className="text-xl font-black text-gray-900 mt-1">{selectedCampaign.name}</h2>
                    <p className="text-xs text-gray-500 font-semibold">Category: <span className="font-bold text-gray-800">{selectedCampaign.category}</span></p>
                  </div>

                  <div className="flex items-center gap-2">
                    {selectedCampaign.status === "RUNNING" && (
                      <button
                        onClick={() => handlePause(selectedCampaign.id)}
                        className="px-3 py-1.5 bg-amber-500 hover:bg-amber-600 text-white text-xs font-bold rounded-lg flex items-center gap-1"
                      >
                        <Pause className="h-3.5 w-3.5 fill-current" /> Pause
                      </button>
                    )}
                    {(selectedCampaign.status === "PAUSED" || selectedCampaign.status === "FAILED") && (
                      <button
                        onClick={() => handleResume(selectedCampaign.id)}
                        className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-lg flex items-center gap-1"
                      >
                        <RotateCw className="h-3.5 w-3.5" /> Resume Campaign
                      </button>
                    )}
                    {selectedCampaign.status !== "CANCELLED" && selectedCampaign.status !== "COMPLETED" && (
                      <button
                        onClick={() => handleCancel(selectedCampaign.id)}
                        className="px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white text-xs font-bold rounded-lg flex items-center gap-1"
                      >
                        <XCircle className="h-3.5 w-3.5" /> Cancel
                      </button>
                    )}
                  </div>
                </div>

                {/* Progress metrics */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="bg-gray-50 p-3 rounded-xl text-center border border-gray-200">
                    <p className="text-[10px] text-gray-500 font-bold uppercase">Completed Regions</p>
                    <p className="text-lg font-black text-gray-900">{selectedCampaign.completed_regions} / {selectedCampaign.total_regions}</p>
                  </div>
                  <div className="bg-gray-50 p-3 rounded-xl text-center border border-gray-200">
                    <p className="text-[10px] text-gray-500 font-bold uppercase">Discovered Orgs</p>
                    <p className="text-lg font-black text-orange-600">{selectedCampaign.discovered_count}</p>
                  </div>
                  <div className="bg-gray-50 p-3 rounded-xl text-center border border-gray-200">
                    <p className="text-[10px] text-gray-500 font-bold uppercase">New Master Orgs</p>
                    <p className="text-lg font-black text-emerald-600">+{selectedCampaign.new_orgs_count}</p>
                  </div>
                  <div className="bg-gray-50 p-3 rounded-xl text-center border border-gray-200">
                    <p className="text-[10px] text-gray-500 font-bold uppercase">Updated Existing</p>
                    <p className="text-lg font-black text-blue-600">{selectedCampaign.updated_orgs_count}</p>
                  </div>
                </div>

                {/* District breakdown table */}
                <div className="space-y-2">
                  <h3 className="text-xs font-bold uppercase text-gray-600 tracking-wider">Per-District Processing Status</h3>

                  <div className="overflow-x-auto max-h-[350px] overflow-y-auto border border-gray-200 rounded-xl">
                    <table className="w-full text-left text-xs border-collapse">
                      <thead className="bg-gray-100 text-gray-700 text-[10px] uppercase font-bold">
                        <tr>
                          <th className="py-2.5 px-4">District / Region</th>
                          <th className="py-2.5 px-4">Status</th>
                          <th className="py-2.5 px-4 text-center">Discovered</th>
                          <th className="py-2.5 px-4 text-center">New</th>
                          <th className="py-2.5 px-4 text-center">Updated</th>
                          <th className="py-2.5 px-4 text-center">Failed</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100 font-medium text-gray-800">
                        {selectedCampaign.items?.map((item: any) => (
                          <tr key={item.id} className="hover:bg-gray-50">
                            <td className="py-2 px-4 font-bold text-gray-900">{item.region_name}</td>
                            <td className="py-2 px-4">
                              <span className={`px-2 py-0.5 rounded text-[10px] font-extrabold uppercase ${
                                item.status === "COMPLETED" ? "bg-emerald-100 text-emerald-800" :
                                item.status === "RUNNING" ? "bg-amber-100 text-amber-800 animate-pulse" :
                                item.status === "FAILED" ? "bg-red-100 text-red-800" : "bg-gray-100 text-gray-600"
                              }`}>
                                {item.status}
                              </span>
                            </td>
                            <td className="py-2 px-4 text-center font-bold">{item.discovered_count}</td>
                            <td className="py-2 px-4 text-center text-emerald-600 font-bold">{item.new_orgs_count}</td>
                            <td className="py-2 px-4 text-center text-blue-600 font-bold">{item.updated_orgs_count}</td>
                            <td className="py-2 px-4 text-center text-red-600 font-bold">{item.failed_count}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </>
            ) : (
              <div className="flex flex-col items-center justify-center py-20 text-gray-400 space-y-2">
                <Building2 className="h-10 w-10 text-gray-300" />
                <p className="text-sm font-bold text-gray-600">Select a campaign from the history list to inspect per-district progress.</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
