"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { 
  Users, ListFilter, Globe, Search, Mail, Phone, Share2, 
  CheckCircle2, AlertTriangle, ShieldCheck, Activity, ArrowRight, Loader2
} from "lucide-react";
import { api } from "@/lib/api";

export default function AdminDashboardPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [overview, setOverview] = useState<any>(null);
  const [recentTasks, setRecentTasks] = useState<any[]>([]);

  useEffect(() => {
    async function loadAdminData() {
      try {
        setLoading(true);
        const [statsData, tasksData] = await Promise.all([
          api.getAdminOverview(),
          api.getAdminTasks()
        ]);
        setOverview(statsData);
        setRecentTasks(tasksData.slice(0, 5));
      } catch (err: any) {
        setError(err.message || "Failed to load admin overview data.");
      } finally {
        setLoading(false);
      }
    }
    loadAdminData();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 text-orange-500 animate-spin" />
          <p className="text-sm font-semibold text-gray-500">Loading Admin Dashboard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 bg-red-50 border border-red-200 rounded-2xl text-red-700">
        <h3 className="font-bold text-base mb-1">Access Error</h3>
        <p className="text-sm mb-4">{error}</p>
        <Link href="/" className="px-4 py-2 bg-red-600 text-white rounded-xl text-sm font-semibold hover:bg-red-700">
          Back to Dashboard
        </Link>
      </div>
    );
  }

  const statCards = [
    { title: "Total Users", value: overview?.total_users || 0, icon: Users, color: "text-blue-600 bg-blue-50" },
    { title: "Total Admins", value: overview?.total_admins || 0, icon: ShieldCheck, color: "text-orange-600 bg-orange-50" },
    { title: "Normal Users", value: overview?.total_normal_users || 0, icon: Users, color: "text-sky-600 bg-sky-50" },
    { title: "Active Users", value: overview?.active_users || 0, icon: CheckCircle2, color: "text-emerald-600 bg-emerald-50" },
    { title: "Suspended Users", value: overview?.suspended_users || 0, icon: AlertTriangle, color: "text-red-600 bg-red-50" },
    { title: "Total Tasks", value: overview?.total_tasks || 0, icon: ListFilter, color: "text-purple-600 bg-purple-50" },
    { title: "Running Tasks", value: overview?.running_tasks || 0, icon: Activity, color: "text-amber-600 bg-amber-50" },
    { title: "Completed Tasks", value: overview?.completed_tasks || 0, icon: CheckCircle2, color: "text-emerald-600 bg-emerald-50" },
    { title: "Failed Tasks", value: overview?.failed_tasks || 0, icon: AlertTriangle, color: "text-red-600 bg-red-50" },
    { title: "Total Discovered", value: overview?.total_discovered || 0, icon: Search, color: "text-indigo-600 bg-indigo-50" },
    { title: "Websites Crawled", value: overview?.total_websites_crawled || 0, icon: Globe, color: "text-teal-600 bg-teal-50" },
    { title: "Total Leads", value: overview?.total_leads || 0, icon: ShieldCheck, color: "text-orange-600 bg-orange-50" },
    { title: "Total Emails", value: overview?.total_emails || 0, icon: Mail, color: "text-sky-600 bg-sky-50" },
    { title: "Total Phone Numbers", value: overview?.total_phones || 0, icon: Phone, color: "text-emerald-600 bg-emerald-50" },
    { title: "Total Social Links", value: overview?.total_socials || 0, icon: Share2, color: "text-pink-600 bg-pink-50" },
    { title: "Failed Crawls", value: overview?.total_failed_crawls || 0, icon: AlertTriangle, color: "text-red-600 bg-red-50" }
  ];

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-6 rounded-2xl border border-gray-200 shadow-sm">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-extrabold bg-orange-100 text-orange-700 uppercase tracking-wider">
              System Admin
            </span>
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Admin Control Center</h1>
          <p className="text-sm text-gray-500">Live platform metrics, user management, and system-wide scraping logs.</p>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/admin/users" className="px-4 py-2.5 rounded-xl text-sm font-semibold bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 shadow-xs">
            Manage Users
          </Link>
          <Link href="/admin/organizations" className="px-4 py-2.5 rounded-xl text-sm font-semibold bg-orange-500 text-white hover:bg-orange-600 shadow-sm">
            Master Organizations
          </Link>
        </div>
      </div>

      {/* Grid Stats — 2-col mobile, 4-col desktop */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
        {statCards.map((card, idx) => {
          const Icon = card.icon;
          return (
            <div key={idx} className="bg-white p-5 rounded-2xl border border-gray-200 shadow-xs flex flex-col justify-between">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-bold text-gray-500 uppercase tracking-wider">{card.title}</span>
                <div className={`p-2 rounded-xl ${card.color}`}>
                  <Icon className="h-4.5 w-4.5" />
                </div>
              </div>
              <p className="text-2xl font-extrabold text-gray-900 tracking-tight">{card.value.toLocaleString()}</p>
            </div>
          );
        })}
      </div>

      {/* Recent Activity Table */}
      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="p-6 border-b border-gray-200 flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-gray-900">Recent Scraping Tasks</h2>
            <p className="text-xs text-gray-500">Recent tasks dispatched across all registered users.</p>
          </div>
          <Link href="/admin/tasks" className="text-xs font-bold text-orange-600 hover:text-orange-700 flex items-center gap-1">
            View All <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-gray-600">
            <thead className="bg-gray-50 text-xs uppercase font-bold text-gray-500 border-b border-gray-200">
              <tr>
                <th className="px-6 py-3.5">Task ID</th>
                <th className="px-6 py-3.5">User</th>
                <th className="px-6 py-3.5">Keyword & Location</th>
                <th className="px-6 py-3.5">Status</th>
                <th className="px-6 py-3.5">Crawled / Leads</th>
                <th className="px-6 py-3.5">Created Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {recentTasks.map((t) => (
                <tr key={t.id} className="hover:bg-gray-50/80 transition-colors">
                  <td className="px-6 py-4 font-mono text-xs font-bold text-gray-900">{t.public_task_id}</td>
                  <td className="px-6 py-4 font-medium text-gray-800">{t.user_email}</td>
                  <td className="px-6 py-4">
                    <span className="font-semibold text-gray-900">{t.keyword}</span>
                    <span className="text-xs text-gray-400 block">{t.location}</span>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`px-2.5 py-1 rounded-full text-xs font-bold ${
                      t.status === "COMPLETED" ? "bg-emerald-100 text-emerald-800" :
                      t.status === "RUNNING" ? "bg-amber-100 text-amber-800 animate-pulse" :
                      t.status === "FAILED" ? "bg-red-100 text-red-800" : "bg-gray-100 text-gray-800"
                    }`}>
                      {t.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 font-semibold text-gray-900">
                    {t.websites_crawled} / <span className="text-orange-600">{t.lead_count}</span>
                  </td>
                  <td className="px-6 py-4 text-xs text-gray-500">
                    {new Date(t.created_at).toLocaleDateString()} {new Date(t.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </td>
                </tr>
              ))}
              {recentTasks.length === 0 && (
                <tr>
                  <td colSpan={6} className="text-center py-8 text-sm text-gray-400">
                    No scraping tasks recorded yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
