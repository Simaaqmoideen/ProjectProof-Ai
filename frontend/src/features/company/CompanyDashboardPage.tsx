import React, { useEffect, useState } from 'react';
import { useAuth } from '../../lib/auth-context';
import { apiRequest } from '../../lib/api';
import { StatusBadge } from '../../components/StatusBadge';
import { CreateProjectModal } from './CreateProjectModal';
import {
  AlertTriangle,
  Building2,
  Calendar,
  CheckCircle2,
  Clock,
  ExternalLink,
  FileCheck,
  Flame,
  FolderPlus,
  Globe,
  Info,
  Mail,
  Send,
  Shield,
  ShieldCheck,
  Users,
  XCircle,
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

interface ProjectSummary {
  id: string;
  title: string;
  category: string;
  difficulty: string;
  duration_days: number;
  xp_max: number;
  max_selected: number;
  status: string;
  created_at: string;
  published_at: string | null;
}

export const CompanyDashboardPage: React.FC = () => {
  const { user } = useAuth();
  const [company, setCompany] = useState<CompanyProfile | null>(null);
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      const compData = await apiRequest<CompanyProfile>('/companies/me');
      setCompany(compData);

      // Fetch company's own projects
      try {
        const projData = await apiRequest<{ items: ProjectSummary[]; total: number }>(
          '/companies/me/projects'
        );
        setProjects(projData.items);
      } catch (e) {
        console.error('Failed to load company projects:', e);
      }
    } catch (err) {
      console.error('Failed to load company profile:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handlePublish = async (projectId: string) => {
    try {
      await apiRequest(`/projects/${projectId}/publish`, { method: 'POST' });
      setActionMessage('Project published successfully and is now open for student applications.');
      fetchData();
    } catch (err: any) {
      alert(err.message || 'Failed to publish project');
    }
  };

  const handleCloseProject = async (projectId: string) => {
    try {
      await apiRequest(`/projects/${projectId}/close`, { method: 'POST' });
      setActionMessage('Project closed for new applications.');
      fetchData();
    } catch (err: any) {
      alert(err.message || 'Failed to close project');
    }
  };

  const isApproved = company?.status === 'approved';
  const isPending = company?.status === 'pending';
  const isSuspended = company?.status === 'suspended';

  const activeProjectsCount = projects.filter((p) => p.status === 'open' || p.status === 'in_progress').length;

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
            onClick={() => setCreateModalOpen(true)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-[6px] text-sm font-medium bg-[#171717] text-[#ffffff] hover:bg-[#000000] transition-colors"
          >
            <FolderPlus className="w-4 h-4" />
            Post New Project
          </button>
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

      {/* Status Alert Banners */}
      {isPending && (
        <div className="p-4 rounded-[6px] border border-[#ebebeb] bg-[#ffffff] flex items-start gap-3">
          <Clock className="w-4 h-4 text-[#7d7d7d] mt-0.5 shrink-0" />
          <div className="text-xs text-[#4d4d4d] space-y-1">
            <p className="font-medium text-[#171717]">Application In Admin Review Queue</p>
            <p>
              Your organization account is undergoing administrative verification. You may draft projects right away, but publishing them to the public catalog requires admin approval (FR-ORG-2).
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
            {company?.trust_score ?? 50} <span className="text-xs font-mono text-[#7d7d7d] font-normal">/ 100</span>
          </div>
          <div className="w-full bg-[#fafafa] border border-[#ebebeb] h-1.5 rounded-full overflow-hidden">
            <div
              className="bg-[#171717] h-full rounded-full"
              style={{ width: `${Math.min(company?.trust_score ?? 50, 100)}%` }}
            />
          </div>
          <p className="text-[11px] text-[#7d7d7d] font-mono">Platform reputation metric (BR-6)</p>
        </div>

        <div className="p-5 rounded-[6px] border border-[#ebebeb] bg-[#ffffff] space-y-2">
          <div className="flex items-center justify-between text-xs text-[#7d7d7d] font-mono uppercase tracking-wider">
            <span>Active Projects</span>
            <Building2 className="w-4 h-4 text-[#171717]" />
          </div>
          <div className="text-2xl font-normal tracking-tight text-[#171717]">
            {activeProjectsCount}
          </div>
          <p className="text-[11px] text-[#7d7d7d]">Open or in-progress listings</p>
        </div>

        <div className="p-5 rounded-[6px] border border-[#ebebeb] bg-[#ffffff] space-y-2">
          <div className="flex items-center justify-between text-xs text-[#7d7d7d] font-mono uppercase tracking-wider">
            <span>Total Projects</span>
            <FolderPlus className="w-4 h-4 text-[#171717]" />
          </div>
          <div className="text-2xl font-normal tracking-tight text-[#171717]">
            {projects.length}
          </div>
          <p className="text-[11px] text-[#7d7d7d]">Drafts, open, and closed</p>
        </div>

        <div className="p-5 rounded-[6px] border border-[#ebebeb] bg-[#ffffff] space-y-2">
          <div className="flex items-center justify-between text-xs text-[#7d7d7d] font-mono uppercase tracking-wider">
            <span>New Company Limit</span>
            <Users className="w-4 h-4 text-[#171717]" />
          </div>
          <div className="text-2xl font-normal tracking-tight text-[#171717]">
            2 Max
          </div>
          <p className="text-[11px] text-[#7d7d7d]">Until 3 evaluations completed (FR-ORG-5)</p>
        </div>
      </div>

      {/* Projects Management Table */}
      <div className="p-6 rounded-[6px] border border-[#ebebeb] bg-[#ffffff] space-y-5">
        <div className="flex items-center justify-between pb-4 border-b border-[#ebebeb]">
          <div>
            <h2 className="text-base font-medium text-[#171717]">Posted Engineering Projects</h2>
            <p className="text-xs text-[#7d7d7d] mt-0.5">
              Manage project lifecycle from draft to publishing, candidate selection, and review.
            </p>
          </div>
          <button
            onClick={() => setCreateModalOpen(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-[4px] bg-[#171717] text-[#ffffff] text-xs font-medium hover:bg-[#000000]"
          >
            <FolderPlus className="w-3.5 h-3.5" /> New Project Draft
          </button>
        </div>

        {projects.length === 0 ? (
          <div className="py-12 text-center text-xs text-[#7d7d7d] space-y-2">
            <Building2 className="w-8 h-8 text-[#a8a8a8] mx-auto" />
            <p>No projects authored yet. Create your first challenge draft to recruit talent.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-[#ebebeb] bg-[#fafafa] font-mono text-[#7d7d7d] uppercase text-[11px]">
                <tr>
                  <th className="py-2.5 px-3">Project Title</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Difficulty</th>
                  <th className="py-2.5 px-3">Duration</th>
                  <th className="py-2.5 px-3">XP Max</th>
                  <th className="py-2.5 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#ebebeb]">
                {projects.map((p) => (
                  <tr key={p.id} className="hover:bg-[#fafafa] transition-colors">
                    <td className="py-3 px-3 font-medium text-[#171717]">
                      <div>{p.title}</div>
                      <span className="text-[10px] font-mono text-[#7d7d7d] capitalize">
                        {p.category}
                      </span>
                    </td>
                    <td className="py-3 px-3">
                      <StatusBadge status={p.status} />
                    </td>
                    <td className="py-3 px-3 capitalize font-mono text-[#4d4d4d]">
                      {p.difficulty}
                    </td>
                    <td className="py-3 px-3 font-mono text-[#7d7d7d]">
                      {p.duration_days} days
                    </td>
                    <td className="py-3 px-3 font-mono text-[#171717] font-medium">
                      +{p.xp_max} XP
                    </td>
                    <td className="py-3 px-3 text-right space-x-2">
                      {p.status === 'draft' && (
                        <button
                          onClick={() => handlePublish(p.id)}
                          className="px-2.5 py-1 rounded-[4px] bg-[#171717] text-[#ffffff] font-medium hover:bg-[#000000]"
                        >
                          Publish (FR-PRJ-3)
                        </button>
                      )}
                      {(p.status === 'open' || p.status === 'in_progress') && (
                        <Link
                          to={`/company/projects/${p.id}/applicants`}
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-[4px] border border-[#ebebeb] bg-[#ffffff] font-medium text-[#171717] hover:bg-[#fafafa]"
                        >
                          <Users className="w-3 h-3" /> Review Applicants (FR-APP-4)
                        </Link>
                      )}
                      {p.status === 'open' && (
                        <button
                          onClick={() => handleCloseProject(p.id)}
                          className="px-2.5 py-1 rounded-[4px] border border-[#ebebeb] text-[#7d7d7d] hover:text-[#ff4d4f]"
                        >
                          Close
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Organization Verification Details */}
      <div className="p-6 rounded-[6px] border border-[#ebebeb] bg-[#ffffff] space-y-5">
        <h2 className="text-base font-medium text-[#171717]">Organization Profile & Credentials</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
          <div className="p-3 rounded-[6px] bg-[#fafafa] border border-[#ebebeb] space-y-1">
            <span className="text-[#7d7d7d] font-mono uppercase">Verified Work Domain</span>
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
        </div>
      </div>

      {/* Create Project Modal */}
      <CreateProjectModal
        isOpen={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        onSuccess={() => {
          setActionMessage('Project draft created successfully.');
          fetchData();
        }}
      />
    </div>
  );
};
