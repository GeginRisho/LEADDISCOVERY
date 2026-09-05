const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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

  public removeToken() {
    if (typeof window !== "undefined") {
      localStorage.removeItem("token");
    }
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
    return res;
  }

  async register(email: string, password: string): Promise<User> {
    return this.request("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password })
    });
  }

  async getMe(): Promise<User> {
    return this.request("/api/auth/me");
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
    return this.request("/api/tasks", {
      method: "POST",
      body: JSON.stringify(data)
    });
  }

  async getTasks(): Promise<ScrapingTask[]> {
    return this.request("/api/tasks");
  }

  async getTask(id: string): Promise<ScrapingTask> {
    return this.request(`/api/tasks/${id}`);
  }

  async getTaskLogs(id: string): Promise<ScrapingLog[]> {
    return this.request(`/api/tasks/${id}/logs`);
  }

  async getTaskLeads(id: string): Promise<Lead[]> {
    return this.request(`/api/tasks/${id}/leads`);
  }

  async cancelTask(id: string): Promise<{ message: string }> {
    return this.request(`/api/tasks/${id}/cancel`, {
      method: "POST"
    });
  }

  // LEADS API
  async getLead(id: number): Promise<Lead> {
    return this.request(`/api/leads/${id}`);
  }

  async deleteLead(id: number): Promise<{ message: string }> {
    return this.request(`/api/leads/${id}`, {
      method: "DELETE"
    });
  }

  // EXPORTS
  async downloadExport(taskId: string, format: "csv" | "excel"): Promise<Blob> {
    return this.request(`/api/tasks/${taskId}/export/${format}`);
  }

  // ADMIN API
  async getAdminOverview(): Promise<any> {
    return this.request("/api/admin/overview");
  }

  async getAdminUsers(): Promise<any[]> {
    return this.request("/api/admin/users");
  }

  async updateAdminUserStatusOrRole(userId: number, payload: { role?: string; status?: string }): Promise<any> {
    return this.request(`/api/admin/users/${userId}`, {
      method: "PATCH",
      body: JSON.stringify(payload)
    });
  }

  async getAdminTasks(): Promise<any[]> {
    return this.request("/api/admin/tasks");
  }

  async getAdminLogs(taskId?: string, eventType?: string): Promise<ScrapingLog[]> {
    const params = new URLSearchParams();
    if (taskId) params.append("task_id", taskId);
    if (eventType) params.append("event_type", eventType);
    const q = params.toString();
    return this.request(`/api/admin/logs${q ? "?" + q : ""}`);
  }

  async getAdminHealth(): Promise<any> {
    return this.request("/api/admin/health");
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
    return this.request("/api/organizations/stats");
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
    return this.request("/api/organizations/districts");
  }

  async getOrganizations(params?: {
    district?: string;
    category?: string;
    city?: string;
    confidence?: string;
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
    if (params?.confidence) qp.append("confidence", params.confidence);
    if (params?.search) qp.append("search", params.search);
    if (params?.page) qp.append("page", params.page.toString());
    if (params?.limit) qp.append("limit", params.limit.toString());
    const str = qp.toString();
    return this.request(`/api/organizations${str ? "?" + str : ""}`);
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
    return this.request("/api/organizations/matrix");
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
    return this.request("/api/organizations/manual", {
      method: "POST",
      body: JSON.stringify(data)
    });
  }

  async updateOrganization(id: number, data: any): Promise<{ message: string }> {
    return this.request(`/api/organizations/${id}`, {
      method: "PUT",
      body: JSON.stringify(data)
    });
  }

  async deleteOrganization(id: number): Promise<{ message: string }> {
    return this.request(`/api/organizations/${id}`, {
      method: "DELETE"
    });
  }

  async verifyOrganization(id: number): Promise<{ message: string }> {
    return this.request(`/api/organizations/${id}/verify`, {
      method: "POST"
    });
  }

  // DISCOVERY CAMPAIGNS API
  async getCampaigns(): Promise<any[]> {
    return this.request("/api/campaigns");
  }

  async getCampaignDetail(id: number): Promise<any> {
    return this.request(`/api/campaigns/${id}`);
  }

  async createCampaign(data: {
    name: string;
    category: string;
    region_scope?: string;
    max_results_per_region?: number;
    max_pages_per_site?: number;
    auto_start?: boolean;
  }): Promise<any> {
    return this.request("/api/campaigns", {
      method: "POST",
      body: JSON.stringify(data)
    });
  }

  async startCampaign(id: number): Promise<{ message: string }> {
    return this.request(`/api/campaigns/${id}/start`, { method: "POST" });
  }

  async pauseCampaign(id: number): Promise<{ message: string }> {
    return this.request(`/api/campaigns/${id}/pause`, { method: "POST" });
  }

  async cancelCampaign(id: number): Promise<{ message: string }> {
    return this.request(`/api/campaigns/${id}/cancel`, { method: "POST" });
  }

  async resumeCampaign(id: number): Promise<{ message: string }> {
    return this.request(`/api/campaigns/${id}/resume`, { method: "POST" });
  }

  async runAllTamilNadu(category: string, max_results_per_region: number = 15): Promise<any> {
    return this.request("/api/campaigns/run-all-tn", {
      method: "POST",
      body: JSON.stringify({ category, max_results_per_region })
    });
  }

  async runPuducherry(category: string, max_results_per_region: number = 15): Promise<any> {
    return this.request("/api/campaigns/run-puducherry", {
      method: "POST",
      body: JSON.stringify({ category, max_results_per_region })
    });
  }

  async runAllRegions(category: string, max_results_per_region: number = 15): Promise<any> {
    return this.request("/api/campaigns/run-all", {
      method: "POST",
      body: JSON.stringify({ category, max_results_per_region })
    });
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
    return this.request(`/api/admin/organizations?${q.toString()}`);
  }

  async getAdminOrganization(id: number): Promise<any> {
    return this.request(`/api/admin/organizations/${id}`);
  }

  async createAdminOrganization(data: any): Promise<any> {
    return this.request("/api/admin/organizations", {
      method: "POST",
      body: JSON.stringify(data)
    });
  }

  async updateAdminOrganization(id: number, data: any): Promise<any> {
    return this.request(`/api/admin/organizations/${id}`, {
      method: "PUT",
      body: JSON.stringify(data)
    });
  }

  async deleteAdminOrganization(id: number): Promise<any> {
    return this.request(`/api/admin/organizations/${id}`, {
      method: "DELETE"
    });
  }

  async addAdminBranch(orgId: number, data: any): Promise<any> {
    return this.request(`/api/admin/organizations/${orgId}/branches`, {
      method: "POST",
      body: JSON.stringify(data)
    });
  }

  async deleteAdminBranch(branchId: number): Promise<any> {
    return this.request(`/api/admin/branches/${branchId}`, {
      method: "DELETE"
    });
  }
}

export const api = new ApiClient();


