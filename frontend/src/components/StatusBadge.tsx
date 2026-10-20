import React from 'react';
import { AlertCircle, AlertTriangle, CheckCircle2, Clock, XCircle } from 'lucide-react';

export type StatusType = 'pending' | 'approved' | 'rejected' | 'suspended' | 'verified' | 'revoked' | 'open' | 'draft' | 'closed';

interface StatusBadgeProps {
  status: StatusType | string;
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, className = '' }) => {
  const norm = status.toLowerCase();

  switch (norm) {
    case 'approved':
    case 'verified':
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-[9999px] text-xs font-mono font-medium bg-[#f0fdf4] text-[#15803d] border border-[#bbf7d0] ${className}`}
        >
          <CheckCircle2 className="w-3.5 h-3.5" aria-hidden="true" />
          <span className="capitalize">{status}</span>
        </span>
      );

    case 'pending':
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-[9999px] text-xs font-mono font-medium bg-[#fffbeb] text-[#b45309] border border-[#fde68a] ${className}`}
        >
          <Clock className="w-3.5 h-3.5" aria-hidden="true" />
          <span className="capitalize">{status}</span>
        </span>
      );

    case 'rejected':
    case 'revoked':
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-[9999px] text-xs font-mono font-medium bg-[#fef2f2] text-[#b91c1c] border border-[#fecaca] ${className}`}
        >
          <XCircle className="w-3.5 h-3.5" aria-hidden="true" />
          <span className="capitalize">{status}</span>
        </span>
      );

    case 'suspended':
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-[9999px] text-xs font-mono font-medium bg-[#fef2f2] text-[#991b1b] border border-[#f87171] ${className}`}
        >
          <AlertTriangle className="w-3.5 h-3.5" aria-hidden="true" />
          <span className="capitalize">{status}</span>
        </span>
      );

    default:
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-[9999px] text-xs font-mono font-medium bg-[#f3f4f6] text-[#374151] border border-[#e5e7eb] ${className}`}
        >
          <AlertCircle className="w-3.5 h-3.5" aria-hidden="true" />
          <span className="capitalize">{status}</span>
        </span>
      );
  }
};
