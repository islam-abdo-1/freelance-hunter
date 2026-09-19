'use client';

import { useState, useEffect, useCallback } from 'react';
import { JobsTable } from './JobsTable';
import { StatsCards } from './StatsCards';
import { FiltersBar } from './FiltersBar';
import { JobModal } from './JobModal';
import { SettingsPanel } from './SettingsPanel';
import { Header } from './Header';
import { ScanProgress } from './ScanProgress';
import { ToastContainer, Toast } from './Toast';
import { Job, DashboardStats, JobFilters, Platform, SchedulerStatus } from '@/types';
import { api, jobsApi, statsApi, platformsApi, scanApi, schedulerApi, emailApi } from '@/lib/api';
import { formatDate } from '@/lib/utils';
import { Loader2, Play, Pause, Bell, CheckCircle2, AlertCircle, Info } from 'lucide-react';

export function Dashboard() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [platforms, setPlatforms] = useState<Platform[]>([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState<JobFilters>({
    page: 1,
    per_page: 20,
    sort_by: 'score',
    sort_order: 'desc',
  });
  const [pagination, setPagination] = useState({ page: 1, total_pages: 1, total: 0 });
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const [scanRunning, setScanRunning] = useState(false);
  const [scanProgress, setScanProgress] = useState<{progress: number; status: string; message: string} | null>(null);
  const [schedulerStatus, setSchedulerStatus] = useState<SchedulerStatus | null>(null);
  const [toasts, setToasts] = useState<Array<{id: number; type: 'success' | 'error' | 'info'; message: string}>>([]);
  const [scanPollingInterval, setScanPollingInterval] = useState<NodeJS.Timeout | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [jobsRes, statsRes, platformsRes] = await Promise.all([
        jobsApi.getAll(filters),
        statsApi.getDashboard(),
        platformsApi.getAll(),
      ]);
      setJobs(jobsRes.data.jobs);
      setPagination({
        page: jobsRes.data.page,
        total_pages: jobsRes.data.total_pages,
        total: jobsRes.data.total,
      });
      setStats(statsRes.data);
      setPlatforms(platformsRes.data.platforms);
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setLoading(false);
    }
  }, [filters.page, filters.sort_by, filters.sort_order]);

  useEffect(() => {
    fetchData();
    loadSchedulerStatus();
  }, [filters.page, filters.sort_by, filters.sort_order]);

  const loadSchedulerStatus = async () => {
    try {
      const res = await schedulerApi.getStatus();
      setSchedulerStatus(res.data);
    } catch (error) {
      console.error('Failed to load scheduler status:', error);
    }
  };

  const showToast = (type: 'success' | 'error' | 'info', message: string) => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, type, message }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 5000);
  };

  const handleFilterChange = (newFilters: Partial<JobFilters>) => {
    setFilters(prev => ({ ...prev, ...newFilters, page: 1 }));
  };

  const handlePageChange = (page: number) => {
    setFilters(prev => ({ ...prev, page }));
  };

  const handleSort = (sort_by: string) => {
    setFilters(prev => ({
      ...prev,
      sort_by,
      sort_order: prev.sort_by === sort_by && prev.sort_order === 'desc' ? 'asc' : 'desc',
    }));
  };

  const startScanPolling = () => {
    if (scanPollingInterval) return;
    
    const interval = setInterval(async () => {
      try {
        const res = await scanApi.getLatestStatus();
        const data = res.data;
        setScanProgress({
          progress: data.progress,
          status: data.status,
          message: data.message
        });
        
        if (data.status === 'completed' || data.status === 'failed') {
          stopScanPolling();
          setScanRunning(false);
          
          if (data.status === 'completed') {
            showToast('success', `اكتمل المسح! ${data.relevant_jobs} فرص ملائمة، ${data.high_match_jobs} مطابقة عالية`);
            fetchData(); // Refresh data
          } else {
            showToast('error', `فشل المسح: ${data.errors?.join(', ') || 'خطأ غير معروف'}`);
          }
        }
      } catch (error) {
        console.error('Polling error:', error);
        stopScanPolling();
      }
    }, 3000); // Poll every 3 seconds
    
    setScanPollingInterval(interval);
  };

  const stopScanPolling = () => {
    if (scanPollingInterval) {
      clearInterval(scanPollingInterval);
      setScanPollingInterval(null);
    }
  };

  const handleScan = async () => {
    setScanRunning(true);
    setScanProgress({ progress: 0, status: 'running', message: 'بدء المسح...' });
    try {
      await scanApi.start({ priority: filters.priority || 1, max_pages: filters.max_pages || 5 });
      showToast('info', 'بدأ المسح في الخلفية...');
      startScanPolling();
    } catch (error) {
      console.error('Scan failed:', error);
      showToast('error', 'فشل بدء المسح');
      setScanRunning(false);
    }
  };

  const handleExport = async (format: string) => {
    try {
      const res = await api.post('/api/export', { format, filters }, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `freelance_jobs_${new Date().toISOString().split('T')[0]}.${format}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      showToast('success', `تم التصدير بصيغة ${format.toUpperCase()}`);
    } catch (error) {
      console.error('Export failed:', error);
      showToast('error', 'فشل التصدير');
    }
  };

  const handleReport = async () => {
    try {
      const res = await statsApi.getDailyReport();
      const win = window.open('', '_blank');
      if (win) {
        win.document.write(`<pre style="font-family: monospace; padding: 20px;">${res.data.report}</pre>`);
      }
      showToast('success', 'تم إنشاء التقرير اليومي');
    } catch (error) {
      console.error('Report failed:', error);
      showToast('error', 'فشل إنشاء التقرير');
    }
  };

  const handleSchedulerControl = async (action: 'start' | 'stop' | 'pause' | 'resume') => {
    try {
      const res = await schedulerApi.control({ action, interval_hours: 6 });
      showToast('success', res.data.message);
      loadSchedulerStatus();
    } catch (error) {
      console.error('Scheduler control error:', error);
      showToast('error', 'فشل التحكم في المجدول');
    }
  };

  const handleTestEmail = async () => {
    try {
      const res = await emailApi.sendTestEmail({});
      showToast('success', res.data.message);
    } catch (error: any) {
      console.error('Test email error:', error);
      showToast('error', error.response?.data?.detail || 'فشل إرسال البريد الاختباري');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-4 border-primary-600 border-t-transparent"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <ToastContainer toasts={toasts} />
      
      <Header 
        onScan={handleScan}
        onExport={handleExport}
        onReport={handleReport}
        onSettings={() => setShowSettings(true)}
        scanRunning={scanRunning}
        scanProgress={scanProgress}
        schedulerStatus={schedulerStatus}
        onSchedulerControl={handleSchedulerControl}
      />
      
      {scanProgress && (
        <ScanProgress progress={scanProgress} onCancel={stopScanPolling} />
      )}
      
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <StatsCards stats={stats} />
        
        <FiltersBar
          filters={filters}
          platforms={platforms}
          onChange={handleFilterChange}
          onSort={handleSort}
        />
        
        <JobsTable
          jobs={jobs}
          pagination={pagination}
          onPageChange={handlePageChange}
          onSort={handleSort}
          currentSort={{ field: filters.sort_by, order: filters.sort_order }}
          onViewJob={setSelectedJob}
        />
      </main>

      {selectedJob && (
        <JobModal
          job={selectedJob}
          onClose={() => setSelectedJob(null)}
        />
      )}

      {showSettings && (
        <SettingsPanel
          onClose={() => setShowSettings(false)}
          onSave={fetchData}
          onTestEmail={handleTestEmail}
        />
      )}
    </div>
  );
}