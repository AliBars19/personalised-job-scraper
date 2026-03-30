-- CorkBoard: Initial Schema
-- Jobs, applications, user profile, field mappings, scrape logs

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
  cv_url TEXT,
  cover_letter_template TEXT,
  additional_fields JSONB DEFAULT '{}'::jsonb,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Form field mappings for auto-fill
CREATE TABLE field_mappings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  domain TEXT NOT NULL,
  page_url_pattern TEXT,
  field_selector TEXT NOT NULL,
  field_type TEXT NOT NULL,
  field_label TEXT,
  maps_to TEXT NOT NULL,
  select_value_map JSONB,
  is_verified BOOLEAN DEFAULT FALSE,
  last_used TIMESTAMPTZ,
  times_used INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(domain, field_selector)
);

-- Unmapped fields flagged for manual review
CREATE TABLE unmapped_fields (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  domain TEXT NOT NULL,
  page_url TEXT NOT NULL,
  field_selector TEXT NOT NULL,
  field_type TEXT NOT NULL,
  field_label TEXT,
  field_name TEXT,
  field_placeholder TEXT,
  screenshot_url TEXT,
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
