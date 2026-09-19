import axios from 'axios';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const jobsApi = {
  getAll: (filters: Record<string, any> = {}) => 
    api.post('/api/jobs', { ...filters, page: 1, per_page: 20 }),
  
  getRecent: (hours = 24, limit = 50) => 
    api.get('/api/jobs/recent', { params: { hours, limit } }),
  
  getById: (jobId: string) => 
    api.get(`/api/jobs/${jobId}`),
  
  updateStatus: (jobId: string, status: string, notes?: string) => 
    api.post(`/api/jobs/${jobId}/status`, { new_status: status, notes }),
};

export const statsApi = {
  getDashboard: () => api.get('/api/stats'),
  getDailyReport: () => api.get('/api/report/daily'),
};

export const platformsApi = {
  getAll: () => api.get('/api/platforms'),
};

export const scanApi = {
  start: (data: { priority: number; max_pages: number }) => 
    api.post('/api/scan', data),
  getLatestStatus: () => 
    api.get('/api/scan/status/latest'),
};

export const schedulerApi = {
  control: (data: { action: string; interval_hours?: number }) => 
    api.post('/api/scheduler/control', data),
  getStatus: () => 
    api.get('/api/scheduler/status'),
};

export const emailApi = {
  getSettings: () => 
    api.get('/api/email/settings'),
  updateSettings: (settings: {
    enabled: boolean;
    smtp_host: string;
    smtp_port: number;
    username: string;
    password: string;
    from_email: string;
    use_tls: boolean;
  }) => api.post('/api/email/settings', settings),
  getNotifications: () => 
    api.get('/api/email/notifications'),
  updateNotifications: (settings: {
    enabled: boolean;
    email: string;
    on_scan_complete: boolean;
    on_high_match: boolean;
    on_new_job: boolean;
  }) => api.post('/api/email/notifications', settings),
  sendTestEmail: (email?: string) => 
    api.post('/api/email/test', { email }),
};