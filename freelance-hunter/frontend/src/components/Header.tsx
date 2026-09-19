'use client';

import { useState } from 'react';
import { Search, Filter, Download, FileText, Settings, RefreshCw, Play, Pause, Bell, Loader2, Zap, Clock, ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';

interface HeaderProps {
  onScan: () => void;
  onExport: (format: string) => void;
  onReport: () => void;
  onSettings: () => void;
  scanRunning: boolean;
  scanProgress: { progress: number; status: string; message: string } | null;
  schedulerStatus: { running: boolean; interval_hours: number } | null;
  onSchedulerControl: (action: 'start' | 'stop' | 'pause' | 'resume') => void;
}

export function Header({ 
  onScan, 
  onExport, 
  onReport, 
  onSettings, 
  scanRunning, 
  scanProgress,
  schedulerStatus,
  onSchedulerControl 
}: HeaderProps) {
  const [showSchedulerMenu, setShowSchedulerMenu] = useState(false);

  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 h-16">
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold text-gray-900">🎯 Freelance Hunter</h1>
            <span className="px-2 py-0.5 text-xs font-medium bg-primary-100 text-primary-800 rounded-full">
              Dashboard
            </span>
          </div>
          
          <div className="flex flex-wrap items-center gap-2">
            {/* Scheduler Control */}
            <div className="relative">
              <button
                onClick={() => setShowSchedulerMenu(!showSchedulerMenu)}
                className={cn(
                  'btn flex items-center gap-2',
                  schedulerStatus?.running ? 'btn-success' : 'btn-secondary'
                )}
              >
                <Zap className="h-4 w-4" />
                <span className="hidden sm:inline">
                  {schedulerStatus?.running ? 'المجدول يعمل' : 'المجدول متوقف'}
                </span>
                <ChevronDown className="h-4 w-4" />
              </button>
              
              {showSchedulerMenu && (
                <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-50 animate-slide-down">
                  <button
                    onClick={() => { onSchedulerControl('start'); setShowSchedulerMenu(false); }}
                    className="w-full px-4 py-2 text-right text-sm hover:bg-gray-50 flex items-center gap-2"
                  >
                    <Play className="h-4 w-4 text-green-600" />
                    بدء المجدول (كل 6 ساعات)
                  </button>
                  <button
                    onClick={() => { onSchedulerControl('stop'); setShowSchedulerMenu(false); }}
                    className="w-full px-4 py-2 text-right text-sm hover:bg-gray-50 flex items-center gap-2"
                  >
                    <Pause className="h-4 w-4 text-red-600" />
                    إيقاف المجدول
                  </button>
                  <hr className="my-1 border-gray-100" />
                  <div className="px-4 py-2 text-xs text-gray-500 text-right">
                    الفترة: {schedulerStatus?.interval_hours || 6} ساعات
                  </div>
                </div>
              )}
            </div>

            <button
              onClick={onScan}
              disabled={scanRunning}
              className={cn(
                'btn btn-primary flex items-center gap-2',
                scanRunning && 'opacity-50 cursor-not-allowed'
              )}
            >
              {scanRunning ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  جاري المسح...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4" />
                  مسح جديد
                </>
              )}
            </button>
            
            <div className="hidden sm:flex items-center gap-1 border border-gray-200 rounded-lg p-1">
              <button
                onClick={() => onExport('csv')}
                className="btn btn-secondary text-sm"
                title="تصدير CSV"
              >
                <Download className="h-4 w-4" />
              </button>
              <button
                onClick={() => onExport('xlsx')}
                className="btn btn-secondary text-sm"
                title="تصدير Excel"
              >
                <FileText className="h-4 w-4" />
              </button>
              <button
                onClick={onReport}
                className="btn btn-secondary text-sm"
                title="تقرير يومي"
              >
                <FileText className="h-4 w-4" />
              </button>
            </div>
            
            <button
              onClick={onSettings}
              className="btn btn-secondary p-2"
              title="الإعدادات"
            >
              <Settings className="h-5 w-5" />
            </button>
            
            <button
              onClick={() => window.location.reload()}
              className="btn btn-secondary p-2"
              title="تحديث"
            >
              <RefreshCw className="h-5 w-5" />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}