"use client";

import React, { useState, useEffect } from "react";
import { 
  Sliders, Settings, Info, CheckCircle2, ShieldCheck, 
  HelpCircle, RefreshCw, Save
} from "lucide-react";
import { useToast } from "@/components/AppLayout";

export default function SettingsPage() {
  const { showToast } = useToast();

  const [maxResults, setMaxResults] = useState(100);
  const [maxPages, setMaxPages] = useState(20);
  const [timeout, setTimeoutVal] = useState(30);
  const [crawlDelay, setCrawlDelay] = useState(0.5);
  const [userAgent, setUserAgent] = useState("");
  const [exportPref, setExportPref] = useState("xlsx");

  useEffect(() => {
    if (typeof window !== "undefined") {
      const savedMaxResults = localStorage.getItem("settings_max_results");
      const savedMaxPages = localStorage.getItem("settings_max_pages");
      const savedTimeout = localStorage.getItem("settings_timeout");
      const savedDelay = localStorage.getItem("settings_delay");
      const savedUA = localStorage.getItem("settings_ua");
      const savedExport = localStorage.getItem("settings_export");

      if (savedMaxResults) setMaxResults(Number(savedMaxResults));
      if (savedMaxPages) setMaxPages(Number(savedMaxPages));
      if (savedTimeout) setTimeoutVal(Number(savedTimeout));
      if (savedDelay) setCrawlDelay(Number(savedDelay));
      if (savedUA) setUserAgent(savedUA);
      if (savedExport) setExportPref(savedExport);
      else {
        setUserAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36");
      }
    }
  }, []);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    try {
      localStorage.setItem("settings_max_results", maxResults.toString());
      localStorage.setItem("settings_max_pages", maxPages.toString());
      localStorage.setItem("settings_timeout", timeout.toString());
      localStorage.setItem("settings_delay", crawlDelay.toString());
      localStorage.setItem("settings_ua", userAgent.trim());
      localStorage.setItem("settings_export", exportPref);
      
      showToast("Scraper preferences saved successfully.", "success");
    } catch (err) {
      showToast("Failed to save scraper preferences.", "error");
    }
  };

  const handleReset = () => {
    setMaxResults(100);
    setMaxPages(20);
    setTimeoutVal(30);
    setCrawlDelay(0.5);
    setUserAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36");
    setExportPref("xlsx");
    showToast("Settings reset to defaults.", "info");
  };

  return (
    <div className="space-y-6 max-w-3xl">
      <div className="border-b border-gray-200 pb-4">
        <h1 className="text-xl md:text-2xl font-extrabold text-gray-900">System Configuration</h1>
        <p className="text-xs text-gray-500 mt-1">Adjust default crawler parameters, request headers, and export formats</p>
      </div>

      <form onSubmit={handleSave} className="space-y-6">
        
        {/* Scraper Limits */}
        <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-xs space-y-5">
          <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2 border-b border-gray-100 pb-3">
            <Sliders className="h-4.5 w-4.5 text-orange-500" /> Default Search & Crawl Limits
          </h3>
          
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
            <div>
              <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-2">Default Max Results</label>
              <input
                type="number"
                value={maxResults}
                onChange={(e) => setMaxResults(Number(e.target.value))}
                min={1}
                max={500}
                className="w-full bg-white border border-gray-200 focus:border-orange-500 focus:ring-2 focus:ring-orange-100 focus:outline-none rounded-xl py-2.5 px-4 text-xs text-gray-900 transition-colors"
                required
              />
              <p className="text-[10px] text-gray-500 mt-1">Default prospect target candidates per search run</p>
            </div>
            
            <div>
              <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-2">Max Pages / Website</label>
              <input
                type="number"
                value={maxPages}
                onChange={(e) => setMaxPages(Number(e.target.value))}
                min={1}
                max={100}
                className="w-full bg-white border border-gray-200 focus:border-orange-500 focus:ring-2 focus:ring-orange-100 focus:outline-none rounded-xl py-2.5 px-4 text-xs text-gray-900 transition-colors"
                required
              />
              <p className="text-[10px] text-gray-500 mt-1">Deep contact crawl depth limit per target domain</p>
            </div>
          </div>
        </div>

        {/* Network Preferences */}
        <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-xs space-y-5">
          <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2 border-b border-gray-100 pb-3">
            <ShieldCheck className="h-4.5 w-4.5 text-orange-500" /> Network Headers & Timeout Controls
          </h3>
          
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
            <div>
              <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-2">Request Timeout (seconds)</label>
              <input
                type="number"
                value={timeout}
                onChange={(e) => setTimeoutVal(Number(e.target.value))}
                min={5}
                max={120}
                className="w-full bg-white border border-gray-200 focus:border-orange-500 focus:ring-2 focus:ring-orange-100 focus:outline-none rounded-xl py-2.5 px-4 text-xs text-gray-900 transition-colors"
                required
              />
            </div>
            
            <div>
              <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-2">Crawl Delay (seconds)</label>
              <input
                type="number"
                value={crawlDelay}
                onChange={(e) => setCrawlDelay(Number(e.target.value))}
                step={0.1}
                min={0}
                max={10}
                className="w-full bg-white border border-gray-200 focus:border-orange-500 focus:ring-2 focus:ring-orange-100 focus:outline-none rounded-xl py-2.5 px-4 text-xs text-gray-900 transition-colors"
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-2">User-Agent Header String</label>
            <textarea
              value={userAgent}
              onChange={(e) => setUserAgent(e.target.value)}
              className="w-full h-20 bg-white border border-gray-200 focus:border-orange-500 focus:ring-2 focus:ring-orange-100 focus:outline-none rounded-xl py-2.5 px-4 text-xs text-gray-900 transition-colors resize-none font-mono"
              required
            />
          </div>
        </div>

        {/* UI / Export Preferences */}
        <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-xs space-y-5">
          <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2 border-b border-gray-100 pb-3">
            <Info className="h-4.5 w-4.5 text-orange-500" /> Export File Options
          </h3>
          
          <div>
            <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-2">Preferred File Download Format</label>
            <div className="flex gap-4">
              <button
                type="button"
                onClick={() => setExportPref("xlsx")}
                className={`px-5 py-3 rounded-xl border text-xs font-bold transition-all ${
                  exportPref === "xlsx" 
                    ? "bg-orange-50 border-orange-300 text-orange-900" 
                    : "bg-white border-gray-200 text-gray-600 hover:bg-gray-50"
                }`}
              >
                Microsoft Excel (.xlsx)
              </button>
              <button
                type="button"
                onClick={() => setExportPref("csv")}
                className={`px-5 py-3 rounded-xl border text-xs font-bold transition-all ${
                  exportPref === "csv" 
                    ? "bg-orange-50 border-orange-300 text-orange-900" 
                    : "bg-white border-gray-200 text-gray-600 hover:bg-gray-50"
                }`}
              >
                Comma-Separated Values (.csv)
              </button>
            </div>
          </div>
        </div>

        {/* Buttons */}
        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={handleReset}
            className="flex items-center gap-2 bg-white hover:bg-gray-50 border border-gray-200 text-gray-700 px-5 py-3 rounded-xl text-xs font-bold transition-all"
          >
            <RefreshCw className="h-4 w-4" /> Reset Defaults
          </button>
          
          <button
            type="submit"
            className="flex items-center gap-2 bg-orange-500 hover:bg-orange-600 text-white px-5 py-3 rounded-xl text-xs font-bold transition-all shadow-md shadow-orange-500/20 active:scale-[0.98]"
          >
            <Save className="h-4 w-4" /> Save Settings
          </button>
        </div>

      </form>
    </div>
  );
}
