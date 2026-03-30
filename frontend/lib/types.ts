export type JobCategory = "hospitality" | "wine";

export type ApplicationStatus =
  | "new"
  | "saved"
  | "applied"
  | "interviewing"
  | "rejected"
  | "offer";

export type ApplicationType =
  | "easy_apply"
  | "external"
  | "email"
  | "ats_known"
  | "unknown";

export interface Job {
  id: string;
  source: string;
  source_url: string;
  title: string;
  company: string;
  location: string;
  salary_text: string | null;
  salary_min: number | null;
  salary_max: number | null;
  description: string | null;
  posted_date: string | null;
  scraped_at: string;
  category: JobCategory;
  application_url: string | null;
  application_type: ApplicationType;
  application_domain: string | null;
  is_active: boolean;
  last_verified: string;
  duplicate_of: string | null;
  created_at: string;
}

export interface Application {
  id: string;
  job_id: string;
  status: ApplicationStatus;
  notes: string | null;
  applied_at: string | null;
  updated_at: string;
  created_at: string;
  job?: Job;
}

export interface UserProfile {
  id: string;
  first_name: string | null;
  last_name: string | null;
  email: string | null;
  phone: string | null;
  address_line_1: string | null;
  address_line_2: string | null;
  city: string | null;
  postcode: string | null;
  country: string | null;
  linkedin_url: string | null;
  portfolio_url: string | null;
  current_job_title: string | null;
  years_experience: number | null;
  right_to_work: string | null;
  notice_period: string | null;
  expected_salary: string | null;
  cv_url: string | null;
  cover_letter_template: string | null;
  additional_fields: Record<string, string>;
  updated_at: string;
}

export interface FieldMapping {
  id: string;
  domain: string;
  page_url_pattern: string | null;
  field_selector: string;
  field_type: string;
  field_label: string | null;
  maps_to: string;
  select_value_map: Record<string, string> | null;
  is_verified: boolean;
  last_used: string | null;
  times_used: number;
  created_at: string;
  updated_at: string;
}

export interface ScrapeLog {
  id: string;
  source: string;
  started_at: string;
  completed_at: string | null;
  jobs_found: number;
  jobs_new: number;
  jobs_duplicate: number;
  jobs_verified: number;
  jobs_expired: number;
  errors: string[];
  status: "running" | "completed" | "failed";
}

// Supabase generated types interface
export interface Database {
  public: {
    Tables: {
      jobs: { Row: Job; Insert: Partial<Job>; Update: Partial<Job> };
      applications: {
        Row: Application;
        Insert: Partial<Application>;
        Update: Partial<Application>;
      };
      user_profile: {
        Row: UserProfile;
        Insert: Partial<UserProfile>;
        Update: Partial<UserProfile>;
      };
      field_mappings: {
        Row: FieldMapping;
        Insert: Partial<FieldMapping>;
        Update: Partial<FieldMapping>;
      };
      scrape_logs: {
        Row: ScrapeLog;
        Insert: Partial<ScrapeLog>;
        Update: Partial<ScrapeLog>;
      };
    };
    Views: Record<string, never>;
    Functions: Record<string, never>;
    Enums: Record<string, never>;
  };
}

// Filter state for the job feed
export interface JobFilters {
  category: JobCategory | "all";
  salaryMin: number | null;
  datePosted: "any" | "24h" | "7d" | "30d";
  source: string | "all";
  status: ApplicationStatus | "all";
  sortBy: "recent" | "salary_high" | "salary_low";
  search: string;
}
