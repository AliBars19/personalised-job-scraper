# JOB_SCRAPER_SPEC.md — "CorkBoard" Job Scraper & Auto-Apply Platform

## Project Overview

A job scraping platform for a non-technical user looking for **hospitality management** and **wine industry** roles in **London**. The system scrapes major UK job boards, verifies link integrity, displays results in a clean LinkedIn-style feed, and provides a Chrome extension that auto-fills application forms using a growing database of per-domain field mappings.

### Architecture

```
┌─────────────────────┐     ┌──────────────┐     ┌──────────────────┐
│  DO Droplet (Scraper)│────▶│   Supabase   │◀────│  Vercel (Next.js)│
│  Python + Playwright │     │   Database   │     │   Frontend UI    │
│  Cron: every 4-6 hrs │     └──────┬───────┘     └──────────────────┘
└─────────────────────┘            │
                                   │
                          ┌────────▼────────┐
                          │ Chrome Extension │
                          │  Auto-fill Forms │
                          └─────────────────┘
```

- **Scraper** — Python, runs on existing DigitalOcean droplet as a systemd service or Docker container. Cron-triggered every 4-6 hours.
- **Database** — Supabase (Postgres). Stores jobs, user profile, application status, and form field mappings.
- **Frontend** — Next.js on Vercel. LinkedIn-style scrolling job feed. Dead simple, no auth (single user, can add a simple password gate if needed).
- **Chrome Extension** — Manifest V3. Reads field mappings from Supabase, auto-fills application forms when user clicks "Apply" from dashboard.

---

## 1. Scraper (Python — DigitalOcean)

### 1.1 Target Sources

Scrape the following sites for hospitality management and wine roles in London:

| Source | Priority | Method | Notes |
|--------|----------|--------|-------|
| **Indeed UK** | P0 | HTTP + BS4 | Largest volume, straightforward HTML |
| **Reed.co.uk** | P0 | HTTP + BS4 | Major UK board, good hospitality coverage |
| **Caterer.com** | P0 | Playwright | THE hospitality-specific board, JS-heavy |
| **Totaljobs** | P1 | HTTP + BS4 | Good general coverage |
| **LinkedIn** | P1 | RSS feeds / API | Anti-scrape is aggressive — use job RSS or unofficial API cautiously |
| **Wine-Searcher Jobs** | P2 | HTTP + BS4 | Niche wine industry listings |
| **Harpers Jobs** | P2 | HTTP + BS4 | Wine & spirits trade publication jobs |
| **Hospitality Jobs UK** | P2 | HTTP + BS4 | Smaller niche board |
| **The Drinks Business Jobs** | P2 | HTTP + BS4 | Wine/spirits specific |

### 1.2 Search Queries

For each source, rotate through these search queries (adapted per site's search syntax):

**Hospitality Management:**
- "hospitality manager london"
- "hotel manager london"
- "restaurant manager london"
- "front of house manager london"
- "food and beverage manager london"
- "events manager hospitality london"
- "general manager hospitality london"
- "assistant manager hospitality london"

**Wine Industry:**
- "wine manager london"
- "sommelier london"
- "wine buyer london"
- "wine sales london"
- "wine merchant london"
- "head sommelier london"
- "wine bar manager london"
- "wine consultant london"
- "cellar manager london"

### 1.3 Data Model — Scraped Job

```python
@dataclass
class ScrapedJob:
    id: str                    # UUID, generated
    source: str                # "indeed", "reed", "caterer", etc.
    source_url: str            # Original listing URL
    title: str
    company: str
    location: str              # Should contain "London" or London postcode
    salary: str | None         # Raw salary text e.g. "£35,000 - £42,000"
    salary_min: int | None     # Parsed minimum (pence)
    salary_max: int | None     # Parsed maximum (pence)
    description: str           # Full job description text
    posted_date: datetime | None
    scraped_at: datetime
    category: str              # "hospitality" or "wine"
    application_url: str | None # Direct apply link if different from listing
    application_type: str      # "easy_apply", "external", "email", "unknown"
    is_active: bool            # Link verification status
    last_verified: datetime
    domain: str                # Extracted domain of application URL for field mapping
```

### 1.4 Scraper Logic

```
For each source:
  1. Fetch search results pages (paginate up to 5 pages per query)
  2. Extract job listing URLs
  3. For each listing URL:
     a. Check if URL already exists in DB → skip if yes
     b. Fetch full listing page
     c. Parse: title, company, location, salary, description, posted date
     d. Filter: must be London-based (check for "London", London postcodes EC/WC/SW/SE/NW/N/E/W + number)
     e. Determine application_type (see 1.5)
     f. Extract application_url and domain
     g. Insert into Supabase
  4. Rate limit: 2-3 second delay between requests per source
  5. Rotate User-Agent headers
  6. Log all scrape runs with counts per source
```

### 1.5 Application Type Detection

When scraping each job, classify the application flow:

| Type | Detection | Example |
|------|-----------|---------|
| `easy_apply` | Apply button stays on same domain, single form | Indeed Easy Apply |
| `external` | Apply redirects to company careers page | Links to company ATS |
| `email` | Application is via email | "Send CV to jobs@company.com" |
| `ats_known` | Redirects to known ATS (Workday, Greenhouse, Lever, etc.) | greenhouse.io/company/jobs/123 |
| `unknown` | Can't determine | Fallback |

Store the `domain` of wherever the apply button leads — this feeds the auto-fill mapping system.

### 1.6 Link Verification

**CRITICAL: Every time the database is updated, verify link integrity.**

```
Link Verification Process (runs after every scrape cycle):
  1. Query all jobs where is_active = true
  2. For each active job:
     a. HEAD request to source_url (follow redirects)
     b. If HTTP 200:
        - Check response for "job expired", "no longer available", "position filled" text patterns
        - If expired text found → mark is_active = false
        - Else → update last_verified timestamp
     c. If HTTP 404/410/301-to-homepage → mark is_active = false
     d. If HTTP 403/429 → skip (rate limited, don't mark inactive)
     e. If connection error/timeout after 3 retries → mark is_active = false
  3. Also verify application_url separately if different from source_url
  4. Rate limit: 1 second between verification requests
  5. Jobs inactive for 14+ days → archive (soft delete, keep in DB but hide from feed)
```

**Additional verification signals per source:**

- **Indeed**: Check for "this job has expired" banner
- **Reed**: Check for "This job is no longer being advertised" text
- **Caterer**: Check for redirect to search page (means listing removed)
- **Totaljobs**: Check for "Sorry, this job is no longer available" text
- **LinkedIn**: Check for "No longer accepting applications" text

### 1.7 Deduplication

Jobs often appear on multiple sites. Deduplicate using:

1. **Exact URL match** — same listing, skip
2. **Fuzzy title + company match** — normalise strings (lowercase, strip Ltd/Limited/Inc, strip punctuation), if title similarity > 85% AND company similarity > 80% AND location matches → flag as duplicate, keep the one with most info (longer description, has salary)
3. Store `duplicate_of` field pointing to the canonical job ID

### 1.8 Cron Schedule

```cron
# Main scrape: every 6 hours
0 */6 * * * /path/to/scraper/run.sh

# Link verification: daily at 3am
0 3 * * * /path/to/scraper/verify.sh

# Archive old inactive jobs: weekly Sunday 4am
0 4 * * 0 /path/to/scraper/archive.sh
```

### 1.9 Dependencies

```
python 3.11+
playwright
beautifulsoup4
httpx (async HTTP client, better than requests for this)
supabase-py
python-dateutil
fuzzywuzzy or rapidfuzz (deduplication)
```

---

## 2. Database Schema (Supabase)

### 2.1 Tables

```sql
-- Core jobs table
CREATE TABLE jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source TEXT NOT NULL,
  source_url TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  company TEXT NOT NULL,
  location TEXT NOT NULL,
  salary_text TEXT,
  salary_min INTEGER,
  salary_max INTEGER,
  description TEXT,
  posted_date TIMESTAMPTZ,
  scraped_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  category TEXT NOT NULL CHECK (category IN ('hospitality', 'wine')),
  application_url TEXT,
  application_type TEXT DEFAULT 'unknown',
  application_domain TEXT,
  is_active BOOLEAN DEFAULT TRUE,
  last_verified TIMESTAMPTZ DEFAULT NOW(),
  duplicate_of UUID REFERENCES jobs(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- User application tracking
CREATE TABLE applications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id UUID REFERENCES jobs(id) NOT NULL,
  status TEXT NOT NULL DEFAULT 'new' CHECK (status IN ('new', 'saved', 'applied', 'interviewing', 'rejected', 'offer')),
  notes TEXT,
  applied_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- User profile for auto-fill
CREATE TABLE user_profile (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  first_name TEXT,
  last_name TEXT,
  email TEXT,
  phone TEXT,
  address_line_1 TEXT,
  address_line_2 TEXT,
  city TEXT DEFAULT 'London',
  postcode TEXT,
  country TEXT DEFAULT 'United Kingdom',
  linkedin_url TEXT,
  portfolio_url TEXT,
  current_job_title TEXT,
  years_experience INTEGER,
  right_to_work TEXT DEFAULT 'Yes',
  notice_period TEXT,
  expected_salary TEXT,
  cv_url TEXT,  -- URL to stored CV file
  cover_letter_template TEXT,
  additional_fields JSONB DEFAULT '{}'::jsonb,  -- Catch-all for extra fields
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Form field mappings for auto-fill (THE KEY TABLE)
CREATE TABLE field_mappings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  domain TEXT NOT NULL,          -- e.g. "careers.hilton.com"
  page_url_pattern TEXT,         -- regex pattern for URL matching
  field_selector TEXT NOT NULL,  -- CSS selector for the form field
  field_type TEXT NOT NULL,      -- "text", "email", "tel", "select", "textarea", "file", "checkbox", "radio"
  field_label TEXT,              -- Human readable label (scraped from <label> or placeholder)
  maps_to TEXT NOT NULL,         -- Which user_profile field this maps to
  select_value_map JSONB,       -- For <select>: {"profile_value": "option_value"}
  is_verified BOOLEAN DEFAULT FALSE,  -- Has this mapping been confirmed working?
  last_used TIMESTAMPTZ,
  times_used INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(domain, field_selector)
);

-- Unmapped fields (flagged for manual review)
CREATE TABLE unmapped_fields (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  domain TEXT NOT NULL,
  page_url TEXT NOT NULL,
  field_selector TEXT NOT NULL,
  field_type TEXT NOT NULL,
  field_label TEXT,
  field_name TEXT,             -- HTML name attribute
  field_placeholder TEXT,
  screenshot_url TEXT,         -- Optional screenshot of the form
  resolved BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Scrape run logs
CREATE TABLE scrape_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source TEXT NOT NULL,
  started_at TIMESTAMPTZ NOT NULL,
  completed_at TIMESTAMPTZ,
  jobs_found INTEGER DEFAULT 0,
  jobs_new INTEGER DEFAULT 0,
  jobs_duplicate INTEGER DEFAULT 0,
  jobs_verified INTEGER DEFAULT 0,
  jobs_expired INTEGER DEFAULT 0,
  errors JSONB DEFAULT '[]'::jsonb,
  status TEXT DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed'))
);

-- Indexes
CREATE INDEX idx_jobs_active ON jobs(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_jobs_category ON jobs(category);
CREATE INDEX idx_jobs_source ON jobs(source);
CREATE INDEX idx_jobs_scraped_at ON jobs(scraped_at DESC);
CREATE INDEX idx_jobs_domain ON jobs(application_domain);
CREATE INDEX idx_applications_status ON applications(status);
CREATE INDEX idx_field_mappings_domain ON field_mappings(domain);
CREATE INDEX idx_unmapped_fields_domain ON unmapped_fields(domain) WHERE resolved = FALSE;
```

### 2.2 Row Level Security

Since this is single-user, RLS can be simple. Use a service key for the scraper and anon key for the frontend with basic policies. If adding auth later, use Supabase Auth.

---

## 3. Frontend (Next.js — Vercel)

### 3.1 Pages

```
/                  → Job feed (main page)
/job/[id]          → Job detail view
/applications      → Track applied jobs
/profile           → Edit auto-fill profile & upload CV
/settings          → Manage search preferences, notification settings
/mappings          → View/manage field mappings (admin-ish page)
```

### 3.2 Main Feed — LinkedIn-Style Scrolling

**This is the core UX. Must feel like scrolling LinkedIn jobs.**

```
┌─────────────────────────────────────────────────┐
│  🔍 [Search/Filter Bar]                         │
│  [All] [Hospitality] [Wine]  [Salary ▼] [Date ▼]│
├─────────────────────────────────────────────────┤
│                                                  │
│  ┌─────────────────────────────────────────┐    │
│  │ 🏨 Restaurant General Manager           │    │
│  │ The Ivy Collection · London W1          │    │
│  │ £45,000 - £55,000 · Posted 2 days ago   │    │
│  │                                          │    │
│  │ [View & Apply]  [Save]  [✓ Applied]     │    │
│  │                              via Indeed  │    │
│  └─────────────────────────────────────────┘    │
│                                                  │
│  ┌─────────────────────────────────────────┐    │
│  │ 🍷 Head Sommelier                       │    │
│  │ Corbin & King · London SW1              │    │
│  │ £40,000 - £48,000 · Posted 1 day ago    │    │
│  │                                          │    │
│  │ [View & Apply]  [Save]  [✓ Applied]     │    │
│  │                            via Caterer   │    │
│  └─────────────────────────────────────────┘    │
│                                                  │
│  ... infinite scroll loading more jobs ...       │
│                                                  │
└─────────────────────────────────────────────────┘
```

**Key behaviours:**
- **Infinite scroll** — load 20 jobs at a time, fetch more on scroll (use `IntersectionObserver`)
- **Smooth scroll animations** — cards slide in with subtle fade + translate-y animation as they enter viewport
- **Job cards** — show title, company, location, salary range, posted date, source badge
- **Category indicator** — 🏨 for hospitality, 🍷 for wine
- **Status tracking on each card:**
  - `New` — default, blue dot indicator
  - `Saved` — bookmarked for later
  - `Applied` — user has submitted application
  - `Interviewing` — progressed to interview stage
  - Status is selectable via a dropdown or button group directly on the card
- **"View & Apply" button** — opens job detail page; if Chrome extension is installed, also triggers auto-fill on the application page
- **Filters:**
  - Category: All / Hospitality / Wine
  - Salary: Any / £25k+ / £35k+ / £45k+ / £55k+
  - Date posted: Any / Last 24h / Last 7 days / Last 30 days
  - Source: All / Indeed / Reed / Caterer / etc.
  - Status: All / New / Saved / Applied
- **Sort:** Most recent (default) / Salary high-low / Salary low-high
- **Only show `is_active = true` jobs** (verified links only)
- **Hide duplicates** — don't show jobs where `duplicate_of IS NOT NULL`
- **Seen indicator** — subtle visual difference for jobs already viewed

### 3.3 Job Detail View

Expanded view of the job with full description. Include:
- Full parsed job description (rendered from text, preserve formatting)
- Salary info
- Source link
- Application type badge
- "Apply" button (opens application URL; if extension installed, triggers auto-fill)
- Status selector (same as card)
- Notes textarea for personal notes about the application

### 3.4 Applications Tracker

Kanban-style or table view of all jobs where status != 'new':

| Saved | Applied | Interviewing | Offered | Rejected |
|-------|---------|-------------|---------|----------|

- Drag-and-drop between columns (if kanban)
- Show applied date, notes, company, role
- Quick stats at top: "You've applied to X jobs this week"

### 3.5 Profile Page

Form to fill in all user_profile fields:
- Personal details (name, email, phone, address)
- Professional info (current title, years experience, notice period, expected salary)
- Links (LinkedIn, portfolio)
- CV upload (store in Supabase Storage, keep URL in profile)
- Cover letter template (textarea with placeholder variables like {company_name}, {job_title})
- Additional fields (dynamic key-value pairs for anything extra)

### 3.6 Styling & Design

- **Framework:** Tailwind CSS
- **Font:** Inter or similar clean sans-serif
- **Palette:** Clean, professional — white background, subtle grays, accent colour for CTAs
- **Mobile responsive** — this user will likely check on phone too
- **Dark mode** — optional but nice to have
- **Animations:** Framer Motion for card entrance animations, status transitions
- **No clutter** — this is for someone who is not tech-savvy. Every screen should be immediately obvious

### 3.7 Tech Stack

```
next.js 14+ (app router)
typescript
tailwind css
framer-motion (animations)
@supabase/supabase-js
@supabase/ssr (for server components)
zustand (minimal state management)
react-intersection-observer (infinite scroll)
```

---

## 4. Chrome Extension — Auto-Fill System

### 4.1 Overview

The Chrome extension is the "magic" feature. When the user clicks "Apply" from the dashboard, it opens the application page and auto-fills every form field it recognises from the field mapping database.

### 4.2 Manifest V3 Structure

```
extension/
├── manifest.json
├── background.js          # Service worker
├── content.js             # Injected into application pages
├── popup.html             # Extension popup UI
├── popup.js
├── mapping-engine.js      # Form field detection & filling logic
├── supabase-client.js     # Supabase connection
└── icons/
```

### 4.3 How It Works

```
Flow:
1. User clicks "View & Apply" on dashboard
2. Dashboard opens application URL in new tab WITH a URL parameter or message:
   ?corkboard_job_id=<job_id>
3. Content script activates on the page
4. Content script:
   a. Detects all form fields on the page
   b. Queries Supabase for field_mappings WHERE domain = current domain
   c. For each mapped field:
      - Get the user_profile value for maps_to
      - Fill the field using the CSS selector
      - Highlight the field in green (so user can see what was filled)
   d. For each UNMAPPED field:
      - Highlight in yellow
      - Log to unmapped_fields table in Supabase
      - Show count in extension popup: "3 fields need manual entry"
   e. For file upload fields (CV):
      - Cannot auto-fill file inputs for security reasons
      - Instead, show a prominent reminder: "📎 Don't forget to attach your CV!"
5. User reviews, fills any remaining fields, submits
6. Extension detects form submission → updates application status to "applied" in Supabase
```

### 4.4 Field Detection Engine

The mapping engine needs to be smart about identifying form fields:

```javascript
// For each <input>, <select>, <textarea> on the page:
function detectFields(formElement) {
  const fields = [];
  
  // Get all form elements
  const inputs = formElement.querySelectorAll('input, select, textarea');
  
  for (const input of inputs) {
    // Skip hidden, submit, button types
    if (['hidden', 'submit', 'button'].includes(input.type)) continue;
    
    const fieldInfo = {
      selector: generateUniqueSelector(input),  // CSS selector
      type: input.type || input.tagName.toLowerCase(),
      label: findLabel(input),        // Check <label>, aria-label, placeholder
      name: input.name,
      id: input.id,
      placeholder: input.placeholder,
      autocomplete: input.autocomplete,  // HTML autocomplete attribute is GOLD
      required: input.required,
    };
    
    fields.push(fieldInfo);
  }
  
  return fields;
}

// Smart matching: use autocomplete attribute, name, id, label text
function guessProfileField(fieldInfo) {
  // Priority 1: HTML autocomplete attribute (most reliable)
  const autocompleteMap = {
    'given-name': 'first_name',
    'family-name': 'last_name',
    'email': 'email',
    'tel': 'phone',
    'address-line1': 'address_line_1',
    'address-line2': 'address_line_2',
    'postal-code': 'postcode',
    'organization': 'current_job_title',
    'url': 'linkedin_url',
  };
  
  if (fieldInfo.autocomplete && autocompleteMap[fieldInfo.autocomplete]) {
    return autocompleteMap[fieldInfo.autocomplete];
  }
  
  // Priority 2: name/id attribute patterns
  const namePatterns = {
    /first.?name|fname|given/i: 'first_name',
    /last.?name|lname|surname|family/i: 'last_name',
    /email/i: 'email',
    /phone|tel|mobile/i: 'phone',
    /address.?1|street|address_line/i: 'address_line_1',
    /address.?2|apt|suite/i: 'address_line_2',
    /city|town/i: 'city',
    /post.?code|zip/i: 'postcode',
    /linkedin/i: 'linkedin_url',
    /salary|compensation/i: 'expected_salary',
    /notice/i: 'notice_period',
    /right.?to.?work|visa|eligib/i: 'right_to_work',
    /experience|years/i: 'years_experience',
    /cover.?letter/i: 'cover_letter_template',
  };
  
  const textToCheck = `${fieldInfo.name} ${fieldInfo.id} ${fieldInfo.label} ${fieldInfo.placeholder}`;
  
  for (const [pattern, profileField] of Object.entries(namePatterns)) {
    if (pattern.test(textToCheck)) return profileField;
  }
  
  return null;  // Unmapped — flag for review
}
```

### 4.5 Building the Mapping Database Over Time

This is the key insight — the mapping DB improves with usage:

```
Phase 1 (Initial Build):
  - Pre-populate mappings for the top 5-10 ATS platforms:
    - Workday, Greenhouse, Lever, BambooHR, Applied (common in UK)
    - Indeed Easy Apply
    - Reed Quick Apply
    - Caterer.com Apply
  - Use the smart guessing engine (4.4) to auto-map fields on first visit
  - Any auto-mapped field starts as is_verified = false

Phase 2 (Learning):
  - When user successfully submits a form without correcting auto-filled fields
    → Mark those mappings as is_verified = true, increment times_used
  - When user manually corrects an auto-filled field
    → Flag the mapping for review, log the correction
  - When user fills an unmapped field manually
    → Prompt: "This looks like [first_name]. Save this mapping?" 
    → Store new mapping

Phase 3 (Periodic Expansion):
  - Weekly: developer (you) reviews unmapped_fields table
  - Batch-add mappings for new domains that appear frequently
  - Run a "discovery scrape" on new ATS domains:
    1. Visit the careers page
    2. Start an application (don't submit)
    3. Map all form fields
    4. Store mappings
  - Over time, coverage grows organically

Phase 4 (Maintenance):
  - When scraper finds jobs on a new domain with 5+ listings
    → Auto-flag domain for mapping in unmapped_fields
  - Monthly: re-verify top 20 domain mappings still work
    (sites update their forms occasionally)
```

### 4.6 Extension Popup UI

Simple popup when clicking the extension icon:

```
┌───────────────────────────┐
│  CorkBoard Auto-Fill      │
│                           │
│  Status: ✅ Connected     │
│  Profile: Complete ✓      │
│                           │
│  This page:               │
│  ✅ 8 fields auto-filled  │
│  ⚠️  2 fields unmapped    │
│  📎 CV upload required    │
│                           │
│  [Open Dashboard]         │
│  [Edit Profile]           │
└───────────────────────────┘
```

---

## 5. Notification System

Keep it simple — email digest or Telegram bot:

### Option A: Email (Simpler)
- Daily email at 8am with new jobs found in last 24 hours
- Use Resend or Supabase Edge Functions + Resend
- Clean HTML email with job cards

### Option B: Telegram Bot (Recommended)
- Instant notifications when new jobs are scraped
- User can reply with "save" or "apply" to update status
- Daily summary at 8am
- python-telegram-bot library on the DO droplet

Pick one. Telegram is better for immediacy but email is more "normal" for a non-tech user.

---

## 6. Environment Variables

### Scraper (.env on DO Droplet)
```
SUPABASE_URL=
SUPABASE_SERVICE_KEY=         # Service role key for full DB access
TELEGRAM_BOT_TOKEN=           # If using Telegram
TELEGRAM_CHAT_ID=             # If using Telegram
RESEND_API_KEY=               # If using email
NOTIFICATION_EMAIL=           # Recipient email
```

### Frontend (.env.local on Vercel)
```
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
```

### Chrome Extension (stored in extension storage, set via popup)
```
SUPABASE_URL
SUPABASE_ANON_KEY
```

---

## 7. Implementation Order

Build in this sequence:

### Sprint 1: Core Scraper + DB (Week 1)
1. Set up Supabase project and run all SQL migrations
2. Build Indeed scraper (highest volume, most straightforward)
3. Build Reed scraper
4. Build Caterer.com scraper (needs Playwright)
5. Implement deduplication logic
6. Implement link verification
7. Set up cron jobs on DO droplet
8. Test: confirm jobs are flowing into Supabase correctly

### Sprint 2: Frontend (Week 2)
1. Scaffold Next.js project
2. Build job feed page with infinite scroll + LinkedIn-style animations
3. Build filters and sort
4. Build job detail page
5. Build application status tracking (tick off applied/saved)
6. Build profile page
7. Build applications tracker page
8. Deploy to Vercel

### Sprint 3: Chrome Extension MVP (Week 3)
1. Build extension skeleton (Manifest V3)
2. Implement field detection engine
3. Pre-populate mappings for Indeed, Reed, Caterer, Workday, Greenhouse
4. Build auto-fill logic
5. Build unmapped field flagging
6. Build extension popup
7. Test on live job applications

### Sprint 4: Polish + Expand (Week 4)
1. Add remaining scraper sources (Totaljobs, LinkedIn, wine-specific sites)
2. Implement notification system (email or Telegram)
3. Add more field mappings from unmapped_fields review
4. Mobile responsive polish
5. Error handling and edge cases
6. Dark mode (optional)

---

## 8. Scraper Implementation Notes

### Rate Limiting & Politeness
- 2-3 second delay between requests to same domain
- Rotate User-Agent strings (maintain a list of 10+ recent browser UAs)
- Respect robots.txt where it exists (Indeed has one, honour it)
- If rate limited (429), back off exponentially
- Don't scrape more than 5 pages deep per query per source

### Anti-Detection
- Use `httpx` with custom headers (Accept, Accept-Language, Accept-Encoding)
- For Playwright pages: use `playwright-stealth` or equivalent
- Don't run all sources simultaneously — stagger by 5-10 minutes

### Error Handling
- Each source scraper should be independent — if Indeed fails, Reed still runs
- Log all errors to scrape_logs table
- If a source fails 3 consecutive runs, send alert notification
- Never crash the main process — catch everything

### Salary Parsing
```python
# Handle common UK salary formats:
# "£35,000 - £42,000"
# "£35k - £42k"  
# "£35,000 - £42,000 per annum"
# "£18 - £22 per hour" → convert to annual (×2080)
# "Up to £50,000"
# "£40,000 + bonus"
# "Competitive" → null
```

---

## 9. Future Enhancements (Post-MVP)

- **AI cover letter generation** — use Claude API to generate tailored cover letters per job using the job description + user profile
- **Job match scoring** — rate how well each job matches user preferences (salary range, commute distance, keywords)
- **Application deadline tracking** — some listings have close dates, surface these
- **Interview prep** — when status moves to "interviewing", pull common interview questions for that company/role
- **Analytics dashboard** — application funnel (scraped → saved → applied → interviewing → offered), response rates per source
- **Multi-user support** — if other friends want to use it, add Supabase Auth and per-user isolation

---

## 10. File Structure

```
job-scraper/
├── scraper/                     # Python — runs on DO droplet
│   ├── main.py                  # Entry point
│   ├── config.py                # Settings, env vars
│   ├── sources/
│   │   ├── base.py              # Abstract scraper class
│   │   ├── indeed.py
│   │   ├── reed.py
│   │   ├── caterer.py
│   │   ├── totaljobs.py
│   │   ├── linkedin.py
│   │   ├── wine_searcher.py
│   │   └── harpers.py
│   ├── processors/
│   │   ├── deduplicator.py
│   │   ├── salary_parser.py
│   │   ├── location_filter.py
│   │   └── link_verifier.py
│   ├── db/
│   │   └── supabase_client.py
│   ├── notifications/
│   │   ├── email.py
│   │   └── telegram.py
│   ├── requirements.txt
│   ├── Dockerfile               # Optional containerisation
│   └── cron/
│       ├── scrape.sh
│       ├── verify.sh
│       └── archive.sh
│
├── frontend/                    # Next.js — deploys to Vercel
│   ├── app/
│   │   ├── page.tsx             # Job feed
│   │   ├── job/[id]/page.tsx    # Job detail
│   │   ├── applications/page.tsx
│   │   ├── profile/page.tsx
│   │   └── mappings/page.tsx
│   ├── components/
│   │   ├── JobCard.tsx
│   │   ├── JobFeed.tsx
│   │   ├── FilterBar.tsx
│   │   ├── StatusSelector.tsx
│   │   ├── ApplicationTracker.tsx
│   │   └── ProfileForm.tsx
│   ├── lib/
│   │   ├── supabase.ts
│   │   └── types.ts
│   ├── package.json
│   └── tailwind.config.ts
│
├── extension/                   # Chrome Extension — Manifest V3
│   ├── manifest.json
│   ├── background.js
│   ├── content.js
│   ├── popup.html
│   ├── popup.js
│   ├── mapping-engine.js
│   ├── supabase-client.js
│   └── icons/
│
└── supabase/
    └── migrations/
        └── 001_initial_schema.sql
```
