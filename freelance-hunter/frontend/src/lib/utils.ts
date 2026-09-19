import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(dateString: string | null): string {
  if (!dateString) return 'Unknown';
  try {
    return new Date(dateString).toLocaleDateString('ar-EG', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return 'Invalid Date';
  }
}

export function formatCurrency(amount: number | null, currency = 'USD'): string {
  if (amount === null || amount === undefined) return 'Not specified';
  const symbols: Record<string, string> = {
    USD: '$',
    EUR: '€',
    GBP: '£',
    EGP: 'EGP',
    SAR: 'SAR',
    AED: 'AED',
  };
  return `${symbols[currency] || currency} ${amount.toLocaleString()}`;
}

export function getMatchLevelColor(level: string): string {
  const colors: Record<string, string> = {
    EXCELLENT_MATCH: 'bg-green-100 text-green-800',
    GOOD_MATCH: 'bg-blue-100 text-blue-800',
    POSSIBLE_MATCH: 'bg-yellow-100 text-yellow-800',
    WEAK_MATCH: 'bg-pink-100 text-pink-800',
    NOT_RELEVANT: 'bg-gray-100 text-gray-800',
  };
  return colors[level] || 'bg-gray-100 text-gray-800';
}

export function getRiskLevelColor(level: string): string {
  const colors: Record<string, string> = {
    LOW: 'bg-green-100 text-green-800',
    MEDIUM: 'bg-yellow-100 text-yellow-800',
    HIGH: 'bg-red-100 text-red-800',
    CRITICAL: 'bg-pink-100 text-pink-800',
  };
  return colors[level] || 'bg-gray-100 text-gray-800';
}

export function getVerificationColor(status: string): string {
  const colors: Record<string, string> = {
    VERIFIED: 'bg-green-100 text-green-800',
    PARTIALLY_VERIFIED: 'bg-yellow-100 text-yellow-800',
    UNVERIFIED: 'bg-red-100 text-red-800',
    FAILED: 'bg-pink-100 text-pink-800',
  };
  return colors[status] || 'bg-gray-100 text-gray-800';
}

export function truncate(str: string, length: number): string {
  if (!str) return '';
  if (str.length <= length) return str;
  return str.slice(0, length).trim() + '...';
}

export function copyToClipboard(text: string): Promise<void> {
  return navigator.clipboard.writeText(text);
}