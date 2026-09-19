'use client';

import { JobFilters, Platform } from '@/types';
import { cn } from '@/lib/utils';

interface FiltersBarProps {
  filters: JobFilters;
  platforms: Platform[];
  onChange: (filters: Partial<JobFilters>) => void;
  onSort: (field: string) => void;
}

const categories = [
  { value: '', label: 'جميع الفئات' },
  { value: 'data_entry', label: 'إدخال البيانات' },
  { value: 'document_pdf_word', label: 'مستندات/PDF/Word' },
  { value: 'powerpoint_presentation', label: 'عروض تقديمية' },
  { value: 'excel_spreadsheet', label: 'Excel/جداول' },
  { value: 'general_freelance', label: 'عام' },
];

const matchLevels = [
  { value: '', label: 'جميع المستويات' },
  { value: 'EXCELLENT_MATCH', label: 'ممتاز' },
  { value: 'GOOD_MATCH', label: 'جيد' },
  { value: 'POSSIBLE_MATCH', label: 'محتمل' },
  { value: 'WEAK_MATCH', label: 'ضعيف' },
  { value: 'NOT_RELEVANT', label: 'غير مرتبط' },
];

const riskLevels = [
  { value: '', label: 'جميع المخاطر' },
  { value: 'LOW', label: 'منخفض' },
  { value: 'MEDIUM', label: 'متوسط' },
  { value: 'HIGH', label: 'عالي' },
  { value: 'CRITICAL', label: 'حرج' },
];

const verifications = [
  { value: '', label: 'الكل' },
  { value: 'VERIFIED', label: 'محقق' },
  { value: 'PARTIALLY_VERIFIED', label: 'جزئي' },
  { value: 'UNVERIFIED', label: 'غير محقق' },
];

export function FiltersBar({ filters, platforms, onChange, onSort }: FiltersBarProps) {
  return (
    <div className="card mb-6">
      <div className="flex flex-col sm:flex-row gap-4 flex-wrap">
        <div className="flex-1 min-w-[200px]">
          <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">
            المنصة
          </label>
          <select
            value={filters.platform_id || ''}
            onChange={(e) => onChange({ platform_id: e.target.value ? parseInt(e.target.value) : undefined })}
            className="input"
          >
            <option value="">جميع المنصات</option>
            {platforms.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </div>

        <div className="flex-1 min-w-[180px]">
          <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">
            الفئة
          </label>
          <select
            value={filters.category || ''}
            onChange={(e) => onChange({ category: e.target.value || undefined })}
            className="input"
          >
            {categories.map((c) => (
              <option key={c.value} value={c.value}>{c.label}</option>
            ))}
          </select>
        </div>

        <div className="flex-1 min-w-[180px]">
          <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">
            مستوى المطابقة
          </label>
          <select
            value={filters.match_level || ''}
            onChange={(e) => onChange({ match_level: e.target.value || undefined })}
            className="input"
          >
            {matchLevels.map((m) => (
              <option key={m.value} value={m.value}>{m.label}</option>
            ))}
          </select>
        </div>

        <div className="flex-1 min-w-[160px]">
          <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">
            التحقق
          </label>
          <select
            value={filters.verification_status || ''}
            onChange={(e) => onChange({ verification_status: e.target.value || undefined })}
            className="input"
          >
            {verifications.map((v) => (
              <option key={v.value} value={v.value}>{v.label}</option>
            ))}
          </select>
        </div>

        <div className="flex-1 min-w-[160px]">
          <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">
            المخاطر
          </label>
          <select
            value={filters.risk_level || ''}
            onChange={(e) => onChange({ risk_level: e.target.value || undefined })}
            className="input"
          >
            {riskLevels.map((r) => (
              <option key={r.value} value={r.value}>{r.label}</option>
            ))}
          </select>
        </div>

        <div className="flex-1 min-w-[140px]">
          <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">
            أقل درجة
          </label>
          <input
            type="number"
            min="0"
            max="100"
            value={filters.min_score || ''}
            onChange={(e) => onChange({ min_score: e.target.value ? parseFloat(e.target.value) : undefined })}
            placeholder="0-100"
            className="input"
          />
        </div>

        <div className="flex-1 min-w-[200px]">
          <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">
            بحث بالكلمة
          </label>
          <input
            type="text"
            value={filters.keyword || ''}
            onChange={(e) => onChange({ keyword: e.target.value || undefined })}
            placeholder="ابحث في العنوان/الوصف..."
            className="input"
            onKeyDown={(e) => e.key === 'Enter' && e.preventDefault()}
          />
        </div>
      </div>
    </div>
  );
}