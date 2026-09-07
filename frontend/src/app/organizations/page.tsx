"use client";

import React, { useEffect, useState } from "react";
import { 
  Building2, Search, Filter, Globe, Phone, Mail, MapPin, 
  ShieldCheck, Loader2, RefreshCw, ChevronLeft, ChevronRight, Share2, Plus, 
  CheckCircle, Trash2, Edit3, ShieldAlert, Layers
} from "lucide-react";
import { api } from "@/lib/api";
import { useToast } from "@/components/AppLayout";

export default function MasterOrganizationsPage() {
  const { showToast } = useToast();

  const [stats, setStats] = useState<{
    total_organizations: number;
    new_today: number;
    updated_today: number;
    verified_websites: number;
    total_phones: number;
    total_emails: number;
  } | null>(null);

  const [districtsList, setDistrictsList] = useState<string[]>([]);
  const [matrix, setMatrix] = useState<any[]>([]);
  const [showRegionalCoverage, setShowRegionalCoverage] = useState(false);

  const [organizations, setOrganizations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(20);
  const [pages, setPages] = useState(1);

  // Filters
  const [search, setSearch] = useState("");
  const [selectedDistrict, setSelectedDistrict] = useState("ALL");
  const [selectedCategory, setSelectedCategory] = useState("ALL");
  const [selectedConfidence, setSelectedConfidence] = useState("ALL");
  const [selectedOrg, setSelectedOrg] = useState<any | null>(null);

  // Add Organization Modal
  const [showAddModal, setShowAddModal] = useState(false);
  const [addLoading, setAddLoading] = useState(false);
  const [newOrgForm, setNewOrgForm] = useState({
    name: "",
    category: "Colleges",
    district: "Chennai",
    city: "",
    address: "",
    phone: "",
    email: "",
    website: "",
    confidence: "LOW"
  });

  const fetchStats = async () => {
    try {
      const s = await api.getOrganizationSummaryStats();
      setStats(s);
    } catch (err) {
      console.error("Failed to load organization stats", err);
    }
  };

  const fetchDistricts = async () => {
    try {
      const dists = await api.getDistrictStats();
      setDistrictsList(dists.map(d => d.district_name));
    } catch (err) {
      console.error("Failed to load district list", err);
    }
  };

  const fetchMatrix = async () => {
    try {
      const mat = await api.getOrganizationMatrix();
      setMatrix(mat);
    } catch (err) {
      console.error("Failed to load matrix data", err);
    }
  };

  const fetchOrgs = async () => {
    try {
      setLoading(true);
      const res = await api.getOrganizations({
        district: selectedDistrict,
        category: selectedCategory,
        confidence: selectedConfidence,
        search: search,
        page: page,
        limit: limit
      });
      setOrganizations(res.organizations);
      setTotal(res.total);
      setPages(res.pages);
    } catch (err: any) {
      showToast(err.message || "Failed to load master organizations.", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
    fetchDistricts();
    fetchMatrix();
  }, []);

  useEffect(() => {
    fetchOrgs();
  }, [selectedDistrict, selectedCategory, selectedConfidence, search, page, limit]);

  const handleAddSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newOrgForm.name || !newOrgForm.category || !newOrgForm.district) {
      showToast("Name, Category, and District/Region are required.", "error");
      return;
    }
    try {
      setAddLoading(true);
      const res = await api.addOrganizationManual(newOrgForm);
      showToast(res.message, "success");
      setShowAddModal(false);
      setNewOrgForm({
        name: "", category: "Colleges", district: "Chennai",
        city: "", address: "", phone: "", email: "", website: "", confidence: "LOW"
      });
      fetchStats();
      fetchOrgs();
      fetchMatrix();
    } catch (err: any) {
      showToast(err.message || "Organization creation failed.", "error");
    } finally {
      setAddLoading(false);
    }
  };

  const handleDeleteOrg = async (id: number, name: string) => {
    if (!confirm(`Are you sure you want to delete organization '${name}'?`)) return;
    try {
      const res = await api.deleteOrganization(id);
      showToast(res.message, "info");
      fetchStats();
      fetchOrgs();
      fetchMatrix();
    } catch (err: any) {
      showToast(err.message || "Failed to delete organization.", "error");
    }
  };

  const handleVerifyOrg = async (id: number) => {
    try {
      const res = await api.verifyOrganization(id);
      showToast(res.message, "success");
      fetchOrgs();
      fetchStats();
    } catch (err: any) {
      showToast(err.message || "Failed to verify organization.", "error");
    }
  };

  const handleUnverifyOrg = async (id: number) => {
    try {
      const res = await api.unverifyOrganization(id);
      showToast(res.message, "info");
      fetchOrgs();
      fetchStats();
    } catch (err: any) {
      showToast(err.message || "Failed to unverify organization.", "error");
    }
  };

  return (
    <div className="space-y-8 max-w-7xl">
      {/* HEADER SECTION */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white border border-gray-200 p-6 rounded-2xl shadow-xs">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="bg-orange-50 text-orange-600 font-extrabold text-[10px] uppercase tracking-wider px-2.5 py-0.5 rounded border border-orange-200 flex items-center gap-1">
              <Building2 className="h-3 w-3" /> Master Directory
            </span>
            <span className="bg-emerald-50 text-emerald-700 font-extrabold text-[10px] uppercase tracking-wider px-2.5 py-0.5 rounded border border-emerald-200">
              1000+ REAL ORGS TARGET ({stats?.total_organizations || 0} / 1000+)
            </span>
          </div>
          <h1 className="text-2xl font-black text-gray-900">Verified Master Organizations</h1>
          <p className="text-xs font-semibold text-gray-500">
            Persistent real-world entity database across 38 TN Districts + Puducherry.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-2 bg-orange-500 hover:bg-orange-600 text-white px-4 py-2.5 rounded-xl text-xs font-bold transition-all shadow-sm"
          >
            <Plus className="h-4 w-4" /> + ADD ORGANIZATION
          </button>
          <button
            onClick={() => { fetchStats(); fetchOrgs(); fetchMatrix(); }}
            className="flex items-center gap-2 bg-white hover:bg-gray-50 border border-gray-200 text-gray-700 px-4 py-2.5 rounded-xl text-xs font-bold transition-all shadow-xs"
          >
            <RefreshCw className="h-4 w-4 text-orange-500" /> Refresh
          </button>
        </div>
      </div>

      {/* STATS OVERVIEW CARDS */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <div className="bg-white border border-gray-200 p-4 rounded-2xl text-center space-y-1 shadow-xs">
            <p className="text-[10px] text-gray-500 font-bold uppercase tracking-wider">Total Organizations</p>
            <p className="text-2xl font-black text-gray-900">{stats.total_organizations}</p>
          </div>
          <div className="bg-white border border-gray-200 p-4 rounded-2xl text-center space-y-1 shadow-xs">
            <p className="text-[10px] text-gray-500 font-bold uppercase tracking-wider">New Today</p>
            <p className="text-2xl font-black text-emerald-600">+{stats.new_today}</p>
          </div>
          <div className="bg-white border border-gray-200 p-4 rounded-2xl text-center space-y-1 shadow-xs">
            <p className="text-[10px] text-gray-500 font-bold uppercase tracking-wider">Updated Today</p>
            <p className="text-2xl font-black text-amber-600">{stats.updated_today}</p>
          </div>
          <div className="bg-white border border-gray-200 p-4 rounded-2xl text-center space-y-1 shadow-xs">
            <p className="text-[10px] text-gray-500 font-bold uppercase tracking-wider">Active Websites</p>
            <p className="text-2xl font-black text-blue-600">{stats.verified_websites}</p>
          </div>
          <div className="bg-white border border-gray-200 p-4 rounded-2xl text-center space-y-1 shadow-xs">
            <p className="text-[10px] text-gray-500 font-bold uppercase tracking-wider">Verified Phones</p>
            <p className="text-2xl font-black text-indigo-600">{stats.total_phones}</p>
          </div>
          <div className="bg-white border border-gray-200 p-4 rounded-2xl text-center space-y-1 shadow-xs">
            <p className="text-[10px] text-gray-500 font-bold uppercase tracking-wider">Verified Emails</p>
            <p className="text-2xl font-black text-purple-600">{stats.total_emails}</p>
          </div>
        </div>
      )}

      {/* REGIONAL COVERAGE TOGGLE */}
      <div className="bg-white border border-gray-200 rounded-2xl overflow-hidden shadow-xs">
        <button
          onClick={() => setShowRegionalCoverage(!showRegionalCoverage)}
          className="w-full p-4 flex items-center justify-between font-bold text-sm text-gray-800 hover:bg-gray-50 transition-colors"
        >
          <span className="flex items-center gap-2">
            <Layers className="h-4 w-4 text-orange-500" /> REGIONAL COVERAGE (38 TN Districts + Puducherry)
          </span>
          <span className="text-xs text-orange-600 font-bold">
            {showRegionalCoverage ? "Hide Matrix" : "View Breakdown Matrix"}
          </span>
        </button>

        {showRegionalCoverage && (
          <div className="p-4 border-t border-gray-200 overflow-x-auto max-h-[400px]">
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-gray-100 font-bold text-gray-700 uppercase text-[10px]">
                <tr>
                  <th className="p-2">Region</th>
                  <th className="p-2 text-center">Colleges</th>
                  <th className="p-2 text-center">Schools</th>
                  <th className="p-2 text-center">Hotels</th>
                  <th className="p-2 text-center">Hospitals</th>
                  <th className="p-2 text-center">Companies</th>
                  <th className="p-2 text-center">IT Companies</th>
                  <th className="p-2 text-right">Total</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 font-medium text-gray-800">
                {matrix.map((row) => (
                  <tr key={row.region} className="hover:bg-orange-50/30">
                    <td className="p-2 font-bold">{row.region}</td>
                    <td className="p-2 text-center">{row.colleges}</td>
                    <td className="p-2 text-center">{row.schools}</td>
                    <td className="p-2 text-center">{row.hotels}</td>
                    <td className="p-2 text-center">{row.hospitals}</td>
                    <td className="p-2 text-center">{row.companies}</td>
                    <td className="p-2 text-center">{row.it_companies}</td>
                    <td className="p-2 text-right font-black text-gray-900">{row.total}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* CONTROLS & FILTERING BAR */}
      <div className="bg-white border border-gray-200 p-4 rounded-2xl space-y-4 shadow-xs">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          
          {/* Search bar */}
          <div className="relative">
            <Search className="h-4 w-4 text-gray-400 absolute left-3 top-3.5" />
            <input
              type="text"
              placeholder="Search by name or keyword..."
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
              className="w-full pl-9 pr-4 py-2.5 text-xs font-semibold border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-orange-500 bg-gray-50/50"
            />
          </div>

          {/* District selector */}
          <div>
            <select
              value={selectedDistrict}
              onChange={(e) => { setSelectedDistrict(e.target.value); setPage(1); }}
              className="w-full px-3 py-2.5 text-xs font-semibold border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-orange-500 bg-gray-50/50"
            >
              <option value="ALL">All Districts (38 TN + Puducherry)</option>
              <option value="Puducherry">Puducherry UT</option>
              {districtsList.map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </div>

          {/* Category selector */}
          <div>
            <select
              value={selectedCategory}
              onChange={(e) => { setSelectedCategory(e.target.value); setPage(1); }}
              className="w-full px-3 py-2.5 text-xs font-semibold border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-orange-500 bg-gray-50/50"
            >
              <option value="ALL">All Categories</option>
              <option value="Colleges">Colleges & Universities</option>
              <option value="Hotels">Hotels & Hospitality</option>
              <option value="Hospitals">Hospitals & Healthcare</option>
              <option value="Companies">Companies & Business</option>
              <option value="IT Companies">IT & Software Companies</option>
              <option value="Schools">Schools & CBSE Institutions</option>
            </select>
          </div>

          {/* Confidence selector */}
          <div>
            <select
              value={selectedConfidence}
              onChange={(e) => { setSelectedConfidence(e.target.value); setPage(1); }}
              className="w-full px-3 py-2.5 text-xs font-semibold border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-orange-500 bg-gray-50/50"
            >
              <option value="ALL">All Confidence Levels</option>
              <option value="HIGH">HIGH Confidence</option>
              <option value="MEDIUM">MEDIUM Confidence</option>
              <option value="LOW">LOW Confidence</option>
            </select>
          </div>

        </div>
      </div>

      {/* ORGANIZATIONS TABLE */}
      <div className="bg-white border border-gray-200 rounded-2xl overflow-hidden shadow-xs">
        {loading ? (
          <div className="flex flex-col items-center justify-center py-20 gap-3">
            <Loader2 className="h-8 w-8 text-orange-500 animate-spin" />
            <p className="text-xs font-bold text-gray-500">Querying Master Database...</p>
          </div>
        ) : organizations.length === 0 ? (
          <div className="text-center py-20 px-4 space-y-2">
            <Building2 className="h-10 w-10 text-gray-300 mx-auto" />
            <p className="text-sm font-bold text-gray-700">No organizations match current filter criteria.</p>
            <p className="text-xs text-gray-500">Try broadening your search or resetting filters.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-gray-50/80 border-b border-gray-200 font-bold text-gray-600 uppercase tracking-wider text-[10px]">
                  <th className="py-3.5 px-4">Organization Name</th>
                  <th className="py-3.5 px-4">Category</th>
                  <th className="py-3.5 px-4">District / City</th>
                  <th className="py-3.5 px-4">Website</th>
                  <th className="py-3.5 px-4">Phones</th>
                  <th className="py-3.5 px-4">Emails</th>
                  <th className="py-3.5 px-4">Verification</th>
                  <th className="py-3.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 font-medium text-gray-800">
                {organizations.map((org) => (
                  <tr key={org.id} className="hover:bg-orange-50/30 transition-colors">
                    <td className="py-3.5 px-4 font-bold text-gray-900">{org.name}</td>
                    <td className="py-3.5 px-4">
                      <span className="bg-gray-100 text-gray-700 font-semibold px-2 py-0.5 rounded text-[11px]">
                        {org.category || "General"}
                      </span>
                    </td>
                    <td className="py-3.5 px-4">
                      {org.district || org.city || "Tamil Nadu"}
                    </td>
                    <td className="py-3.5 px-4">
                      {org.website?.url ? (
                        <a
                          href={org.website.url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-orange-600 hover:underline flex items-center gap-1 font-semibold"
                        >
                          <Globe className="h-3 w-3 shrink-0" />
                          <span className="truncate max-w-[140px]">{org.website.domain || "Website"}</span>
                        </a>
                      ) : (
                        <span className="text-gray-400 italic text-[11px]">Not available</span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 font-mono">
                      {org.phones && org.phones.length > 0 ? (
                        <span className="text-indigo-700 font-bold">{org.phones[0].normalized}</span>
                      ) : (
                        <span className="text-gray-400 italic text-[11px]">Not available</span>
                      )}
                    </td>
                    <td className="py-3.5 px-4">
                      {org.emails && org.emails.length > 0 ? (
                        <span className="text-blue-700 font-semibold">{org.emails[0].email}</span>
                      ) : (
                        <span className="text-gray-400 italic text-[11px]">Not available</span>
                      )}
                    </td>
                    <td className="py-3.5 px-4">
                      <span className={`text-[10px] font-extrabold uppercase px-2 py-0.5 rounded border ${
                        org.admin_verified ? "bg-blue-50 border-blue-200 text-blue-700" :
                        org.confidence === "HIGH" ? "bg-emerald-50 border-emerald-200 text-emerald-700" :
                        org.confidence === "MEDIUM" ? "bg-blue-50 border-blue-200 text-blue-700" :
                        "bg-amber-50 border-amber-200 text-amber-700"
                      }`}>
                        {org.admin_verified ? "ADMIN VERIFIED" : `${org.confidence} CONFIDENCE`}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-right flex items-center justify-end gap-2">
                      <button
                        onClick={() => setSelectedOrg(org)}
                        className="text-orange-600 hover:text-orange-700 font-bold text-[11px]"
                      >
                        View
                      </button>
                      {org.admin_verified ? (
                        <button
                          onClick={() => handleUnverifyOrg(org.id)}
                          className="text-amber-600 hover:text-amber-700 font-bold text-[11px]"
                        >
                          Unverify
                        </button>
                      ) : (
                        <button
                          onClick={() => handleVerifyOrg(org.id)}
                          className="text-emerald-600 hover:text-emerald-700 font-bold text-[11px]"
                        >
                          Verify
                        </button>
                      )}
                      <button
                        onClick={() => handleDeleteOrg(org.id, org.name)}
                        className="text-red-600 hover:text-red-700 font-bold text-[11px]"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* PAGINATION FOOTER */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-4 border-t border-gray-200 bg-gray-50/50">
          <div className="text-xs font-semibold text-gray-500">
            Showing Page <span className="font-bold text-gray-900">{page}</span> of <span className="font-bold text-gray-900">{pages || 1}</span> ({total} total organizations)
          </div>

          <div className="flex items-center gap-2">
            <select
              value={limit}
              onChange={(e) => { setLimit(Number(e.target.value)); setPage(1); }}
              className="px-2 py-1.5 text-xs font-bold border border-gray-200 rounded-lg bg-white"
            >
              <option value={20}>20 per page</option>
              <option value={50}>50 per page</option>
              <option value={100}>100 per page</option>
            </select>

            <button
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              className="p-1.5 border border-gray-200 rounded-lg bg-white hover:bg-gray-50 disabled:opacity-40"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <button
              disabled={page >= pages}
              onClick={() => setPage((p) => p + 1)}
              className="p-1.5 border border-gray-200 rounded-lg bg-white hover:bg-gray-50 disabled:opacity-40"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      {/* ADD ORGANIZATION MODAL */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl">
            <div className="flex justify-between items-center border-b border-gray-100 pb-3">
              <h2 className="text-lg font-bold text-gray-900">+ Add Master Organization</h2>
              <button onClick={() => setShowAddModal(false)} className="text-gray-400 hover:text-gray-600 font-bold">✕</button>
            </div>

            <form onSubmit={handleAddSubmit} className="space-y-3 text-xs">
              <div>
                <label className="block font-bold text-gray-700 mb-1">Organization Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Sona College of Technology"
                  value={newOrgForm.name}
                  onChange={(e) => setNewOrgForm({...newOrgForm, name: e.target.value})}
                  className="w-full p-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500 font-semibold"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block font-bold text-gray-700 mb-1">Category *</label>
                  <select
                    value={newOrgForm.category}
                    onChange={(e) => setNewOrgForm({...newOrgForm, category: e.target.value})}
                    className="w-full p-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500 font-semibold"
                  >
                    <option value="Colleges">Colleges</option>
                    <option value="Schools">Schools</option>
                    <option value="Hotels">Hotels</option>
                    <option value="Hospitals">Hospitals</option>
                    <option value="Companies">Companies</option>
                    <option value="IT Companies">IT Companies</option>
                  </select>
                </div>
                <div>
                  <label className="block font-bold text-gray-700 mb-1">Region / District *</label>
                  <select
                    value={newOrgForm.district}
                    onChange={(e) => setNewOrgForm({...newOrgForm, district: e.target.value})}
                    className="w-full p-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500 font-semibold"
                  >
                    <option value="Puducherry">Puducherry (UT)</option>
                    {districtsList.map((d) => (
                      <option key={d} value={d}>{d}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block font-bold text-gray-700 mb-1">City</label>
                  <input
                    type="text"
                    placeholder="City / Town"
                    value={newOrgForm.city}
                    onChange={(e) => setNewOrgForm({...newOrgForm, city: e.target.value})}
                    className="w-full p-2.5 border border-gray-300 rounded-xl font-semibold"
                  />
                </div>
                <div>
                  <label className="block font-bold text-gray-700 mb-1">Phone Number</label>
                  <input
                    type="text"
                    placeholder="+91 44 24501234"
                    value={newOrgForm.phone}
                    onChange={(e) => setNewOrgForm({...newOrgForm, phone: e.target.value})}
                    className="w-full p-2.5 border border-gray-300 rounded-xl font-semibold"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block font-bold text-gray-700 mb-1">Email Address</label>
                  <input
                    type="email"
                    placeholder="info@org.edu.in"
                    value={newOrgForm.email}
                    onChange={(e) => setNewOrgForm({...newOrgForm, email: e.target.value})}
                    className="w-full p-2.5 border border-gray-300 rounded-xl font-semibold"
                  />
                </div>
                <div>
                  <label className="block font-bold text-gray-700 mb-1">Official Website</label>
                  <input
                    type="url"
                    placeholder="https://org.edu.in"
                    value={newOrgForm.website}
                    onChange={(e) => setNewOrgForm({...newOrgForm, website: e.target.value})}
                    className="w-full p-2.5 border border-gray-300 rounded-xl font-semibold"
                  />
                </div>
              </div>

              <div>
                <label className="block font-bold text-gray-700 mb-1">Full Physical Address</label>
                <textarea
                  rows={2}
                  placeholder="Street address, landmark, pincode..."
                  value={newOrgForm.address}
                  onChange={(e) => setNewOrgForm({...newOrgForm, address: e.target.value})}
                  className="w-full p-2.5 border border-gray-300 rounded-xl font-semibold"
                />
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-xl font-bold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={addLoading}
                  className="px-4 py-2 bg-orange-500 hover:bg-orange-600 text-white rounded-xl font-bold flex items-center gap-1.5"
                >
                  {addLoading && <Loader2 className="h-4 w-4 animate-spin" />}
                  Save Master Record
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* FULL DETAILS DRAWER MODAL */}
      {selectedOrg && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-2xl w-full p-6 space-y-6 max-h-[90vh] overflow-y-auto shadow-2xl">
            <div className="flex justify-between items-start border-b border-gray-100 pb-4">
              <div>
                <span className="text-[10px] font-bold text-orange-600 bg-orange-50 px-2 py-0.5 rounded border border-orange-200 uppercase">
                  {selectedOrg.category || "Organization"}
                </span>
                <h2 className="text-xl font-black text-gray-900 mt-1">{selectedOrg.name}</h2>
                <p className="text-xs text-gray-500 font-semibold flex items-center gap-1 mt-0.5">
                  <MapPin className="h-3.5 w-3.5 text-orange-500" /> {selectedOrg.district || selectedOrg.city || "Tamil Nadu"}
                </p>
              </div>
              <button
                onClick={() => setSelectedOrg(null)}
                className="text-gray-400 hover:text-gray-600 p-1 font-bold text-lg"
              >
                ✕
              </button>
            </div>

            {/* Address */}
            <div className="space-y-1 bg-gray-50 p-3.5 rounded-xl border border-gray-200 text-xs">
              <span className="font-bold text-gray-500 uppercase tracking-wider text-[10px]">Physical Address</span>
              <p className="font-semibold text-gray-800">{selectedOrg.address || "Not publicly available"}</p>
            </div>

            {/* Phones List */}
            <div className="space-y-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-gray-500">Phone Numbers</h3>
              {selectedOrg.phones && selectedOrg.phones.length > 0 ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {selectedOrg.phones.map((p: any, i: number) => (
                    <div key={i} className="p-2.5 bg-indigo-50/50 border border-indigo-100 rounded-xl text-xs flex justify-between items-center">
                      <span className="font-mono font-bold text-indigo-900">{p.normalized}</span>
                      <span className="text-[10px] uppercase font-bold text-indigo-600 bg-indigo-100 px-1.5 rounded">{p.type}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs italic text-gray-400">Not available</p>
              )}
            </div>

            {/* Emails List */}
            <div className="space-y-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-gray-500">Email Addresses</h3>
              {selectedOrg.emails && selectedOrg.emails.length > 0 ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {selectedOrg.emails.map((e: any, i: number) => (
                    <div key={i} className="p-2.5 bg-blue-50/50 border border-blue-100 rounded-xl text-xs font-semibold text-blue-900">
                      {e.email}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs italic text-gray-400">Not available</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
