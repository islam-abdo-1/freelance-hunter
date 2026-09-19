'use client';

import { Job } from '@/types';
import { cn, getMatchLevelColor, getRiskLevelColor, getVerificationColor, formatDate, truncate } from '@/lib/utils';
import { X, Copy, CheckCircle2, AlertTriangle, Star, User, MapPin, Clock, DollarSign, Link2, ExternalLink, Loader2 } from 'lucide-react';

interface JobModalProps {
  job: Job;
  onClose: () => void;
}

export function JobModal({ job, onClose }: JobModalProps) {
  const copyProposal = async (text: string, label: string) => {
    try {
      await navigator.clipboard.writeText(text);
      alert(`تم نسخ ${label}!`);
    } catch {
      alert('فشل النسخ');
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <div className="bg-white rounded-xl shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-start justify-between p-4 border-b border-gray-100 sticky top-0 bg-white">
          <div>
            <h2 className="text-lg font-bold text-gray-900 line-clamp-2">{job.title}</h2>
            <div className="flex flex-wrap items-center gap-2 mt-1">
              <span className={cn('badge', getMatchLevelColor(job.match_level))}>
                {job.match_level.replace('_', ' ')}
              </span>
              <span className={cn('badge', getRiskLevelColor(job.risk_level))}>
                {job.risk_level}
              </span>
              <span className={cn('badge', getVerificationColor(job.verification_status))}>
                {job.verification_status.replace('_', ' ')}
              </span>
            </div>
          </div>
          <button onClick={onClose} className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-6">
          {/* Quick Info Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-gray-50 rounded-lg p-3">
              <p className="text-xs text-gray-500">المنصة</p>
              <p className="font-medium text-gray-900">{job.platform}</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-3">
              <p className="text-xs text-gray-500">النشر</p>
              <p className="font-medium text-gray-900">{job.time_since_posted}</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-3">
              <p className="text-xs text-gray-500">الميزانية</p>
              <p className="font-medium text-gray-900">{job.budget}</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-3">
              <p className="text-xs text-gray-500">النوع</p>
              <p className="font-medium text-gray-900 capitalize">{job.fixed_price_or_hourly}</p>
            </div>
          </div>

          {/* Match Analysis */}
          <div className="border-t border-b border-gray-100 py-4">
            <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5 text-green-600" />
              تحليل المطابقة
            </h3>
            <div className="prose max-w-none text-gray-700">
              <p className="mb-2"><strong>الدرجة:</strong> {job.match_score?.toFixed(1) || 'N/A'}/100</p>
              <p className="mb-2"><strong>السبب:</strong> {job.match_reason}</p>
              <p className="mb-2"><strong>المهارات المطابقة:</strong> {job.matched_skills?.join(', ') || 'لا توجد'}</p>
              <p className="mb-2"><strong>المهارات المطلوبة:</strong> {job.required_skills?.join(', ') || 'غير محددة'}</p>
            </div>
          </div>

          {/* Score Breakdown */}
          {job.score_breakdown && Object.keys(job.score_breakdown).length > 0 && (
            <div className="border-t border-b border-gray-100 py-4">
              <h3 className="font-semibold text-gray-900 mb-3">تفاصيل التقييم</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {Object.entries(job.score_breakdown).map(([key, value]) => (
                  <div key={key} className="bg-gray-50 rounded-lg p-3">
                    <p className="text-xs text-gray-500 capitalize">{key.replace('_', ' ')}</p>
                    <p className="text-2xl font-bold text-gray-900">{value.toFixed(1)}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Client Info */}
          <div className="border-t border-b border-gray-100 py-4">
            <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
              <User className="h-5 w-5 text-blue-600" />
              معلومات العميل
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <p className="text-xs text-gray-500">الاسم</p>
                <p className="font-medium text-gray-900">{job.client_name || 'غير معروف'}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">البلد</p>
                <p className="font-medium text-gray-900 flex items-center gap-1">
                  <MapPin className="h-3 w-3" /> {job.client_country || 'غير معروف'}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500">التقييم</p>
                <p className="font-medium text-gray-900 flex items-center gap-1">
                  <Star className="h-4 w-4 text-yellow-500 fill-current" />
                  {job.client_rating?.toFixed(1) || 'N/A'} ({job.client_review_count || 0} مراجعة)
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500">السجل</p>
                <p className="font-medium text-gray-900">
                  {job.client_hire_history || 0} توظيف | ${job.client_total_spent?.toLocaleString() || 0} إنفاق
                </p>
              </div>
            </div>
            {job.client_payment_status && (
              <p className="mt-2 text-sm text-gray-600">
                حالة الدفع: <span className="font-medium capitalize">{job.client_payment_status}</span>
              </p>
            )}
          </div>

          {/* Description */}
          <div className="border-t border-b border-gray-100 py-4">
            <h3 className="font-semibold text-gray-900 mb-2">الوصف الكامل</h3>
            <div className="prose max-w-none bg-gray-50 p-4 rounded-lg text-gray-700 whitespace-pre-wrap">
              {job.full_description || job.short_description || 'لا يوجد وصف'}
            </div>
          </div>

          {/* Risk Flags */}
          {job.risk_reasons && job.risk_reasons.length > 0 && (
            <div className="border-t border-b border-gray-100 py-4 bg-red-50">
              <h3 className="font-semibold text-red-800 mb-2 flex items-center gap-2">
                <AlertTriangle className="h-5 w-5" />
                علامات الخطر المكتشفة
              </h3>
              <ul className="list-disc list-inside space-y-1 text-red-700">
                {job.risk_reasons.map((reason, i) => (
                  <li key={i}>{reason.replace(/_/g, ' ')}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Proposals */}
          <div className="border-t border-b border-gray-100 py-4">
            <h3 className="font-semibold text-gray-900 mb-3">العروض المقترحة</h3>
            <div className="space-y-4">
              {[
                { label: 'العرض المختصر', content: job.proposal_short },
                { label: 'العرض العادي', content: job.proposal_normal },
                { label: 'العرض الموجز جداً', content: job.proposal_ultra_short },
              ].map(({ label, content }) => (
                <div key={label} className="border border-gray-200 rounded-lg overflow-hidden">
                  <div className="flex items-center justify-between bg-gray-50 px-3 py-2 border-b border-gray-200">
                    <span className="font-medium text-gray-700">{label}</span>
                    <button
                      onClick={() => copyProposal(content || '', label)}
                      className="btn btn-secondary text-sm"
                    >
                      نسخ
                    </button>
                  </div>
                  <div className="p-3 bg-gray-50">
                    <pre className="whitespace-pre-wrap text-sm text-gray-700">{content || 'لم يتم توليده بعد'}</pre>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Original Link */}
          <div className="border-t pt-4">
            <div className="flex items-center gap-3 p-4 bg-gray-50 rounded-lg">
              <Link2 className="h-6 w-6 text-gray-400" />
              <div className="flex-1 min-w-0">
                <p className="text-xs text-gray-500">رابط الوظيفة الأصلي</p>
                <a
                  href={job.job_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary-600 hover:underline truncate block"
                >
                  {job.job_url}
                </a>
              </div>
              <a
                href={job.job_url}
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn-primary"
              >
                <ExternalLink className="h-4 w-4 mr-1" />
                فتح
              </a>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-100 bg-gray-50 flex justify-end gap-2">
          <button onClick={onClose} className="btn btn-secondary">
            إغلاق
          </button>
        </div>
      </div>
    </div>
  );
}