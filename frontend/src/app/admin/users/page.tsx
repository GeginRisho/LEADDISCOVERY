"use client";

import React, { useState, useEffect } from "react";
import { Users, Shield, Lock, CheckCircle, AlertCircle, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { useToast } from "@/components/AppLayout";

export default function AdminUsersPage() {
  const { showToast } = useToast();
  const [loading, setLoading] = useState(true);
  const [users, setUsers] = useState<any[]>([]);

  const loadUsers = async () => {
    try {
      setLoading(true);
      const data = await api.getAdminUsers();
      setUsers(data);
    } catch (err: any) {
      showToast(err.message || "Failed to load user accounts.", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUsers();
  }, []);

  const handleUpdateUser = async (userId: number, payload: { role?: string; status?: string }) => {
    try {
      await api.updateAdminUserStatusOrRole(userId, payload);
      showToast("User account updated successfully.", "success");
      loadUsers();
    } catch (err: any) {
      showToast(err.message || "Failed to update user account.", "error");
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 text-orange-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
            <Users className="h-6 w-6 text-orange-500" /> User Accounts & Access Control
          </h1>
          <p className="text-sm text-gray-500">Manage user roles, account statuses, task counts, and lead metrics.</p>
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
        {/* Desktop Table View */}
        <div className="hidden md:block overflow-x-auto">
          <table className="w-full text-left text-sm text-gray-600">
            <thead className="bg-gray-50 text-xs uppercase font-bold text-gray-500 border-b border-gray-200">
              <tr>
                <th className="px-6 py-4">User ID</th>
                <th className="px-6 py-4">Email</th>
                <th className="px-6 py-4">Role</th>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4">Tasks</th>
                <th className="px-6 py-4">Leads</th>
                <th className="px-6 py-4">Created Date</th>
                <th className="px-6 py-4">Last Activity</th>
                <th className="px-6 py-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {users.map((u) => (
                <tr key={u.id} className="hover:bg-gray-50/80 transition-colors">
                  <td className="px-6 py-4 font-mono text-xs font-bold text-gray-900">{u.user_id_display || `USER-${u.id}`}</td>
                  <td className="px-6 py-4 font-semibold text-gray-900">
                    <div>{u.email}</div>
                    {u.name && <div className="text-xs text-gray-400 font-normal">{u.name}</div>}
                  </td>
                  <td className="px-6 py-4">
                    <span className={`px-2.5 py-1 rounded-full text-xs font-bold ${
                      u.role === "ADMIN" ? "bg-orange-100 text-orange-800" : "bg-gray-100 text-gray-700"
                    }`}>
                      {u.role}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`px-2.5 py-1 rounded-full text-xs font-bold ${
                      u.status === "ACTIVE" ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-800"
                    }`}>
                      {u.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 font-bold text-gray-800">{u.task_count} tasks</td>
                  <td className="px-6 py-4 font-bold text-orange-600">{u.lead_count} leads</td>
                  <td className="px-6 py-4 text-xs text-gray-500">
                    {new Date(u.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-4 text-xs text-gray-500">
                    {u.last_activity ? new Date(u.last_activity).toLocaleDateString() : "No activity"}
                  </td>
                  <td className="px-6 py-4 text-right space-x-2">
                    <button
                      onClick={() => handleUpdateUser(u.id, { role: u.role === "ADMIN" ? "USER" : "ADMIN" })}
                      className="px-3 py-1.5 text-xs font-semibold rounded-lg border border-gray-300 hover:bg-gray-50 text-gray-700"
                    >
                      Toggle {u.role === "ADMIN" ? "User" : "Admin"}
                    </button>
                    <button
                      onClick={() => handleUpdateUser(u.id, { status: u.status === "ACTIVE" ? "SUSPENDED" : "ACTIVE" })}
                      className={`px-3 py-1.5 text-xs font-semibold rounded-lg border ${
                        u.status === "ACTIVE" 
                          ? "border-red-200 bg-red-50 text-red-700 hover:bg-red-100" 
                          : "border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100"
                      }`}
                    >
                      {u.status === "ACTIVE" ? "Suspend" : "Activate"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Mobile Card Layout */}
        <div className="md:hidden divide-y divide-gray-100">
          {users.map((u) => (
            <div key={u.id} className="p-4 space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-bold text-gray-900 text-sm">{u.email}</span>
                <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${
                  u.role === "ADMIN" ? "bg-orange-100 text-orange-800" : "bg-gray-100 text-gray-700"
                }`}>
                  {u.role}
                </span>
              </div>
              <div className="flex items-center justify-between text-xs text-gray-500">
                <span>Tasks: <b>{u.task_count}</b> | Leads: <b className="text-orange-600">{u.lead_count}</b></span>
                <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                  u.status === "ACTIVE" ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-800"
                }`}>
                  {u.status}
                </span>
              </div>
              <div className="flex items-center gap-2 pt-1">
                <button
                  onClick={() => handleUpdateUser(u.id, { role: u.role === "ADMIN" ? "USER" : "ADMIN" })}
                  className="flex-1 py-2 text-xs font-semibold rounded-lg border border-gray-300 bg-white text-gray-700 hover:bg-gray-50"
                >
                  Make {u.role === "ADMIN" ? "User" : "Admin"}
                </button>
                <button
                  onClick={() => handleUpdateUser(u.id, { status: u.status === "ACTIVE" ? "SUSPENDED" : "ACTIVE" })}
                  className={`flex-1 py-2 text-xs font-semibold rounded-lg border ${
                    u.status === "ACTIVE" 
                      ? "border-red-200 bg-red-50 text-red-700" 
                      : "border-emerald-200 bg-emerald-50 text-emerald-700"
                  }`}
                >
                  {u.status === "ACTIVE" ? "Suspend" : "Activate"}
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
