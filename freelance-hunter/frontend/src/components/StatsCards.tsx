'use client';

import { DashboardStats } from '@/types';
import { CheckCircle2, Clock, TrendingUp, AlertTriangle } from 'lucide-react';

interface StatsCardsProps {
  stats: DashboardStats | null;
}

const statItems = [
  {
    key: 'total_jobs',
    label: 'إجمالي الوظائف',
    icon: TrendingUp,
    color: 'bg-blue-500',
    bgColor: 'bg-blue-50',
  },
  {
    key: 'verified_jobs',
    label: 'تم التحقق',
    icon: CheckCircle2,
    color: 'bg-green-500',
    bgColor: 'bg-green-50',
  },
  {
    key: 'new_today',
    label: 'جديد اليوم',
    icon: Clock,
    color: 'bg-purple-500',
    bgColor: 'bg-purple-50',
  },
  {
    key: 'high_match_jobs',
    label: 'مطابقة عالية',
    icon: TrendingUp,
    color: 'bg-orange-500',
    bgColor: 'bg-orange-50',
  },
  {
    key: 'high_risk_jobs',
    label: 'مخاطر عالية',
    icon: AlertTriangle,
    color: 'bg-red-500',
    bgColor: 'bg-red-50',
  },
];

export function StatsCards({ stats }: StatsCardsProps) {
  if (!stats) return null;

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4 mb-6">
      {statItems.map((item) => (
        <div
          key={item.key}
          className={`card ${item.bgColor} border-l-4 border-l-${item.color.replace('bg-', '')}`}
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">{item.label}</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">
                {stats[item.key as keyof DashboardStats]?.toLocaleString() || 0}
              </p>
            </div>
            <div className={`p-3 rounded-full ${item.bgColor}`}>
              <item.icon className={`h-6 w-6 ${item.color}`} />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}