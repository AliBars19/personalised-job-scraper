# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CorkBoard is a job scraping platform for hospitality/wine roles in London. It has four independent components that communicate through a shared Supabase (Postgres) database:

- **scraper/** — Python async CLI that scrapes 9 UK job boards, runs on a DigitalOcean droplet via cron
- **frontend/** — Next.js 15 + React 19 app with LinkedIn-style infinite-scroll job feed, deployed to Vercel
- **extension/** — Chrome Manifest V3 extension that auto-fills job application forms
- **supabase/migrations/** — Database schema and RLS policies

## Commands

### Scraper (Python 3.11+)
```bash
python -m scraper.main scrape       # Fetch new jobs from all sources
python -m scraper.main verify       # Verify active job links are still live
python -m scraper.main archive      # Archive jobs inactive 14+ days
pytest scraper/tests/ -v            # Run unit tests (39 tests)
pytest scraper/tests/test_salary_parser.py  # Run single test file
```

### Frontend (Next.js)
```bash
cd frontend
npm install
npm run dev                          # Dev server at http://localhost:3000
npm run build                        # Production build (also runs type checking)
npm run lint                         # ESLint
```

### Extension (Chrome)
No build step. Load `extension/` as unpacked extension in `chrome://extensions`.

## Architecture

### Data Flow
```
Scraper (service key) → inserts into jobs table
Frontend (anon key)   → reads active jobs, manages applications/profile
Extension (anon key)  → reads profile + field_mappings, auto-fills forms, logs unmapped fields
```

### Scraper Pipeline
Each source inherits from `BaseScraper` (sources/base.py) and implements `fetch_listings()`. Indeed and Caterer override `run()` to use a shared Playwright browser. The pipeline:
1. Fetch search results (HTTP or Playwright per source)
2. Filter to London only (processors/location_filter.py)
3. Parse salary strings to min/max pence (processors/salary_parser.py)
4. Skip if URL already in DB
5. Insert into Supabase
6. Cross-source fuzzy deduplication (processors/deduplicator.py — rapidfuzz, 85% title + 80% company threshold)

### Frontend State
Zustand store (`lib/store.ts`) holds filters, seen job IDs, and application status cache. All persistent data goes to Supabase. The job feed uses `react-intersection-observer` for infinite scroll with Framer Motion card animations.

### Extension Field Detection
`mapping-engine.js` detects form fields and maps them to user profile data using (in priority order): HTML autocomplete attributes, name/id regex patterns, label/placeholder text. Filled fields highlight green, unmapped fields highlight yellow and get logged to the `unmapped_fields` table.

## Database

Six tables: `jobs`, `applications`, `user_profile`, `field_mappings`, `unmapped_fields`, `scrape_logs`. RLS is enabled on all tables. The scraper uses the service role key (bypasses RLS); frontend and extension use the anon key.

Supabase project ID: `jiciexeymynkasvdhmqf` (region: eu-west-2).

## Environment Variables

**Scraper** (`scraper/.env`): `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, optional `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` or `RESEND_API_KEY`/`NOTIFICATION_EMAIL`.

**Frontend** (`frontend/.env.local`): `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`. Both validated at runtime with clear error messages on missing values.

**Extension**: Credentials configured via popup UI, stored in `chrome.storage.local`.

## Key Patterns

- Python config uses `dataclass(frozen=True)` with `field(default_factory=...)` for deferred env var reads
- All URLs stored in DB are validated to http/https scheme only (SSRF/XSS protection)
- All frontend job link hrefs pass through `safeUrl()` (`lib/url.ts`) to block javascript: URIs
- Extension validates `corkboard_job_id` URL parameter as UUID v4 before any DB write
- Link verifier has SSRF protection blocking private IPs, loopback, and cloud metadata endpoints
- Frontend search input escapes PostgREST ilike wildcards before query interpolation
- StatusSelector uses optimistic updates with rollback on DB write failure

## Deployment

- **Scraper**: Deployed to DO droplet at `/opt/corkboard/`, cron runs every 6h (scrape) and daily at 3am (verify)
- **Frontend**: Vercel (auto-deploy from main branch)
- **Extension**: Load unpacked for development; Chrome Web Store for distribution
