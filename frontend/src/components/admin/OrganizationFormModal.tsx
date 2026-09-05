"use client";

import React, { useState, useEffect } from "react";
import { X, Plus, Trash2, Save, Loader2, MapPin, Globe, Phone, Mail, Link as LinkIcon, Building } from "lucide-react";
import { api } from "@/lib/api";
import { useToast } from "@/components/AppLayout";

const TN_DISTRICTS = [
  "Ariyalur", "Chengalpattu", "Chennai", "Coimbatore", "Cuddalore", "Dharmapuri", "Dindigul", "Erode",
  "Kallakurichi", "Kanchipuram", "Kanyakumari", "Karur", "Krishnagiri", "Madurai", "Mayiladuthurai",
  "Nagapattinam", "Namakkal", "Nilgiris", "Perambalur", "Pudukkottai", "Ramanathapuram", "Ranipet",
  "Salem", "Sivaganga", "Tenkasi", "Thanjavur", "Theni", "Thoothukudi", "Tiruchirappalli", "Tirunelveli",
  "Tirupathur", "Tiruppur", "Tiruvallur", "Tiruvannamalai", "Tiruvarur", "Vellore", "Viluppuram", "Virudhunagar"
];

const PUDUCHERRY_DISTRICTS = ["Puducherry", "Karaikal", "Mahe", "Yanam"];

interface Props {
  orgId?: number | null;
  onClose: () => void;
  onSuccess: () => void;
}

export default function OrganizationFormModal({ orgId, onClose, onSuccess }: Props) {
  const { showToast } = useToast();
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Form State
  const [name, setName] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [category, setCategory] = useState("");
  const [subCategory, setSubCategory] = useState("");
  const [description, setDescription] = useState("");

  const [country, setCountry] = useState("India");
  const [state, setState] = useState("Tamil Nadu");
  const [district, setDistrict] = useState("Erode");
  const [city, setCity] = useState("");
  const [address, setAddress] = useState("");
  const [pincode, setPincode] = useState("");
  const [googleMapsUrl, setGoogleMapsUrl] = useState("");

  const [officialWebsiteUrl, setOfficialWebsiteUrl] = useState("");

  // Phone list
  const [phones, setPhones] = useState<{ raw_value: string; type: string }[]>([
    { raw_value: "", type: "main" }
  ]);

  // Email list
  const [emails, setEmails] = useState<{ email: string; extraction_method: string }[]>([
    { email: "", extraction_method: "admin_manual" }
  ]);

  // Social Links
  const [facebookUrl, setFacebookUrl] = useState("");
  const [instagramUrl, setInstagramUrl] = useState("");
  const [linkedinUrl, setLinkedinUrl] = useState("");
  const [youtubeUrl, setYoutubeUrl] = useState("");
  const [xUrl, setXUrl] = useState("");
  const [whatsappUrl, setWhatsappUrl] = useState("");

  // Custom Links
  const [otherLinks, setOtherLinks] = useState<{ label: string; url: string }[]>([]);

  // Branches
  const [branches, setBranches] = useState<{
    branch_name: string;
    district: string;
    state: string;
    city: string;
    address: string;
    pincode: string;
    phone: string;
    email: string;
    website_url: string;
  }[]>([]);

  const availableDistricts = state === "Puducherry UT" ? PUDUCHERRY_DISTRICTS : TN_DISTRICTS;

  useEffect(() => {
    if (orgId) {
      async function loadOrg() {
        try {
          setLoading(true);
          const data = await api.getAdminOrganization(orgId!);
          setName(data.name || "");
          setDisplayName(data.display_name || "");
          setCategory(data.category || "");
          setSubCategory(data.sub_category || "");
          setDescription(data.description || "");
          setCountry(data.country || "India");
          setState(data.state || "Tamil Nadu");
          setDistrict(data.district || "Erode");
          setCity(data.city || "");
          setAddress(data.address || "");
          setPincode(data.pincode || "");
          setGoogleMapsUrl(data.google_maps_url || "");
          setOfficialWebsiteUrl(data.official_website_url || "");

          if (data.phone_numbers && data.phone_numbers.length > 0) {
            setPhones(data.phone_numbers.map((p: any) => ({ raw_value: p.raw_value, type: p.type || "main" })));
          }
          if (data.email_addresses && data.email_addresses.length > 0) {
            setEmails(data.email_addresses.map((e: any) => ({ email: e.email, extraction_method: "admin_manual" })));
          }

          if (data.social_links) {
            setFacebookUrl(data.social_links.facebook_url || "");
            setInstagramUrl(data.social_links.instagram_url || "");
            setLinkedinUrl(data.social_links.linkedin_url || "");
            setYoutubeUrl(data.social_links.youtube_url || "");
            setXUrl(data.social_links.x_url || "");
            setWhatsappUrl(data.social_links.whatsapp_url || "");
          }

          setOtherLinks(data.other_links || []);

          if (data.branches) {
            setBranches(data.branches.map((b: any) => ({
              branch_name: b.branch_name,
              district: b.district,
              state: b.state,
              city: b.city || "",
              address: b.address || "",
              pincode: b.pincode || "",
              phone: b.phone_numbers?.[0]?.raw_value || "",
              email: b.email_addresses?.[0]?.email || "",
              website_url: b.website_url || ""
            })));
          }

        } catch (err: any) {
          showToast(err.message || "Failed to load organization.", "error");
        } finally {
          setLoading(false);
        }
      }
      loadOrg();
    }
  }, [orgId, showToast]);

  const handleStateChange = (newState: string) => {
    setState(newState);
    if (newState === "Puducherry UT") {
      setDistrict("Puducherry");
    } else {
      setDistrict("Erode");
    }
  };

  const addPhone = () => setPhones([...phones, { raw_value: "", type: "office" }]);
  const removePhone = (idx: number) => setPhones(phones.filter((_, i) => i !== idx));

  const addEmail = () => setEmails([...emails, { email: "", extraction_method: "admin_manual" }]);
  const removeEmail = (idx: number) => setEmails(emails.filter((_, i) => i !== idx));

  const addOtherLink = () => setOtherLinks([...otherLinks, { label: "", url: "" }]);
  const removeOtherLink = (idx: number) => setOtherLinks(otherLinks.filter((_, i) => i !== idx));

  const addBranch = () => setBranches([...branches, {
    branch_name: "", district: district, state: state, city: "", address: "", pincode: "", phone: "", email: "", website_url: ""
  }]);
  const removeBranch = (idx: number) => setBranches(branches.filter((_, i) => i !== idx));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !category.trim() || !district.trim()) {
      showToast("Organization Name, Category, and District are required.", "error");
      return;
    }

    setSubmitting(true);

    const payload = {
      name: name.trim(),
      display_name: displayName.trim() || null,
      category: category.trim(),
      sub_category: subCategory.trim() || null,
      description: description.trim() || null,
      country,
      state,
      district,
      city: city.trim() || district,
      address: address.trim() || null,
      pincode: pincode.trim() || null,
      official_website_url: officialWebsiteUrl.trim() || null,
      google_maps_url: googleMapsUrl.trim() || null,
      facebook_url: facebookUrl.trim() || null,
      instagram_url: instagramUrl.trim() || null,
      linkedin_url: linkedinUrl.trim() || null,
      youtube_url: youtubeUrl.trim() || null,
      x_url: xUrl.trim() || null,
      whatsapp_url: whatsappUrl.trim() || null,
      other_links: otherLinks.filter(l => l.label.trim() && l.url.trim()),
      phone_numbers: phones.filter(p => p.raw_value.trim()).map(p => ({ raw_value: p.raw_value.trim(), normalized_value: p.raw_value.trim(), type: p.type })),
      email_addresses: emails.filter(e => e.email.trim()).map(e => ({ email: e.email.trim(), extraction_method: "admin_manual" })),
      branches: branches.filter(b => b.branch_name.trim()).map(b => ({
        branch_name: b.branch_name.trim(),
        district: b.district,
        state: b.state,
        city: b.city.trim() || b.district,
        address: b.address.trim() || null,
        pincode: b.pincode.trim() || null,
        phone_numbers: b.phone ? [{ raw_value: b.phone.trim(), normalized_value: b.phone.trim(), type: "office" }] : [],
        email_addresses: b.email ? [{ email: b.email.trim(), extraction_method: "admin_manual" }] : [],
        website_url: b.website_url.trim() || null
      }))
    };

    try {
      if (orgId) {
        await api.updateAdminOrganization(orgId, payload);
        showToast("Master Organization updated successfully!", "success");
      } else {
        await api.createAdminOrganization(payload);
        showToast("Master Organization created and indexed into Fast Search!", "success");
      }
      onSuccess();
    } catch (err: any) {
      showToast(err.message || "Failed to save organization.", "error");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-white border border-gray-200 rounded-3xl max-w-4xl w-full max-h-[90vh] flex flex-col shadow-2xl overflow-hidden my-auto">
        
        {/* MODAL HEADER */}
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between bg-gray-50/80">
          <div>
            <span className="text-[10px] font-extrabold uppercase bg-orange-100 text-orange-800 px-2 py-0.5 rounded border border-orange-200">
              {orgId ? "Edit Organization" : "Create Master Organization"}
            </span>
            <h2 className="text-lg font-black text-gray-900 mt-1">
              {orgId ? `Editing ID #${orgId}` : "Add Verified Master Organization"}
            </h2>
          </div>
          <button onClick={onClose} className="p-2 text-gray-400 hover:text-gray-700 rounded-full hover:bg-gray-100 transition-colors">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* MODAL BODY */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6 space-y-6">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-20 gap-3">
              <Loader2 className="h-8 w-8 text-orange-500 animate-spin" />
              <p className="text-xs text-gray-500 font-semibold">Loading organization data...</p>
            </div>
          ) : (
            <>
              {/* SECTION A: BASIC INFORMATION */}
              <div className="space-y-4">
                <h3 className="text-xs font-black uppercase tracking-wider text-orange-600 flex items-center gap-1.5 border-b border-gray-100 pb-2">
                  <Building className="h-4 w-4" /> Section A — Basic Information
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-bold text-gray-700 mb-1">Organization Name *</label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. Puducherry Multi-Specialty Hospital"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-xl text-xs focus:ring-2 focus:ring-orange-500 outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-gray-700 mb-1">Display Name (Optional)</label>
                    <input
                      type="text"
                      placeholder="e.g. Puducherry Hospital"
                      value={displayName}
                      onChange={(e) => setDisplayName(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-xl text-xs focus:ring-2 focus:ring-orange-500 outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-gray-700 mb-1">Category *</label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. Hospital, School, Hotel, College"
                      value={category}
                      onChange={(e) => setCategory(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-xl text-xs focus:ring-2 focus:ring-orange-500 outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-gray-700 mb-1">Subcategory (Optional)</label>
                    <input
                      type="text"
                      placeholder="e.g. MULTISPECIALTY, CBSE, ENGINEERING"
                      value={subCategory}
                      onChange={(e) => setSubCategory(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-xl text-xs focus:ring-2 focus:ring-orange-500 outline-none"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">Description (Optional)</label>
                  <textarea
                    rows={2}
                    placeholder="Brief description of the organization..."
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-xl text-xs focus:ring-2 focus:ring-orange-500 outline-none"
                  />
                </div>
              </div>

              {/* SECTION B: LOCATION */}
              <div className="space-y-4">
                <h3 className="text-xs font-black uppercase tracking-wider text-orange-600 flex items-center gap-1.5 border-b border-gray-100 pb-2">
                  <MapPin className="h-4 w-4" /> Section B — Normalized Location
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-xs font-bold text-gray-700 mb-1">Country *</label>
                    <input
                      type="text"
                      disabled
                      value={country}
                      className="w-full px-3 py-2 border border-gray-200 bg-gray-50 rounded-xl text-xs font-semibold text-gray-600 outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-gray-700 mb-1">State / UT *</label>
                    <select
                      value={state}
                      onChange={(e) => handleStateChange(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-xl text-xs focus:ring-2 focus:ring-orange-500 outline-none bg-white font-semibold"
                    >
                      <option value="Tamil Nadu">Tamil Nadu</option>
                      <option value="Puducherry UT">Puducherry UT</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-gray-700 mb-1">District *</label>
                    <select
                      value={district}
                      onChange={(e) => setDistrict(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-xl text-xs focus:ring-2 focus:ring-orange-500 outline-none bg-white font-semibold"
                    >
                      {availableDistricts.map((d) => (
                        <option key={d} value={d}>{d}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-xs font-bold text-gray-700 mb-1">City / Town</label>
                    <input
                      type="text"
                      placeholder="e.g. Puducherry"
                      value={city}
                      onChange={(e) => setCity(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-xl text-xs focus:ring-2 focus:ring-orange-500 outline-none"
                    />
                  </div>
                  <div className="sm:col-span-2">
                    <label className="block text-xs font-bold text-gray-700 mb-1">Full Physical Address</label>
                    <input
                      type="text"
                      placeholder="Door No, Street Name, Landmark..."
                      value={address}
                      onChange={(e) => setAddress(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-xl text-xs focus:ring-2 focus:ring-orange-500 outline-none"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-bold text-gray-700 mb-1">Pincode</label>
                    <input
                      type="text"
                      placeholder="e.g. 605001"
                      value={pincode}
                      onChange={(e) => setPincode(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-xl text-xs focus:ring-2 focus:ring-orange-500 outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-gray-700 mb-1">Google Maps URL</label>
                    <input
                      type="url"
                      placeholder="https://maps.google.com/?cid=..."
                      value={googleMapsUrl}
                      onChange={(e) => setGoogleMapsUrl(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-xl text-xs focus:ring-2 focus:ring-orange-500 outline-none"
                    />
                  </div>
                </div>
              </div>

              {/* SECTION C: OFFICIAL WEBSITE */}
              <div className="space-y-3">
                <h3 className="text-xs font-black uppercase tracking-wider text-orange-600 flex items-center gap-1.5 border-b border-gray-100 pb-2">
                  <Globe className="h-4 w-4" /> Section C — Official Website
                </h3>
                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">Official Website URL</label>
                  <input
                    type="url"
                    placeholder="https://www.example-hospital.org"
                    value={officialWebsiteUrl}
                    onChange={(e) => setOfficialWebsiteUrl(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-xl text-xs focus:ring-2 focus:ring-orange-500 outline-none"
                  />
                </div>
              </div>

              {/* SECTION D: PHONE NUMBERS */}
              <div className="space-y-3">
                <div className="flex items-center justify-between border-b border-gray-100 pb-2">
                  <h3 className="text-xs font-black uppercase tracking-wider text-orange-600 flex items-center gap-1.5">
                    <Phone className="h-4 w-4" /> Section D — Verified Phone Numbers
                  </h3>
                  <button type="button" onClick={addPhone} className="text-xs text-orange-600 font-bold hover:underline flex items-center gap-1">
                    <Plus className="h-3.5 w-3.5" /> Add Phone
                  </button>
                </div>
                {phones.map((p, idx) => (
                  <div key={idx} className="flex items-center gap-2">
                    <input
                      type="text"
                      placeholder="+91-9876543210"
                      value={p.raw_value}
                      onChange={(e) => {
                        const next = [...phones];
                        next[idx].raw_value = e.target.value;
                        setPhones(next);
                      }}
                      className="flex-1 px-3 py-2 border border-gray-300 rounded-xl text-xs focus:ring-2 focus:ring-orange-500 outline-none"
                    />
                    <select
                      value={p.type}
                      onChange={(e) => {
                        const next = [...phones];
                        next[idx].type = e.target.value;
                        setPhones(next);
                      }}
                      className="w-32 px-3 py-2 border border-gray-300 rounded-xl text-xs focus:ring-2 focus:ring-orange-500 outline-none bg-white"
                    >
                      <option value="main">Main</option>
                      <option value="office">Office</option>
                      <option value="admissions">Admissions</option>
                      <option value="whatsapp">WhatsApp</option>
                      <option value="emergency">Emergency</option>
                    </select>
                    {phones.length > 1 && (
                      <button type="button" onClick={() => removePhone(idx)} className="p-2 text-red-500 hover:bg-red-50 rounded-lg">
                        <Trash2 className="h-4 w-4" />
                      </button>
                    )}
                  </div>
                ))}
              </div>

              {/* SECTION E: EMAIL ADDRESSES */}
              <div className="space-y-3">
                <div className="flex items-center justify-between border-b border-gray-100 pb-2">
                  <h3 className="text-xs font-black uppercase tracking-wider text-orange-600 flex items-center gap-1.5">
                    <Mail className="h-4 w-4" /> Section E — Verified Email Addresses
                  </h3>
                  <button type="button" onClick={addEmail} className="text-xs text-orange-600 font-bold hover:underline flex items-center gap-1">
                    <Plus className="h-3.5 w-3.5" /> Add Email
                  </button>
                </div>
                {emails.map((e, idx) => (
                  <div key={idx} className="flex items-center gap-2">
                    <input
                      type="email"
                      placeholder="info@example-hospital.org"
                      value={e.email}
                      onChange={(ev) => {
                        const next = [...emails];
                        next[idx].email = ev.target.value;
                        setEmails(next);
                      }}
                      className="flex-1 px-3 py-2 border border-gray-300 rounded-xl text-xs focus:ring-2 focus:ring-orange-500 outline-none"
                    />
                    {emails.length > 1 && (
                      <button type="button" onClick={() => removeEmail(idx)} className="p-2 text-red-500 hover:bg-red-50 rounded-lg">
                        <Trash2 className="h-4 w-4" />
                      </button>
                    )}
                  </div>
                ))}
              </div>

              {/* SECTION F: SOCIAL & OTHER LINKS */}
              <div className="space-y-3">
                <h3 className="text-xs font-black uppercase tracking-wider text-orange-600 flex items-center gap-1.5 border-b border-gray-100 pb-2">
                  <LinkIcon className="h-4 w-4" /> Section F — Social & Custom Links
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <input type="url" placeholder="Facebook URL" value={facebookUrl} onChange={(e) => setFacebookUrl(e.target.value)} className="px-3 py-2 border border-gray-300 rounded-xl text-xs outline-none" />
                  <input type="url" placeholder="Instagram URL" value={instagramUrl} onChange={(e) => setInstagramUrl(e.target.value)} className="px-3 py-2 border border-gray-300 rounded-xl text-xs outline-none" />
                  <input type="url" placeholder="LinkedIn URL" value={linkedinUrl} onChange={(e) => setLinkedinUrl(e.target.value)} className="px-3 py-2 border border-gray-300 rounded-xl text-xs outline-none" />
                  <input type="url" placeholder="YouTube URL" value={youtubeUrl} onChange={(e) => setYoutubeUrl(e.target.value)} className="px-3 py-2 border border-gray-300 rounded-xl text-xs outline-none" />
                  <input type="url" placeholder="X / Twitter URL" value={xUrl} onChange={(e) => setXUrl(e.target.value)} className="px-3 py-2 border border-gray-300 rounded-xl text-xs outline-none" />
                  <input type="url" placeholder="WhatsApp Link" value={whatsappUrl} onChange={(e) => setWhatsappUrl(e.target.value)} className="px-3 py-2 border border-gray-300 rounded-xl text-xs outline-none" />
                </div>

                <div className="pt-2">
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-xs font-bold text-gray-700">Other Official Links (Portal, Admissions, Menu...)</label>
                    <button type="button" onClick={addOtherLink} className="text-xs text-orange-600 font-bold hover:underline flex items-center gap-1">
                      <Plus className="h-3.5 w-3.5" /> Add Link
                    </button>
                  </div>
                  {otherLinks.map((ol, idx) => (
                    <div key={idx} className="flex items-center gap-2 mb-2">
                      <input
                        type="text"
                        placeholder="Label (e.g. Admissions Portal)"
                        value={ol.label}
                        onChange={(e) => {
                          const next = [...otherLinks];
                          next[idx].label = e.target.value;
                          setOtherLinks(next);
                        }}
                        className="w-1/3 px-3 py-2 border border-gray-300 rounded-xl text-xs outline-none"
                      />
                      <input
                        type="url"
                        placeholder="https://..."
                        value={ol.url}
                        onChange={(e) => {
                          const next = [...otherLinks];
                          next[idx].url = e.target.value;
                          setOtherLinks(next);
                        }}
                        className="flex-1 px-3 py-2 border border-gray-300 rounded-xl text-xs outline-none"
                      />
                      <button type="button" onClick={() => removeOtherLink(idx)} className="p-2 text-red-500 hover:bg-red-50 rounded-lg">
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>

              {/* SECTION G: MULTI-LOCATION BRANCHES */}
              <div className="space-y-3">
                <div className="flex items-center justify-between border-b border-gray-100 pb-2">
                  <h3 className="text-xs font-black uppercase tracking-wider text-orange-600 flex items-center gap-1.5">
                    <Building className="h-4 w-4" /> Section G — Multi-Location Branches
                  </h3>
                  <button type="button" onClick={addBranch} className="text-xs text-orange-600 font-bold hover:underline flex items-center gap-1">
                    <Plus className="h-3.5 w-3.5" /> Add Branch
                  </button>
                </div>

                {branches.map((b, idx) => (
                  <div key={idx} className="p-4 bg-gray-50 border border-gray-200 rounded-2xl space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-gray-800">Branch #{idx + 1}</span>
                      <button type="button" onClick={() => removeBranch(idx)} className="text-xs text-red-500 hover:underline flex items-center gap-1">
                        <Trash2 className="h-3.5 w-3.5" /> Remove Branch
                      </button>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                      <input
                        type="text"
                        placeholder="Branch Name (e.g. Karaikal Branch)"
                        value={b.branch_name}
                        onChange={(e) => {
                          const next = [...branches];
                          next[idx].branch_name = e.target.value;
                          setBranches(next);
                        }}
                        className="px-3 py-2 border border-gray-300 rounded-xl text-xs outline-none bg-white"
                      />
                      <select
                        value={b.state}
                        onChange={(e) => {
                          const next = [...branches];
                          next[idx].state = e.target.value;
                          next[idx].district = e.target.value === "Puducherry UT" ? "Karaikal" : "Erode";
                          setBranches(next);
                        }}
                        className="px-3 py-2 border border-gray-300 rounded-xl text-xs outline-none bg-white font-semibold"
                      >
                        <option value="Tamil Nadu">Tamil Nadu</option>
                        <option value="Puducherry UT">Puducherry UT</option>
                      </select>
                      <select
                        value={b.district}
                        onChange={(e) => {
                          const next = [...branches];
                          next[idx].district = e.target.value;
                          setBranches(next);
                        }}
                        className="px-3 py-2 border border-gray-300 rounded-xl text-xs outline-none bg-white font-semibold"
                      >
                        {(b.state === "Puducherry UT" ? PUDUCHERRY_DISTRICTS : TN_DISTRICTS).map((d) => (
                          <option key={d} value={d}>{d}</option>
                        ))}
                      </select>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <input
                        type="text"
                        placeholder="Phone Number"
                        value={b.phone}
                        onChange={(e) => {
                          const next = [...branches];
                          next[idx].phone = e.target.value;
                          setBranches(next);
                        }}
                        className="px-3 py-2 border border-gray-300 rounded-xl text-xs outline-none bg-white"
                      />
                      <input
                        type="email"
                        placeholder="Email Address"
                        value={b.email}
                        onChange={(e) => {
                          const next = [...branches];
                          next[idx].email = e.target.value;
                          setBranches(next);
                        }}
                        className="px-3 py-2 border border-gray-300 rounded-xl text-xs outline-none bg-white"
                      />
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}

          {/* SUBMIT BUTTON */}
          <div className="pt-4 border-t border-gray-200 flex justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-5 py-2.5 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-xl text-xs font-bold transition-all"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting || loading}
              className="px-6 py-2.5 bg-orange-500 hover:bg-orange-600 text-white rounded-xl text-xs font-bold transition-all shadow-md shadow-orange-500/20 active:scale-[0.98] flex items-center gap-2 disabled:opacity-50"
            >
              {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
              {orgId ? "Save Changes" : "Create Master Organization"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
