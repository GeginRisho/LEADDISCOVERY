"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { 
  Sparkles, ListCollapse, Database, Globe, ShieldX, Play, ArrowRight,
  TrendingUp, Calendar, MapPin, Tag
} from "lucide-react";
import { api, ScrapingTask } from "@/lib/api";
import { useToast } from "@/components/AppLayout";

export default function DashboardPage() {
  const { showToast } = useToast();
  const [tasks, setTasks] = useState<ScrapingTask[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadTasks() {
      try {
        const data = await api.getTasks();
        setTasks(data);
      } catch (err) {
        showToast("Failed to load scraping tasks.", "error");
      } finally {
        setLoading(false);
      }
    }
    loadTasks();
  }, [showToast]);

  // Aggregate totals
  const totalTasks = tasks.length;
  const totalWebsitesFound = tasks.reduce((acc, t) => acc + t.websites_found, 0);
  const totalCrawled = tasks.reduce((acc, t) => acc + t.websites_crawled, 0);
  const totalFailed = tasks.reduce((acc, t) => acc + t.failed_count, 0);

  const recentTasks = tasks.slice(0, 5);

  return (
    <div className="space-y-8">
      
      {/* Welcome Banner - Renders Immediately */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 bg-white border border-gray-200 rounded-2xl p-6 md:p-8 shadow-sm">
        <div>
          <h1 className="text-2xl md:text-3xl font-extrabold text-gray-900 tracking-tight flex items-center gap-2">
            Welcome to LeadDiscovery <Sparkles className="h-6 w-6 text-orange-500" />
          </h1>
          <p className="text-gray-600 text-sm mt-1.5 max-w-xl leading-relaxed">
            Enterprise SaaS platform to discover organizations, verify domains, and extract verified contact details safely.
          </p>
        </div>
        <Link 
          href="/scrape" 
          className="flex items-center justify-center gap-2 bg-orange-500 hover:bg-orange-600 text-white px-5 py-3 rounded-xl font-bold shadow-md shadow-orange-500/20 active:scale-[0.98] transition-all"
        >
          <Play className="h-4 w-4 fill-white" />
          Start New Scrape
          <ArrowRight className="h-4 w-4" />
        </Link>
      </div>

      {/* Aggregate Stats Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        
        <div className="bg-white border border-gray-200 rounded-2xl p-6 flex items-center justify-between shadow-sm">
          <div>
            <p className="text-xs font-bold text-gray-500 uppercase tracking-wider">Total Tasks Run</p>
            {loading ? (
              <div className="h-8 w-16 bg-gray-200 animate-pulse rounded mt-2"></div>
            ) : (
              <h3 className="text-3xl font-black text-gray-900 mt-2">{totalTasks}</h3>
            )}
            <p className="text-[10px] text-orange-600 mt-1 flex items-center gap-1 font-semibold">
              <TrendingUp className="h-3 w-3" /> Historical sessions
            </p>
          </div>
          <div className="h-12 w-12 rounded-xl bg-orange-50 flex items-center justify-center border border-orange-100">
            <ListCollapse className="h-6 w-6 text-orange-500" />
          </div>
        </div>

        <div className="bg-white border border-gray-200 rounded-2xl p-6 flex items-center justify-between shadow-sm">
          <div>
            <p className="text-xs font-bold text-gray-500 uppercase tracking-wider">Websites Identified</p>
            {loading ? (
              <div className="h-8 w-16 bg-gray-200 animate-pulse rounded mt-2"></div>
            ) : (
              <h3 className="text-3xl font-black text-gray-900 mt-2">{totalWebsitesFound}</h3>
            )}
            <p className="text-[10px] text-emerald-600 mt-1 flex items-center gap-1 font-semibold">
              <TrendingUp className="h-3 w-3" /> Official domains
            </p>
          </div>
          <div className="h-12 w-12 rounded-xl bg-emerald-50 flex items-center justify-center border border-emerald-100">
            <Globe className="h-6 w-6 text-emerald-600" />
          </div>
        </div>

        <div className="bg-white border border-gray-200 rounded-2xl p-6 flex items-center justify-between shadow-sm">
          <div>
            <p className="text-xs font-bold text-gray-500 uppercase tracking-wider">Domains Crawled</p>
            {loading ? (
              <div className="h-8 w-16 bg-gray-200 animate-pulse rounded mt-2"></div>
            ) : (
              <h3 className="text-3xl font-black text-gray-900 mt-2">{totalCrawled}</h3>
            )}
            <p className="text-[10px] text-blue-600 mt-1 flex items-center gap-1 font-semibold">
              <TrendingUp className="h-3 w-3" /> Deep contact crawls
            </p>
          </div>
          <div className="h-12 w-12 rounded-xl bg-blue-50 flex items-center justify-center border border-blue-100">
            <Database className="h-6 w-6 text-blue-600" />
          </div>
        </div>

        <div className="bg-white border border-gray-200 rounded-2xl p-6 flex items-center justify-between shadow-sm">
          <div>
            <p className="text-xs font-bold text-gray-500 uppercase tracking-wider">Crawls Blocked/Failed</p>
            {loading ? (
              <div className="h-8 w-16 bg-gray-200 animate-pulse rounded mt-2"></div>
            ) : (
              <h3 className="text-3xl font-black text-gray-900 mt-2">{totalFailed}</h3>
            )}
            <p className="text-[10px] text-red-600 mt-1 flex items-center gap-1 font-semibold">
              Robots/Connection limits
            </p>
          </div>
          <div className="h-12 w-12 rounded-xl bg-red-50 flex items-center justify-center border border-red-100">
            <ShieldX className="h-6 w-6 text-red-600" />
          </div>
        </div>

      </div>

      {/* Recent Scrapes History Table */}
      <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm space-y-6">
        <div className="flex items-center justify-between border-b border-gray-100 pb-4">
          <div>
            <h2 className="text-lg font-bold text-gray-900">Recent Crawling Sessions</h2>
            <p className="text-xs text-gray-500">Real-time status updates of active and historical runs</p>
          </div>
          <Link href="/history" className="text-xs text-orange-600 hover:text-orange-700 font-bold flex items-center gap-1">
            View All History <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>

        {loading ? (
          <div className="space-y-3">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-20 bg-gray-100 animate-pulse rounded-xl"></div>
            ))}
          </div>
        ) : totalTasks === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <div className="h-16 w-16 rounded-full bg-orange-50 border border-orange-100 flex items-center justify-center mb-4">
              <ListCollapse className="h-8 w-8 text-orange-500" />
            </div>
            <h3 className="text-base font-bold text-gray-900">No scraping tasks created yet</h3>
            <p className="text-xs text-gray-500 mt-1 max-w-sm">
              Generate target lead databases by defining search keywords and cities.
            </p>
            <Link 
              href="/scrape" 
              className="mt-6 flex items-center gap-2 bg-orange-500 hover:bg-orange-600 text-white px-4 py-2.5 rounded-xl text-xs font-bold transition-all shadow-sm"
            >
              <Play className="h-3.5 w-3.5 fill-white" /> Start Scraping
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {recentTasks.map((task) => {
              const isRunning = task.status === "RUNNING";
              const isCompleted = task.status === "COMPLETED";
              const isFailed = task.status === "FAILED";
              
              return (
                <Link
                  href={`/tasks/${task.public_task_id}`}
                  key={task.id}
                  className="block p-5 rounded-xl bg-gray-50/50 border border-gray-200 hover:border-orange-300 hover:bg-orange-50/30 transition-all group"
                >
                  <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                    
                    <div className="space-y-1.5">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono font-bold text-gray-400">{task.public_task_id}</span>
                        <span className={`text-[10px] uppercase font-bold tracking-wider px-2.5 py-0.5 rounded border ${
                          isCompleted ? "bg-emerald-50 border-emerald-200 text-emerald-700" :
                          isRunning ? "bg-orange-50 border-orange-200 text-orange-700 animate-pulse" :
                          isFailed ? "bg-red-50 border-red-200 text-red-700" :
                          "bg-gray-100 border-gray-200 text-gray-600"
                        }`}>
                          {task.status}
                        </span>
                      </div>
                      
                      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm font-bold text-gray-900">
                        <span className="flex items-center gap-1">
                          <Tag className="h-4 w-4 text-orange-500" /> {task.keyword}
                        </span>
                        <span className="text-gray-400 font-normal">in</span>
                        <span className="flex items-center gap-1 text-orange-600">
                          <MapPin className="h-4 w-4 text-orange-500" /> {task.location}
                        </span>
                      </div>
                    </div>

                    {/* Progress bar */}
                    <div className="w-full lg:w-64 space-y-1.5">
                      <div className="flex justify-between text-xs text-gray-500 font-semibold">
                        <span>Crawl Progress</span>
                        <span className="font-bold text-gray-700">{task.progress}%</span>
                      </div>
                      <div className="h-2 w-full bg-gray-200 rounded-full overflow-hidden">
                        <div 
                          className={`h-full transition-all duration-500 ${
                            isFailed ? "bg-red-500" :
                            isCompleted ? "bg-emerald-500" :
                            "bg-orange-500"
                          }`}
                          style={{ width: `${task.progress}%` }}
                        ></div>
                      </div>
                    </div>

                    {/* Counter badges */}
                    <div className="flex flex-wrap items-center gap-2">
                      <div className="bg-white px-3 py-1.5 rounded-lg border border-gray-200 text-[11px] font-bold text-gray-600">
                        Websites: <span className="text-gray-900">{task.websites_found}</span>
                      </div>
                      <div className="bg-white px-3 py-1.5 rounded-lg border border-gray-200 text-[11px] font-bold text-gray-600">
                        Emails: <span className="text-gray-900">{task.email_count}</span>
                      </div>
                      <div className="bg-white px-3 py-1.5 rounded-lg border border-gray-200 text-[11px] font-bold text-gray-600">
                        Phones: <span className="text-gray-900">{task.phone_count}</span>
                      </div>
                    </div>

                    <div className="text-gray-400 group-hover:text-orange-500 transition-colors hidden lg:block">
                      <ArrowRight className="h-5 w-5 transform group-hover:translate-x-1 transition-transform" />
                    </div>

                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </div>

    </div>
  );
}
