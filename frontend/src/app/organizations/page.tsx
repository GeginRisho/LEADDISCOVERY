"use client";

import React, { useEffect, useState } from "react";
import { 
  Building2, Search, Filter, Globe, Phone, Mail, MapPin, 
  ShieldCheck, Loader2, RefreshCw, ChevronLeft, ChevronRight, Share2, Plus, 
  CheckCircle, Trash2, Edit3, ShieldAlert, Layers, ExternalLink, X, Map,
  Link as LinkIcon, GitBranch, AlertTriangle
} from "lucide-react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useToast } from "@/components/AppLayout";

export default function MasterOrganizationsPage() {
  const router = useRouter();
  const { showToast } = useToast();

  const [accessDenied, setAccessDenied] = useState(false);

  const [stats, setStats] = useState<{
    total_organizations: number;
    new_today: number;
    updated_today: number;
    verified_websites: number;
    total_phones: number;
    total_emails: number;
  } | null>(null);

  const [districtsList, setDistrictsList] = useState<string[]>([]);
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
  const [selectedCountry, setSelectedCountry] = useState("ALL");
  const [selectedState, setSelectedState] = useState("ALL");
  const [selectedCity, setSelectedCity] = useState("");
  const [selectedVerificationStatus, setSelectedVerificationStatus] = useState("ALL");

  // Modals
  const [selectedOrg, setSelectedOrg] = useState<any | null>(null); // View Modal
  const [showFormModal, setShowFormModal] = useState(false); // Add/Edit Modal
  const [editingOrgId, setEditingOrgId] = useState<number | null>(null);
  const [activeFormTab, setActiveFormTab] = useState<
    "identity" | "location" | "contact" | "website" | "social" | "other_links" | "branches" | "verification"
  >("identity");

  const [formLoading, setFormLoading] = useState(false);

  // Initial Form State
  const initialFormState = {
    name: "",
    display_name: "",
    category: "Colleges",
    sub_category: "",
    description: "",
    country: "India",
    state: "Tamil Nadu",
    district: "Chennai",
    city: "",
    address: "",
    pincode: "",
    // Contact
    primary_phone: "",
    secondary_phone: "",
    whatsapp_phone: "",
    emergency_phone: "",
    general_email: "",
    admissions_email: "",
    support_email: "",
    hr_email: "",
    // Website & Maps
    official_website_url: "",
    google_maps_url: "",
    // Social
    facebook_url: "",
    instagram_url: "",
    linkedin_url: "",
    youtube_url: "",
    x_url: "",
    whatsapp_url: "",
    // Verification
    admin_verified: true,
    is_quarantined: false,
    quarantine_reason: "",
    // Dynamic lists
    other_links: [] as Array<{ label: string; url: string; link_type: string }>,
    branches: [] as Array<{
      branch_name: string;
      country: string;
      state: string;
      district: string;
      city: string;
      address: string;
      pincode: string;
      website_url: string;
      maps_url: string;
      phone: string;
      email: string;
    }>
  };

  const [form, setForm] = useState(initialFormState);

  const checkAccessError = (err: any) => {
    if (err?.status === 403 || err?.message?.includes("403") || err?.message?.includes("Admin privileges required")) {
      setAccessDenied(true);
      return true;
    }
    return false;
  };

  const fetchStats = async () => {
    try {
      const s = await api.getOrganizationSummaryStats();
      setStats(s);
    } catch (err: any) {
      if (!checkAccessError(err)) {
        console.error("Failed to load organization stats", err);
      }
    }
  };

  const fetchDistricts = async () => {
    try {
      const dists = await api.getDistrictStats();
      setDistrictsList(dists.map(d => d.district_name));
    } catch (err: any) {
      if (!checkAccessError(err)) {
        console.error("Failed to load district list", err);
      }
    }
  };

  const fetchOrgs = async () => {
    try {
      setLoading(true);
      const res = await api.getOrganizations({
        district: selectedDistrict,
        category: selectedCategory,
        country: selectedCountry,
        state: selectedState,
        city: selectedCity,
        verification_status: selectedVerificationStatus,
        search: search,
        page: page,
        limit: limit
      });
      setOrganizations(res.organizations);
      setTotal(res.total);
      setPages(res.pages);
    } catch (err: any) {
      if (!checkAccessError(err)) {
        showToast(err.message || "Failed to load master organizations.", "error");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let isMounted = true;
    const loadAllData = async () => {
      setLoading(true);
      await Promise.allSettled([
        api.getOrganizationSummaryStats().then(s => { if (isMounted) setStats(s); }).catch(err => checkAccessError(err)),
        api.getDistrictStats().then(dists => { if (isMounted) setDistrictsList(dists.map(d => d.district_name)); }).catch(err => checkAccessError(err)),
        api.getOrganizations({
          district: selectedDistrict,
          category: selectedCategory,
          country: selectedCountry,
          state: selectedState,
          city: selectedCity,
          verification_status: selectedVerificationStatus,
          search: search,
          page: page,
          limit: limit
        }).then(res => {
          if (isMounted) {
            setOrganizations(res.organizations);
            setTotal(res.total);
            setPages(res.pages);
          }
        }).catch(err => {
          if (isMounted && !checkAccessError(err)) {
            showToast(err.message || "Failed to load master organizations.", "error");
          }
        })
      ]);
      if (isMounted) setLoading(false);
    };

    loadAllData();
    return () => { isMounted = false; };
  }, [selectedDistrict, selectedCategory, selectedCountry, selectedState, selectedCity, selectedVerificationStatus, search, page, limit]);

  const openAddModal = () => {
    setEditingOrgId(null);
    setForm(initialFormState);
    setActiveFormTab("identity");
    setShowFormModal(true);
  };

  const openEditModal = (org: any) => {
    setEditingOrgId(org.id);
    const mainPhone = org.phones?.[0]?.raw || "";
    const secondaryPhone = org.phones?.[1]?.raw || "";
    const mainEmail = org.emails?.[0]?.email || "";
    const admissionsEmail = org.emails?.[1]?.email || "";

    setForm({
      name: org.name || "",
      display_name: org.display_name || "",
      category: org.category || "",
      sub_category: org.sub_category || "",
      description: org.description || "",
      country: org.country || "India",
      state: org.state || "",
      district: org.district || "",
      city: org.city || "",
      address: org.address || "",
      pincode: org.pincode || "",
      primary_phone: mainPhone,
      secondary_phone: secondaryPhone,
      whatsapp_phone: org.whatsapp_url ? org.whatsapp_url.replace("https://wa.me/", "") : "",
      emergency_phone: "",
      general_email: mainEmail,
      admissions_email: admissionsEmail,
      support_email: "",
      hr_email: "",
      official_website_url: org.official_website_url || org.website?.url || "",
      google_maps_url: org.google_maps_url || "",
      facebook_url: org.facebook_url || "",
      instagram_url: org.instagram_url || "",
      linkedin_url: org.linkedin_url || "",
      youtube_url: org.youtube_url || "",
      x_url: org.x_url || "",
      whatsapp_url: org.whatsapp_url || "",
      admin_verified: org.admin_verified ?? true,
      is_quarantined: org.is_quarantined ?? false,
      quarantine_reason: org.quarantine_reason || "",
      other_links: org.other_links ? [...org.other_links] : [],
      branches: org.branches ? org.branches.map((b: any) => ({
        branch_name: b.branch_name || "",
        country: b.country || "India",
        state: b.state || "",
        district: b.district || "",
        city: b.city || "",
        address: b.address || "",
        pincode: b.pincode || "",
        website_url: b.website_url || "",
        maps_url: b.maps_url || "",
        phone: b.phone_numbers?.[0] || "",
        email: b.email_addresses?.[0] || ""
      })) : []
    });
    setActiveFormTab("identity");
    setShowFormModal(true);
  };

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim() || !form.category.trim() || !form.district.trim() || !form.country.trim()) {
      showToast("Organization Name, Category, Country, and District are required.", "error");
      return;
    }

    // Build payload
    const phoneList = [];
    if (form.primary_phone.trim()) phoneList.push({ raw_value: form.primary_phone.trim(), type: "PRIMARY" });
    if (form.secondary_phone.trim()) phoneList.push({ raw_value: form.secondary_phone.trim(), type: "SECONDARY" });
    if (form.whatsapp_phone.trim()) phoneList.push({ raw_value: form.whatsapp_phone.trim(), type: "WHATSAPP" });
    if (form.emergency_phone.trim()) phoneList.push({ raw_value: form.emergency_phone.trim(), type: "EMERGENCY" });

    const emailList = [];
    if (form.general_email.trim()) emailList.push({ email: form.general_email.trim(), extraction_method: "admin_entry" });
    if (form.admissions_email.trim()) emailList.push({ email: form.admissions_email.trim(), extraction_method: "admissions" });
    if (form.support_email.trim()) emailList.push({ email: form.support_email.trim(), extraction_method: "support" });
    if (form.hr_email.trim()) emailList.push({ email: form.hr_email.trim(), extraction_method: "hr" });

    const branchesList = form.branches.map(b => ({
      branch_name: b.branch_name.trim(),
      country: b.country.trim() || "India",
      state: b.state.trim() || form.state,
      district: b.district.trim() || form.district,
      city: b.city.trim() || b.district.trim(),
      address: b.address.trim(),
      pincode: b.pincode.trim(),
      website_url: b.website_url.trim(),
      maps_url: b.maps_url.trim(),
      phone_numbers: b.phone.trim() ? [b.phone.trim()] : [],
      email_addresses: b.email.trim() ? [b.email.trim()] : []
    }));

    const payload = {
      name: form.name.trim(),
      display_name: form.display_name.trim() || null,
      category: form.category.trim(),
      sub_category: form.sub_category.trim() || null,
      description: form.description.trim() || null,
      country: form.country.trim(),
      state: form.state.trim(),
      district: form.district.trim(),
      city: form.city.trim() || form.district.trim(),
      address: form.address.trim() || null,
      pincode: form.pincode.trim() || null,
      official_website_url: form.official_website_url.trim() || null,
      website: form.official_website_url.trim() || null,
      google_maps_url: form.google_maps_url.trim() || null,
      facebook_url: form.facebook_url.trim() || null,
      instagram_url: form.instagram_url.trim() || null,
      linkedin_url: form.linkedin_url.trim() || null,
      youtube_url: form.youtube_url.trim() || null,
      x_url: form.x_url.trim() || null,
      whatsapp_url: form.whatsapp_url.trim() || null,
      admin_verified: form.admin_verified,
      is_quarantined: form.is_quarantined,
      quarantine_reason: form.quarantine_reason.trim() || null,
      phone_numbers: phoneList,
      email_addresses: emailList,
      other_links: form.other_links.filter(l => l.label.trim() && l.url.trim()),
      branches: branchesList
    };

    try {
      setFormLoading(true);
      if (editingOrgId) {
        await api.updateAdminOrganization(editingOrgId, payload);
        showToast("Organization updated successfully.", "success");
      } else {
        await api.createAdminOrganization(payload);
        showToast("Organization added successfully.", "success");
      }
      setShowFormModal(false);
      fetchStats();
      fetchOrgs();
    } catch (err: any) {
      showToast(err.message || "Failed to save organization.", "error");
    } finally {
      setFormLoading(false);
    }
  };

  const handleDeleteOrg = async (id: number, name: string) => {
    if (!confirm(`Are you sure you want to delete organization '${name}'?`)) return;
    try {
      const res = await api.deleteOrganization(id);
      showToast(res.message, "info");
      fetchStats();
      fetchOrgs();
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

  // Helper dynamic row manipulators
  const addOtherLinkRow = () => {
    setForm(prev => ({
      ...prev,
      other_links: [...prev.other_links, { label: "", url: "", link_type: "PORTAL" }]
    }));
  };

  const removeOtherLinkRow = (idx: number) => {
    setForm(prev => ({
      ...prev,
      other_links: prev.other_links.filter((_, i) => i !== idx)
    }));
  };

  const addBranchRow = () => {
    setForm(prev => ({
      ...prev,
      branches: [
        ...prev.branches,
        {
          branch_name: "",
          country: "India",
          state: prev.state || "Tamil Nadu",
          district: "",
          city: "",
          address: "",
          pincode: "",
          website_url: "",
          maps_url: "",
          phone: "",
          email: ""
        }
      ]
    }));
  };

  const removeBranchRow = (idx: number) => {
    setForm(prev => ({
      ...prev,
      branches: prev.branches.filter((_, i) => i !== idx)
    }));
  };

  if (accessDenied) {
    return (
      <div className="max-w-xl mx-auto my-12 p-8 bg-white rounded-3xl border border-red-200 shadow-xl text-center space-y-6 animate-in fade-in-20">
        <div className="h-16 w-16 bg-red-50 text-red-500 rounded-2xl flex items-center justify-center mx-auto border border-red-100">
          <ShieldAlert className="h-8 w-8" />
        </div>
        <div className="space-y-2">
          <h2 className="text-2xl font-black text-gray-900 tracking-tight">Access Denied: Admin Privileges Required</h2>
          <p className="text-sm text-gray-600 font-medium leading-relaxed">
            Master Organizations is a restricted administrative database interface. Your account does not have authorization to view or manage these records.
          </p>
        </div>
        <div className="pt-2">
          <button
            onClick={() => router.push("/")}
            className="w-full bg-orange-500 hover:bg-orange-600 text-white font-bold py-3.5 px-6 rounded-xl transition-all shadow-md shadow-orange-500/20"
          >
            Return to Dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* HEADER SECTION */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white border border-gray-200 p-6 rounded-2xl shadow-xs">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="bg-orange-50 text-orange-600 font-extrabold text-[10px] uppercase tracking-wider px-2.5 py-0.5 rounded border border-orange-200 flex items-center gap-1">
              <Building2 className="h-3 w-3" /> Master Directory
            </span>
            <span className="bg-emerald-50 text-emerald-700 font-extrabold text-[10px] uppercase tracking-wider px-2.5 py-0.5 rounded border border-emerald-200">
              {stats?.total_organizations || total} Verified Records
            </span>
          </div>
          <h1 className="text-2xl font-black text-gray-900">Master Organizations Database</h1>
          <p className="text-xs font-semibold text-gray-500">
            Persistent real-world master index supporting multi-branch organizations across any category and location.
          </p>
        </div>

        <button
          onClick={openAddModal}
          className="flex items-center justify-center gap-2 bg-orange-500 hover:bg-orange-600 text-white px-5 py-3 rounded-xl text-xs font-black tracking-wide transition-all shadow-sm"
        >
          <Plus className="h-4 w-4" /> + ADD ORGANIZATION
        </button>
      </div>

      {/* STATS OVERVIEW CARDS */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
          <div className="bg-white p-4 rounded-xl border border-gray-200">
            <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Total Orgs</p>
            <p className="text-lg font-black text-gray-900 mt-1">{stats.total_organizations}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-gray-200">
            <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">New Today</p>
            <p className="text-lg font-black text-emerald-600 mt-1">+{stats.new_today}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-gray-200">
            <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Websites</p>
            <p className="text-lg font-black text-blue-600 mt-1">{stats.verified_websites}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-gray-200">
            <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Phones</p>
            <p className="text-lg font-black text-purple-600 mt-1">{stats.total_phones}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-gray-200">
            <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Emails</p>
            <p className="text-lg font-black text-amber-600 mt-1">{stats.total_emails}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-gray-200">
            <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Updated</p>
            <p className="text-lg font-black text-sky-600 mt-1">{stats.updated_today}</p>
          </div>
        </div>
      )}

      {/* FILTER & CONTROL BAR */}
      <div className="bg-white p-5 rounded-2xl border border-gray-200 shadow-xs space-y-4">
        <div className="flex flex-col md:flex-row items-center gap-3">
          {/* Search Box */}
          <div className="relative flex-1 w-full">
            <Search className="absolute left-3.5 top-3 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search by organization name, category, district, city..."
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
              className="w-full pl-10 pr-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-orange-500 focus:bg-white transition-all"
            />
          </div>

          {/* Verification Status Filter */}
          <select
            value={selectedVerificationStatus}
            onChange={(e) => { setSelectedVerificationStatus(e.target.value); setPage(1); }}
            className="w-full md:w-48 px-3 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-xs font-bold text-gray-700 focus:outline-none focus:ring-2 focus:ring-orange-500"
          >
            <option value="ALL">All Verification Statuses</option>
            <option value="ADMIN_VERIFIED">ADMIN VERIFIED</option>
            <option value="SCRAPER_VERIFIED">SCRAPER VERIFIED</option>
            <option value="UNVERIFIED">UNVERIFIED</option>
            <option value="QUARANTINED">QUARANTINED</option>
          </select>
        </div>

        {/* Secondary Filters */}
        <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-5 gap-3 pt-2 border-t border-gray-100">
          {/* Category Input / Suggestions */}
          <div>
            <label className="block text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-1">Category</label>
            <input
              type="text"
              placeholder="e.g. Hotel, School, Bank"
              value={selectedCategory === "ALL" ? "" : selectedCategory}
              onChange={(e) => { setSelectedCategory(e.target.value || "ALL"); setPage(1); }}
              className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-xs font-semibold focus:ring-1 focus:ring-orange-500"
            />
          </div>

          {/* District Selector */}
          <div>
            <label className="block text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-1">District</label>
            <select
              value={selectedDistrict}
              onChange={(e) => { setSelectedDistrict(e.target.value); setPage(1); }}
              className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-xs font-semibold focus:ring-1 focus:ring-orange-500"
            >
              <option value="ALL">All Districts</option>
              {districtsList.map(d => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </div>

          {/* City Filter */}
          <div>
            <label className="block text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-1">City / Town</label>
            <input
              type="text"
              placeholder="e.g. Puducherry"
              value={selectedCity}
              onChange={(e) => { setSelectedCity(e.target.value); setPage(1); }}
              className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-xs font-semibold focus:ring-1 focus:ring-orange-500"
            />
          </div>

          {/* State / UT Filter */}
          <div>
            <label className="block text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-1">State / UT</label>
            <input
              type="text"
              placeholder="e.g. Puducherry UT"
              value={selectedState === "ALL" ? "" : selectedState}
              onChange={(e) => { setSelectedState(e.target.value || "ALL"); setPage(1); }}
              className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-xs font-semibold focus:ring-1 focus:ring-orange-500"
            />
          </div>

          {/* Page Limit */}
          <div>
            <label className="block text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-1">Rows Per Page</label>
            <select
              value={limit}
              onChange={(e) => { setLimit(Number(e.target.value)); setPage(1); }}
              className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-xs font-semibold focus:ring-1 focus:ring-orange-500"
            >
              <option value={20}>20 rows</option>
              <option value={50}>50 rows</option>
              <option value={100}>100 rows</option>
            </select>
          </div>
        </div>
      </div>

      {/* ORGANIZATIONS LIST */}
      {loading && organizations.length === 0 ? (
        <div className="space-y-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="bg-white p-6 rounded-2xl border border-gray-200 shadow-xs h-32 animate-pulse"></div>
          ))}
        </div>
      ) : organizations.length === 0 ? (
        <div className="p-12 text-center bg-white rounded-2xl border border-gray-200">
          <Building2 className="h-10 w-10 text-gray-300 mx-auto mb-3" />
          <h3 className="text-sm font-bold text-gray-800">No organizations found</h3>
          <p className="text-xs text-gray-500 mt-1">Try adjusting your filters or search terms.</p>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-4">
            {organizations.map((org) => {
              const isAdminVerified = org.admin_verified;
              const isQuarantined = org.is_quarantined;
              const isScraperVerified = !isAdminVerified && org.source_type === "SCRAPER_VERIFIED";

              return (
                <div key={org.id} className="bg-white p-5 rounded-2xl border border-gray-200 shadow-xs hover:border-gray-300 transition-all flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div className="space-y-2 flex-1">
                    {/* Top Badges */}
                    <div className="flex flex-wrap items-center gap-2">
                      {isQuarantined ? (
                        <span className="px-2.5 py-0.5 rounded-md text-[10px] font-extrabold bg-red-100 text-red-800 border border-red-200 flex items-center gap-1">
                          <AlertTriangle className="h-3 w-3 text-red-600" /> QUARANTINED
                        </span>
                      ) : isAdminVerified ? (
                        <span className="px-2.5 py-0.5 rounded-md text-[10px] font-extrabold bg-emerald-100 text-emerald-800 border border-emerald-200 flex items-center gap-1">
                          <ShieldCheck className="h-3 w-3 text-emerald-600" /> ADMIN VERIFIED
                        </span>
                      ) : isScraperVerified ? (
                        <span className="px-2.5 py-0.5 rounded-md text-[10px] font-extrabold bg-sky-100 text-sky-800 border border-sky-200 flex items-center gap-1">
                          <CheckCircle className="h-3 w-3 text-sky-600" /> SCRAPER VERIFIED
                        </span>
                      ) : (
                        <span className="px-2.5 py-0.5 rounded-md text-[10px] font-extrabold bg-gray-100 text-gray-700 border border-gray-200">
                          UNVERIFIED
                        </span>
                      )}

                      <span className="px-2.5 py-0.5 rounded-md text-[10px] font-bold bg-orange-50 text-orange-700 border border-orange-200 uppercase">
                        {org.category}
                      </span>

                      {org.source_type && (
                        <span className="px-2 py-0.5 rounded text-[9px] font-semibold bg-gray-100 text-gray-600">
                          Src: {org.source_type}
                        </span>
                      )}
                    </div>

                    {/* Name & Location */}
                    <div>
                      <h3 className="text-base font-bold text-gray-900 flex items-center gap-2">
                        {org.name}
                        {org.display_name && <span className="text-xs font-normal text-gray-500">({org.display_name})</span>}
                      </h3>
                      <p className="text-xs text-gray-500 flex items-center gap-1 mt-0.5">
                        <MapPin className="h-3.5 w-3.5 text-gray-400 shrink-0" />
                        {org.city || org.district}, {org.district}, {org.state || "India"} ({org.country || "India"})
                      </p>
                    </div>

                    {/* Contact Details & Links */}
                    <div className="flex flex-wrap items-center gap-4 text-xs text-gray-600 pt-1">
                      {org.official_website_url || org.website?.url ? (
                        <a
                          href={org.official_website_url || org.website?.url}
                          target="_blank"
                          rel="noreferrer"
                          className="flex items-center gap-1 text-orange-600 font-semibold hover:underline"
                        >
                          <Globe className="h-3.5 w-3.5" />
                          {(org.official_website_url || org.website?.url).replace("https://", "").replace("http://", "").split("/")[0]}
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      ) : (
                        <span className="text-gray-400 flex items-center gap-1">
                          <Globe className="h-3.5 w-3.5" /> No website
                        </span>
                      )}

                      {org.phones?.length > 0 && (
                        <span className="flex items-center gap-1 text-gray-700">
                          <Phone className="h-3.5 w-3.5 text-gray-400" />
                          {org.phones[0].raw || org.phones[0].normalized}
                          {org.phones.length > 1 && <span className="text-[10px] text-gray-400">(+{org.phones.length - 1})</span>}
                        </span>
                      )}

                      {org.emails?.length > 0 && (
                        <span className="flex items-center gap-1 text-gray-700">
                          <Mail className="h-3.5 w-3.5 text-gray-400" />
                          {org.emails[0].email}
                        </span>
                      )}

                      {org.branches?.length > 0 && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-50 text-indigo-700 border border-indigo-200 flex items-center gap-1">
                          <GitBranch className="h-3 w-3" /> {org.branches.length} Branch{org.branches.length > 1 ? "es" : ""}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2 border-t md:border-t-0 pt-3 md:pt-0 border-gray-100">
                    <button
                      onClick={() => setSelectedOrg(org)}
                      className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg text-xs font-bold transition-all"
                    >
                      View
                    </button>

                    <button
                      onClick={() => openEditModal(org)}
                      className="px-3 py-1.5 bg-white border border-gray-300 hover:bg-gray-50 text-gray-800 rounded-lg text-xs font-bold flex items-center gap-1 transition-all"
                    >
                      <Edit3 className="h-3.5 w-3.5 text-gray-500" /> Edit
                    </button>

                    {isAdminVerified ? (
                      <button
                        onClick={() => handleUnverifyOrg(org.id)}
                        className="px-3 py-1.5 bg-amber-50 hover:bg-amber-100 text-amber-800 border border-amber-300 rounded-lg text-xs font-bold transition-all"
                      >
                        Unverify
                      </button>
                    ) : (
                      <button
                        onClick={() => handleVerifyOrg(org.id)}
                        className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold shadow-xs transition-all flex items-center gap-1"
                      >
                        <ShieldCheck className="h-3.5 w-3.5" /> Verify
                      </button>
                    )}

                    <button
                      onClick={() => handleDeleteOrg(org.id, org.name)}
                      className="p-1.5 text-red-500 hover:bg-red-50 rounded-lg transition-all"
                      title="Delete Organization"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>

          {/* PAGINATION CONTROLS */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 bg-white p-4 rounded-2xl border border-gray-200">
            <p className="text-xs font-semibold text-gray-500">
              Showing <span className="font-bold text-gray-900">{organizations.length}</span> of <span className="font-bold text-gray-900">{total}</span> total organizations
            </p>

            <div className="flex items-center gap-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage(p => Math.max(1, p - 1))}
                className="px-3 py-1.5 rounded-lg border border-gray-200 text-xs font-bold text-gray-700 hover:bg-gray-50 disabled:opacity-40 flex items-center gap-1"
              >
                <ChevronLeft className="h-4 w-4" /> Previous
              </button>

              <span className="text-xs font-bold text-gray-700 px-3">
                Page {page} of {pages || 1}
              </span>

              <button
                disabled={page >= pages}
                onClick={() => setPage(p => Math.min(pages, p + 1))}
                className="px-3 py-1.5 rounded-lg border border-gray-200 text-xs font-bold text-gray-700 hover:bg-gray-50 disabled:opacity-40 flex items-center gap-1"
              >
                Next <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* VIEW ORGANIZATION DETAIL MODAL */}
      {selectedOrg && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4 z-50 overflow-y-auto">
          <div className="bg-white rounded-2xl max-w-2xl w-full p-6 space-y-6 shadow-xl relative max-h-[90vh] overflow-y-auto">
            <button
              onClick={() => setSelectedOrg(null)}
              className="absolute top-4 right-4 p-2 text-gray-400 hover:bg-gray-100 rounded-full"
            >
              <X className="h-5 w-5" />
            </button>

            <div>
              <span className="px-2.5 py-0.5 rounded text-[10px] font-extrabold uppercase bg-orange-100 text-orange-700">
                {selectedOrg.category}
              </span>
              <h2 className="text-xl font-black text-gray-900 mt-1">{selectedOrg.name}</h2>
              {selectedOrg.display_name && <p className="text-xs text-gray-500">Display Name: {selectedOrg.display_name}</p>}
            </div>

            {/* Location & Summary */}
            <div className="bg-gray-50 p-4 rounded-xl border border-gray-200 text-xs space-y-1">
              <p className="font-bold text-gray-800">Address & Location:</p>
              <p className="text-gray-600">{selectedOrg.address || "No street address specified"}</p>
              <p className="text-gray-600">{selectedOrg.city}, {selectedOrg.district}, {selectedOrg.state} - {selectedOrg.pincode} ({selectedOrg.country})</p>
            </div>

            {/* Contact Details */}
            <div className="space-y-2">
              <h4 className="text-xs font-extrabold text-gray-400 uppercase tracking-wider">Contact & Communications</h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                {selectedOrg.phones?.map((p: any, idx: number) => (
                  <div key={idx} className="p-2.5 bg-gray-50 rounded-lg flex items-center gap-2">
                    <Phone className="h-4 w-4 text-orange-500" />
                    <div>
                      <p className="font-bold text-gray-800">{p.raw || p.normalized}</p>
                      <p className="text-[10px] text-gray-400 uppercase">{p.type}</p>
                    </div>
                  </div>
                ))}
                {selectedOrg.emails?.map((e: any, idx: number) => (
                  <div key={idx} className="p-2.5 bg-gray-50 rounded-lg flex items-center gap-2">
                    <Mail className="h-4 w-4 text-blue-500" />
                    <div>
                      <p className="font-bold text-gray-800">{e.email}</p>
                      <p className="text-[10px] text-gray-400 uppercase">{e.extraction_method || "General"}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Other Official Links */}
            {selectedOrg.other_links?.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-xs font-extrabold text-gray-400 uppercase tracking-wider">Other Official Portals & Links</h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                  {selectedOrg.other_links.map((link: any, idx: number) => (
                    <a key={idx} href={link.url} target="_blank" rel="noreferrer" className="p-2.5 bg-orange-50/60 border border-orange-200 rounded-lg flex items-center justify-between text-orange-800 font-bold hover:bg-orange-100">
                      <span>{link.label}</span>
                      <ExternalLink className="h-3.5 w-3.5 text-orange-600" />
                    </a>
                  ))}
                </div>
              </div>
            )}

            {/* Branches */}
            {selectedOrg.branches?.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-xs font-extrabold text-gray-400 uppercase tracking-wider">Branches ({selectedOrg.branches.length})</h4>
                <div className="space-y-2">
                  {selectedOrg.branches.map((b: any, idx: number) => (
                    <div key={idx} className="p-3 bg-indigo-50/50 border border-indigo-100 rounded-xl text-xs space-y-1">
                      <p className="font-bold text-indigo-900 flex items-center gap-1">
                        <GitBranch className="h-3.5 w-3.5 text-indigo-600" /> {b.branch_name}
                      </p>
                      <p className="text-gray-600">{b.address ? `${b.address}, ` : ""}{b.city}, {b.district}, {b.state} ({b.country})</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Verification Metadata */}
            <div className="p-3 bg-gray-100 rounded-xl text-[11px] text-gray-600 flex justify-between items-center">
              <span>Verified By: <strong>{selectedOrg.verified_by || "System/Scraper"}</strong></span>
              <span>Method: <strong>{selectedOrg.verification_method || "Automatic"}</strong></span>
            </div>
          </div>
        </div>
      )}

      {/* MULTI-TAB ADD & EDIT ORGANIZATION MODAL */}
      {showFormModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 z-50 overflow-y-auto">
          <div className="bg-white rounded-2xl max-w-3xl w-full p-6 shadow-2xl relative max-h-[90vh] flex flex-col">
            {/* Modal Header */}
            <div className="flex items-center justify-between pb-4 border-b border-gray-200 shrink-0">
              <div>
                <h2 className="text-lg font-black text-gray-900">
                  {editingOrgId ? "Edit Master Organization" : "+ Add New Master Organization"}
                </h2>
                <p className="text-xs text-gray-500">
                  Enter complete identity, location, contacts, website, social links, custom links, and branch information.
                </p>
              </div>
              <button
                onClick={() => setShowFormModal(false)}
                className="p-2 text-gray-400 hover:bg-gray-100 rounded-full"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Tab Bar */}
            <div className="flex items-center gap-1 border-b border-gray-200 overflow-x-auto py-2 shrink-0">
              {[
                { id: "identity", label: "1. Identity" },
                { id: "location", label: "2. Location" },
                { id: "contact", label: "3. Contacts" },
                { id: "website", label: "4. Web & Maps" },
                { id: "social", label: "5. Social Media" },
                { id: "other_links", label: "6. Custom Links" },
                { id: "branches", label: "7. Branches" },
                { id: "verification", label: "8. Status" }
              ].map(tab => (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setActiveFormTab(tab.id as any)}
                  className={`px-3 py-1.5 text-xs font-bold rounded-lg whitespace-nowrap transition-all ${
                    activeFormTab === tab.id
                      ? "bg-orange-500 text-white shadow-xs"
                      : "text-gray-600 hover:bg-gray-100"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Form Body */}
            <form onSubmit={handleFormSubmit} className="space-y-4 pt-4 overflow-y-auto flex-1 pr-1">
              {/* TAB 1: IDENTITY */}
              {activeFormTab === "identity" && (
                <div className="space-y-4">
                  <div>
                    <label className="block text-xs font-bold text-gray-700 mb-1">Organization Name *</label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. Puducherry Multi-Specialty Hospital"
                      value={form.name}
                      onChange={e => setForm({ ...form, name: e.target.value })}
                      className="w-full px-3.5 py-2.5 text-xs font-semibold border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500"
                    />
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-bold text-gray-700 mb-1">Display Name (Optional)</label>
                      <input
                        type="text"
                        placeholder="e.g. Puducherry Hospital"
                        value={form.display_name}
                        onChange={e => setForm({ ...form, display_name: e.target.value })}
                        className="w-full px-3.5 py-2.5 text-xs font-semibold border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-bold text-gray-700 mb-1">Category *</label>
                      <input
                        type="text"
                        required
                        placeholder="e.g. Hotel, CBSE School, Hospital, NGO, Bank"
                        value={form.category}
                        onChange={e => setForm({ ...form, category: e.target.value })}
                        className="w-full px-3.5 py-2.5 text-xs font-semibold border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-bold text-gray-700 mb-1">Subcategory (Optional)</label>
                      <input
                        type="text"
                        placeholder="e.g. Multispecialty, CBSE, Engineering"
                        value={form.sub_category}
                        onChange={e => setForm({ ...form, sub_category: e.target.value })}
                        className="w-full px-3.5 py-2.5 text-xs font-semibold border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-bold text-gray-700 mb-1">Description</label>
                      <textarea
                        rows={2}
                        placeholder="Brief overview of the organization"
                        value={form.description}
                        onChange={e => setForm({ ...form, description: e.target.value })}
                        className="w-full px-3.5 py-2 text-xs font-semibold border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500"
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 2: LOCATION */}
              {activeFormTab === "location" && (
                <div className="space-y-4">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-bold text-gray-700 mb-1">Country *</label>
                      <input
                        type="text"
                        required
                        value={form.country}
                        onChange={e => setForm({ ...form, country: e.target.value })}
                        className="w-full px-3.5 py-2.5 text-xs font-semibold border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-bold text-gray-700 mb-1">State / UT *</label>
                      <input
                        type="text"
                        required
                        placeholder="e.g. Puducherry UT or Tamil Nadu"
                        value={form.state}
                        onChange={e => setForm({ ...form, state: e.target.value })}
                        className="w-full px-3.5 py-2.5 text-xs font-semibold border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div>
                      <label className="block text-xs font-bold text-gray-700 mb-1">District *</label>
                      <input
                        type="text"
                        required
                        placeholder="e.g. Puducherry"
                        value={form.district}
                        onChange={e => setForm({ ...form, district: e.target.value })}
                        className="w-full px-3.5 py-2.5 text-xs font-semibold border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-bold text-gray-700 mb-1">City / Town</label>
                      <input
                        type="text"
                        placeholder="e.g. Puducherry"
                        value={form.city}
                        onChange={e => setForm({ ...form, city: e.target.value })}
                        className="w-full px-3.5 py-2.5 text-xs font-semibold border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-bold text-gray-700 mb-1">Pincode</label>
                      <input
                        type="text"
                        placeholder="e.g. 605001"
                        value={form.pincode}
                        onChange={e => setForm({ ...form, pincode: e.target.value })}
                        className="w-full px-3.5 py-2.5 text-xs font-semibold border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-gray-700 mb-1">Full Physical Address</label>
                    <textarea
                      rows={2}
                      placeholder="e.g. 100 Beach Promenade, Near General Hospital"
                      value={form.address}
                      onChange={e => setForm({ ...form, address: e.target.value })}
                      className="w-full px-3.5 py-2 text-xs font-semibold border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500"
                    />
                  </div>
                </div>
              )}

              {/* TAB 3: CONTACTS */}
              {activeFormTab === "contact" && (
                <div className="space-y-4">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-bold text-gray-700 mb-1">Primary Phone</label>
                      <input
                        type="text"
                        placeholder="e.g. 0413-2223344"
                        value={form.primary_phone}
                        onChange={e => setForm({ ...form, primary_phone: e.target.value })}
                        className="w-full px-3.5 py-2.5 text-xs font-semibold border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-bold text-gray-700 mb-1">Secondary Phone</label>
                      <input
                        type="text"
                        placeholder="e.g. 9876543210"
                        value={form.secondary_phone}
                        onChange={e => setForm({ ...form, secondary_phone: e.target.value })}
                        className="w-full px-3.5 py-2.5 text-xs font-semibold border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-bold text-gray-700 mb-1">WhatsApp Phone</label>
                      <input
                        type="text"
                        placeholder="e.g. +91 9876543210"
                        value={form.whatsapp_phone}
                        onChange={e => setForm({ ...form, whatsapp_phone: e.target.value })}
                        className="w-full px-3.5 py-2.5 text-xs font-semibold border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-bold text-gray-700 mb-1">Emergency / Hotline Phone</label>
                      <input
                        type="text"
                        placeholder="e.g. 1066 / 0413-9999"
                        value={form.emergency_phone}
                        onChange={e => setForm({ ...form, emergency_phone: e.target.value })}
                        className="w-full px-3.5 py-2.5 text-xs font-semibold border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-bold text-gray-700 mb-1">General Email</label>
                      <input
                        type="email"
                        placeholder="e.g. info@puducherryhospital.com"
                        value={form.general_email}
                        onChange={e => setForm({ ...form, general_email: e.target.value })}
                        className="w-full px-3.5 py-2.5 text-xs font-semibold border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-bold text-gray-700 mb-1">Admissions / Desk Email</label>
                      <input
                        type="email"
                        placeholder="e.g. admissions@puducherryhospital.com"
                        value={form.admissions_email}
                        onChange={e => setForm({ ...form, admissions_email: e.target.value })}
                        className="w-full px-3.5 py-2.5 text-xs font-semibold border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-bold text-gray-700 mb-1">Support / Appointments Email</label>
                      <input
                        type="email"
                        placeholder="e.g. support@puducherryhospital.com"
                        value={form.support_email}
                        onChange={e => setForm({ ...form, support_email: e.target.value })}
                        className="w-full px-3.5 py-2.5 text-xs font-semibold border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-bold text-gray-700 mb-1">HR / Careers Email</label>
                      <input
                        type="email"
                        placeholder="e.g. hr@puducherryhospital.com"
                        value={form.hr_email}
                        onChange={e => setForm({ ...form, hr_email: e.target.value })}
                        className="w-full px-3.5 py-2.5 text-xs font-semibold border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500"
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 4: WEBSITE & MAPS */}
              {activeFormTab === "website" && (
                <div className="space-y-4">
                  <div>
                    <label className="block text-xs font-bold text-gray-700 mb-1">Official Website URL</label>
                    <input
                      type="url"
                      placeholder="e.g. https://puducherryhospital.com"
                      value={form.official_website_url}
                      onChange={e => setForm({ ...form, official_website_url: e.target.value })}
                      className="w-full px-3.5 py-2.5 text-xs font-semibold border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500"
                    />
                    <p className="text-[10px] text-gray-400 mt-1">Must be an official organization domain. Localhost & private network IPs are blocked by SSRF protection.</p>
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-gray-700 mb-1">Google Maps URL</label>
                    <input
                      type="url"
                      placeholder="e.g. https://maps.google.com/?q=puducherry+hospital"
                      value={form.google_maps_url}
                      onChange={e => setForm({ ...form, google_maps_url: e.target.value })}
                      className="w-full px-3.5 py-2.5 text-xs font-semibold border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500"
                    />
                  </div>
                </div>
              )}

              {/* TAB 5: SOCIAL MEDIA */}
              {activeFormTab === "social" && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-bold text-gray-700 mb-1">Facebook URL</label>
                    <input
                      type="url"
                      placeholder="https://facebook.com/org"
                      value={form.facebook_url}
                      onChange={e => setForm({ ...form, facebook_url: e.target.value })}
                      className="w-full px-3 py-2 text-xs font-semibold border border-gray-300 rounded-xl"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-gray-700 mb-1">Instagram URL</label>
                    <input
                      type="url"
                      placeholder="https://instagram.com/org"
                      value={form.instagram_url}
                      onChange={e => setForm({ ...form, instagram_url: e.target.value })}
                      className="w-full px-3 py-2 text-xs font-semibold border border-gray-300 rounded-xl"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-gray-700 mb-1">LinkedIn URL</label>
                    <input
                      type="url"
                      placeholder="https://linkedin.com/company/org"
                      value={form.linkedin_url}
                      onChange={e => setForm({ ...form, linkedin_url: e.target.value })}
                      className="w-full px-3 py-2 text-xs font-semibold border border-gray-300 rounded-xl"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-gray-700 mb-1">YouTube URL</label>
                    <input
                      type="url"
                      placeholder="https://youtube.com/c/org"
                      value={form.youtube_url}
                      onChange={e => setForm({ ...form, youtube_url: e.target.value })}
                      className="w-full px-3 py-2 text-xs font-semibold border border-gray-300 rounded-xl"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-gray-700 mb-1">X / Twitter URL</label>
                    <input
                      type="url"
                      placeholder="https://x.com/org"
                      value={form.x_url}
                      onChange={e => setForm({ ...form, x_url: e.target.value })}
                      className="w-full px-3 py-2 text-xs font-semibold border border-gray-300 rounded-xl"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-gray-700 mb-1">WhatsApp URL / Link</label>
                    <input
                      type="url"
                      placeholder="https://wa.me/919876543210"
                      value={form.whatsapp_url}
                      onChange={e => setForm({ ...form, whatsapp_url: e.target.value })}
                      className="w-full px-3 py-2 text-xs font-semibold border border-gray-300 rounded-xl"
                    />
                  </div>
                </div>
              )}

              {/* TAB 6: OTHER OFFICIAL LINKS */}
              {activeFormTab === "other_links" && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <p className="text-xs text-gray-500">
                      Add custom official links (e.g. Admissions, Booking, Patient Portal, Careers, Menu, Registration).
                    </p>
                    <button
                      type="button"
                      onClick={addOtherLinkRow}
                      className="px-3 py-1.5 bg-orange-50 hover:bg-orange-100 text-orange-700 border border-orange-200 rounded-lg text-xs font-bold flex items-center gap-1"
                    >
                      <Plus className="h-3.5 w-3.5" /> Add Link Row
                    </button>
                  </div>

                  {form.other_links.map((link, idx) => (
                    <div key={idx} className="p-3 bg-gray-50 border border-gray-200 rounded-xl flex items-center gap-2">
                      <input
                        type="text"
                        placeholder="Label (e.g. Admissions Portal)"
                        value={link.label}
                        onChange={e => {
                          const updated = [...form.other_links];
                          updated[idx].label = e.target.value;
                          setForm({ ...form, other_links: updated });
                        }}
                        className="w-1/3 px-3 py-1.5 text-xs border border-gray-300 rounded-lg bg-white"
                      />
                      <input
                        type="url"
                        placeholder="URL (https://...)"
                        value={link.url}
                        onChange={e => {
                          const updated = [...form.other_links];
                          updated[idx].url = e.target.value;
                          setForm({ ...form, other_links: updated });
                        }}
                        className="flex-1 px-3 py-1.5 text-xs border border-gray-300 rounded-lg bg-white"
                      />
                      <button
                        type="button"
                        onClick={() => removeOtherLinkRow(idx)}
                        className="p-1 text-red-500 hover:bg-red-50 rounded-lg"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {/* TAB 7: BRANCHES */}
              {activeFormTab === "branches" && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <p className="text-xs text-gray-500">
                      Add organization branches. Each branch maintains independent location scoping for searches.
                    </p>
                    <button
                      type="button"
                      onClick={addBranchRow}
                      className="px-3 py-1.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-200 rounded-lg text-xs font-bold flex items-center gap-1"
                    >
                      <Plus className="h-3.5 w-3.5" /> Add Branch Entry
                    </button>
                  </div>

                  {form.branches.map((b, idx) => (
                    <div key={idx} className="p-4 bg-indigo-50/40 border border-indigo-200 rounded-xl space-y-3 relative">
                      <button
                        type="button"
                        onClick={() => removeBranchRow(idx)}
                        className="absolute top-3 right-3 p-1 text-red-500 hover:bg-red-50 rounded-lg"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>

                      <p className="text-xs font-bold text-indigo-900">Branch #{idx + 1}</p>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        <input
                          type="text"
                          required
                          placeholder="Branch Name (e.g. Puducherry Branch)"
                          value={b.branch_name}
                          onChange={e => {
                            const updated = [...form.branches];
                            updated[idx].branch_name = e.target.value;
                            setForm({ ...form, branches: updated });
                          }}
                          className="px-3 py-1.5 text-xs border border-gray-300 rounded-lg bg-white"
                        />
                        <input
                          type="text"
                          placeholder="District (e.g. Puducherry)"
                          value={b.district}
                          onChange={e => {
                            const updated = [...form.branches];
                            updated[idx].district = e.target.value;
                            setForm({ ...form, branches: updated });
                          }}
                          className="px-3 py-1.5 text-xs border border-gray-300 rounded-lg bg-white"
                        />
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                        <input
                          type="text"
                          placeholder="City / Town"
                          value={b.city}
                          onChange={e => {
                            const updated = [...form.branches];
                            updated[idx].city = e.target.value;
                            setForm({ ...form, branches: updated });
                          }}
                          className="px-3 py-1.5 text-xs border border-gray-300 rounded-lg bg-white"
                        />
                        <input
                          type="text"
                          placeholder="State / UT"
                          value={b.state}
                          onChange={e => {
                            const updated = [...form.branches];
                            updated[idx].state = e.target.value;
                            setForm({ ...form, branches: updated });
                          }}
                          className="px-3 py-1.5 text-xs border border-gray-300 rounded-lg bg-white"
                        />
                        <input
                          type="text"
                          placeholder="Phone Number"
                          value={b.phone}
                          onChange={e => {
                            const updated = [...form.branches];
                            updated[idx].phone = e.target.value;
                            setForm({ ...form, branches: updated });
                          }}
                          className="px-3 py-1.5 text-xs border border-gray-300 rounded-lg bg-white"
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* TAB 8: VERIFICATION */}
              {activeFormTab === "verification" && (
                <div className="space-y-4">
                  <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center justify-between">
                    <div>
                      <p className="font-bold text-xs text-emerald-900">Admin Verified Priority</p>
                      <p className="text-[11px] text-emerald-700">When checked, organization becomes immediately searchable at top priority for matching searches.</p>
                    </div>
                    <input
                      type="checkbox"
                      checked={form.admin_verified}
                      onChange={e => setForm({ ...form, admin_verified: e.target.checked })}
                      className="h-5 w-5 text-orange-500 rounded focus:ring-orange-500"
                    />
                  </div>

                  <div className="p-4 bg-red-50 border border-red-200 rounded-xl space-y-2">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-bold text-xs text-red-900">Quarantine Record</p>
                        <p className="text-[11px] text-red-700">Quarantined records are excluded from user fast searches.</p>
                      </div>
                      <input
                        type="checkbox"
                        checked={form.is_quarantined}
                        onChange={e => setForm({ ...form, is_quarantined: e.target.checked })}
                        className="h-5 w-5 text-red-500 rounded focus:ring-red-500"
                      />
                    </div>
                    {form.is_quarantined && (
                      <input
                        type="text"
                        placeholder="Reason for quarantine (e.g. Directory portal site)"
                        value={form.quarantine_reason}
                        onChange={e => setForm({ ...form, quarantine_reason: e.target.value })}
                        className="w-full px-3 py-2 text-xs border border-red-300 rounded-lg bg-white"
                      />
                    )}
                  </div>
                </div>
              )}

              {/* Modal Footer Controls */}
              <div className="flex items-center justify-between pt-4 border-t border-gray-200 shrink-0">
                <button
                  type="button"
                  onClick={() => setShowFormModal(false)}
                  className="px-4 py-2.5 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-xl text-xs font-bold"
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  disabled={formLoading}
                  className="px-6 py-2.5 bg-orange-500 hover:bg-orange-600 text-white rounded-xl text-xs font-black tracking-wide shadow-sm flex items-center gap-2"
                >
                  {formLoading && <Loader2 className="h-4 w-4 animate-spin" />}
                  {editingOrgId ? "SAVE CHANGES" : "CREATE ORGANIZATION"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
