# CorkBoard

Job scraping platform for hospitality management and wine roles in London. Aggregates listings from multiple UK job boards, filters for relevance, deduplicates across sources, and provides a LinkedIn-style feed with application tracking and auto-fill.

## Architecture

```
Scraper (DO droplet)  ──> Supabase (Postgres) <──  Frontend (Vercel)
     cron every 6h              shared DB              Next.js 15
                                    ^
                                    |
                            Chrome Extension
                           (auto-fill forms)
```

**Four independent components:**

| Component | Stack | Purpose |
|-----------|-------|---------|
| `scraper/` | Python 3.11, httpx, BeautifulSoup | Scrapes job boards, filters, deduplicates, inserts into DB |
| `frontend/` | Next.js 15, React 19, Tailwind, Zustand | Job feed with filters, application tracker, profile management |
| `extension/` | Chrome Manifest V3 | Auto-fills job application forms from your profile |
| `supabase/` | PostgreSQL, RLS | Schema migrations and row-level security policies |

## Job Sources

| Source | Method | Schedule |
|--------|--------|----------|
| Reed | Direct HTTP | 4x/day |
| LinkedIn | Direct HTTP | 4x/day |
| Adzuna | Direct HTTP | 4x/day |
| Indeed | ScraperAPI (render) | 1x/day |

Link verification runs 30 minutes after each scrape to mark expired listings as inactive.

## Scraper Pipeline

```
Fetch search results (HTTP or ScraperAPI per source)
  -> Filter to London only (postcode regex + keyword)
  -> Relevance filter (hospitality/wine title keywords, company blacklist)
  -> Skip if URL already in DB
  -> Parse salary to min/max pence
  -> Insert into Supabase
  -> Cross-source fuzzy deduplication (rapidfuzz, 85% title + 80% company)
```

## Setup

### Scraper

```bash
cd scraper
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Fill in Supabase credentials
```

```bash
python -m scraper.main scrape                # All sources
python -m scraper.main scrape --sources direct  # Free sources only
python -m scraper.main scrape --sources proxy   # ScraperAPI sources only
python -m scraper.main verify                # Check active job links
python -m scraper.main archive               # Archive old inactive jobs
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local  # Fill in Supabase anon key
npm run dev                  # http://localhost:3000
```

### Extension

Load `extension/` as an unpacked extension in `chrome://extensions`. Configure Supabase URL and anon key via the popup.

### Tests

```bash
pip install -r scraper/requirements.txt
pytest scraper/tests/ -v   # 150 tests
```

## Environment Variables

**Scraper** (`scraper/.env`):
- `SUPABASE_URL` — Supabase project URL
- `SUPABASE_SERVICE_KEY` — Service role key (bypasses RLS)
- `SCRAPER_API_KEY` — ScraperAPI key (unlocks Indeed; optional)
- `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` — Telegram notifications (optional)
- `RESEND_API_KEY` / `NOTIFICATION_EMAIL` — Email notifications (optional)

**Frontend** (`frontend/.env.local`):
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`

## Database

Six tables: `jobs`, `applications`, `user_profile`, `field_mappings`, `unmapped_fields`, `scrape_logs`. RLS enabled on all. See `supabase/migrations/` for schema.

## Deployment

- **Scraper**: DigitalOcean droplet, deployed via SCP, cron-scheduled
- **Frontend**: Vercel, auto-deploys from `main` branch
- **Extension**: Chrome Web Store or load unpacked for development

## Cron Schedule

```
0 */6 * * *   # Scrape Reed + LinkedIn + Adzuna (direct, free)
30 */6 * * *  # Verify all active job links
0 9 * * *     # Scrape Indeed via ScraperAPI (proxy)
```
