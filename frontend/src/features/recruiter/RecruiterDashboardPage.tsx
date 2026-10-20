import React, { useEffect, useState } from 'react';
import { useAuth } from '../../lib/auth-context';
import { apiRequest } from '../../lib/api';
import { StatusBadge } from '../../components/StatusBadge';
import {
  Briefcase,
  Clock,
  Eye,
  FileCheck,
  Lock,
  Search,
  Shield,
  ShieldCheck,
  UserCheck,
  Users,
} from 'lucide-react';
import { Link } from 'react-router-dom';

interface RecruiterProfile {
  user_id: string;
  full_name: string;
  organization: string;
  work_email_domain: string | null;
  approval_status: string;
  email: string;
}

export const RecruiterDashboardPage: React.FC = () => {
  const { user } = useAuth();
  const [recruiter, setRecruiter] = useState<RecruiterProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const data = await apiRequest<RecruiterProfile>('/recruiters/me');
        setRecruiter(data);
      } catch (err) {
        console.error('Failed to load recruiter profile:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchProfile();
  }, []);

  const isApproved = recruiter?.approval_status === 'approved';
  const isPending = recruiter?.approval_status === 'pending';

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-6 border-b border-[#ebebeb]">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="font-mono text-[11px] tracking-wider uppercase text-[#7d7d7d]">
              Recruiter Portal
            </span>
            <span className="text-[#ebebeb]">•</span>
            <span className="font-mono text-[11px] text-[#297a3a] flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-[#297a3a]" /> Live
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-normal text-[#171717] tracking-tight flex items-center gap-3">
            {recruiter?.full_name || 'Recruiter Workspace'}
            {recruiter && <StatusBadge status={recruiter.approval_status} />}
          </h1>
          <p className="mt-1 text-sm text-[#4d4d4d]">
            Discover candidate engineering talent backed by tamper-proof cryptographic project evidence.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            to="/verify"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-[6px] border border-[#ebebeb] bg-[#ffffff] text-sm font-medium text-[#171717] hover:bg-[#fafafa] transition-colors"
          >
            <ShieldCheck className="w-4 h-4 text-[#297a3a]" />
            Verify Certificate ID
          </Link>
        </div>
      </div>

      {/* Approval Status Banner */}
      {isPending && (
        <div className="p-4 rounded-[6px] border border-[#ebebeb] bg-[#ffffff] flex items-start gap-3">
          <Clock className="w-4 h-4 text-[#7d7d7d] mt-0.5 shrink-0" />
          <div className="text-xs text-[#4d4d4d] space-y-1">
            <p className="font-medium text-[#171717]">Recruiter Account Awaiting Admin Review</p>
            <p>
              Under ProjectProof privacy protocol (<code>FR-SEC-1</code>), student profiles remain private by default. Recruiter accounts require administrative approval before unlocking candidate searches and talent pool access.
            </p>
          </div>
        </div>
      )}

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-5 rounded-[6px] border border-[#ebebeb] bg-[#ffffff] space-y-2">
          <div className="flex items-center justify-between text-xs text-[#7d7d7d] font-mono uppercase tracking-wider">
            <span>Organization</span>
            <Briefcase className="w-4 h-4 text-[#171717]" />
          </div>
          <div className="text-xl font-normal tracking-tight text-[#171717] truncate">
            {recruiter?.organization || 'Organization Pending'}
          </div>
          <p className="text-[11px] font-mono text-[#7d7d7d]">
            Domain: {recruiter?.work_email_domain || 'Pending'}
          </p>
        </div>

        <div className="p-5 rounded-[6px] border border-[#ebebeb] bg-[#ffffff] space-y-2">
          <div className="flex items-center justify-between text-xs text-[#7d7d7d] font-mono uppercase tracking-wider">
            <span>Candidate Access</span>
            {isApproved ? (
              <Eye className="w-4 h-4 text-[#297a3a]" />
            ) : (
              <Lock className="w-4 h-4 text-[#7d7d7d]" />
            )}
          </div>
          <div className="text-xl font-normal tracking-tight text-[#171717]">
            {isApproved ? 'Full Access' : 'Locked (Pending Approval)'}
          </div>
          <p className="text-[11px] text-[#7d7d7d]">Public student profiles only</p>
        </div>

        <div className="p-5 rounded-[6px] border border-[#ebebeb] bg-[#ffffff] space-y-2">
          <div className="flex items-center justify-between text-xs text-[#7d7d7d] font-mono uppercase tracking-wider">
            <span>Cryptographic Proof</span>
            <FileCheck className="w-4 h-4 text-[#297a3a]" />
          </div>
          <div className="text-xl font-normal tracking-tight text-[#171717]">Live DB Lookup</div>
          <p className="text-[11px] text-[#7d7d7d]">Cache-Control: no-store guaranteed</p>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-medium text-[#171717]">Candidate Discovery</h2>
            <span className="text-xs text-[#7d7d7d] font-mono">
              {isApproved ? 'Directory active' : 'Locked'}
            </span>
          </div>

          {isApproved ? (
            <div className="p-8 rounded-[6px] border border-[#ebebeb] bg-[#ffffff] text-center space-y-3">
              <Users className="w-8 h-8 text-[#7d7d7d] mx-auto" />
              <p className="text-sm font-medium text-[#171717]">Talent Directory</p>
              <p className="text-xs text-[#7d7d7d] max-w-sm mx-auto">
                Search verified students by proven skills, completed projects, and platform XP.
              </p>
            </div>
          ) : (
            <div className="p-8 rounded-[6px] border border-[#ebebeb] bg-[#ffffff] text-center space-y-3">
              <div className="w-10 h-10 mx-auto rounded-full bg-[#fafafa] border border-[#ebebeb] flex items-center justify-center">
                <Lock className="w-5 h-5 text-[#7d7d7d]" />
              </div>
              <p className="text-sm font-medium text-[#171717]">Approval Required to View Candidates</p>
              <p className="text-xs text-[#7d7d7d] max-w-md mx-auto">
                Once an administrator reviews your organization affiliation, you will have access to all students who have opted into public recruiter discovery.
              </p>
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          <div className="p-5 rounded-[6px] border border-[#ebebeb] bg-[#ffffff] space-y-3">
            <h3 className="text-xs font-mono uppercase tracking-wider text-[#7d7d7d]">
              Recruiter Guidelines
            </h3>
            <p className="text-xs text-[#4d4d4d] leading-relaxed">
              Certificates viewed on ProjectProof are live platform verification records. They validate that specific code was merged into an approved company repo and verified by that company's lead engineer.
            </p>
            <div className="p-2.5 rounded-[6px] bg-[#fafafa] border border-[#ebebeb] text-[11px] text-[#4d4d4d]">
              <strong>Rule 12 Reminder:</strong> GitHub links provided by applicants are self-reported and do not affect verification scores.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
