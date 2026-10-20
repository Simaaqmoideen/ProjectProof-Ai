import React, { useEffect, useState } from 'react';
import { useAuth } from '../../lib/auth-context';
import { apiRequest } from '../../lib/api';
import { StatusBadge } from '../../components/StatusBadge';
import {
  AlertCircle,
  Award,
  Briefcase,
  CheckCircle2,
  ChevronRight,
  Clock,
  ExternalLink,
  FileCode2,
  Flame,
  Info,
  ShieldCheck,
  Sparkles,
  XCircle,
  Zap,
} from 'lucide-react';
import { Link } from 'react-router-dom';

interface StudentApplication {
  id: string;
  project_id: string;
  status: string;
  match_score: number | null;
  applied_at: string;
  status_reason: string | null;
  project?: {
    id: string;
    title: string;
    difficulty: string;
    duration_days: number;
    xp_max: number;
    company: {
      name: string;
    };
  } | null;
}

interface RecommendedItem {
  project: {
    id: string;
    title: string;
    difficulty: string;
    duration_days: number;
    xp_max: number;
    company: {
      name: string;
    };
  };
  recommendation_score: number;
  match_score: number;
  reason: string;
}

export const StudentDashboardPage: React.FC = () => {
  const { user } = useAuth();
  const [applications, setApplications] = useState<StudentApplication[]>([]);
  const [recommended, setRecommended] = useState<RecommendedItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      if (user?.email_verified) {
        // Fetch own applications
        try {
          const appsData = await apiRequest<{ items: StudentApplication[]; total: number }>(
            '/applications/me'
          );
          setApplications(appsData.items);
        } catch (e) {
          console.error('Failed to load applications:', e);
        }

        // Fetch recommendations
        try {
          const recData = await apiRequest<{ items?: RecommendedItem[] } | RecommendedItem[]>(
            '/projects/recommended/list'
          );
          const list = Array.isArray(recData) ? recData : recData.items || [];
          setRecommended(list.slice(0, 3));
        } catch (e) {
          console.error('Failed to load recommendations:', e);
        }
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [user]);

  const handleWithdraw = async (applicationId: string) => {
    if (!window.confirm('Are you sure you want to withdraw this application?')) return;
    try {
      await apiRequest(`/applications/${applicationId}/withdraw`, { method: 'POST' });
      setActionMessage('Application withdrawn successfully.');
      fetchData();
    } catch (err: any) {
      alert(err.message || 'Failed to withdraw application');
    }
  };

  const activeAppsCount = applications.filter(
    (a) => a.status === 'applied' || a.status === 'in_progress'
  ).length;

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

      {actionMessage && (
        <div className="p-3 rounded-[6px] border border-[#297a3a]/30 bg-[#297a3a]/5 text-xs text-[#297a3a] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{actionMessage}</span>
          </div>
          <button onClick={() => setActionMessage(null)} className="text-xs underline">
            Dismiss
          </button>
        </div>
      )}

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
          <p className="text-[11px] text-[#7d7d7d] font-mono">100 XP to Level 2 (BR-8)</p>
        </div>

        <div className="p-5 rounded-[6px] border border-[#ebebeb] bg-[#ffffff] space-y-2">
          <div className="flex items-center justify-between text-xs text-[#7d7d7d] font-mono uppercase tracking-wider">
            <span>Active Projects</span>
            <FileCode2 className="w-4 h-4 text-[#171717]" />
          </div>
          <div className="text-2xl font-normal tracking-tight text-[#171717]">
            {activeAppsCount}
          </div>
          <p className="text-[11px] text-[#7d7d7d]">Max 3 active applications (FR-APP-1)</p>
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

      {/* Recommended Projects Row (FR-APP-10, BR-10) */}
      {recommended.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Zap className="w-4 h-4 text-[#297a3a]" />
              <h2 className="text-sm font-medium text-[#171717] font-mono uppercase tracking-wider">
                Recommended Challenges For Your Profile
              </h2>
            </div>
            <Link to="/projects" className="text-xs font-mono text-[#7d7d7d] hover:underline">
              View Catalog &rarr;
            </Link>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {recommended.map((rec) => (
              <div
                key={`rec-dash-${rec.project.id}`}
                className="p-4 rounded-[6px] border border-[#ebebeb] bg-[#ffffff] hover:border-[#171717] transition-all flex flex-col justify-between space-y-3"
              >
                <div>
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="font-mono text-[#297a3a] font-medium">
                      Score {rec.recommendation_score}
                    </span>
                    <span className="font-mono text-[#7d7d7d]">
                      {rec.match_score}% Match
                    </span>
                  </div>
                  <h3 className="text-sm font-medium text-[#171717] line-clamp-1">
                    {rec.project.title}
                  </h3>
                  <div className="text-[11px] text-[#7d7d7d] font-mono mt-0.5">
                    {rec.project.company.name} • {rec.project.difficulty}
                  </div>
                  <p className="text-xs text-[#4d4d4d] mt-2 line-clamp-2">
                    {rec.reason}
                  </p>
                </div>
                <div className="pt-2 border-t border-[#ebebeb] flex items-center justify-between">
                  <span className="text-xs font-mono text-[#171717] font-medium">
                    +{rec.project.xp_max} XP
                  </span>
                  <Link
                    to={`/projects/${rec.project.id}`}
                    className="text-xs font-medium text-[#171717] hover:underline inline-flex items-center gap-0.5"
                  >
                    View & Apply &rarr;
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Student Applications Table (FR-APP-2, FR-APP-3) */}
      <div className="p-6 rounded-[6px] border border-[#ebebeb] bg-[#ffffff] space-y-5">
        <div className="flex items-center justify-between pb-4 border-b border-[#ebebeb]">
          <div>
            <h2 className="text-base font-medium text-[#171717]">My Project Applications</h2>
            <p className="text-xs text-[#7d7d7d] mt-0.5">
              Track review status, company selections, and active development milestones.
            </p>
          </div>
          <Link
            to="/projects"
            className="text-xs font-mono text-[#171717] hover:underline"
          >
            Apply to New Project &rarr;
          </Link>
        </div>

        {applications.length === 0 ? (
          <div className="py-12 text-center text-xs text-[#7d7d7d] space-y-2">
            <FileCode2 className="w-8 h-8 text-[#a8a8a8] mx-auto" />
            <p>You have not applied to any projects yet.</p>
            <Link
              to="/projects"
              className="inline-block mt-2 px-3 py-1.5 rounded-[4px] bg-[#171717] text-[#ffffff] text-xs font-medium"
            >
              Browse Open Catalog
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-[#ebebeb] bg-[#fafafa] font-mono text-[#7d7d7d] uppercase text-[11px]">
                <tr>
                  <th className="py-2.5 px-3">Project & Organization</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Match Score</th>
                  <th className="py-2.5 px-3">Applied Date</th>
                  <th className="py-2.5 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#ebebeb]">
                {applications.map((app) => (
                  <tr key={app.id} className="hover:bg-[#fafafa] transition-colors">
                    <td className="py-3 px-3 font-medium text-[#171717]">
                      {app.project ? (
                        <Link to={`/projects/${app.project.id}`} className="hover:underline">
                          {app.project.title}
                        </Link>
                      ) : (
                        'Project'
                      )}
                      <div className="text-[11px] font-mono text-[#7d7d7d]">
                        {app.project?.company.name || 'Company'} • {app.project?.difficulty || 'Standard'}
                      </div>
                    </td>
                    <td className="py-3 px-3">
                      <StatusBadge status={app.status} />
                    </td>
                    <td className="py-3 px-3 font-mono">
                      {app.match_score !== null ? (
                        <span className="text-[#297a3a] font-medium">
                          {app.match_score}%
                        </span>
                      ) : (
                        <span className="text-[#7d7d7d]">—</span>
                      )}
                    </td>
                    <td className="py-3 px-3 font-mono text-[#7d7d7d]">
                      {new Date(app.applied_at).toLocaleDateString()}
                    </td>
                    <td className="py-3 px-3 text-right space-x-2">
                      {app.status === 'applied' && (
                        <button
                          onClick={() => handleWithdraw(app.id)}
                          className="px-2.5 py-1 rounded-[4px] border border-[#ebebeb] text-[#ff4d4f] hover:bg-[#fafafa] text-xs font-medium"
                          title="Withdraw application before selection (FR-APP-2)"
                        >
                          Withdraw
                        </button>
                      )}
                      {(app.status === 'in_progress' || app.status === 'changes_requested') && (
                        <Link
                          to={`/student/applications/${app.id}/workspace`}
                          className="px-2.5 py-1 rounded-[4px] text-xs font-mono font-medium inline-flex items-center gap-1 transition-colors"
                          style={{ background: '#171717', color: '#ffffff' }}
                        >
                          Open Workspace →
                        </Link>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
