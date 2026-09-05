"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Sparkles, Mail, Lock, ArrowRight, UserPlus } from "lucide-react";
import { api } from "@/lib/api";
import { useToast } from "@/components/AppLayout";

export default function RegisterPage() {
  const router = useRouter();
  const { showToast } = useToast();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password || !confirmPassword) {
      showToast("Please fill in all fields.", "error");
      return;
    }

    if (password.length < 6) {
      showToast("Password must be at least 6 characters.", "error");
      return;
    }

    if (password !== confirmPassword) {
      showToast("Passwords do not match.", "error");
      return;
    }

    setLoading(true);
    try {
      await api.register(email, password);
      showToast("Account created successfully! Logging in...", "success");
      
      await api.login(email, password);
      showToast("Logged in successfully. Welcome!", "success");
      router.push("/");
    } catch (err: any) {
      showToast(err.message || "Failed to create account. Email may already be in use.", "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white border border-gray-200 rounded-2xl p-8 shadow-xl shadow-gray-200/50">
      <div className="flex flex-col items-center gap-3 mb-8 text-center">
        <div className="h-12 w-12 rounded-2xl bg-orange-500 flex items-center justify-center shadow-lg shadow-orange-500/20">
          <UserPlus className="h-6 w-6 text-white" />
        </div>
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-gray-900">Create your Account</h1>
          <p className="text-xs text-gray-500 mt-1">Get started with LeadDiscovery platform</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-2">Email Address</label>
          <div className="relative">
            <Mail className="absolute left-3.5 top-3.5 h-4.5 w-4.5 text-gray-400" />
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="name@company.com"
              className="w-full bg-white border border-gray-200 hover:border-gray-300 focus:border-orange-500 focus:ring-2 focus:ring-orange-100 focus:outline-none rounded-xl py-3 pl-11 pr-4 text-sm text-gray-900 placeholder-gray-400 transition-colors"
              required
            />
          </div>
        </div>

        <div>
          <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-2">Password</label>
          <div className="relative">
            <Lock className="absolute left-3.5 top-3.5 h-4.5 w-4.5 text-gray-400" />
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="At least 6 characters"
              className="w-full bg-white border border-gray-200 hover:border-gray-300 focus:border-orange-500 focus:ring-2 focus:ring-orange-100 focus:outline-none rounded-xl py-3 pl-11 pr-4 text-sm text-gray-900 placeholder-gray-400 transition-colors"
              required
            />
          </div>
        </div>

        <div>
          <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-2">Confirm Password</label>
          <div className="relative">
            <Lock className="absolute left-3.5 top-3.5 h-4.5 w-4.5 text-gray-400" />
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Repeat your password"
              className="w-full bg-white border border-gray-200 hover:border-gray-300 focus:border-orange-500 focus:ring-2 focus:ring-orange-100 focus:outline-none rounded-xl py-3 pl-11 pr-4 text-sm text-gray-900 placeholder-gray-400 transition-colors"
              required
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full flex items-center justify-center gap-2 bg-orange-500 hover:bg-orange-600 text-white font-semibold rounded-xl py-3.5 shadow-md shadow-orange-500/20 active:scale-[0.98] transition-all disabled:opacity-50 disabled:pointer-events-none"
        >
          {loading ? "Creating account..." : "Register"}
          {!loading && <ArrowRight className="h-4 w-4" />}
        </button>
      </form>

      <div className="mt-8 text-center border-t border-gray-100 pt-6">
        <p className="text-xs text-gray-500">
          Already have an account?{" "}
          <Link href="/login" className="text-orange-600 hover:text-orange-700 font-semibold transition-colors">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
