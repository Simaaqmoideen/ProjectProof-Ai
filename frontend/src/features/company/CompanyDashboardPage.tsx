import React, { useEffect, useState } from 'react';
import { useAuth } from '../../lib/auth-context';
import { apiRequest } from '../../lib/api';
import { StatusBadge } from '../../components/StatusBadge';
import {
  AlertTriangle,
  Building2,
  CheckCircle2,
  Clock,
  ExternalLink,
  FileCheck,
  FolderPlus,
  Globe,
  Info,
  Mail,
  Shield,
  ShieldCheck,
  Users,
} from 'lucide-react';
import { Link } from 'react-router-dom';

interface CompanyProfile {
  id: string;
  name: string;
  website: string | null;
  email_domain: string | null;
  description: string | null;
  registration_doc_key: string | null;
  status: string;
  trust_score: number;
  created_at: string;
}

export const CompanyDashboardPage: React.FC = () => {
  const { user } = useAuth();
  const [company, setCompany] = useState<CompanyProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchCompany = async () => {
      try {
        const data = await apiRequest<CompanyProfile>('/companies/me');
        setCompany(data);
      } catch (err) {
        console.error('Failed to load company profile:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchCompany();
  }, []);

  const isApproved = company?.status === 'approved';
  const isPending = company?.status === 'pending';
  const isSuspended = company?.status === 'suspended';

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-6 border-b border-[#ebebeb]">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="font-mono text-[11px] tracking-wider uppercase text-[#7d7d7d]">
              Company Workspace
            </span>
            <span className="text-[#ebebeb]">•</span>
            <span className="font-mono text-[11px] text-[#297a3a] flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-[#297a3a]" /> Live
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-normal text-[#171717] tracking-tight flex items-center gap-3">
            {company ? company.name : 'Company Portal'}
            {company && <StatusBadge status={company.status} />}
          </h1>
          <p className="mt-1 text-sm text-[#4d4d4d]">
            Post authentic engineering projects, vet student deliverables, and sign off on cryptographic completion proofs.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            disabled={!isApproved}
            className={`inline-flex items-center gap-2 px-4 py-2 rounded-[6px] text-sm font-medium transition-colors ${
              isApproved
                ? 'bg-[#171717] text-[#ffffff] hover:bg-[#000000]'
                : 'bg-[#ebebeb] text-[#8f8f8f] cursor-not-allowed'
            }`}
            title={isApproved ? 'Create a new project' : 'Company approval required to post projects'}
          >
            <FolderPlus className="w-4 h-4" />
            Post New Project
          </button>
        </div>
      </div>

      {/* Status Alert Banners */}
      {isPending && (
        <div className="p-4 rounded-[6px] border border-[#ebebeb] bg-[#ffffff] flex items-start gap-3">
          <Clock className="w-4 h-4 text-[#7d7d7d] mt-0.5 shrink-0" />
          <div className="text-xs text-[#4d4d4d] space-y-1">
            <p className="font-medium text-[#171717]">Application In Admin Review Queue</p>
            <p>
              Your organization account is undergoing administrative verification. Automated domain matching, document checks, and trust scoring are evaluating your submission. Project creation will activate once approved.
            </p>
          </div>
        </div>
      )}

      {isSuspended && (
        <div className="p-4 rounded-[6px] border border-[#c4231c]/20 bg-[#ffffff] flex items-start gap-3">
          <AlertTriangle className="w-4 h-4 text-[#c4231c] mt-0.5 shrink-0" />
          <div className="text-xs text-[#4d4d4d] space-y-1">
            <p className="font-medium text-[#c4231c]">Account Suspended</p>
            <p>
              This company account is currently suspended. Existing certificates remain unaltered as immutable historical platform records, but new postings and approvals are frozen.
            </p>
          </div>
        </div>
      )}

      {/* Trust & Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-5 rounded-[6px] border border-[#ebebeb] bg-[#ffffff] space-y-2">
          <div className="flex items-center justify-between text-xs text-[#7d7d7d] font-mono uppercase tracking-wider">
            <span>Trust Score</span>
            <Shield className="w-4 h-4 text-[#171717]" />
          </div>
          <div className="text-2xl font-normal tracking-tight text-[#171717]">
            {company?.trust_score ?? 100} <span className="text-xs font-mono text-[#7d7d7d] font-normal">/ 100</span>
          </div>
          <div className="w-full bg-[#fafafa] border border-[#ebebeb] h-1.5 rounded-full overflow-hidden">
            <div
              className="bg-[#171717] h-full rounded-full"
              style={{ width: `${Math.min(company?.trust_score ?? 100, 100)}%` }}
            />
          </div>
          <p className="text-[11px] text-[#7d7d7d] font-mono">Platform reputation metric</p>
        </div>

        <div className="p-5 rounded-[6px] border border-[#ebebeb] bg-[#ffffff] space-y-2">
          <div className="flex items-center justify-between text-xs text-[#7d7d7d] font-mono uppercase tracking-wider">
            <span>Active Projects</span>
            <Building2 className="w-4 h-4 text-[#171717]" />
          </div>
          <div className="text-2xl font-normal tracking-tight text-[#171717]">0</div>
          <p className="text-[11px] text-[#7d7d7d]">Public listings visible to students</p>
        </div>

        <div className="p-5 rounded-[6px] border border-[#ebebeb] bg-[#ffffff] space-y-2">
          <div className="flex items-center justify-between text-xs text-[#7d7d7d] font-mono uppercase tracking-wider">
            <span>Verified Issued</span>
            <CheckCircle2 className="w-4 h-4 text-[#297a3a]" />
          </div>
          <div className="text-2xl font-normal tracking-tight text-[#171717]">0</div>
          <p className="text-[11px] text-[#7d7d7d]">Certificates awarded</p>
        </div>

        <div className="p-5 rounded-[6px] border border-[#ebebeb] bg-[#ffffff] space-y-2">
          <div className="flex items-center justify-between text-xs text-[#7d7d7d] font-mono uppercase tracking-wider">
            <span>Review Queue</span>
            <Users className="w-4 h-4 text-[#171717]" />
          </div>
          <div className="text-2xl font-normal tracking-tight text-[#171717]">0</div>
          <p className="text-[11px] text-[#7d7d7d]">Milestone submissions pending</p>
        </div>
      </div>

      {/* Company Verification Details */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-4">
          <div className="p-6 rounded-[6px] border border-[#ebebeb] bg-[#ffffff] space-y-5">
            <h2 className="text-base font-medium text-[#171717]">Organization Details</h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div className="p-3 rounded-[6px] bg-[#fafafa] border border-[#ebebeb] space-y-1">
                <span className="text-[#7d7d7d] font-mono uppercase">Work Domain</span>
                <p className="font-mono text-[#171717] text-sm">
                  {company?.email_domain || 'Pending configuration'}
                </p>
              </div>

              <div className="p-3 rounded-[6px] bg-[#fafafa] border border-[#ebebeb] space-y-1">
                <span className="text-[#7d7d7d] font-mono uppercase">Official Website</span>
                <p className="text-[#171717] text-sm flex items-center gap-1.5 truncate">
                  <Globe className="w-3.5 h-3.5 text-[#7d7d7d] shrink-0" />
                  {company?.website ? (
                    <a
                      href={company.website}
                      target="_blank"
                      rel="noreferrer"
                      className="hover:underline flex items-center gap-1"
                    >
                      {company.website} <ExternalLink className="w-3 h-3" />
                    </a>
                  ) : (
                    'Not specified'
                  )}
                </p>
              </div>

              <div className="sm:col-span-2 p-3 rounded-[6px] bg-[#fafafa] border border-[#ebebeb] space-y-1">
                <span className="text-[#7d7d7d] font-mono uppercase">Company Description</span>
                <p className="text-[#4d4d4d] text-xs leading-relaxed">
                  {company?.description || 'No description provided during registration.'}
                </p>
              </div>

              <div className="sm:col-span-2 p-3 rounded-[6px] bg-[#fafafa] border border-[#ebebeb] flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FileCheck className="w-4 h-4 text-[#297a3a]" />
                  <span className="text-[#4d4d4d] text-xs">
                    Verification Document: <code className="font-mono text-[#171717]">{company?.registration_doc_key || 'Uploaded'}</code>
                  </span>
                </div>
                <span className="font-mono text-[10px] text-[#7d7d7d] uppercase">Encrypted Storage</span>
              </div>
            </div>
          </div>
        </div>

        {/* Sidebar Info */}
        <div className="space-y-6">
          <div className="p-5 rounded-[6px] border border-[#ebebeb] bg-[#ffffff] space-y-3">
            <h3 className="text-xs font-mono uppercase tracking-wider text-[#7d7d7d]">
              Audit & Governance
            </h3>
            <p className="text-xs text-[#4d4d4d] leading-relaxed">
              Every change to company approval status, trust score adjustments, or project removals writes an append-only transaction row into the administrative audit ledger.
            </p>
            <div className="pt-2 border-t border-[#ebebeb] text-[11px] font-mono text-[#7d7d7d]">
              Admin Account: <span className="text-[#171717]">{user?.email}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
