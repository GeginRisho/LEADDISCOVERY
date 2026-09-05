"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { 
  Sparkles, Search, MapPin, Layers, Sliders, CheckCircle2, 
  HelpCircle, Compass, ListTodo, Play, ShieldCheck
} from "lucide-react";
import { api } from "@/lib/api";
import { useToast } from "@/components/AppLayout";

export default function ScrapeCreatorPage() {
  const router = useRouter();
  const { showToast } = useToast();

  const [location, setLocation] = useState("");
  const [keyword, setKeyword] = useState("");
  const [radius, setRadius] = useState<number | undefined>(undefined);
  const [maxResults, setMaxResults] = useState(50);
  const [maxPages, setMaxPages] = useState(15);
  const [loading, setLoading] = useState(false);

  const [requestedFields, setRequestedFields] = useState<string[]>([
    "name", "category", "phone", "alt_phone", "email", "website", "address", "city", "state", "pincode", "whatsapp", "people", "designation", "facebook", "instagram", "linkedin", "youtube"
  ]);

  const fieldOptions = [
    { value: "name", label: "1. Organization Name" },
    { value: "category", label: "2. Business Category" },
    { value: "phone", label: "3. Phone Number" },
    { value: "alt_phone", label: "4. Alt Phone" },
    { value: "email", label: "5. Email Address" },
    { value: "website", label: "6. Official Website" },
    { value: "address", label: "7. Physical Address" },
    { value: "city", label: "8. City" },
    { value: "state", label: "9. State" },
    { value: "pincode", label: "10. Pincode" },
    { value: "whatsapp", label: "11. WhatsApp Contact" },
    { value: "people", label: "12. Contact Person" },
    { value: "designation", label: "13. Designation" },
    { value: "facebook", label: "14. Facebook Page" },
    { value: "instagram", label: "15. Instagram Handle" },
    { value: "linkedin", label: "16. LinkedIn Profile" },
    { value: "youtube", label: "17. YouTube Channel" },
  ];

  const handleRequestedToggle = (val: string) => {
    setRequestedFields((prev) => 
      prev.includes(val) ? prev.filter((item) => item !== val) : [...prev, val]
    );
  };

  const handleSelectAll = () => {
    setRequestedFields(fieldOptions.map((f) => f.value));
  };

  const handleSelectNone = () => {
    setRequestedFields([]);
  };

  const handleStartScrape = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!location.trim() || !keyword.trim()) {
      showToast("Please fill in both location and category/keyword.", "error");
      return;
    }

    setLoading(true);
    try {
      const task = await api.createTask({
        location: location.trim(),
        keyword: keyword.trim(),
        radius,
        max_results: maxResults,
        max_pages_per_site: maxPages,
        requested_fields: requestedFields,
        required_fields: []
      });
      showToast("Scraping task initiated successfully!", "success");
      router.push(`/tasks/${task.public_task_id}`);
    } catch (err: any) {
      showToast(err.message || "Failed to start scraping task.", "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto px-4 md:px-0">
      <div className="border-b border-gray-200 pb-4">
        <h1 className="text-xl md:text-2xl font-extrabold text-gray-900 flex items-center gap-2">
          Start New Scraping Session <Sparkles className="h-5 w-5 text-orange-500" />
        </h1>
        <p className="text-xs text-gray-500 mt-1">
          Configure prospect discovery parameters, search depth limits, and target extraction fields.
        </p>
      </div>

      <form onSubmit={handleStartScrape} className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* LEFT COLUMN: INPUTS & PARAMETERS */}
        <div className="lg:col-span-2 space-y-6">
          
          <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm space-y-5">
            <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2 border-b border-gray-100 pb-3">
              <Compass className="h-4 w-4 text-orange-500" /> Discovery & Search Parameters
            </h3>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
              <div>
                <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-2">
                  Target Keyword / Category
                </label>
                <div className="relative">
                  <Layers className="absolute left-3.5 top-3.5 h-4.5 w-4.5 text-gray-400" />
                  <input
                    type="text"
                    value={keyword}
                    onChange={(e) => setKeyword(e.target.value)}
                    placeholder="e.g. CBSE Schools, Software Companies"
                    className="w-full bg-white border border-gray-200 hover:border-gray-300 focus:border-orange-500 focus:ring-2 focus:ring-orange-100 focus:outline-none rounded-xl py-3 pl-11 pr-4 text-sm text-gray-900 placeholder-gray-400 transition-colors"
                    required
                  />
                </div>
              </div>
              
              <div>
                <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-2">
                  Location / City / Region
                </label>
                <div className="relative">
                  <MapPin className="absolute left-3.5 top-3.5 h-4.5 w-4.5 text-gray-400" />
                  <input
                    type="text"
                    value={location}
                    onChange={(e) => setLocation(e.target.value)}
                    placeholder="e.g. Puducherry, Kanyakumari, Chennai"
                    className="w-full bg-white border border-gray-200 hover:border-gray-300 focus:border-orange-500 focus:ring-2 focus:ring-orange-100 focus:outline-none rounded-xl py-3 pl-11 pr-4 text-sm text-gray-900 placeholder-gray-400 transition-colors"
                    required
                  />
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-5 border-t border-gray-100 pt-5">
              <div>
                <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-2">Max Results</label>
                <input
                  type="number"
                  value={maxResults}
                  onChange={(e) => setMaxResults(Number(e.target.value))}
                  min={1}
                  max={250}
                  className="w-full bg-white border border-gray-200 hover:border-gray-300 focus:border-orange-500 focus:ring-2 focus:ring-orange-100 focus:outline-none rounded-xl py-3 px-4 text-sm text-gray-900 transition-colors"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-2">Max Pages / Domain</label>
                <input
                  type="number"
                  value={maxPages}
                  onChange={(e) => setMaxPages(Number(e.target.value))}
                  min={1}
                  max={100}
                  className="w-full bg-white border border-gray-200 hover:border-gray-300 focus:border-orange-500 focus:ring-2 focus:ring-orange-100 focus:outline-none rounded-xl py-3 px-4 text-sm text-gray-900 transition-colors"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-2">Radius (km)</label>
                <input
                  type="number"
                  value={radius || ""}
                  onChange={(e) => setRadius(e.target.value ? Number(e.target.value) : undefined)}
                  placeholder="Optional"
                  className="w-full bg-white border border-gray-200 hover:border-gray-300 focus:border-orange-500 focus:ring-2 focus:ring-orange-100 focus:outline-none rounded-xl py-3 px-4 text-sm text-gray-900 transition-colors"
                />
              </div>
            </div>

          </div>

          <div className="bg-orange-50/60 border border-orange-200/80 rounded-2xl p-6 shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ShieldCheck className="h-5 w-5 text-orange-600" />
                <h4 className="text-xs font-bold text-gray-900 uppercase tracking-wider">SSRF & Compliance Safeguards</h4>
              </div>
              <span className="text-[10px] uppercase font-extrabold px-2.5 py-0.5 rounded-full bg-orange-100 text-orange-700 border border-orange-200">Active</span>
            </div>
            <ul className="text-xs text-gray-700 space-y-1.5 pl-4 list-disc font-medium">
              <li>Dynamic SSRF Protection blocks private and local network destinations on redirect chains.</li>
              <li>Domain Robots.txt rules are automatically checked and respected prior to deep page crawls.</li>
              <li>Playwright Chromium fallback automatically renders dynamic SPAs when standard static HTML yields incomplete results.</li>
            </ul>
          </div>
          
        </div>

        {/* RIGHT COLUMN: REQUESTED FIELDS ONLY */}
        <div className="space-y-6">
          <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm space-y-5">
            <div className="flex items-center justify-between border-b border-gray-100 pb-3">
              <div>
                <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2">
                  <ListTodo className="h-4 w-4 text-orange-500" /> Requested Fields
                </h3>
                <p className="text-[11px] text-gray-500 mt-1">Select the information you want the scraper to collect.</p>
              </div>
              <div className="flex items-center gap-1.5 text-[11px] font-bold shrink-0">
                <button
                  type="button"
                  onClick={handleSelectAll}
                  className="text-orange-600 hover:text-orange-700 bg-orange-50 hover:bg-orange-100 px-2.5 py-1 rounded-lg transition-colors"
                >
                  All
                </button>
                <button
                  type="button"
                  onClick={handleSelectNone}
                  className="text-gray-500 hover:text-gray-700 bg-gray-100 hover:bg-gray-200 px-2.5 py-1 rounded-lg transition-colors"
                >
                  None
                </button>
              </div>
            </div>
            
            <div className="space-y-2 max-h-[460px] overflow-y-auto pr-1">
              {fieldOptions.map((opt) => {
                const checked = requestedFields.includes(opt.value);
                return (
                  <button
                    type="button"
                    key={opt.value}
                    onClick={() => handleRequestedToggle(opt.value)}
                    className={`w-full flex items-center justify-between p-2.5 rounded-xl border text-left text-xs font-semibold transition-all duration-150 ${
                      checked 
                        ? "bg-orange-50 border-orange-300 text-orange-900" 
                        : "bg-white border-gray-200 text-gray-600 hover:bg-gray-50"
                    }`}
                  >
                    <span>{opt.label}</span>
                    <CheckCircle2 className={`h-4 w-4 transition-colors ${checked ? "text-orange-500 fill-orange-100" : "text-gray-300"}`} />
                  </button>
                );
              })}
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 bg-orange-500 hover:bg-orange-600 text-white font-bold rounded-xl py-3.5 shadow-md shadow-orange-500/20 active:scale-[0.98] transition-all disabled:opacity-50"
            >
              <Play className="h-4 w-4 fill-white" />
              {loading ? "Initializing Task..." : "START SCRAPING"}
            </button>
          </div>
        </div>

      </form>
    </div>
  );
}
