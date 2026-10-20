import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiRequest, ApiException } from '../../lib/api';
import { StatusBadge } from '../../components/StatusBadge';
import { ApplicantComparisonModal } from './ApplicantComparisonModal';
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  ChevronRight,
  Clock,
  Columns,
  ExternalLink,
  Flame,
  Info,
  ShieldAlert,
  UserCheck,
  UserX,
  Users,
  XCircle,
  Zap,
} from 'lucide-react';

interface StudentInfo {
  user_id: string;
  full_name: string;
  headline: string | null;
  college: string | null;
  graduation_year: number | null;
  github_username: string | null;
  verified_projects_count: number;
  xp: number;
}

interface ApplicationItem {
  id: string;
  project_id: string;
  student_id: string;
  status: string;
  cover_note: string | null;
  match_score: number | null;
  match_breakdown: {
    skill_match: number;
    level_alignment: number;
    coursework_overlap: number;
    category_alignment: number;
  } | null;
  applied_at: string;
  decided_at: string | null;
  status_reason: string | null;
  started_at: string | null;
  due_at: string | null;
  student: StudentInfo | null;
}

export const CompanyApplicantsPage: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const [applications, setApplications] = useState<ApplicationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Comparison Modal
  const [comparisonOpen, setComparisonOpen] = useState(false);

  // Reject Modal State
  const [rejectingAppId, setRejectingAppId] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState('');
  const [isRejecting, setIsRejecting] = useState(false);

  const fetchApplications = async () => {
    if (!projectId) return;
    setLoading(true);
    try {
      const data = await apiRequest<{ items: ApplicationItem[]; total: number }>(
        `/projects/${projectId}/applications`
      );
      setApplications(data.items);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch applicants');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchApplications();
  }, [projectId]);

  const handleSelect = async (applicationId: string) => {
    try {
      await apiRequest(`/applications/${applicationId}/select`, { method: 'POST' });
      setActionSuccess('Applicant selected! Application is now in_progress.');
      fetchApplications();
    } catch (err: any) {
      alert(err.message || 'Failed to select applicant');
    }
  };

  const handleRejectSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rejectingAppId) return;
    setIsRejecting(true);
    try {
      await apiRequest(`/applications/${rejectingAppId}/reject`, {
        method: 'POST',
        body: JSON.stringify({ reason: rejectReason.trim() || null }),
      });
      setActionSuccess('Application rejected.');
      setRejectingAppId(null);
      setRejectReason('');
      fetchApplications();
    } catch (err: any) {
      alert(err.message || 'Failed to reject applicant');
    } finally {
      setIsRejecting(false);
    }
  };

  const appliedCount = applications.filter((a) => a.status === 'applied').length;
  const inProgressCount = applications.filter((a) => a.status === 'in_progress').length;

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Breadcrumb */}
      <div>
        <Link
          to="/company"
          className="inline-flex items-center gap-1.5 text-xs font-mono text-[#7d7d7d] hover:text-[#171717] transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Company Workspace
        </Link>
      </div>

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-6 border-b border-[#ebebeb]">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="font-mono text-[11px] tracking-wider uppercase text-[#7d7d7d]">
              Applicant Review Queue (FR-APP-4)
            </span>
            <span className="text-[#ebebeb]">•</span>
            <span className="font-mono text-[11px] text-[#297a3a] flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-[#297a3a]" /> Live Ledger
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-normal text-[#171717] tracking-tight">
            Review Candidate Submissions
          </h1>
          <p className="mt-1 text-sm text-[#4d4d4d]">
            Inspect deterministic match scores, review candidate credentials, and select engineers to begin work.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setComparisonOpen(true)}
            disabled={appliedCount < 1}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-[6px] border border-[#ebebeb] bg-[#ffffff] text-xs font-medium text-[#171717] hover:bg-[#fafafa] disabled:text-[#8f8f8f] disabled:cursor-not-allowed shadow-sm transition-colors"
          >
            <Columns className="w-4 h-4" />
            Compare Side-by-Side (FR-APP-7)
          </button>
        </div>
      </div>

      {actionSuccess && (
        <div className="p-3 rounded-[6px] border border-[#297a3a]/30 bg-[#297a3a]/5 text-xs text-[#297a3a] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{actionSuccess}</span>
          </div>
          <button onClick={() => setActionSuccess(null)} className="text-xs underline">
            Dismiss
          </button>
        </div>
      )}

      {/* Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="p-4 rounded-[6px] border border-[#ebebeb] bg-[#ffffff] space-y-1">
          <div className="text-xs font-mono text-[#7d7d7d] uppercase">Total Applicants</div>
          <div className="text-2xl font-normal text-[#171717]">{applications.length}</div>
        </div>
        <div className="p-4 rounded-[6px] border border-[#ebebeb] bg-[#ffffff] space-y-1">
          <div className="text-xs font-mono text-[#7d7d7d] uppercase">Pending Review</div>
          <div className="text-2xl font-normal text-[#171717]">{appliedCount}</div>
        </div>
        <div className="p-4 rounded-[6px] border border-[#ebebeb] bg-[#ffffff] space-y-1">
          <div className="text-xs font-mono text-[#7d7d7d] uppercase">Selected (In Progress)</div>
          <div className="text-2xl font-normal text-[#297a3a]">{inProgressCount}</div>
        </div>
      </div>

      {/* Applicants List */}
      <div className="space-y-4">
        <h2 className="text-base font-medium text-[#171717]">Applicant Roster</h2>

        {loading ? (
          <div className="py-16 text-center">
            <span className="font-mono text-xs text-[#7d7d7d] animate-pulse">
              Retrieving applicant records...
            </span>
          </div>
        ) : applications.length === 0 ? (
          <div className="p-12 text-center rounded-[6px] border border-[#ebebeb] bg-[#ffffff] space-y-3">
            <Users className="w-8 h-8 text-[#a8a8a8] mx-auto" />
            <h3 className="text-sm font-medium text-[#171717]">No applications received yet</h3>
            <p className="text-xs text-[#7d7d7d] max-w-sm mx-auto">
              Once students discover this project in the public catalog, their applications with verified credentials will populate here.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {applications.map((app) => (
              <div
                key={app.id}
                className="p-5 rounded-[6px] border border-[#ebebeb] bg-[#ffffff] hover:border-[#171717] transition-all space-y-4"
              >
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                  {/* Student Summary */}
                  <div className="space-y-1.5">
                    <div className="flex items-center gap-3">
                      <h3 className="text-base font-medium text-[#171717]">
                        {app.student?.full_name || 'Anonymous Student'}
                      </h3>
                      <StatusBadge status={app.status} />
                      {app.match_score !== null && (
                        <span
                          className="px-2 py-0.5 rounded-[4px] bg-[#297a3a]/10 text-[#297a3a] text-xs font-mono font-medium flex items-center gap-1"
                          title="Deterministic match score calculated on application (BR-3)"
                        >
                          <Zap className="w-3 h-3" /> {app.match_score}% Match
                        </span>
                      )}
                    </div>

                    <div className="text-xs text-[#4d4d4d]">
                      {app.student?.headline || 'Undergraduate Engineer'}
                    </div>

                    <div className="flex items-center gap-4 text-xs font-mono text-[#7d7d7d] pt-1">
                      <span>{app.student?.college || 'University'}</span>
                      <span>•</span>
                      <span>Class of {app.student?.graduation_year || 'N/A'}</span>
                      <span>•</span>
                      <span className="flex items-center gap-1 text-[#171717]">
                        <Flame className="w-3 h-3 text-[#171717]" />
                        {app.student?.xp || 0} XP
                      </span>
                      <span>•</span>
                      <span>{app.student?.verified_projects_count || 0} Verified Projects</span>
                    </div>
                  </div>

                  {/* Actions for Company */}
                  <div className="flex items-center gap-2 shrink-0">
                    {app.status === 'applied' && (
                      <>
                        <button
                          onClick={() => handleSelect(app.id)}
                          className="px-3 py-1.5 rounded-[4px] bg-[#171717] text-[#ffffff] text-xs font-medium hover:bg-[#000000] transition-colors"
                        >
                          Select (FR-APP-5)
                        </button>
                        <button
                          onClick={() => setRejectingAppId(app.id)}
                          className="px-3 py-1.5 rounded-[4px] border border-[#ebebeb] text-[#ff4d4f] text-xs font-medium hover:bg-[#fafafa] transition-colors"
                        >
                          Reject
                        </button>
                      </>
                    )}
                    {app.status === 'in_progress' && (
                      <span className="text-xs font-mono text-[#297a3a] flex items-center gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5" /> In Progress (Selected)
                      </span>
                    )}
                    {app.status === 'rejected' && (
                      <span className="text-xs font-mono text-[#7d7d7d]">
                        Rejected {app.status_reason ? `(${app.status_reason})` : ''}
                      </span>
                    )}
                  </div>
                </div>

                {/* Match Score Breakdown Bar */}
                {app.match_breakdown && (
                  <div className="p-3 rounded-[4px] bg-[#fafafa] border border-[#ebebeb] grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] font-mono">
                    <div>
                      <span className="text-[#7d7d7d]">Skills:</span>{' '}
                      <span className="text-[#171717] font-medium">
                        {app.match_breakdown.skill_match}%
                      </span>
                    </div>
                    <div>
                      <span className="text-[#7d7d7d]">Level:</span>{' '}
                      <span className="text-[#171717] font-medium">
                        {app.match_breakdown.level_alignment}%
                      </span>
                    </div>
                    <div>
                      <span className="text-[#7d7d7d]">Coursework:</span>{' '}
                      <span className="text-[#171717] font-medium">
                        {app.match_breakdown.coursework_overlap}%
                      </span>
                    </div>
                    <div>
                      <span className="text-[#7d7d7d]">Category:</span>{' '}
                      <span className="text-[#171717] font-medium">
                        {app.match_breakdown.category_alignment}%
                      </span>
                    </div>
                  </div>
                )}

                {/* Cover Note */}
                {app.cover_note && (
                  <div className="pt-2 border-t border-[#ebebeb] text-xs space-y-1">
                    <span className="font-mono text-[11px] text-[#7d7d7d] uppercase">
                      Candidate Statement:
                    </span>
                    <p className="text-[#4d4d4d] italic">"{app.cover_note}"</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Comparison Modal */}
      {projectId && (
        <ApplicantComparisonModal
          isOpen={comparisonOpen}
          projectId={projectId}
          onClose={() => setComparisonOpen(false)}
          onSelectApplicant={handleSelect}
        />
      )}

      {/* Reject Reason Modal */}
      {rejectingAppId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#000000]/40 backdrop-blur-sm">
          <div className="w-full max-w-md bg-[#ffffff] rounded-[6px] border border-[#ebebeb] p-6 shadow-xl space-y-4">
            <h3 className="text-base font-medium text-[#171717]">Reject Application (FR-APP-6)</h3>
            <p className="text-xs text-[#7d7d7d]">
              Provide an optional reason or feedback for the student explaining why this application was not selected.
            </p>
            <form onSubmit={handleRejectSubmit} className="space-y-4">
              <textarea
                rows={3}
                placeholder="Reason (optional, e.g. role filled, skill prerequisites)..."
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                maxLength={500}
                className="w-full p-2.5 text-xs rounded-[4px] border border-[#ebebeb] bg-[#fafafa] text-[#171717] focus:outline-none focus:border-[#171717]"
              />
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setRejectingAppId(null)}
                  className="px-3 py-1.5 rounded-[4px] border border-[#ebebeb] text-xs font-medium text-[#4d4d4d]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isRejecting}
                  className="px-3 py-1.5 rounded-[4px] bg-[#ff4d4f] text-[#ffffff] text-xs font-medium hover:bg-[#d9363e]"
                >
                  {isRejecting ? 'Rejecting...' : 'Confirm Rejection'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
