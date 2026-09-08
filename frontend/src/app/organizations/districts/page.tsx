"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { 
  Map, Building2, GraduationCap, School, Hotel, Hospital, Briefcase, 
  Loader2, RefreshCw, ExternalLink, ChevronRight
} from "lucide-react";
import { api } from "@/lib/api";
import { useToast } from "@/components/AppLayout";

export default function TamilNaduDistrictDashboardPage() {
  const router = useRouter();
  const { showToast } = useToast();

  const [districts, setDistricts] = useState<Array<{
    district_id: number;
    district_name: string;
    state: string;
    country: string;
    official_district_url: string;
    total_organizations: number;
    companies_count: number;
    schools_count: number;
    colleges_count: number;
    hotels_count: number;
    hospitals_count: number;
    it_companies_count?: number;
  }>>([]);

  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  const fetchDistricts = async () => {
    try {
      setLoading(true);
      const data = await api.getDistrictStats();
      setDistricts(data);
    } catch (err: any) {
      showToast(err.message || "Failed to load Tamil Nadu district breakdown.", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDistricts();
  }, []);

  const filteredDistricts = districts.filter(d => 
    d.district_name.toLowerCase().includes(search.toLowerCase())
  );

  const totalOrgsSum = districts.reduce((acc, d) => acc + d.total_organizations, 0);

  return (
    <div className="space-y-8 max-w-7xl">
      {/* HEADER SECTION */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white border border-gray-200 p-6 rounded-2xl shadow-xs">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="bg-orange-50 text-orange-600 font-extrabold text-[10px] uppercase tracking-wider px-2.5 py-0.5 rounded border border-orange-200 flex items-center gap-1">
              <Map className="h-3 w-3" /> State Intelligence
            </span>
            <span className="bg-emerald-50 text-emerald-700 font-extrabold text-[10px] uppercase tracking-wider px-2.5 py-0.5 rounded border border-emerald-200">
              38 Official Districts
            </span>
          </div>
          <h1 className="text-2xl font-black text-gray-900">Tamil Nadu District Breakdown</h1>
          <p className="text-xs font-semibold text-gray-500">
            Real database counts aggregated across all 38 districts of Tamil Nadu.
          </p>
        </div>
        <button
          onClick={fetchDistricts}
          className="flex items-center gap-2 bg-white hover:bg-gray-50 border border-gray-200 text-gray-700 px-4 py-2.5 rounded-xl text-xs font-bold transition-all shadow-xs"
        >
          <RefreshCw className="h-4 w-4 text-orange-500" /> Refresh Counts
        </button>
      </div>

      {/* SEARCH AND SUMMARY STATS */}
      <div className="flex flex-col sm:flex-row justify-between items-center gap-4 bg-white border border-gray-200 p-4 rounded-2xl shadow-xs">
        <div className="w-full sm:w-72">
          <input
            type="text"
            placeholder="Search district (e.g. Salem, Coimbatore)..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full px-3.5 py-2 text-xs font-semibold border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-orange-500 bg-gray-50/50"
          />
        </div>
        <div className="text-xs font-semibold text-gray-600">
          Total Organizations Discovered Across TN: <span className="text-orange-600 font-black text-sm">{totalOrgsSum}</span>
        </div>
      </div>

      {/* 38 DISTRICT CARDS GRID */}
      {loading && filteredDistricts.length === 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="bg-white border border-gray-200 rounded-2xl p-5 h-44 animate-pulse"></div>
          ))}
        </div>
      ) : filteredDistricts.length === 0 ? (
        <div className="text-center py-16 bg-white border border-gray-200 rounded-2xl">
          <p className="text-sm font-bold text-gray-700">No district matches query '{search}'.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredDistricts.map((d) => (
            <div
              key={d.district_id}
              onClick={() => router.push(`/organizations?district=${encodeURIComponent(d.district_name)}`)}
              className="bg-white border border-gray-200 hover:border-orange-300 rounded-2xl p-5 space-y-4 cursor-pointer hover:shadow-md transition-all group"
            >
              <div className="flex justify-between items-start">
                <div>
                  <h2 className="text-lg font-black text-gray-900 group-hover:text-orange-600 transition-colors flex items-center gap-1.5">
                    {d.district_name}
                    <ChevronRight className="h-4 w-4 opacity-0 group-hover:opacity-100 transition-opacity" />
                  </h2>
                  <p className="text-[11px] font-semibold text-gray-400">{d.state}, India</p>
                </div>
                <div className="text-right">
                  <span className="text-2xl font-black text-orange-500">{d.total_organizations}</span>
                  <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Total Orgs</p>
                </div>
              </div>

              {/* Category Count Pills */}
              <div className="grid grid-cols-3 gap-2 pt-2 border-t border-gray-100 text-center">
                <div className="bg-orange-50/60 p-2 rounded-xl border border-orange-100">
                  <p className="text-[10px] text-gray-500 font-bold uppercase">Colleges</p>
                  <p className="text-sm font-black text-orange-600">{d.colleges_count}</p>
                </div>
                <div className="bg-emerald-50/60 p-2 rounded-xl border border-emerald-100">
                  <p className="text-[10px] text-gray-500 font-bold uppercase">Hotels</p>
                  <p className="text-sm font-black text-emerald-600">{d.hotels_count}</p>
                </div>
                <div className="bg-purple-50/60 p-2 rounded-xl border border-purple-100">
                  <p className="text-[10px] text-gray-500 font-bold uppercase">Hospitals</p>
                  <p className="text-sm font-black text-purple-600">{d.hospitals_count}</p>
                </div>
                <div className="bg-blue-50/60 p-2 rounded-xl border border-blue-100">
                  <p className="text-[10px] text-gray-500 font-bold uppercase">Companies</p>
                  <p className="text-sm font-black text-blue-600">{d.companies_count}</p>
                </div>
                <div className="bg-indigo-50/60 p-2 rounded-xl border border-indigo-100 col-span-2">
                  <p className="text-[10px] text-gray-500 font-bold uppercase">IT Companies</p>
                  <p className="text-sm font-black text-indigo-600">{d.it_companies_count || 0}</p>
                </div>
              </div>

              {d.official_district_url && (
                <div className="pt-2 flex justify-between items-center text-[11px] text-gray-400">
                  <span>Official Portal</span>
                  <a
                    href={d.official_district_url}
                    target="_blank"
                    rel="noreferrer"
                    onClick={(e) => e.stopPropagation()}
                    className="text-orange-600 hover:underline font-semibold flex items-center gap-0.5"
                  >
                    nic.in <ExternalLink className="h-3 w-3" />
                  </a>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
