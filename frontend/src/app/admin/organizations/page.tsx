"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { 
  Building2, Plus, Search, Filter, RefreshCw, Eye, Edit, Trash2, 
  CheckCircle, Globe, Phone, Mail, MapPin, Loader2, ShieldCheck, ChevronLeft, ChevronRight
} from "lucide-react";
import { api } from "@/lib/api";
import { useToast } from "@/components/AppLayout";
import OrganizationFormModal from "@/components/admin/OrganizationFormModal";

export default function AdminOrganizationsPage() {
  const { showToast } = useToast();

  const [organizations, setOrganizations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [totalRecords, setTotalRecords] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [page, setPage] = useState(1);
  const pageSize = 20;

  // Filters
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [districtFilter, setDistrictFilter] = useState("");
  const [verificationFilter, setVerificationFilter] = useState("ALL");

  // Modal State
  const [modalOpen, setModalOpen] = useState(false);
  const [editingOrgId, setEditingOrgId] = useState<number | null>(null);

  const fetchOrganizations = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.getAdminOrganizations({
        search,
        category: categoryFilter,
        district: districtFilter,
        verification_status: verificationFilter,
        page,
        page_size: pageSize
      });
      setOrganizations(res.items || []);
      setTotalRecords(res.total_records || 0);
      setTotalPages(res.total_pages || 1);
    } catch (err: any) {
      showToast(err.message || "Failed to fetch master organizations.", "error");
    } finally {
      setLoading(false);
    }
  }, [search, categoryFilter, districtFilter, verificationFilter, page, showToast]);

  useEffect(() => {
    fetchOrganizations();
  }, [fetchOrganizations]);

  const handleDelete = async (id: number, name: string) => {
    if (!confirm(`Are you sure you want to delete Master Organization '${name}' (ID: ${id})?`)) return;
    try {
      await api.deleteAdminOrganization(id);
      showToast(`Organization '${name}' deleted successfully.`, "success");
      fetchOrganizations();
    } catch (err: any) {
      showToast(err.message || "Failed to delete organization.", "error");
    }
  };

  const handleCreateNew = () => {
    setEditingOrgId(null);
    setModalOpen(true);
  };

  const handleEdit = (id: number) => {
    setEditingOrgId(id);
    setModalOpen(true);
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto px-4 md:px-0">
      
      {/* HEADER */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white border border-gray-200 rounded-2xl p-6 shadow-xs">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono font-bold text-orange-600 bg-orange-50 border border-orange-200 px-2 py-0.5 rounded">
              ADMIN CONTROL
            </span>
          </div>
          <h1 className="text-xl md:text-2xl font-black text-gray-900 flex items-center gap-2 mt-1">
            <Building2 className="h-6 w-6 text-orange-500" /> Master Organizations Index
          </h1>
          <p className="text-xs text-gray-500 mt-1">
            Manage verified master organizations, branches, official links, and contact channels.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchOrganizations}
            className="p-2.5 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-xl transition-all"
            title="Refresh Table"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
          <button
            onClick={handleCreateNew}
            className="flex items-center gap-2 bg-orange-500 hover:bg-orange-600 text-white font-bold text-xs px-4 py-2.5 rounded-xl transition-all shadow-md shadow-orange-500/20 active:scale-[0.98]"
          >
            <Plus className="h-4 w-4" /> Add Master Organization
          </button>
        </div>
      </div>

      {/* FILTER & SEARCH BAR */}
      <div className="bg-white border border-gray-200 rounded-2xl p-4 shadow-xs grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
        <div className="relative">
          <Search className="h-4 w-4 text-gray-400 absolute left-3 top-3" />
          <input
            type="text"
            placeholder="Search name, city, website..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-xl text-xs focus:ring-2 focus:ring-orange-500 focus:border-orange-500 outline-none"
          />
        </div>

        <input
          type="text"
          placeholder="Filter by Category (e.g. Hospital, CBSE school)"
          value={categoryFilter}
          onChange={(e) => { setCategoryFilter(e.target.value); setPage(1); }}
          className="w-full px-3 py-2 border border-gray-300 rounded-xl text-xs focus:ring-2 focus:ring-orange-500 focus:border-orange-500 outline-none"
        />

        <input
          type="text"
          placeholder="Filter by District (e.g. Puducherry, Erode)"
          value={districtFilter}
          onChange={(e) => { setDistrictFilter(e.target.value); setPage(1); }}
          className="w-full px-3 py-2 border border-gray-300 rounded-xl text-xs focus:ring-2 focus:ring-orange-500 focus:border-orange-500 outline-none"
        />

        <select
          value={verificationFilter}
          onChange={(e) => { setVerificationFilter(e.target.value); setPage(1); }}
          className="w-full px-3 py-2 border border-gray-300 rounded-xl text-xs focus:ring-2 focus:ring-orange-500 focus:border-orange-500 outline-none bg-white"
        >
          <option value="ALL">All Verification Statuses</option>
          <option value="ADMIN_VERIFIED">Admin Verified Only</option>
          <option value="WEB_VERIFIED">Web Verified Only</option>
          <option value="UNVERIFIED">Unverified Only</option>
        </select>
      </div>

      {/* TABLE */}
      <div className="bg-white border border-gray-200 rounded-2xl overflow-hidden shadow-xs">
        {loading ? (
          <div className="flex flex-col items-center justify-center py-20 gap-3">
            <Loader2 className="h-8 w-8 text-orange-500 animate-spin" />
            <p className="text-xs text-gray-500 font-semibold">Fetching Master Organizations...</p>
          </div>
        ) : organizations.length === 0 ? (
          <div className="text-center py-16 px-4">
            <Building2 className="h-12 w-12 text-gray-300 mx-auto mb-3" />
            <h3 className="text-sm font-bold text-gray-800">No Master Organizations Found</h3>
            <p className="text-xs text-gray-500 mt-1 max-w-md mx-auto">
              No entities match your search parameters. Click "Add Master Organization" to insert a new verified record.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200 text-[11px] font-bold text-gray-500 uppercase tracking-wider">
                  <th className="py-3.5 px-4">Organization Name</th>
                  <th className="py-3.5 px-4">Category</th>
                  <th className="py-3.5 px-4">Location</th>
                  <th className="py-3.5 px-4">Website & Contacts</th>
                  <th className="py-3.5 px-4">Provenance</th>
                  <th className="py-3.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 text-xs">
                {organizations.map((org) => (
                  <tr key={org.id} className="hover:bg-gray-50/80 transition-colors">
                    <td className="py-3.5 px-4">
                      <div className="font-bold text-gray-900">{org.name}</div>
                      {org.display_name && (
                        <div className="text-[11px] text-gray-500 font-medium">({org.display_name})</div>
                      )}
                      {org.branch_count > 0 && (
                        <span className="inline-block mt-1 text-[10px] font-semibold text-blue-700 bg-blue-50 border border-blue-200 px-1.5 py-0.5 rounded">
                          {org.branch_count} {org.branch_count === 1 ? "Branch" : "Branches"}
                        </span>
                      )}
                    </td>

                    <td className="py-3.5 px-4">
                      <span className="font-semibold text-gray-800">{org.category}</span>
                      {org.sub_category && org.sub_category !== org.category && (
                        <span className="block text-[10px] text-orange-600 font-bold uppercase">{org.sub_category}</span>
                      )}
                    </td>

                    <td className="py-3.5 px-4">
                      <div className="flex items-center gap-1 font-semibold text-gray-800">
                        <MapPin className="h-3.5 w-3.5 text-gray-400 shrink-0" />
                        {org.district}, {org.state}
                      </div>
                      {org.city && org.city !== org.district && (
                        <div className="text-[11px] text-gray-500 pl-4">{org.city}</div>
                      )}
                    </td>

                    <td className="py-3.5 px-4 space-y-1">
                      {org.official_website_url ? (
                        <a
                          href={org.official_website_url}
                          target="_blank"
                          rel="noreferrer"
                          className="flex items-center gap-1 text-orange-600 hover:underline font-medium text-[11px] max-w-[200px] truncate"
                        >
                          <Globe className="h-3 w-3 shrink-0" />
                          {org.official_website_url.replace(/^https?:\/\//, "")}
                        </a>
                      ) : (
                        <span className="text-[11px] text-gray-400 italic">No official site</span>
                      )}
                      <div className="flex gap-2 text-[10px] text-gray-500 font-medium">
                        {org.phone_count > 0 && <span>{org.phone_count} Phone(s)</span>}
                        {org.email_count > 0 && <span>{org.email_count} Email(s)</span>}
                      </div>
                    </td>

                    <td className="py-3.5 px-4">
                      <span className={`inline-flex items-center gap-1 text-[10px] font-extrabold uppercase px-2.5 py-0.5 rounded border ${
                        org.admin_verified
                          ? "bg-blue-50 border-blue-200 text-blue-700"
                          : org.official_website_verified
                          ? "bg-emerald-50 border-emerald-200 text-emerald-700"
                          : "bg-amber-50 border-amber-200 text-amber-800"
                      }`}>
                        <ShieldCheck className="h-3 w-3" />
                        {org.verification_badge}
                      </span>
                    </td>

                    <td className="py-3.5 px-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Link
                          href={`/admin/organizations/${org.id}`}
                          className="p-1.5 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors"
                          title="View Details"
                        >
                          <Eye className="h-3.5 w-3.5" />
                        </Link>
                        <button
                          onClick={() => handleEdit(org.id)}
                          className="p-1.5 bg-orange-50 hover:bg-orange-100 text-orange-700 rounded-lg transition-colors"
                          title="Edit Organization"
                        >
                          <Edit className="h-3.5 w-3.5" />
                        </button>
                        <button
                          onClick={() => handleDelete(org.id, org.name)}
                          className="p-1.5 bg-red-50 hover:bg-red-100 text-red-700 rounded-lg transition-colors"
                          title="Delete Organization"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* PAGINATION */}
        {!loading && totalRecords > 0 && (
          <div className="bg-gray-50 border-t border-gray-200 px-4 py-3 flex items-center justify-between text-xs text-gray-600">
            <div>
              Showing <span className="font-bold">{(page - 1) * pageSize + 1}</span> to{" "}
              <span className="font-bold">{Math.min(page * pageSize, totalRecords)}</span> of{" "}
              <span className="font-bold">{totalRecords}</span> entries
            </div>

            <div className="flex items-center gap-2">
              <button
                disabled={page === 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="flex items-center gap-1 px-3 py-1.5 border border-gray-300 rounded-lg bg-white disabled:opacity-50 text-xs font-semibold"
              >
                <ChevronLeft className="h-3.5 w-3.5" /> Prev
              </button>
              <span className="font-bold text-gray-700">
                Page {page} of {totalPages}
              </span>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                className="flex items-center gap-1 px-3 py-1.5 border border-gray-300 rounded-lg bg-white disabled:opacity-50 text-xs font-semibold"
              >
                Next <ChevronRight className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* ADD / EDIT MODAL */}
      {modalOpen && (
        <OrganizationFormModal
          orgId={editingOrgId}
          onClose={() => setModalOpen(false)}
          onSuccess={() => {
            setModalOpen(false);
            fetchOrganizations();
          }}
        />
      )}
    </div>
  );
}
