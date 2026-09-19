'use client';

import { useEffect, useRef } from 'react';
import { X, Loader2, CheckCircle2, AlertCircle, AlertTriangle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ScanProgressProps {
  progress: { progress: number; status: string; message: string };
  onCancel: () => void;
}

export function ScanProgress({ progress, onCancel }: ScanProgressProps) {
  const progressRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (progressRef.current) {
      progressRef.current.style.width = `${progress.progress}%`;
    }
  }, [progress.progress]);

  const getStatusIcon = () => {
    switch (progress.status) {
      case 'completed':
        return <CheckCircle2 className="h-5 w-5 text-green-500" />;
      case 'failed':
        return <AlertCircle className="h-5 w-5 text-red-500" />;
      case 'running':
        return <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />;
      default:
        return <AlertTriangle className="h-5 w-5 text-yellow-500" />;
    }
  };

  const getStatusColor = () => {
    switch (progress.status) {
      case 'completed':
        return 'bg-green-500';
      case 'failed':
        return 'bg-red-500';
      case 'running':
        return 'bg-blue-500';
      default:
        return 'bg-yellow-500';
    }
  };

  return (
    <div className="fixed top-0 left-0 right-0 z-50 bg-white border-b border-gray-200 shadow-lg animate-slide-down">
      <div className="max-w-7xl mx-auto px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={cn('p-2 rounded-lg', progress.status === 'completed' && 'bg-green-100', progress.status === 'failed' && 'bg-red-100', progress.status === 'running' && 'bg-blue-100')}>
              {getStatusIcon()}
            </div>
            <div>
              <p className="font-medium text-gray-900">
                {progress.status === 'running' && 'جاري المسح...'}
                {progress.status === 'completed' && 'اكتمل المسح بنجاح!'}
                {progress.status === 'failed' && 'فشل المسح'}
                {progress.status === 'partial' && 'اكتمل المسح جزئياً'}
              </p>
              <p className="text-sm text-gray-500">{progress.message}</p>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="hidden sm:block w-48">
              <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                <div
                  ref={progressRef}
                  className={cn('h-full transition-all duration-500 ease-out', getStatusColor())}
                  style={{ width: '0%' }}
                />
              </div>
            </div>
            <span className="text-sm font-medium text-gray-600 w-12 text-right">
              {Math.round(progress.progress)}%
            </span>
            <button
              onClick={onCancel}
              className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
              title="إيقاف التحديث التلقائي"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}