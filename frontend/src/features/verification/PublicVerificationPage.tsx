import React, { useState } from 'react';
import { apiRequest } from '../../lib/api';
import { StatusBadge } from '../../components/StatusBadge';
import { AlertCircle, Award, CheckCircle2, Info, Loader2, QrCode, Search, ShieldCheck } from 'lucide-react';
import { useParams } from 'react-router-dom';

interface VerificationData {
  verification_id: string;
  student_name: string;
  project_title: string;
  company_name: string;
  issue_date: string;
  xp_awarded: number;
  status: 'valid' | 'revoked';
  qr_code_url?: string;
  revocation_reason?: string | null;
}

export const PublicVerificationPage: React.FC = () => {
  const { id: routeId } = useParams<{ id: string }>();
  const [searchId, setSearchId] = useState(routeId || '');
  const [data, setData] = useState<VerificationData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleVerify = async (idToQuery: string) => {
    if (!idToQuery.trim()) return;
    setLoading(true);
    setError(null);
    setData(null);

    try {
      // In accordance with Non-negotiable Rule 1: Verified means live.
      // Cache-Control: no-store must be respected, query live backend endpoint
      const result = await apiRequest<VerificationData>(`/verify/${encodeURIComponent(idToQuery.trim())}`);
      setData(result);
    } catch (err: any) {
      setError(err.message || 'Verification failed. Certificate record not found on live ledger.');
    } finally {
      setLoading(false);
    }
  };

  React.useEffect(() => {
    if (routeId) {
      handleVerify(routeId);
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
          Enter a cryptographic verification ID to inspect live authenticity against the primary database view.
        </p>
      </div>

      {/* Search Input */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleVerify(searchId);
        }}
        className="max-w-xl mx-auto flex gap-2"
      >
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-[#7d7d7d] absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchId}
            onChange={(e) => setSearchId(e.target.value)}
            placeholder="e.g. CRT-2026-F4B2 or UUID"
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
                {data.project_title}
              </h2>
              <p className="text-sm text-[#4d4d4d] mt-1">
                Awarded to <strong className="text-[#171717]">{data.student_name}</strong>
              </p>
            </div>
            <StatusBadge status={data.status === 'valid' ? 'verified' : 'revoked'} />
          </div>

          <div className="grid grid-cols-2 gap-4 text-xs font-mono">
            <div className="p-3 rounded-[6px] bg-[#fafafa] border border-[#ebebeb] space-y-1">
              <span className="text-[#7d7d7d] uppercase">Issuing Company</span>
              <p className="font-sans text-sm font-medium text-[#171717]">{data.company_name}</p>
            </div>
            <div className="p-3 rounded-[6px] bg-[#fafafa] border border-[#ebebeb] space-y-1">
              <span className="text-[#7d7d7d] uppercase">XP Earned</span>
              <p className="font-sans text-sm font-medium text-[#171717]">{data.xp_awarded} XP</p>
            </div>
            <div className="p-3 rounded-[6px] bg-[#fafafa] border border-[#ebebeb] space-y-1">
              <span className="text-[#7d7d7d] uppercase">Issue Date</span>
              <p className="text-[#171717]">{new Date(data.issue_date).toLocaleDateString()}</p>
            </div>
            <div className="p-3 rounded-[6px] bg-[#fafafa] border border-[#ebebeb] space-y-1">
              <span className="text-[#7d7d7d] uppercase">Ledger Source</span>
              <p className="text-[#297a3a]">PostgreSQL v_public_verification</p>
            </div>
          </div>

          {data.status === 'revoked' && (
            <div className="p-3 rounded-[6px] bg-[#c4231c]/10 border border-[#c4231c]/20 text-xs text-[#c4231c] space-y-1">
              <p className="font-semibold">Reason for Revocation:</p>
              <p>{data.revocation_reason || 'Administrative revocation'}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
