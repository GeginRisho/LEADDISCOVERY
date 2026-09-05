"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import { 
  LayoutDashboard, Search, History, Settings, LogOut, 
  Menu, X, ShieldAlert, Sparkles, User, CheckCircle, AlertCircle, Loader2,
  ShieldCheck, Users, ListFilter, FileText, Activity, Building2, Map
} from "lucide-react";
import { api, User as UserType } from "@/lib/api";

// 1. Toast Provider Setup
interface Toast {
  id: string;
  message: string;
  type: "success" | "error" | "info";
}

interface ToastContextType {
  showToast: (message: string, type?: "success" | "error" | "info") => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) throw new Error("useToast must be used within ToastProvider");
  return context;
};

type AuthStatus = "loading" | "authenticated" | "unauthenticated";

// 2. AppLayout Component
export default function AppLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  
  const [authStatus, setAuthStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<UserType | null>(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [toasts, setToasts] = useState<Toast[]>([]);

  const showToast = React.useCallback((message: string, type: "success" | "error" | "info" = "success") => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  }, []);

  useEffect(() => {
    let isMounted = true;

    async function initializeAuth() {
      const isAuthRoute = pathname === "/login" || pathname === "/register";
      const hasToken = typeof window !== "undefined" && !!localStorage.getItem("token");

      if (!hasToken) {
        if (isMounted) {
          setUser(null);
          setAuthStatus("unauthenticated");
          if (!isAuthRoute) {
            router.push("/login");
          }
        }
        return;
      }

      try {
        const userData = await api.getMe();
        if (isMounted) {
          setUser(userData);
          setAuthStatus("authenticated");
          if (isAuthRoute) {
            router.push("/");
          }
        }
      } catch (err: any) {
        if (isMounted) {
          const stillHasToken = typeof window !== "undefined" && !!localStorage.getItem("token");
          if (!stillHasToken) {
            setUser(null);
            setAuthStatus("unauthenticated");
            if (!isAuthRoute) {
              router.push("/login");
            }
          } else {
            // Non-401 error (e.g. server down). Don't redirect to login if authenticated.
            if (user) {
              setAuthStatus("authenticated");
            } else {
              setAuthStatus("unauthenticated");
              if (!isAuthRoute) {
                router.push("/login");
              }
            }
          }
        }
      }
    }

    initializeAuth();

    return () => {
      isMounted = false;
    };
  }, [pathname, router]);

  const handleLogout = () => {
    api.removeToken();
    setUser(null);
    setAuthStatus("unauthenticated");
    showToast("Logged out successfully.", "info");
    router.push("/login");
  };

  const navLinks = [
    { href: "/", label: "Dashboard", icon: LayoutDashboard },
    { href: "/scrape", label: "New Scrape Task", icon: Search },
    { href: "/history", label: "Task History", icon: History },
    { href: "/organizations", label: "Master Organizations", icon: Building2 },
    { href: "/settings", label: "Settings", icon: Settings }
  ];

  const adminNavLinks = [
    { href: "/admin", label: "Admin Dashboard", icon: ShieldCheck },
    { href: "/admin/campaigns", label: "Discovery Campaigns", icon: Sparkles },
    { href: "/admin/users", label: "Users", icon: Users },
    { href: "/admin/tasks", label: "Admin Tasks", icon: ListFilter },
    { href: "/admin/logs", label: "Scraping Logs", icon: FileText },
    { href: "/admin/health", label: "System Health", icon: Activity }
  ];

  const isAuthPage = pathname === "/login" || pathname === "/register";

  // Prevent flicker during session initialization
  if (authStatus === "loading") {
    return (
      <div className="min-h-screen bg-[#FFFDF9] flex items-center justify-center flex-col gap-4 text-gray-800">
        <div className="relative flex items-center justify-center">
          <div className="h-14 w-14 rounded-full border-4 border-orange-100 border-t-orange-500 animate-spin"></div>
          <Sparkles className="h-6 w-6 text-orange-500 absolute" />
        </div>
        <p className="text-sm font-semibold tracking-wide text-gray-600 animate-pulse">Initializing LeadDiscovery...</p>
      </div>
    );
  }

  if (isAuthPage) {
    return (
      <ToastContext.Provider value={{ showToast }}>
        <div className="min-h-screen bg-[#FFFDF9] flex items-center justify-center p-4 relative overflow-hidden">
          {/* Subtle light orange background gradients */}
          <div className="absolute -top-32 -left-32 h-96 w-96 rounded-full bg-orange-100/60 blur-3xl pointer-events-none"></div>
          <div className="absolute -bottom-32 -right-32 h-96 w-96 rounded-full bg-amber-100/60 blur-3xl pointer-events-none"></div>
          
          <div className="w-full max-w-md z-10">{children}</div>
          
          <ToastContainer toasts={toasts} setToasts={setToasts} />
        </div>
      </ToastContext.Provider>
    );
  }

  return (
    <ToastContext.Provider value={{ showToast }}>
      <div className="min-h-screen bg-[#FFFDF9] text-gray-900 flex overflow-hidden">
        
        {/* DESKTOP SIDEBAR */}
        <aside className="hidden md:flex flex-col w-64 bg-white border-r border-gray-200 flex-shrink-0">
          <div className="h-16 flex items-center gap-3 px-6 border-b border-gray-200">
            <div className="h-9 w-9 rounded-xl bg-orange-500 flex items-center justify-center shadow-md shadow-orange-500/20">
              <Sparkles className="h-5 w-5 text-white" />
            </div>
            <div>
              <h1 className="font-bold text-base tracking-tight text-gray-900">LeadDiscovery</h1>
              <p className="text-[10px] text-orange-600 font-bold uppercase tracking-wider">Lead Generator Platform</p>
            </div>
          </div>
          
          <nav className="flex-1 px-4 py-6 space-y-1.5 overflow-y-auto">
            <div className="text-[10px] font-bold text-gray-400 uppercase tracking-wider px-3 mb-2">Main Menu</div>
            {navLinks.map((link) => {
              const Icon = link.icon;
              const active = pathname === link.href;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-semibold transition-all duration-200 group ${
                    active 
                      ? "bg-orange-50 text-orange-600 border-l-4 border-orange-500 font-bold" 
                      : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                  }`}
                >
                  <Icon className={`h-5 w-5 transition-transform duration-200 group-hover:scale-105 ${active ? "text-orange-500" : "text-gray-400 group-hover:text-gray-600"}`} />
                  {link.label}
                </Link>
              );
            })}

            {user?.role === "ADMIN" && (
              <div className="pt-4 mt-4 border-t border-gray-100">
                <div className="text-[10px] font-bold text-orange-600 uppercase tracking-wider px-3 mb-2 flex items-center gap-1.5">
                  <ShieldCheck className="h-3.5 w-3.5" />
                  Admin Console
                </div>
                {adminNavLinks.map((link) => {
                  const Icon = link.icon;
                  const active = pathname === link.href || (link.href !== "/admin" && pathname.startsWith(link.href));
                  return (
                    <Link
                      key={link.href}
                      href={link.href}
                      className={`flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm font-semibold transition-all duration-200 group ${
                        active 
                          ? "bg-orange-500 text-white font-bold shadow-md shadow-orange-500/20" 
                          : "text-gray-600 hover:bg-orange-50 hover:text-orange-700"
                      }`}
                    >
                      <Icon className={`h-4.5 w-4.5 ${active ? "text-white" : "text-gray-400 group-hover:text-orange-600"}`} />
                      {link.label}
                    </Link>
                  );
                })}
              </div>
            )}
          </nav>

          <div className="p-4 border-t border-gray-200">
            <div className="flex items-center gap-3 px-3 py-2.5 mb-2 rounded-xl bg-orange-50/50 border border-orange-100">
              <div className="h-8 w-8 rounded-full bg-orange-100 flex items-center justify-center border border-orange-200">
                <User className="h-4 w-4 text-orange-600" />
              </div>
              <div className="truncate flex-1">
                <p className="text-xs font-bold truncate text-gray-800">{user?.email || "User"}</p>
                <p className="text-[10px] text-gray-500 font-medium">Authorized Account</p>
              </div>
            </div>
            
            <button
              onClick={handleLogout}
              className="w-full flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm font-semibold text-gray-600 hover:bg-red-50 hover:text-red-600 transition-all duration-200"
            >
              <LogOut className="h-4.5 w-4.5" />
              Logout
            </button>
          </div>
        </aside>

        {/* MOBILE DRAWER SIDEBAR */}
        {mobileMenuOpen && (
          <div 
            className="fixed inset-0 z-50 flex md:hidden bg-gray-900/40 backdrop-blur-xs animate-in fade-in-20"
            onClick={() => setMobileMenuOpen(false)}
          >
            <div 
              className="w-64 bg-white flex flex-col h-full border-r border-gray-200 shadow-xl"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="h-16 flex items-center justify-between px-6 border-b border-gray-200">
                <div className="flex items-center gap-2.5">
                  <div className="h-8 w-8 rounded-lg bg-orange-500 flex items-center justify-center text-white">
                    <Sparkles className="h-4.5 w-4.5" />
                  </div>
                  <span className="font-bold text-gray-900">LeadDiscovery</span>
                </div>
                <button onClick={() => setMobileMenuOpen(false)} className="p-1 rounded-lg text-gray-500 hover:bg-gray-100">
                  <X className="h-5 w-5" />
                </button>
              </div>
              
              <nav className="flex-1 px-4 py-6 space-y-1 overflow-y-auto">
                <div className="text-[10px] font-bold text-gray-400 uppercase tracking-wider px-3 mb-1">Main Menu</div>
                {navLinks.map((link) => {
                  const Icon = link.icon;
                  const active = pathname === link.href;
                  return (
                    <Link
                      key={link.href}
                      href={link.href}
                      onClick={() => setMobileMenuOpen(false)}
                      className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-semibold transition-all ${
                        active 
                          ? "bg-orange-50 text-orange-600 font-bold" 
                          : "text-gray-600 hover:bg-gray-50"
                      }`}
                    >
                      <Icon className="h-5 w-5" />
                      {link.label}
                    </Link>
                  );
                })}

                {user?.role === "ADMIN" && (
                  <div className="pt-4 mt-4 border-t border-gray-100 space-y-1">
                    <div className="text-[10px] font-bold text-orange-600 uppercase tracking-wider px-3 mb-1 flex items-center gap-1.5">
                      <ShieldCheck className="h-3.5 w-3.5" />
                      Admin Console
                    </div>
                    {adminNavLinks.map((link) => {
                      const Icon = link.icon;
                      const active = pathname === link.href || (link.href !== "/admin" && pathname.startsWith(link.href));
                      return (
                        <Link
                          key={link.href}
                          href={link.href}
                          onClick={() => setMobileMenuOpen(false)}
                          className={`flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm font-semibold transition-all ${
                            active 
                              ? "bg-orange-500 text-white font-bold" 
                              : "text-gray-600 hover:bg-orange-50 hover:text-orange-700"
                          }`}
                        >
                          <Icon className="h-4.5 w-4.5" />
                          {link.label}
                        </Link>
                      );
                    })}
                  </div>
                )}
              </nav>

              <div className="p-4 border-t border-gray-200">
                <p className="text-xs text-gray-500 mb-2 truncate px-2 font-medium">{user?.email}</p>
                <button
                  onClick={handleLogout}
                  className="w-full flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm font-semibold text-red-600 hover:bg-red-50 transition-all"
                >
                  <LogOut className="h-5 w-5" />
                  Logout
                </button>
              </div>
            </div>
          </div>
        )}

        {/* MAIN PANEL CONTENT WRAPPER */}
        <div className="flex-1 flex flex-col overflow-hidden relative">
          
          {/* TOP NAV BAR */}
          <header className="h-16 border-b border-gray-200 bg-white flex items-center justify-between px-6 z-20 flex-shrink-0">
            <div className="flex items-center gap-3">
              <button 
                onClick={() => setMobileMenuOpen(true)}
                className="p-2 -ml-2 rounded-lg text-gray-600 hover:bg-gray-100 md:hidden"
              >
                <Menu className="h-6 w-6" />
              </button>
              <h2 className="text-lg font-bold text-gray-900">
                {pathname === "/" ? "Dashboard Overview" : 
                 pathname === "/scrape" ? "Create Scraping Task" :
                 pathname === "/history" ? "Task History" :
                 pathname === "/settings" ? "Configuration Settings" :
                 pathname.startsWith("/tasks/") ? "Live Scraping Task" : "LeadDiscovery Platform"}
              </h2>
            </div>
            
            <div className="flex items-center gap-4">
              <div className="hidden md:flex items-center gap-2 text-xs font-semibold px-3 py-1.5 rounded-full bg-orange-50 border border-orange-200 text-orange-700">
                <CheckCircle className="h-3.5 w-3.5 text-orange-500" />
                SSRF Protection Active
              </div>
            </div>
          </header>

          {/* PAGE INNER CONTENT CONTAINER */}
          <main className="flex-1 overflow-y-auto p-6 md:p-8 z-10 bg-[#FFFDF9]">
            {children}
          </main>
        </div>

        {/* Global Toast Render */}
        <ToastContainer toasts={toasts} setToasts={setToasts} />
      </div>
    </ToastContext.Provider>
  );
}

// 3. Render Container for toasts
function ToastContainer({ toasts, setToasts }: { toasts: Toast[]; setToasts: React.Dispatch<React.SetStateAction<Toast[]>> }) {
  if (toasts.length === 0) return null;
  
  return (
    <div className="fixed bottom-5 right-5 z-[9999] flex flex-col gap-2 max-w-sm w-full animate-in fade-in-20 slide-in-from-bottom-5">
      {toasts.map((toast) => {
        const isSuccess = toast.type === "success";
        const isError = toast.type === "error";
        return (
          <div
            key={toast.id}
            className={`flex items-start gap-3 p-4 rounded-xl border shadow-lg text-sm transition-all duration-300 ${
              isSuccess 
                ? "bg-white border-emerald-200 text-emerald-900"
                : isError
                ? "bg-white border-red-200 text-red-900"
                : "bg-white border-orange-200 text-gray-900"
            }`}
          >
            {isSuccess ? (
              <CheckCircle className="h-5 w-5 text-emerald-500 flex-shrink-0 mt-0.5" />
            ) : isError ? (
              <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
            ) : (
              <ShieldAlert className="h-5 w-5 text-orange-500 flex-shrink-0 mt-0.5" />
            )}
            <div className="flex-1 pr-4 font-medium">{toast.message}</div>
            <button 
              onClick={() => setToasts((prev) => prev.filter((t) => t.id !== toast.id))}
              className="text-xs font-bold text-gray-400 hover:text-gray-600 transition-opacity"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
