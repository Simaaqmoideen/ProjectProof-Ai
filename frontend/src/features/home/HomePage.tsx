import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../lib/auth-context';
import { ArrowRight, Check, CheckCircle2, ShieldCheck, Terminal } from 'lucide-react';

export const HomePage: React.FC = () => {
  const { user } = useAuth();

  return (
    <div className="bg-[#fafafa] min-h-[calc(100vh-3.5rem)] text-[#171717]">
      {/* Hero Section */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-20 pb-16 lg:pt-28 lg:pb-24">
        <div className="max-w-4xl space-y-8">
          {/* Eyebrow */}
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-[6px] border border-[#ebebeb] bg-[#ffffff] text-xs font-mono tracking-wider uppercase text-[#171717]">
            <span className="text-[#171717] font-black">▲</span>
            <span>Proof of Project Execution</span>
          </div>

          {/* Headline */}
          <h1 className="text-4xl sm:text-6xl lg:text-7xl font-normal tracking-[-0.05em] leading-[1.05] text-[#171717]">
            Work with verified companies.
            <br />
            <span className="text-[#7d7d7d]">Prove it with cryptography.</span>
          </h1>

          {/* Subtitle */}
          <p className="text-lg sm:text-xl text-[#4d4d4d] max-w-2xl leading-relaxed font-normal">
            ProjectProof AI connects approved organizations with engineering students to build real software deliverables. Every completion produces a live, tamper-evident cryptographic certificate.
          </p>

          {/* CTA Cluster */}
          <div className="flex flex-wrap items-center gap-4 pt-4">
            {user ? (
              <Link
                to={
                  user.role === 'admin'
                    ? '/admin/approvals'
                    : user.role === 'company'
                    ? '/company'
                    : user.role === 'recruiter'
                    ? '/recruiter'
                    : '/student'
                }
                className="inline-flex items-center gap-2 px-6 py-3 rounded-[6px] bg-[#171717] text-[#ffffff] text-sm font-medium hover:bg-[#000000] transition-colors"
              >
                Go to Workspace <ArrowRight className="w-4 h-4" />
              </Link>
            ) : (
              <>
                <Link
                  to="/register"
                  className="inline-flex items-center gap-2 px-6 py-3 rounded-[6px] bg-[#171717] text-[#ffffff] text-sm font-medium hover:bg-[#000000] transition-colors"
                >
                  Create Free Account <ArrowRight className="w-4 h-4" />
                </Link>
                <Link
                  to="/login"
                  className="inline-flex items-center gap-2 px-6 py-3 rounded-[6px] border border-[#ebebeb] bg-[#ffffff] text-sm font-medium text-[#4d4d4d] hover:text-[#171717] hover:bg-[#fafafa] transition-colors"
                >
                  Sign In
                </Link>
              </>
            )}
          </div>
        </div>

        {/* CLI Terminal Output Demonstration */}
        <div className="mt-16 rounded-[6px] border border-[#ebebeb] bg-[#ffffff] p-6 shadow-sm max-w-3xl font-mono text-xs text-[#171717] space-y-2">
          <div className="flex items-center justify-between pb-3 border-b border-[#ebebeb] text-[#7d7d7d]">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-[#ebebeb]" />
              <span className="w-2.5 h-2.5 rounded-full bg-[#ebebeb]" />
              <span className="w-2.5 h-2.5 rounded-full bg-[#ebebeb]" />
              <span className="ml-2 font-mono text-[11px] uppercase tracking-wider text-[#7d7d7d]">
                Live Verification Protocol
              </span>
            </div>
            <span className="text-[10px] text-[#297a3a] flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-[#297a3a]" /> no-store
            </span>
          </div>
          <div className="pt-2 text-[#4d4d4d]">
            <span className="text-[#171717] font-semibold">▲</span> curl -s -H "Cache-Control: no-store" https://projectproof.ai/verify/CRT-2026-F4B2
          </div>
          <div className="text-[#297a3a] flex items-center gap-2">
            <Check className="w-3.5 h-3.5" /> status: VERIFIED (live ledger read)
          </div>
          <div className="text-[#4d4d4d] pl-5">
            candidate: Alex Chen · XP Awarded: 450 · Role: Lead Fullstack
          </div>
          <div className="text-[#4d4d4d] pl-5">
            issuing_org: Nova Labs (Approved Company, Trust Score: 100/100)
          </div>
          <div className="text-[#7d7d7d] pl-5 pt-1 text-[11px]">
            Platform Notice: "A certificate is a platform record, not formal employment experience."
          </div>
        </div>
      </section>

      {/* Triad Architecture Section */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 border-t border-[#ebebeb]">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Students */}
          <div className="p-6 rounded-[6px] border border-[#ebebeb] bg-[#ffffff] space-y-3">
            <span className="font-mono text-[11px] uppercase tracking-wider text-[#7d7d7d]">
              For Engineers & Students
            </span>
            <h3 className="text-xl font-normal text-[#171717] tracking-tight">
              Real Work, Cryptographic Proof
            </h3>
            <p className="text-xs text-[#4d4d4d] leading-relaxed">
              Work on approved company scopes. Submissions are reviewed by verified company maintainers and validated against rigorous criteria.
            </p>
          </div>

          {/* Companies */}
          <div className="p-6 rounded-[6px] border border-[#ebebeb] bg-[#ffffff] space-y-3">
            <span className="font-mono text-[11px] uppercase tracking-wider text-[#7d7d7d]">
              For Approved Companies
            </span>
            <h3 className="text-xl font-normal text-[#171717] tracking-tight">
              Automated Trust & Verification
            </h3>
            <p className="text-xs text-[#4d4d4d] leading-relaxed">
              Post real projects to vetted candidates. Automated domain validation and admin vetting safeguard your intellectual property and reputation.
            </p>
          </div>

          {/* Recruiters */}
          <div className="p-6 rounded-[6px] border border-[#ebebeb] bg-[#ffffff] space-y-3">
            <span className="font-mono text-[11px] uppercase tracking-wider text-[#7d7d7d]">
              For Verified Recruiters
            </span>
            <h3 className="text-xl font-normal text-[#171717] tracking-tight">
              Live Database Validation
            </h3>
            <p className="text-xs text-[#4d4d4d] leading-relaxed">
              No embellished resumes or fake credentials. Look up candidate certificate IDs directly on the live database view with zero client-side caching.
            </p>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-[#ebebeb] py-8 text-center text-xs text-[#7d7d7d] font-mono space-y-2">
        <p>ProjectProof AI · Production Architecture Phase 1</p>
        <p className="text-[11px] text-[#8f8f8f]">
          Strict Server Rules · Live Database Verification · Privacy by Default
        </p>
      </footer>
    </div>
  );
};
