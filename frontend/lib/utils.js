import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(amount) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(amount);
}

export function formatDate(date) {
  if (date === null || date === undefined || date === '') return '-';

  const parsedDate = new Date(date);
  if (Number.isNaN(parsedDate.getTime())) return '-';

  return new Intl.DateTimeFormat('en-IN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(parsedDate);
}

export function formatDateTime(date) {
  if (date === null || date === undefined || date === '') return '-';

  const parsedDate = new Date(date);
  if (Number.isNaN(parsedDate.getTime())) return '-';

  return new Intl.DateTimeFormat('en-IN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(parsedDate);
}

export function getStatusColor(status) {
  const colors = {
    pending: 'text-yellow-700 bg-yellow-100 border-yellow-200',
    in_progress: 'text-blue-700 bg-blue-100 border-blue-200',
    approved: 'text-green-700 bg-green-100 border-green-200',
    rejected: 'text-red-700 bg-red-100 border-red-200',
    disbursed: 'text-purple-700 bg-purple-100 border-purple-200',
    active: 'text-green-700 bg-green-100 border-green-200',
    closed: 'text-gray-700 bg-gray-100 border-gray-200',
    defaulted: 'text-red-700 bg-red-100 border-red-200',
  };
  return colors[status] || 'text-gray-700 bg-gray-100 border-gray-200';
}

export function getRiskColor(segment) {
  const colors = {
    LOW: 'text-green-700 bg-green-100 border-green-200',
    MEDIUM: 'text-yellow-700 bg-yellow-100 border-yellow-200',
    HIGH: 'text-red-700 bg-red-100 border-red-200',
  };
  return colors[segment] || 'text-gray-700 bg-gray-100 border-gray-200';
}

export function downloadFile(blob, filename) {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
}

export function getInitials(name) {
  if (!name) return '?';
  return name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

export function truncate(str, length = 50) {
  if (!str) return '';
  if (str.length <= length) return str;
  return str.slice(0, length) + '...';
}
