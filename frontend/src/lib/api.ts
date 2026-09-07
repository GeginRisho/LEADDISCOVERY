const getApiBase = (): string => {
  const url = process.env.NEXT_PUBLIC_API_URL || "https://leaddiscovery.onrender.com";
  return url.replace(/\/+$/, "");
};
const API_BASE = getApiBase();

export interface User {
  id: number;
  email: string;
  role: string;
  status: string;
  created_at: string;
}

export interface ScrapingTask {
  id: number;
  public_task_id: string;
  user_id?: number | null;
  user_email?: string | null;
  location: string;
  keyword: string;
  radius: number | null;
  max_results: number;
  max_pages_per_site: number;
  requested_fields?: string[];
  required_fields: string[];
  status: string;
  progress: number;
  discovered_count: number;
  websites_found: number;
  websites_crawled: number;
  phone_count: number;
  email_count: number;
  address_count: number;
  social_count?: number;
  duplicate_count: number;
  failed_count: number;
  lead_count?: number;
  error_info: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface ScrapingLog {
  id: number;
  task_id: number;
  event_type: string;
  message: string;
  metadata_json: Record<string, any> | null;
  created_at: string;
}

export interface PhoneNumber {
  id: number;
  raw_value: string;
  normalized_value: string;
  type: string;
  source_page_url: string | null;
  created_at: string;
}

export interface EmailAddress {
  id: number;
  email: string;
  extraction_method: string | null;
  source_page_url: string | null;
  created_at: string;
}

export interface SocialLink {
  id: number;
  platform: string;
  url: string;
  source_page_url: string | null;
  created_at: string;
}

export interface Website {
  id: number;
  domain: string | null;
  url: string | null;
  status: string;
  reason: string | null;
  confidence: string;
  created_at: string;
}

export interface Lead {
  id: number;
  task_id: number;
  name: string;
  category: string | null;
  discovery_source_url: string | null;
  address: string | null;
  city: string | null;
  state: string | null;
  pincode: string | null;
  confidence: string;
  created_at: string;
  updated_at: string;
  
  website: Website | null;
  phone_numbers: PhoneNumber[];
  email_addresses: EmailAddress[];
  social_links: SocialLink[];
}

class ApiClient {
  private inFlightRequests: Map<string, Promise<any>> = new Map();
  private memoryCache: Map<string, { data: any; timestamp: number }> = new Map();

  private getToken(): string | null {
    if (typeof window !== "undefined") {
      return localStorage.getItem("token");
    }
    return null;
  }

  private setToken(token: string) {
    if (typeof window !== "undefined") {
      localStorage.setItem("token", token);
    }
  }

  public getCachedUser(): User | null {
    if (typeof window !== "undefined") {
      const raw = localStorage.getItem("user_profile");
      if (raw) {
        try {
          return JSON.parse(raw);
        } catch {
          return null;
        }
      }
    }
    return null;
  }

  public setCachedUser(user: User | null) {
    if (typeof window !== "undefined") {
      if (user) {
        localStorage.setItem("user_profile", JSON.stringify(user));
      } else {
        localStorage.removeItem("user_profile");
      }
    }
  }

  public removeToken() {
    if (typeof window !== "undefined") {
      localStorage.removeItem("token");
      localStorage.removeItem("user_profile");
    }
    this.memoryCache.clear();
    this.inFlightRequests.clear();
  }

  public clearCache(pattern?: string) {
    if (!pattern) {
      this.memoryCache.clear();
      return;
    }
    for (const key of this.memoryCache.keys()) {
      if (key.includes(pattern)) {
        this.memoryCache.delete(key);
      }
    }
  }

  private async cachedGet<T>(endpoint: string, ttlMs: number): Promise<T> {
    const cached = this.memoryCache.get(endpoint);
    const now = Date.now();

    // Fresh cache: return immediately (< 1ms)
    if (cached && (now - cached.timestamp) < ttlMs) {
      return cached.data as T;
    }

    // In-flight deduplication: reuse running request promise
    let inFlight = this.inFlightRequests.get(endpoint);
    if (!inFlight) {
      inFlight = this.request(endpoint)
        .then((data) => {
          this.memoryCache.set(endpoint, { data, timestamp: Date.now() });
          this.inFlightRequests.delete(endpoint);
          return data;
        })
        .catch((err) => {
          this.inFlightRequests.delete(endpoint);
          throw err;
        });
      this.inFlightRequests.set(endpoint, inFlight);
    }

    // Stale-while-revalidate: return stale cached data instantly while background revalidates
    if (cached) {
      return cached.data as T;
    }

    return inFlight;
  }

  private async request(endpoint: string, options: RequestInit = {}): Promise<any> {
    const url = `${API_BASE}${endpoint}`;
    const headers = new Headers(options.headers || {});
    
    // Inject JWT token if available
    const token = this.getToken();
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }

    if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }

    let response: Response;
    try {
      response = await fetch(url, {
        ...options,
        headers
      });
    } catch (err: any) {
      throw new Error("Unable to connect to the server.");
    }

    if (response.status === 401) {
      this.removeToken();
      if (typeof window !== "undefined" && window.location.pathname !== "/login" && window.location.pathname !== "/register") {
        window.location.href = "/login";
      }
      throw new Error("Session expired. Please sign in again.");
    }

    if (!response.ok) {
      let errorDetail = "An error occurred.";
      try {
        const errorData = await response.json();
        errorDetail = errorData.detail || errorDetail;
      } catch {
        if (response.status === 500 || response.status === 502 || response.status === 503) {
          errorDetail = "Server unavailable. Please try again later.";
        }
      }
      throw new Error(errorDetail);
    }

    // Handle file streams/blobs (e.g. downloads)
    const contentType = response.headers.get("content-type");
    if (contentType && (contentType.includes("csv") || contentType.includes("sheet") || contentType.includes("excel") || contentType.includes("octet-stream") || contentType.includes("application/vnd"))) {
      return response.blob();
    }

    return response.json();
  }

  // AUTH API
  async login(email: string, password: string): Promise<{ access_token: string }> {
    const res = await this.request("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password })
    });
    this.setToken(res.access_token);
    try {
      const user = await this.getMe();
      this.setCachedUser(user);
    } catch {}
    return res;
  }

  async register(email: string, password: string): Promise<User> {
    return this.request("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password })
    });
  }

  async getMe(): Promise<User> {
    const user = await this.cachedGet<User>("/api/auth/me", 300_000); // 5 min TTL
    if (user) {
      this.setCachedUser(user);
    }
    return user;
  }

  // TASKS API
  async createTask(data: {
    location: string;
    keyword: string;
    radius?: number;
    max_results?: number;
    max_pages_per_site?: number;
    requested_fields?: string[];
    required_fields?: string[];
  }): Promise<ScrapingTask> {
    const res = await this.request("/api/tasks", {
      method: "POST",
      body: JSON.stringify(data)
    });
    this.clearCache("tasks");
    this.clearCache("overview");
    return res;
  }

  async getTasks(page: number = 1, limit: number = 50): Promise<ScrapingTask[]> {
    return this.cachedGet<ScrapingTask[]>(`/api/tasks?page=${page}&limit=${limit}`, 15_000);
  }

  async getTask(id: string): Promise<ScrapingTask> {
    return this.cachedGet<ScrapingTask>(`/api/tasks/${id}`, 15_000);
  }

  async getTaskLogs(id: string): Promise<ScrapingLog[]> {
    return this.cachedGet<ScrapingLog[]>(`/api/tasks/${id}/logs`, 15_000);
  }

  async getTaskLeads(id: string): Promise<Lead[]> {
    return this.cachedGet<Lead[]>(`/api/tasks/${id}/leads`, 15_000);
  }

  async cancelTask(id: string): Promise<{ message: string }> {
    const res = await this.request(`/api/tasks/${id}/cancel`, {
      method: "POST"
    });
    this.clearCache("tasks");
    return res;
  }

  // LEADS API
  async getLead(id: number): Promise<Lead> {
    return this.cachedGet<Lead>(`/api/leads/${id}`, 30_000);
  }

  async deleteLead(id: number): Promise<{ message: string }> {
    const res = await this.request(`/api/leads/${id}`, {
      method: "DELETE"
    });
    this.clearCache("leads");
    this.clearCache("tasks");
    return res;
  }

  // EXPORTS
  async downloadExport(taskId: string, format: "csv" | "excel"): Promise<Blob> {
    return this.request(`/api/tasks/${taskId}/export/${format}`);
  }

  // ADMIN API
  async getAdminOverview(): Promise<any> {
    return this.cachedGet<any>("/api/admin/overview", 20_000);
  }

  async getAdminUsers(): Promise<any[]> {
    return this.cachedGet<any[]>("/api/admin/users", 20_000);
  }

  async updateAdminUserStatusOrRole(userId: number, payload: { role?: string; status?: string }): Promise<any> {
    const res = await this.request(`/api/admin/users/${userId}`, {
      method: "PATCH",
      body: JSON.stringify(payload)
    });
    this.clearCache("admin");
    return res;
  }

  async getAdminTasks(): Promise<any[]> {
    return this.cachedGet<any[]>("/api/admin/tasks", 15_000);
  }

  async getAdminLogs(taskId?: string, eventType?: string): Promise<ScrapingLog[]> {
    const params = new URLSearchParams();
    if (taskId) params.append("task_id", taskId);
    if (eventType) params.append("event_type", eventType);
    const q = params.toString();
    return this.cachedGet<ScrapingLog[]>(`/api/admin/logs${q ? "?" + q : ""}`, 15_000);
  }

  async getAdminHealth(): Promise<any> {
    return this.cachedGet<any>("/api/admin/health", 10_000);
  }

  // ORGANIZATIONS & DISTRICTS API
  async getOrganizationSummaryStats(): Promise<{
    total_organizations: number;
    new_today: number;
    updated_today: number;
    verified_websites: number;
    total_phones: number;
    total_emails: number;
  }> {
    return this.cachedGet("/api/organizations/stats", 30_000);
  }

  async getDistrictStats(): Promise<Array<{
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
  }>> {
    return this.cachedGet("/api/organizations/districts", 60_000);
  }

  async getOrganizations(params?: {
    district?: string;
    category?: string;
    city?: string;
    state?: string;
    country?: string;
    confidence?: string;
    verification_status?: string;
    search?: string;
    page?: number;
    limit?: number;
  }): Promise<{
    total: number;
    page: number;
    limit: number;
    pages: number;
    organizations: any[];
  }> {
    const qp = new URLSearchParams();
    if (params?.district) qp.append("district", params.district);
    if (params?.category) qp.append("category", params.category);
    if (params?.city) qp.append("city", params.city);
    if (params?.state) qp.append("state", params.state);
    if (params?.country) qp.append("country", params.country);
    if (params?.confidence) qp.append("confidence", params.confidence);
    if (params?.verification_status) qp.append("verification_status", params.verification_status);
    if (params?.search) qp.append("search", params.search);
    if (params?.page) qp.append("page", params.page.toString());
    if (params?.limit) qp.append("limit", params.limit.toString());
    const str = qp.toString();
    return this.cachedGet(`/api/organizations${str ? "?" + str : ""}`, 30_000);
  }

  async getOrganizationMatrix(): Promise<Array<{
    region: string;
    colleges: number;
    schools: number;
    hotels: number;
    hospitals: number;
    companies: number;
    it_companies: number;
    total: number;
  }>> {
    return this.cachedGet("/api/organizations/matrix", 30_000);
  }

  async addOrganizationManual(data: {
    name: string;
    category: string;
    district: string;
    city?: string;
    address?: string;
    phone?: string;
    email?: string;
    website?: string;
    whatsapp?: string;
    confidence?: string;
  }): Promise<{ message: string; id: number }> {
    const res = await this.request("/api/organizations/manual", {
      method: "POST",
      body: JSON.stringify(data)
    });
    this.clearCache("organizations");
    this.clearCache("search");
    return res;
  }

  async updateOrganization(id: number, data: any): Promise<{ message: string }> {
    const res = await this.request(`/api/organizations/${id}`, {
      method: "PUT",
      body: JSON.stringify(data)
    });
    this.clearCache("organizations");
    this.clearCache("search");
    return res;
  }

  async deleteOrganization(id: number): Promise<{ message: string }> {
    const res = await this.request(`/api/organizations/${id}`, {
      method: "DELETE"
    });
    this.clearCache("organizations");
    this.clearCache("search");
    return res;
  }

  async verifyOrganization(id: number): Promise<{ message: string }> {
    const res = await this.request(`/api/organizations/${id}/verify`, {
      method: "POST"
    });
    this.clearCache("organizations");
    this.clearCache("search");
    return res;
  }

  async unverifyOrganization(id: number): Promise<{ message: string }> {
    const res = await this.request(`/api/organizations/${id}/unverify`, {
      method: "POST"
    });
    this.clearCache("organizations");
    this.clearCache("search");
    return res;
  }

  // DISCOVERY CAMPAIGNS API
  async getCampaigns(): Promise<any[]> {
    return this.cachedGet<any[]>("/api/campaigns", 30_000);
  }

  async getCampaignDetail(id: number): Promise<any> {
    return this.cachedGet<any>(`/api/campaigns/${id}`, 15_000);
  }

  async createCampaign(data: {
    name: string;
    category: string;
    region_scope?: string;
    max_results_per_region?: number;
    max_pages_per_site?: number;
    auto_start?: boolean;
  }): Promise<any> {
    const res = await this.request("/api/campaigns", {
      method: "POST",
      body: JSON.stringify(data)
    });
    this.clearCache("campaigns");
    return res;
  }

  async startCampaign(id: number): Promise<{ message: string }> {
    const res = await this.request(`/api/campaigns/${id}/start`, { method: "POST" });
    this.clearCache("campaigns");
    return res;
  }

  async pauseCampaign(id: number): Promise<{ message: string }> {
    const res = await this.request(`/api/campaigns/${id}/pause`, { method: "POST" });
    this.clearCache("campaigns");
    return res;
  }

  async cancelCampaign(id: number): Promise<{ message: string }> {
    const res = await this.request(`/api/campaigns/${id}/cancel`, { method: "POST" });
    this.clearCache("campaigns");
    return res;
  }

  async resumeCampaign(id: number): Promise<{ message: string }> {
    const res = await this.request(`/api/campaigns/${id}/resume`, { method: "POST" });
    this.clearCache("campaigns");
    return res;
  }

  async runAllTamilNadu(category: string, max_results_per_region: number = 15): Promise<any> {
    const res = await this.request("/api/campaigns/run-all-tn", {
      method: "POST",
      body: JSON.stringify({ category, max_results_per_region })
    });
    this.clearCache("campaigns");
    return res;
  }

  async runPuducherry(category: string, max_results_per_region: number = 15): Promise<any> {
    const res = await this.request("/api/campaigns/run-puducherry", {
      method: "POST",
      body: JSON.stringify({ category, max_results_per_region })
    });
    this.clearCache("campaigns");
    return res;
  }

  async runAllRegions(category: string, max_results_per_region: number = 15): Promise<any> {
    const res = await this.request("/api/campaigns/run-all", {
      method: "POST",
      body: JSON.stringify({ category, max_results_per_region })
    });
    this.clearCache("campaigns");
    return res;
  }

  // ADMIN MASTER ORGANIZATIONS API
  async getAdminOrganizations(params?: {
    search?: string;
    category?: string;
    sub_category?: string;
    district?: string;
    state?: string;
    verification_status?: string;
    page?: number;
    page_size?: number;
  }): Promise<{ page: number; page_size: number; total_records: number; total_pages: number; items: any[] }> {
    const q = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== "") q.append(k, String(v));
      });
    }
    return this.cachedGet(`/api/admin/organizations?${q.toString()}`, 30_000);
  }

  async getAdminOrganization(id: number): Promise<any> {
    return this.cachedGet(`/api/admin/organizations/${id}`, 30_000);
  }

  async createAdminOrganization(data: any): Promise<any> {
    const res = await this.request("/api/admin/organizations", {
      method: "POST",
      body: JSON.stringify(data)
    });
    this.clearCache("organizations");
    this.clearCache("search");
    return res;
  }

  async updateAdminOrganization(id: number, data: any): Promise<any> {
    const res = await this.request(`/api/admin/organizations/${id}`, {
      method: "PUT",
      body: JSON.stringify(data)
    });
    this.clearCache("organizations");
    this.clearCache("search");
    return res;
  }

  async deleteAdminOrganization(id: number): Promise<any> {
    const res = await this.request(`/api/admin/organizations/${id}`, {
      method: "DELETE"
    });
    this.clearCache("organizations");
    this.clearCache("search");
    return res;
  }

  async addAdminBranch(orgId: number, data: any): Promise<any> {
    const res = await this.request(`/api/admin/organizations/${orgId}/branches`, {
      method: "POST",
      body: JSON.stringify(data)
    });
    this.clearCache("organizations");
    this.clearCache("search");
    return res;
  }

  async deleteAdminBranch(branchId: number): Promise<any> {
    const res = await this.request(`/api/admin/branches/${branchId}`, {
      method: "DELETE"
    });
    this.clearCache("organizations");
    this.clearCache("search");
    return res;
  }

  async verifyAdminOrganization(id: number): Promise<any> {
    const res = await this.request(`/api/admin/organizations/${id}/verify`, {
      method: "POST"
    });
    this.clearCache("organizations");
    this.clearCache("search");
    return res;
  }

  async unverifyAdminOrganization(id: number): Promise<any> {
    const res = await this.request(`/api/admin/organizations/${id}/unverify`, {
      method: "POST"
    });
    this.clearCache("organizations");
    this.clearCache("search");
    return res;
  }
}

export const api = new ApiClient();


