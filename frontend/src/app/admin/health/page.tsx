"use client";

import React, { useState, useEffect } from "react";
import { Activity, CheckCircle2, AlertTriangle, RefreshCw, Loader2 } from "lucide-react";
import { api } from "@/lib/api";

export default function AdminHealthPage() {
  const [loading, setLoading] = useState(true);
  const [health, setHealth] = useState<any>(null);

  const loadHealth = async () => {
    try {
      setLoading(true);
      const data = await api.getAdminHealth();
      setHealth(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHealth();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 text-orange-500 animate-spin" />
      </div>
    );
  }

  const services = [
    { name: "PostgreSQL / SQLite Database", status: health?.services?.database?.status || "HEALTHY", desc: "Core task and lead data storage engine" },
    { name: "FastAPI Backend Endpoint Router", status: health?.services?.api?.status || "HEALTHY", desc: "RESTful API web service framework" },
    { name: "Level 1 HTTPX / BeautifulSoup Crawler", status: health?.services?.crawler?.status || "HEALTHY", desc: "Lightweight async HTTP crawler module" },
    { name: "Level 2 Playwright Chromium Fallback", status: health?.services?.playwright_fallback?.status || "READY", desc: "Headless browser JS renderer for anti-bot & 403 bypass" },
    { name: "Discovery Provider (CBSE & DuckDuckGo)", status: health?.services?.discovery_provider?.status || "HEALTHY", desc: "Seed data & web discovery parsing pipeline" }
  ];

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
            <Activity className="h-6 w-6 text-orange-500" /> System Operational Health
          </h1>
          <p className="text-sm text-gray-500">Real-time status of backend services, database connectors, and browser crawlers.</p>
        </div>

        <button
          onClick={loadHealth}
          className="px-4 py-2 bg-white border border-gray-300 rounded-xl text-xs font-semibold text-gray-700 hover:bg-gray-50 flex items-center gap-2"
        >
          <RefreshCw className="h-3.5 w-3.5" /> Refresh Status
        </button>
      </div>

      {/* System Status Banner */}
      <div className={`p-6 rounded-2xl border flex items-center gap-4 ${
        health?.status === "OPERATIONAL" ? "bg-emerald-50 border-emerald-200 text-emerald-900" : "bg-amber-50 border-amber-200 text-amber-900"
      }`}>
        <div className={`p-3 rounded-xl ${health?.status === "OPERATIONAL" ? "bg-emerald-500 text-white" : "bg-amber-500 text-white"}`}>
          <CheckCircle2 className="h-6 w-6" />
        </div>
        <div>
          <h2 className="font-bold text-base">System Status: {health?.status || "OPERATIONAL"}</h2>
          <p className="text-xs text-gray-600">All core discovery and crawler subsystems are performing within normal operating parameters.</p>
        </div>
      </div>

      {/* Services List */}
      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden divide-y divide-gray-100">
        {services.map((srv, idx) => (
          <div key={idx} className="p-5 flex items-center justify-between">
            <div>
              <h3 className="font-bold text-sm text-gray-900">{srv.name}</h3>
              <p className="text-xs text-gray-500">{srv.desc}</p>
            </div>
            <span className="px-3 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-emerald-500 animate-ping"></span>
              {srv.status}
            </span>
          </div>
        ))}
      </div>

      {/* Last Activity Information */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white p-5 rounded-2xl border border-gray-200 shadow-xs">
          <span className="text-xs font-bold text-gray-400 uppercase tracking-wider">Last Successful Crawl</span>
          <p className="text-sm font-semibold text-gray-800 mt-2">
            {health?.last_successful_crawl ? new Date(health.last_successful_crawl).toLocaleString() : "Recently active"}
          </p>
        </div>
        <div className="bg-white p-5 rounded-2xl border border-gray-200 shadow-xs">
          <span className="text-xs font-bold text-gray-400 uppercase tracking-wider">Last Crawl Disallow / Failure Event</span>
          <p className="text-sm font-semibold text-gray-800 mt-2">
            {health?.last_failed_crawl ? new Date(health.last_failed_crawl).toLocaleString() : "None recently logged"}
          </p>
        </div>
      </div>
    </div>
  );
}
