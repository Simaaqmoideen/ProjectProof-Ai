import React from 'react';
import { useAuth } from '../../lib/auth-context';
import { StatusBadge } from '../../components/StatusBadge';
import { Award, Briefcase, CheckCircle2, ChevronRight, FileCode2, Info, ShieldCheck, Sparkles } from 'lucide-react';
import { Link } from 'react-router-dom';

export const StudentDashboardPage: React.FC = () => {
  const { user } = useAuth();

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-6 border-b border-[#ebebeb]">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="font-mono text-[11px] tracking-wider uppercase text-[#7d7d7d]">
              Student Workspace
            </span>
            <span className="text-[#ebebeb]">•</span>
            <span className="font-mono text-[11px] text-[#297a3a] flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-[#297a3a]" /> Live
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-normal text-[#171717] tracking-tight">
            Welcome, {user?.email.split('@')[0]}
          </h1>
          <p className="mt-1 text-sm text-[#4d4d4d]">
            Build real software projects posted by approved companies, earn XP, and unlock cryptographically verifiable certificates.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            to="/projects"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-[6px] bg-[#171717] text-[#ffffff] text-sm font-medium hover:bg-[#000000] transition-colors"
          >
            <Briefcase className="w-4 h-4" />
            Browse Projects
          </Link>
        </div>
      </div>

      {/* Verification Notice / Banner */}
      <div className="p-4 rounded-[6px] border border-[#ebebeb] bg-[#ffffff] flex items-start gap-3">
        <Info className="w-4 h-4 text-[#7d7d7d] mt-0.5 shrink-0" />
        <div className="text-xs text-[#4d4d4d] space-y-1">
          <p className="font-medium text-[#171717]">Platform Guarantee & Policy</p>
          <p>
            A ProjectProof certificate is a platform record of verified project completion, not formal employment experience. Every certificate carries a live cryptographic verification ID queried against the primary ledger in real-time.
          </p>
        </div>
      </div>

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-5 rounded-[6px] border border-[#ebebeb] bg-[#ffffff] space-y-2">
          <div className="flex items-center justify-between text-xs text-[#7d7d7d] font-mono uppercase tracking-wider">
            <span>Level & XP</span>
            <Sparkles className="w-4 h-4 text-[#171717]" />
          </div>
          <div className="text-2xl font-normal tracking-tight text-[#171717]">
            Level 1 <span className="text-xs font-mono text-[#7d7d7d] font-normal">/ 0 XP</span>
          </div>
          <div className="w-full bg-[#fafafa] border border-[#ebebeb] h-1.5 rounded-full overflow-hidden">
            <div className="bg-[#171717] h-full rounded-full" style={{ width: '0%' }} />
          </div>
          <p className="text-[11px] text-[#7d7d7d] font-mono">100 XP to Level 2</p>
        </div>

        <div className="p-5 rounded-[6px] border border-[#ebebeb] bg-[#ffffff] space-y-2">
          <div className="flex items-center justify-between text-xs text-[#7d7d7d] font-mono uppercase tracking-wider">
            <span>Active Projects</span>
            <FileCode2 className="w-4 h-4 text-[#171717]" />
          </div>
          <div className="text-2xl font-normal tracking-tight text-[#171717]">0</div>
          <p className="text-[11px] text-[#7d7d7d]">Max 2 simultaneous projects</p>
        </div>

        <div className="p-5 rounded-[6px] border border-[#ebebeb] bg-[#ffffff] space-y-2">
          <div className="flex items-center justify-between text-xs text-[#7d7d7d] font-mono uppercase tracking-wider">
            <span>Verified Proofs</span>
            <Award className="w-4 h-4 text-[#171717]" />
          </div>
          <div className="text-2xl font-normal tracking-tight text-[#171717]">0</div>
          <p className="text-[11px] text-[#7d7d7d]">Live verification enabled</p>
        </div>

        <div className="p-5 rounded-[6px] border border-[#ebebeb] bg-[#ffffff] space-y-2">
          <div className="flex items-center justify-between text-xs text-[#7d7d7d] font-mono uppercase tracking-wider">
            <span>Account Status</span>
            <ShieldCheck className="w-4 h-4 text-[#297a3a]" />
          </div>
          <div className="flex items-center gap-2 pt-1">
            <StatusBadge status="approved" />
          </div>
          <p className="text-[11px] font-mono text-[#7d7d7d]">
            Email: {user?.email_verified ? 'Verified' : 'Pending verification'}
          </p>
        </div>
      </div>

      {/* Main Content Sections */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Active Submissions & Projects */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-medium text-[#171717]">Current Projects</h2>
            <span className="text-xs text-[#7d7d7d] font-mono">0 active</span>
          </div>

          <div className="p-8 rounded-[6px] border border-[#ebebeb] bg-[#ffffff] text-center space-y-3">
            <div className="w-10 h-10 mx-auto rounded-full bg-[#fafafa] border border-[#ebebeb] flex items-center justify-center">
              <Briefcase className="w-5 h-5 text-[#7d7d7d]" />
            </div>
            <div>
              <p className="text-sm font-medium text-[#171717]">No active projects yet</p>
              <p className="text-xs text-[#7d7d7d] mt-1 max-w-sm mx-auto">
                Explore project listings posted by vetted companies. Submit milestone pull requests to earn XP and certificates.
              </p>
            </div>
            <div className="pt-2">
              <Link
                to="/projects"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-[6px] border border-[#ebebeb] text-xs font-medium text-[#171717] hover:bg-[#fafafa] transition-colors"
              >
                Find your first project <ChevronRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>
        </div>

        {/* Sidebar: Profile & Rules */}
        <div className="space-y-6">
          <div className="p-5 rounded-[6px] border border-[#ebebeb] bg-[#ffffff] space-y-4">
            <h3 className="text-xs font-mono uppercase tracking-wider text-[#7d7d7d]">
              Proof Protocol
            </h3>
            <ul className="text-xs text-[#4d4d4d] space-y-3">
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-[#297a3a] shrink-0 mt-0.5" />
                <span>
                  <strong>Live Database Guarantee:</strong> QR codes and public URLs query real-time status with <code className="px-1 py-0.5 rounded bg-[#fafafa] font-mono text-[10px]">no-store</code> caching.
                </span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-[#297a3a] shrink-0 mt-0.5" />
                <span>
                  <strong>Server-Computed XP:</strong> XP and levels follow strict mathematical curves verified on backend transactions.
                </span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-[#297a3a] shrink-0 mt-0.5" />
                <span>
                  <strong>Private by Default:</strong> Student profiles remain invisible to recruiters until explicitly made public by the student.
                </span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};
