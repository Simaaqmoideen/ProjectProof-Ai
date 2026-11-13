import React, { useState } from 'react';
import { apiRequest } from '../../lib/api';
import { StatusBadge } from '../../components/StatusBadge';
import { AlertCircle, Info, Loader2, Search, ShieldCheck } from 'lucide-react';
import { useParams } from 'react-router-dom';

interface VerificationData {
  verification_id: string;
  status: 'issued' | 'revoked';
  project: {
    title: string;
    difficulty: string;
    duration_days: number;
  };
  company: {
    name: string;
    approved: boolean;
  };
  student: {
    display_name: string;
  };
  evaluation: {
    summary: string | null;
    evaluated_at: string | null;
  };
  skills: string[];
  timeline: {
    applied_at: string | null;
    started_at: string | null;
    completed_at: string | null;
  };
  checked_at: string;
  qr_code_data_uri: string;
  disclaimer: string;
  revoked_at?: string | null;
  revocation_reason?: string | null;
}

export const PublicVerificationPage: React.FC = () => {
  const { id: routeId } = useParams<{ id: string }>();
  const [searchId, setSearchId] = useState(routeId || '');
  const [data, setData] = useState<VerificationData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleVerify = async (valueToQuery: string, lookupKind: 'qr' | 'id') => {
    const value = valueToQuery.trim();
    if (!value) return;
    setLoading(true);
    setError(null);
    setData(null);

    try {
      // In accordance with Non-negotiable Rule 1: Verified means live.
      // Cache-Control: no-store must be respected, query live backend endpoint
      const path = lookupKind === 'qr' ? '/public/verify/' : '/public/verify-id/';
      const result = await apiRequest<VerificationData>(`${path}${encodeURIComponent(value)}`);
      setData(result);
    } catch (err: any) {
      setError(err.message || 'Verification failed. Certificate record not found on live ledger.');
    } finally {
      setLoading(false);
    }
  };

  React.useEffect(() => {
    if (routeId) {
      setSearchId(routeId);
      handleVerify(routeId, 'qr');
    }
  }, [routeId]);

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12 space-y-8">
      {/* Header */}
      <div className="text-center space-y-2">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-[#ebebeb] bg-[#fafafa] text-xs font-mono text-[#171717]">
          <ShieldCheck className="w-3.5 h-3.5 text-[#297a3a]" />
          <span>Live Ledger Read · Cache-Control: no-store</span>
        </div>
        <h1 className="text-3xl font-normal tracking-tight text-[#171717]">
          Public Certificate Verification
        </h1>
        <p className="text-sm text-[#4d4d4d] max-w-lg mx-auto">
          Enter a verification ID or open a QR link to inspect the record live against the primary database view.
        </p>
      </div>

      {/* Search Input */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          const isVerificationId = /^EXP-\d{4}-[A-Z0-9]{4}-\d{4}$/i.test(searchId.trim());
          handleVerify(searchId, isVerificationId ? 'id' : 'qr');
        }}
        className="max-w-xl mx-auto flex gap-2"
      >
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-[#7d7d7d] absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchId}
            onChange={(e) => setSearchId(e.target.value)}
            aria-label="Verification ID or QR token"
            placeholder="e.g. EXP-2026-AB12-9821"
            className="w-full pl-9 pr-3 py-2 text-sm rounded-[6px] border border-[#ebebeb] bg-[#ffffff] text-[#171717] placeholder-[#a8a8a8] focus:outline-none focus:ring-1 focus:ring-[#171717] font-mono"
          />
        </div>
        <button
          type="submit"
          disabled={loading || !searchId.trim()}
          className="px-4 py-2 rounded-[6px] bg-[#171717] text-[#ffffff] text-sm font-medium hover:bg-[#000000] disabled:opacity-50 transition-colors flex items-center gap-2"
        >
          {loading && <Loader2 className="w-4 h-4 animate-spin" />}
          Verify Live
        </button>
      </form>

      {/* Mandatory Platform Disclaimer */}
      <div className="p-4 rounded-[6px] border border-[#ebebeb] bg-[#ffffff] flex items-start gap-3 max-w-2xl mx-auto">
        <Info className="w-4 h-4 text-[#7d7d7d] mt-0.5 shrink-0" />
        <p className="text-xs text-[#4d4d4d]">
          <strong>Mandatory Platform Notice:</strong> A certificate is a platform record, not formal employment experience. This verification page queries live data on every request and disallows caching.
        </p>
      </div>

      {/* Error View */}
      {error && (
        <div className="p-6 rounded-[6px] border border-[#c4231c]/20 bg-[#ffffff] max-w-2xl mx-auto text-center space-y-2">
          <AlertCircle className="w-8 h-8 text-[#c4231c] mx-auto" />
          <h3 className="text-sm font-medium text-[#171717]">Record Not Found or Unverified</h3>
          <p className="text-xs text-[#4d4d4d]">{error}</p>
        </div>
      )}

      {/* Verification Result Card */}
      {data && (
        <div className="max-w-2xl mx-auto rounded-[6px] border border-[#ebebeb] bg-[#ffffff] p-8 space-y-6 shadow-sm">
          <div className="flex items-start justify-between border-b border-[#ebebeb] pb-6">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="font-mono text-[11px] uppercase tracking-wider text-[#7d7d7d]">
                  Verification ID: {data.verification_id}
                </span>
              </div>
              <h2 className="text-2xl font-normal text-[#171717] tracking-tight">
                {data.project.title}
              </h2>
              <p className="text-sm text-[#4d4d4d] mt-1">
                Awarded to <strong className="text-[#171717]">{data.student.display_name}</strong>
              </p>
            </div>
            <StatusBadge status={data.status === 'issued' ? 'verified' : 'revoked'} />
          </div>

          <div className="grid grid-cols-2 gap-4 text-xs font-mono">
            <div className="p-3 rounded-[6px] bg-[#fafafa] border border-[#ebebeb] space-y-1">
              <span className="text-[#7d7d7d] uppercase">Issuing Company</span>
              <p className="font-sans text-sm font-medium text-[#171717]">{data.company.name}</p>
            </div>
            <div className="p-3 rounded-[6px] bg-[#fafafa] border border-[#ebebeb] space-y-1">
              <span className="text-[#7d7d7d] uppercase">Project Difficulty</span>
              <p className="font-sans text-sm font-medium capitalize text-[#171717]">{data.project.difficulty}</p>
            </div>
            <div className="p-3 rounded-[6px] bg-[#fafafa] border border-[#ebebeb] space-y-1">
              <span className="text-[#7d7d7d] uppercase">Duration</span>
              <p className="text-[#171717]">{data.project.duration_days} days</p>
            </div>
            <div className="p-3 rounded-[6px] bg-[#fafafa] border border-[#ebebeb] space-y-1">
              <span className="text-[#7d7d7d] uppercase">Completed</span>
              <p className="text-[#171717]">
                {data.timeline.completed_at
                  ? new Date(data.timeline.completed_at).toLocaleDateString()
                  : 'Date unavailable'}
              </p>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-t border-[#ebebeb] pt-5">
            <div className="space-y-1">
              <h3 className="text-xs font-mono uppercase tracking-wide text-[#7d7d7d]">Scan to Verify</h3>
              <p className="text-sm text-[#4d4d4d]">This QR code opens this live verification record.</p>
            </div>
            <img
              src={data.qr_code_data_uri}
              alt={`QR code for verification ${data.verification_id}`}
              className="w-32 h-32 border border-[#ebebeb] rounded-[6px] p-2 bg-white"
            />
          </div>

          {data.evaluation.summary && (
            <div className="border-t border-[#ebebeb] pt-5 space-y-2">
              <h3 className="text-xs font-mono uppercase tracking-wide text-[#7d7d7d]">Public Evaluation Summary</h3>
              <p className="text-sm leading-6 text-[#4d4d4d]">{data.evaluation.summary}</p>
            </div>
          )}

          {data.skills.length > 0 && (
            <div className="border-t border-[#ebebeb] pt-5 space-y-2">
              <h3 className="text-xs font-mono uppercase tracking-wide text-[#7d7d7d]">Demonstrated Skills</h3>
              <ul className="flex flex-wrap gap-2" aria-label="Demonstrated skills">
                {data.skills.map((skill) => (
                  <li key={skill} className="rounded-[6px] border border-[#ebebeb] px-2.5 py-1 text-xs text-[#4d4d4d]">
                    {skill}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {data.status === 'revoked' && (
            <div className="p-3 rounded-[6px] bg-[#c4231c]/10 border border-[#c4231c]/20 text-xs text-[#c4231c] space-y-1">
              <p className="font-semibold">Reason for Revocation:</p>
              <p>{data.revocation_reason || 'Administrative revocation'}</p>
            </div>
          )}

          <p className="border-t border-[#ebebeb] pt-4 text-xs text-[#4d4d4d]">{data.disclaimer}</p>
        </div>
      )}
    </div>
  );
};
