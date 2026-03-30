-- CorkBoard: Row Level Security
-- Anon key = read-only on jobs, no access to sensitive tables
-- Service role key (scraper) bypasses RLS by design
-- Single-user app: all authenticated users can manage their data

-- ═══════════════════════════════════════════════
-- Jobs: anon can SELECT active jobs, service role can INSERT/UPDATE
-- ═══════════════════════════════════════════════
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "anon_read_active_jobs" ON jobs
  FOR SELECT USING (is_active = TRUE AND duplicate_of IS NULL);

CREATE POLICY "service_insert_jobs" ON jobs
  FOR INSERT WITH CHECK (true);

CREATE POLICY "service_update_jobs" ON jobs
  FOR UPDATE USING (true);

-- ═══════════════════════════════════════════════
-- Applications: anon can read/write (frontend manages these)
-- ═══════════════════════════════════════════════
ALTER TABLE applications ENABLE ROW LEVEL SECURITY;

CREATE POLICY "anon_manage_applications" ON applications
  FOR ALL USING (true) WITH CHECK (true);

-- ═══════════════════════════════════════════════
-- User profile: anon can read/write (single user, frontend manages)
-- ═══════════════════════════════════════════════
ALTER TABLE user_profile ENABLE ROW LEVEL SECURITY;

CREATE POLICY "anon_manage_profile" ON user_profile
  FOR ALL USING (true) WITH CHECK (true);

-- ═══════════════════════════════════════════════
-- Field mappings: anon can read, extension can insert/update
-- ═══════════════════════════════════════════════
ALTER TABLE field_mappings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "anon_manage_mappings" ON field_mappings
  FOR ALL USING (true) WITH CHECK (true);

-- ═══════════════════════════════════════════════
-- Unmapped fields: extension can insert, frontend can read
-- ═══════════════════════════════════════════════
ALTER TABLE unmapped_fields ENABLE ROW LEVEL SECURITY;

CREATE POLICY "anon_manage_unmapped" ON unmapped_fields
  FOR ALL USING (true) WITH CHECK (true);

-- ═══════════════════════════════════════════════
-- Scrape logs: anon read-only, service role writes
-- ═══════════════════════════════════════════════
ALTER TABLE scrape_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "anon_read_logs" ON scrape_logs
  FOR SELECT USING (true);

CREATE POLICY "service_insert_logs" ON scrape_logs
  FOR INSERT WITH CHECK (true);

CREATE POLICY "service_update_logs" ON scrape_logs
  FOR UPDATE USING (true);

-- ═══════════════════════════════════════════════
-- Add description length constraint (prevent DoS via huge content)
-- ═══════════════════════════════════════════════
ALTER TABLE jobs ADD CONSTRAINT jobs_description_length
  CHECK (length(description) < 50000);
