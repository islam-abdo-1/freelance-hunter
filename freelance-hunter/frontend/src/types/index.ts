export interface Job {
  id: number;
  job_id: string;
  platform: string;
  title: string;
  short_summary: string;
  category: string;
  sub_category: string;
  matched_skills: string[];
  date_posted: string | null;
  time_since_posted: string;
  budget: string;
  budget_min: number | null;
  budget_max: number | null;
  currency: string;
  fixed_price_or_hourly: string;
  experience_level: string;
  required_skills: string[];
  proposals_count: number | null;
  hires_count: number | null;
  client_name: string;
  client_country: string;
  client_rating: number | null;
  client_review_count: number | null;
  client_hire_history: number | null;
  client_total_spent: number | null;
  client_payment_status: string;
  verification_status: string;
  match_level: string;
  match_score: number;
  score_breakdown: Record<string, number>;
  match_reason: string;
  risk_level: string;
  risk_reasons: string[];
  proposal_short: string;
  proposal_normal: string;
  proposal_ultra_short: string;
  status: string;
  job_url: string;
  discovered_at: string | null;
}

export interface DashboardStats {
  total_jobs: number;
  verified_jobs: number;
  new_today: number;
  high_match_jobs: number;
  high_risk_jobs: number;
  platform_breakdown: Record<string, number>;
}

export interface JobsResponse {
  jobs: Job[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface Platform {
  id: number;
  name: string;
  url: string;
  jobs_url: string;
  search_url: string;
  category: string;
  country_region: string;
  login_required: boolean;
  public_access: boolean;
  is_active: boolean;
  last_scanned_at: string | null;
  scan_count: number;
  jobs_found: number;
  verified_jobs: number;
}

export interface UserProfile {
  skills: string[];
  experience_level: string;
  languages: string[];
  location: string;
  availability: string;
  strengths: string[];
  portfolio_urls: string[];
  bio: string;
  hourly_rate_range: {
    min: number;
    max: number;
    currency: string;
  };
  preferred_job_types: string[];
  max_hours_per_week: number;
  email_notifications?: {
    enabled: boolean;
    email: string;
    on_scan_complete: boolean;
    on_high_match: boolean;
    on_new_job: boolean;
  };
}

export interface JobFilters {
  platform_id?: number;
  category?: string;
  match_level?: string;
  verification_status?: string;
  risk_level?: string;
  status?: string;
  min_score?: number;
  max_score?: number;
  date_from?: string;
  date_to?: string;
  min_budget?: number;
  max_budget?: number;
  currency?: string;
  experience_level?: string;
  keyword?: string;
  sort_by?: string;
  sort_order?: string;
  page?: number;
  per_page?: number;
}

export interface SchedulerStatus {
  running: boolean;
  interval_hours: number;
  next_run: string | null;
  jobs_count: number;
}

export interface ScanStatus {
  run_id: string;
  status: string;
  progress: number;
  started_at: string | null;
  completed_at: string | null;
  platforms_scanned: number;
  raw_jobs_found: number;
  verified_jobs: number;
  relevant_jobs: number;
  high_match_jobs: number;
  duration_seconds: number;
  errors: string[];
  message: string;
}

export interface EmailConfig {
  enabled: boolean;
  smtp_host: string;
  smtp_port: number;
  username: string;
  password: string;
  from_email: string;
  use_tls: boolean;
}

export interface NotificationSettings {
  enabled: boolean;
  email: string;
  on_scan_complete: boolean;
  on_high_match: boolean;
  on_new_job: boolean;
}

export interface Pagination {
  page: number;
  total_pages: number;
  total: number;
}