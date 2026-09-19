'use client';

import { Job, Pagination } from '@/types';
import { cn, getMatchLevelColor, getRiskLevelColor, getVerificationColor, formatDate, truncate } from '@/lib/utils';
import { ExternalLink, Copy, Eye, ChevronLeft, ChevronRight, Loader2 } from 'lucide-react';

interface JobsTableProps {
  jobs: Job[];
  pagination: Pagination;
  onPageChange: (page: number) => void;
  onSort: (field: string) => void;
  currentSort: { field: string; order: string };
  onViewJob: (job: Job) => void;
}

const columns = [
  { key: 'title', label: 'العنوان', sortable: true },
  { key: 'platform', label: 'المنصة', sortable: true },
  { key: 'time_since_posted', label: 'منذ', sortable: true },
  { key: 'budget', label: 'الميزانية', sortable: true },
  { key: 'match_level', label: 'المطابقة', sortable: true },
  { key: 'risk_level', label: 'المخاطر', sortable: true },
  { key: 'verification_status', label: 'التحقق', sortable: true },
  { key: 'actions', label: 'إجراءات', sortable: false },
];

export function JobsTable({ jobs, pagination, onPageChange, onSort, currentSort, onViewJob }: JobsTableProps) {
  const handleSort = (field: string) => {
    if (field !== 'actions') onSort(field);
  };

  if (jobs.length === 0) {
    return (
      <div className="card text-center py-12">
        <div className="text-gray-400 mb-2">📭</div>
        <p className="text-gray-500">لا توجد وظائف مطابقة للفلاتر الحالية</p>
        <p className="text-sm text-gray-400 mt-1">جرب تعديل الفلاتر أو قم بمسح جديد</p>
      </div>
    );
  }

  return (
    <div className="card overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              {columns.map((col) => (
                <th
                  key={col.key}
                  className={cn(
                    'px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider',
                    col.sortable && 'cursor-pointer hover:bg-gray-100 select-none'
                  )}
                  onClick={() => col.sortable && handleSort(col.key)}
                  style={{ width: col.key === 'title' ? '35%' : col.key === 'actions' ? '120px' : 'auto' }}
                >
                  <div className="flex items-center justify-end gap-1">
                    {col.label}
                    {col.sortable && currentSort.field === col.key && (
                      currentSort.order === 'desc' ? '⬇' : '⬆'
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {jobs.map((job) => (
              <tr
                key={job.job_id}
                className="hover:bg-gray-50 cursor-pointer transition-colors"
                onClick={() => onViewJob(job)}
              >
                <td className="px-4 py-3">
                  <div>
                    <p className="font-medium text-gray-900 line-clamp-1 max-w-xs" title={job.title}>
                      {job.title}
                    </p>
                    <p className="text-xs text-gray-500 truncate max-w-xs">{job.platform}</p>
                  </div>
                </td>
                <td className="px-4 py-3 text-sm text-gray-500">{job.platform}</td>
                <td className="px-4 py-3 text-sm text-gray-500">{job.time_since_posted}</td>
                <td className="px-4 py-3 text-sm font-medium text-gray-900">{job.budget}</td>
                <td className="px-4 py-3">
                  <span className={cn('badge', getMatchLevelColor(job.match_level))}>
                    {job.match_level.replace('_', ' ')}
                  </span>
                  {job.match_score && (
                    <p className="text-xs text-gray-500 mt-0.5">{job.match_score.toFixed(1)}%</p>
                  )}
                </td>
                <td className="px-4 py-3">
                  <span className={cn('badge', getRiskLevelColor(job.risk_level))}>
                    {job.risk_level}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className={cn('badge', getVerificationColor(job.verification_status))}>
                    {job.verification_status.replace('_', ' ')}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center justify-end gap-1">
                    <button
                      onClick={(e) => { e.stopPropagation(); onViewJob(job); }}
                      className="btn btn-secondary p-1.5"
                      title="عرض التفاصيل"
                    >
                      <Eye className="h-4 w-4" />
                    </button>
                    <button
                      onClick={(e) => { e.stopPropagation(); navigator.clipboard.writeText(job.proposal_short || ''); }}
                      className="btn btn-secondary p-1.5"
                      title="نسخ العرض المختصر"
                    >
                      <Copy className="h-4 w-4" />
                    </button>
                    <a
                      href={job.job_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      className="btn btn-secondary p-1.5"
                      title="فتح الوظيفة"
                    >
                      <ExternalLink className="h-4 w-4" />
                    </a>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {pagination.total_pages > 1 && (
        <div className="flex items-center justify-between mt-4 px-4">
          <div className="text-sm text-gray-500">
            صفحة {pagination.page} من {pagination.total_pages} — إجمالي {pagination.total} وظيفة
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => onPageChange(pagination.page - 1)}
              disabled={pagination.page <= 1}
              className="btn btn-secondary p-2 disabled:opacity-50"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
            <button
              onClick={() => onPageChange(pagination.page + 1)}
              disabled={pagination.page >= pagination.total_pages}
              className="btn btn-secondary p-2 disabled:opacity-50"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}