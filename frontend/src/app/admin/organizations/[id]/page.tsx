"use client";

import React, { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { 
  Building2, ArrowLeft, Edit, Trash2, ShieldCheck, CheckCircle2, 
  MapPin, Globe, Phone, Mail, ExternalLink, Calendar, UserCheck, 
  GitBranch, Loader2, Share2, AlertCircle
} from "lucide-react";
import { api } from "@/lib/api";
import { useToast } from "@/components/AppLayout";
import OrganizationFormModal from "@/components/admin/OrganizationFormModal";

export default function AdminOrganizationDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { showToast } = useToast();
  const orgId = Number(params?.id);

  const [org, setOrg] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [editModalOpen, setEditModalOpen] = useState(false);

  const fetchDetail = useCallback(async () => {
    if (!orgId) return;
    try {
      setLoading(true);
      const data = await api.getAdminOrganization(orgId);
      setOrg(data);
    } catch (err: any) {
      showToast(err.message || "Failed to load organization details.", "error");
    } finally {
      setLoading(false);
    }
  }, [orgId, showToast]);

  useEffect(() => {
    fetchDetail();
  }, [fetchDetail]);

  const handleDelete = async () => {
    if (!org) return;
    if (!confirm(`Are you sure you want to delete Master Organization '${org.name}' (ID: ${org.id})?`)) return;
    try {
      await api.deleteAdminOrganization(org.id);
      showToast(`Organization '${org.name}' deleted successfully.`, "success");
      router.push("/admin/organizations");
    } catch (err: any) {
      showToast(err.message || "Failed to delete organization.", "error");
    }
  };

  if (loading && !org) {
    return (
      <div className="space-y-6 max-w-7xl mx-auto px-4 md:px-0">
        <div className="flex items-center justify-between">
          <Link href="/admin/organizations" className="inline-flex items-center gap-1.5 text-xs font-semibold text-gray-600">
            <ArrowLeft className="h-4 w-4" /> Back to Master Organizations
          </Link>
        </div>
        <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-xs h-40 animate-pulse"></div>
      </div>
    );
  }

  if (!org) {
    return (
      <div className="max-w-4xl mx-auto p-8 text-center bg-white border border-gray-200 rounded-2xl shadow-xs">
        <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-3" />
        <h2 className="text-xl font-bold text-gray-900">Organization Not Found</h2>
        <p className="text-sm text-gray-500 mt-1">The master organization you requested does not exist or has been removed.</p>
        <Link
          href="/admin/organizations"
          className="mt-4 inline-flex items-center gap-2 px-4 py-2 bg-gray-900 text-white rounded-lg font-semibold text-sm hover:bg-black transition-colors"
        >
          <ArrowLeft className="h-4 w-4" /> Back to Organizations
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto px-4 md:px-0">
      {/* NAVIGATION BAR */}
      <div className="flex items-center justify-between">
        <Link
          href="/admin/organizations"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-gray-600 hover:text-gray-900 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" /> Back to Master Organizations
        </Link>
        
        <div className="flex items-center gap-2">
          <button
            onClick={() => setEditModalOpen(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <Edit className="h-3.5 w-3.5" /> Edit Master Organization
          </button>
          <button
            onClick={handleDelete}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold text-red-600 bg-red-50 border border-red-200 rounded-lg hover:bg-red-100 transition-colors"
          >
            <Trash2 className="h-3.5 w-3.5" /> Delete
          </button>
        </div>
      </div>

      {/* HEADER CARD */}
      <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-xs relative overflow-hidden">
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs font-mono font-bold text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
                ORG ID #{org.id}
              </span>

              {/* PROVENANCE BADGES */}
              {org.admin_verified ? (
                <span className="inline-flex items-center gap-1 text-xs font-bold text-amber-700 bg-amber-50 border border-amber-300 px-2.5 py-0.5 rounded-full">
                  <ShieldCheck className="h-3.5 w-3.5 text-amber-600" /> ADMIN VERIFIED
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 text-xs font-bold text-emerald-700 bg-emerald-50 border border-emerald-300 px-2.5 py-0.5 rounded-full">
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" /> WEB VERIFIED
                </span>
              )}

              {org.sub_category && (
                <span className="text-xs font-semibold text-blue-700 bg-blue-50 border border-blue-200 px-2.5 py-0.5 rounded-full">
                  Subcategory: {org.sub_category}
                </span>
              )}
            </div>

            <h1 className="text-2xl md:text-3xl font-black text-gray-900 mt-2">
              {org.display_name || org.name}
            </h1>
            {org.display_name && org.display_name !== org.name && (
              <p className="text-xs font-mono text-gray-500 mt-0.5">Legal Name: {org.name}</p>
            )}

            <p className="text-xs font-semibold text-orange-600 uppercase tracking-wider mt-2">
              {org.category?.replace(/_/g, " ")}
            </p>

            {org.description && (
              <p className="text-sm text-gray-600 mt-3 max-w-3xl leading-relaxed">
                {org.description}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* 2-COLUMN GRID */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* LEFT COLUMN - MAIN DETAILS */}
        <div className="lg:col-span-2 space-y-6">

          {/* HEADQUARTERS LOCATION CARD */}
          <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-xs space-y-4">
            <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2 border-b border-gray-100 pb-3">
              <MapPin className="h-4 w-4 text-orange-500" /> Headquarters Location
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div>
                <span className="font-semibold text-gray-500 block">Address</span>
                <span className="font-medium text-gray-900">{org.address || "N/A"}</span>
              </div>
              <div>
                <span className="font-semibold text-gray-500 block">City</span>
                <span className="font-medium text-gray-900">{org.city || "N/A"}</span>
              </div>
              <div>
                <span className="font-semibold text-gray-500 block">District</span>
                <span className="font-medium text-gray-900">{org.district || "N/A"}</span>
              </div>
              <div>
                <span className="font-semibold text-gray-500 block">State / UT</span>
                <span className="font-medium text-gray-900">{org.state || "N/A"}</span>
              </div>
              <div>
                <span className="font-semibold text-gray-500 block">Pincode</span>
                <span className="font-medium text-gray-900">{org.pincode || "N/A"}</span>
              </div>
              <div>
                <span className="font-semibold text-gray-500 block">Country</span>
                <span className="font-medium text-gray-900">{org.country || "India"}</span>
              </div>
            </div>

            {org.google_maps_url && (
              <div className="pt-2">
                <a
                  href={org.google_maps_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-xs font-bold text-blue-600 hover:underline"
                >
                  <MapPin className="h-3.5 w-3.5" /> View Headquarters on Google Maps <ExternalLink className="h-3 w-3" />
                </a>
              </div>
            )}
          </div>

          {/* CONTACT CHANNELS CARD */}
          <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-xs space-y-4">
            <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2 border-b border-gray-100 pb-3">
              <Phone className="h-4 w-4 text-emerald-500" /> Contact Channels
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* PHONES */}
              <div>
                <h4 className="text-xs font-bold text-gray-700 flex items-center gap-1 mb-2">
                  <Phone className="h-3.5 w-3.5 text-gray-400" /> Phone Numbers ({org.phone_numbers?.length || 0})
                </h4>
                {org.phone_numbers && org.phone_numbers.length > 0 ? (
                  <ul className="space-y-1.5">
                    {org.phone_numbers.map((p: any, idx: number) => (
                      <li key={idx} className="text-xs bg-gray-50 p-2 rounded-lg border border-gray-100 flex items-center justify-between">
                        <span className="font-mono font-medium text-gray-900">{p.normalized_value || p.raw_value || p}</span>
                        <span className="text-[10px] uppercase font-bold text-gray-500 bg-gray-200 px-1.5 py-0.5 rounded">
                          {p.type || "MAIN"}
                        </span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-xs text-gray-400 italic">No phone numbers listed</p>
                )}
              </div>

              {/* EMAILS */}
              <div>
                <h4 className="text-xs font-bold text-gray-700 flex items-center gap-1 mb-2">
                  <Mail className="h-3.5 w-3.5 text-gray-400" /> Email Addresses ({org.email_addresses?.length || 0})
                </h4>
                {org.email_addresses && org.email_addresses.length > 0 ? (
                  <ul className="space-y-1.5">
                    {org.email_addresses.map((e: any, idx: number) => (
                      <li key={idx} className="text-xs bg-gray-50 p-2 rounded-lg border border-gray-100 font-mono text-gray-900">
                        {typeof e === "string" ? e : e.email}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-xs text-gray-400 italic">No email addresses listed</p>
                )}
              </div>
            </div>
          </div>

          {/* MULTI-LOCATION BRANCHES CARD */}
          <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-gray-100 pb-3">
              <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2">
                <GitBranch className="h-4 w-4 text-purple-500" /> Multi-Location Branches ({org.branches?.length || 0})
              </h3>
            </div>

            {org.branches && org.branches.length > 0 ? (
              <div className="grid grid-cols-1 gap-4">
                {org.branches.map((branch: any) => (
                  <div key={branch.id || branch.branch_name} className="bg-purple-50/50 border border-purple-100 rounded-xl p-4 space-y-2">
                    <div className="flex items-center justify-between">
                      <h4 className="text-xs font-bold text-purple-950 flex items-center gap-1.5">
                        <Building2 className="h-3.5 w-3.5 text-purple-600" /> {branch.branch_name}
                      </h4>
                      <span className="text-[10px] font-bold text-purple-700 bg-purple-100 px-2 py-0.5 rounded">
                        {branch.city || branch.district || "Branch"}
                      </span>
                    </div>

                    <p className="text-xs text-gray-600">
                      <span className="font-semibold">Address:</span> {branch.address}, {branch.city}, {branch.district}, {branch.state} - {branch.pincode}
                    </p>

                    <div className="flex flex-wrap gap-4 text-xs text-gray-600 pt-1">
                      {branch.phone_numbers && branch.phone_numbers.length > 0 && (
                        <div>
                          <span className="font-semibold text-gray-500">Phones: </span>
                          <span className="font-mono text-gray-900">{branch.phone_numbers.join(", ")}</span>
                        </div>
                      )}
                      {branch.email_addresses && branch.email_addresses.length > 0 && (
                        <div>
                          <span className="font-semibold text-gray-500">Emails: </span>
                          <span className="font-mono text-gray-900">{branch.email_addresses.join(", ")}</span>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-gray-400 italic">No additional branches configured for this organization.</p>
            )}
          </div>

        </div>

        {/* RIGHT COLUMN - PROVENANCE & LINKS */}
        <div className="space-y-6">

          {/* VERIFICATION & PROVENANCE CARD */}
          <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-xs space-y-3">
            <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2 border-b border-gray-100 pb-3">
              <UserCheck className="h-4 w-4 text-amber-500" /> Provenance & Verification
            </h3>

            <div className="space-y-2 text-xs">
              <div>
                <span className="font-semibold text-gray-500 block">Verification Source</span>
                <span className="font-bold text-gray-900">{org.source_type || (org.admin_verified ? "ADMIN_VERIFIED" : "SCRAPER_VERIFIED")}</span>
              </div>
              <div>
                <span className="font-semibold text-gray-500 block">Verification Method</span>
                <span className="font-medium text-gray-900">{org.verification_method || (org.admin_verified ? "ADMIN" : "SCRAPER")}</span>
              </div>
              <div>
                <span className="font-semibold text-gray-500 block">Verified By</span>
                <span className="font-medium text-gray-900">{org.verified_by || "System Admin"}</span>
              </div>
              <div>
                <span className="font-semibold text-gray-500 block">Verified At</span>
                <span className="font-mono text-gray-700">{org.verified_at ? new Date(org.verified_at).toLocaleString() : "N/A"}</span>
              </div>
              <div>
                <span className="font-semibold text-gray-500 block">Confidence Level</span>
                <span className="font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200 inline-block mt-0.5">
                  {org.confidence || "HIGH"}
                </span>
              </div>
            </div>
          </div>

          {/* OFFICIAL WEBSITE CARD */}
          <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-xs space-y-3">
            <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2 border-b border-gray-100 pb-3">
              <Globe className="h-4 w-4 text-blue-500" /> Official Website
            </h3>

            {org.website_url ? (
              <a
                href={org.website_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs font-semibold text-blue-600 hover:underline flex items-center gap-1 break-all"
              >
                {org.website_url} <ExternalLink className="h-3 w-3 shrink-0" />
              </a>
            ) : (
              <p className="text-xs text-gray-400 italic">No official website listed</p>
            )}
          </div>

          {/* SOCIAL & OFFICIAL LINKS CARD */}
          <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-xs space-y-3">
            <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2 border-b border-gray-100 pb-3">
              <Share2 className="h-4 w-4 text-indigo-500" /> Social & External Links
            </h3>

            <div className="space-y-2 text-xs">
              {org.facebook_url && (
                <a href={org.facebook_url} target="_blank" rel="noopener noreferrer" className="flex items-center justify-between text-blue-700 hover:underline">
                  <span>Facebook</span> <ExternalLink className="h-3 w-3" />
                </a>
              )}
              {org.instagram_url && (
                <a href={org.instagram_url} target="_blank" rel="noopener noreferrer" className="flex items-center justify-between text-pink-700 hover:underline">
                  <span>Instagram</span> <ExternalLink className="h-3 w-3" />
                </a>
              )}
              {org.linkedin_url && (
                <a href={org.linkedin_url} target="_blank" rel="noopener noreferrer" className="flex items-center justify-between text-blue-900 hover:underline">
                  <span>LinkedIn</span> <ExternalLink className="h-3 w-3" />
                </a>
              )}
              {org.youtube_url && (
                <a href={org.youtube_url} target="_blank" rel="noopener noreferrer" className="flex items-center justify-between text-red-700 hover:underline">
                  <span>YouTube</span> <ExternalLink className="h-3 w-3" />
                </a>
              )}
              {org.x_url && (
                <a href={org.x_url} target="_blank" rel="noopener noreferrer" className="flex items-center justify-between text-gray-900 hover:underline">
                  <span>X (Twitter)</span> <ExternalLink className="h-3 w-3" />
                </a>
              )}
              {org.whatsapp_url && (
                <a href={org.whatsapp_url} target="_blank" rel="noopener noreferrer" className="flex items-center justify-between text-emerald-700 hover:underline">
                  <span>WhatsApp</span> <ExternalLink className="h-3 w-3" />
                </a>
              )}

              {/* CUSTOM OTHER LINKS */}
              {org.other_links && org.other_links.length > 0 && (
                <div className="pt-2 border-t border-gray-100">
                  <span className="font-semibold text-gray-500 block mb-1">Custom Links</span>
                  {org.other_links.map((link: any, idx: number) => (
                    <a
                      key={idx}
                      href={link.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center justify-between text-indigo-600 hover:underline my-1"
                    >
                      <span>{link.label || link.link_type || "Link"}</span> <ExternalLink className="h-3 w-3" />
                    </a>
                  ))}
                </div>
              )}
            </div>
          </div>

        </div>

      </div>

      {/* EDIT MODAL */}
      {editModalOpen && (
        <OrganizationFormModal
          orgId={org.id}
          onClose={() => setEditModalOpen(false)}
          onSuccess={() => {
            setEditModalOpen(false);
            fetchDetail();
          }}
        />
      )}
    </div>
  );
}
