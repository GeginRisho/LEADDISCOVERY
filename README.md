# LeadDiscovery SaaS Platform

LeadDiscovery is an enterprise-grade full-stack Web Scraping & Lead Discovery SaaS Platform designed to securely discover business organizations, identify their official websites, responsibly crawl relevant subpaths, and extract publicly visible contact details.

---

## 🛠️ Tech Stack & Architecture

### Frontend (Next.js Application)
- **Framework**: Next.js 15+ (App Router, TypeScript)
- **Styling**: Tailwind CSS v4, Lucide Icons, responsive viewport queries
- **Data Fetching**: Custom API client featuring automatic JWT injection and session routing guards

### Backend (Python Application)
- **Framework**: FastAPI (async event triggers, auto Swagger docs)
- **Database ORM**: SQLAlchemy 2.0 mapping to PostgreSQL
- **Parsing**: BeautifulSoup4 & lxml
- **Scraper Engine**: HTTPX (Level 1 crawling) with a lazy-allocated Playwright Chromium context (Level 2 fallback for SPA pages)

---

## 🔒 Security & Responsible Crawling Controls

1. **SSRF Protection**: Every user-provided or search-discovered URL is resolved to its IP addresses. Hostnames that resolve to private subnets (`127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), Link-local ranges (`169.254.0.0/16`), or multicast/loopback destinations are immediately blocked.
2. **Redirect Revalidation**: A manual redirection flow intercepts every hop and revalidates destination URLs before following them.
3. **Robots.txt Enforcements**: A cached robots checker verifies crawl permissions for every target domain. Domains with disallowed robots paths are logged and skipped.
4. **No Captcha/Auth Bypasses**: Does not bypass CAPTCHAs, paywalls, or credential fields. Respects rate limits, timeouts, and stop signals.

---

## 🚀 Installation & Local Setup

### Prerequisites
- **Node.js (v18+)**
- **Python (3.10+)**
- **PostgreSQL Database** (running locally on port 5432)

---

### 1. Environment Configurations
Copy `.env.example` to `.env` in the project root:
```bash
cp .env.example .env
```
Ensure `DATABASE_URL` matches your local PostgreSQL username, password, and port:
```env
DATABASE_URL=postgresql://postgres:1234@localhost:5432/lead_scraper
SECRET_KEY=generate-a-strong-jwt-hex-secret
```

---

### 2. Backend Initialization
1. Navigate to `backend`:
   ```bash
   cd backend
   ```
2. Install Python packages:
   ```bash
   pip install -r requirements.txt
   ```
3. Install Playwright Chromium browser binaries:
   ```bash
   python -m playwright install chromium
   ```
4. Start the FastAPI server (it will automatically create the `lead_scraper` database and all required tables on startup if they don't exist):
   ```bash
   python app/main.py
   ```
   The backend server boots on `http://localhost:8000`. You can access auto-generated OpenAPI documentation at `http://localhost:8000/docs`.

---

### 3. Frontend Initialization
1. Open a new terminal in the `frontend` folder:
   ```bash
   cd frontend
   ```
2. Install Node packages:
   ```bash
   npm install
   ```
3. Start the Next.js development server:
   ```bash
   npm run dev
   ```
   The frontend application boots on `http://localhost:3000`. Open this URL in your web browser.

---

### 4. Running Automated Tests
The backend contains a suite of 13 unit tests verifying extraction regex, URL safety blocklists, deduplication, and REST API controllers.
To run the tests:
1. Open a terminal in the root workspace:
   ```bash
   $env:PYTHONPATH="backend"
   python -m pytest backend/tests
   ```

---

## 📈 Database Models
The platform implements a fully normalized database schema:
- **`users`**: Registers credentials and creation dates.
- **`scraping_tasks`**: Stores search inputs, live stats counters, and progress states.
- **`organizations`**: Houses merged entity records, physical addresses, and Jaccard match keys.
- **`websites`**: Stores identified official domains, robots status, and connection results.
- **`source_pages`**: Tracks crawled subpaths (e.g. `/contact`, `/about`) to maintain audits.
- **`phone_numbers`**, **`email_addresses`**, and **`social_links`**: Extracted data records linked directly back to their parent `source_pages` URL.
- **`scraping_logs`**: Chronological log trail of task milestones.
