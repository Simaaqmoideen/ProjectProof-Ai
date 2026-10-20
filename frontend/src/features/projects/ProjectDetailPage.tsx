import React, { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../lib/auth-context';
import { apiRequest, ApiException } from '../../lib/api';
import { StatusBadge } from '../../components/StatusBadge';
import {
  AlertCircle,
  ArrowLeft,
  Building2,
  Calendar,
  CheckCircle2,
  Clock,
  ExternalLink,
  Flame,
  Info,
  Layers,
  Send,
  ShieldCheck,
  UserCheck,
} from 'lucide-react';

interface Task {
  id: string;
  position: number;
  title: string;
  description: string | null;
}

interface Milestone {
  id: string;
  position: number;
  title: string;
  description: string | null;
  due_day_offset: number;
  tasks: Task[];
}

interface ProjectDetail {
  id: string;
  title: string;
  description: string;
  category: string;
  difficulty: string;
  duration_days: number;
  xp_max: number;
  max_selected: number;
  status: string;
  application_deadline: string | null;
  published_at: string | null;
  company: {
    id: string;
    name: string;
    website: string | null;
    status: string;
    trust_score: number;
  };
  skills: string[];
  milestones: Milestone[];
  created_at: string;
  match?: {
    score: number;
    breakdown: {
      skill_match: number;
      level_alignment: number;
      coursework_overlap: number;
      category_alignment: number;
    };
  } | null;
}

export const ProjectDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();

  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Application Form State
  const [coverNote, setCoverNote] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [applySuccess, setApplySuccess] = useState(false);
  const [applyError, setApplyError] = useState<string | null>(null);

  useEffect(() => {
    const fetchDetail = async () => {
      try {
        const data = await apiRequest<ProjectDetail>(`/projects/${id}`);
        setProject(data);
      } catch (err: any) {
        setError(err.message || 'Failed to load project');
      } finally {
        setLoading(false);
      }
    };
    if (id) fetchDetail();
  }, [id]);

  const handleApply = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id) return;
    setSubmitting(true);
    setApplyError(null);

    try {
      await apiRequest(`/projects/${id}/applications`, {
        method: 'POST',
        body: JSON.stringify({ cover_note: coverNote.trim() || null }),
      });
      setApplySuccess(true);
    } catch (err: any) {
      if (err instanceof ApiException) {
        setApplyError(err.message);
      } else {
        setApplyError(err.message || 'Failed to submit application');
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-16 text-center">
        <span className="font-mono text-xs text-[#7d7d7d] animate-pulse">Loading project details...</span>
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-16 text-center space-y-4">
        <AlertCircle className="w-8 h-8 text-[#7d7d7d] mx-auto" />
        <h2 className="text-lg font-medium text-[#171717]">Project not found or unavailable</h2>
        <p className="text-xs text-[#7d7d7d]">{error || 'This project does not exist or is not public.'}</p>
        <Link
          to="/projects"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-[6px] bg-[#171717] text-[#ffffff] text-xs font-medium"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Project Catalog
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Navigation Breadcrumb */}
      <div>
        <Link
          to="/projects"
          className="inline-flex items-center gap-1.5 text-xs font-mono text-[#7d7d7d] hover:text-[#171717] transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Projects
        </Link>
      </div>

      {/* Main Header Card */}
      <div className="p-6 rounded-[6px] border border-[#ebebeb] bg-[#ffffff] space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 pb-6 border-b border-[#ebebeb]">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs text-[#7d7d7d] uppercase tracking-wider">
                {project.category}
              </span>
              <span className="text-[#ebebeb]">•</span>
              <span className="font-mono text-xs text-[#4d4d4d] capitalize">
                {project.difficulty}
              </span>
              <span className="text-[#ebebeb]">•</span>
              <StatusBadge status={project.status} />
            </div>

            <h1 className="text-2xl sm:text-3xl font-normal text-[#171717] tracking-tight">
              {project.title}
            </h1>

            <div className="flex items-center gap-2 text-xs text-[#4d4d4d] pt-1">
              <Building2 className="w-4 h-4 text-[#7d7d7d]" />
              <span className="font-medium text-[#171717]">{project.company.name}</span>
              {project.company.website && (
                <a
                  href={project.company.website}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[#7d7d7d] hover:text-[#171717] inline-flex items-center gap-0.5"
                >
                  <ExternalLink className="w-3 h-3" />
                </a>
              )}
              <span className="text-[#ebebeb]">•</span>
              <span className="font-mono text-[#7d7d7d]" title="Company Trust Score">
                Trust Score: {project.company.trust_score}
              </span>
            </div>
          </div>

          <div className="flex sm:flex-col items-center sm:items-end justify-between sm:justify-start gap-2 bg-[#fafafa] p-4 rounded-[6px] border border-[#ebebeb] shrink-0">
            <div className="text-left sm:text-right">
              <div className="text-[11px] font-mono text-[#7d7d7d] uppercase tracking-wider">
                XP Reward
              </div>
              <div className="text-xl font-medium text-[#171717] flex items-center sm:justify-end gap-1">
                <Flame className="w-4 h-4 text-[#171717]" />
                +{project.xp_max} XP
              </div>
            </div>
            <div className="text-[11px] font-mono text-[#7d7d7d] text-left sm:text-right pt-1 border-t sm:border-t-0 sm:pt-0 border-[#ebebeb]">
              {project.duration_days} Days Expected
            </div>
          </div>
        </div>

        {/* Project Match Score Banner (Student Only) */}
        {user?.role === 'student' && project.match && (
          <div className="p-4 rounded-[6px] border border-[#297a3a]/30 bg-[#297a3a]/5 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-[#297a3a]" />
                <span className="text-xs font-mono font-medium text-[#297a3a] uppercase tracking-wider">
                  Deterministic Match Score (BR-3)
                </span>
              </div>
              <span className="text-lg font-mono font-medium text-[#297a3a]">
                {project.match.score}%
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-[#297a3a]/20 text-[11px] font-mono">
              <div>
                <span className="text-[#7d7d7d]">Skills (40%):</span>{' '}
                <span className="text-[#171717] font-medium">{project.match.breakdown.skill_match}%</span>
              </div>
              <div>
                <span className="text-[#7d7d7d]">Level (25%):</span>{' '}
                <span className="text-[#171717] font-medium">{project.match.breakdown.level_alignment}%</span>
              </div>
              <div>
                <span className="text-[#7d7d7d]">Coursework (20%):</span>{' '}
                <span className="text-[#171717] font-medium">{project.match.breakdown.coursework_overlap}%</span>
              </div>
              <div>
                <span className="text-[#7d7d7d]">Category (15%):</span>{' '}
                <span className="text-[#171717] font-medium">{project.match.breakdown.category_alignment}%</span>
              </div>
            </div>
          </div>
        )}

        {/* Description */}
        <div className="space-y-2">
          <h2 className="text-xs font-mono uppercase tracking-wider text-[#7d7d7d]">
            Project Overview & Scope
          </h2>
          <div className="text-sm text-[#4d4d4d] leading-relaxed whitespace-pre-wrap">
            {project.description}
          </div>
        </div>

        {/* Required Skills */}
        {project.skills.length > 0 && (
          <div className="space-y-2">
            <h2 className="text-xs font-mono uppercase tracking-wider text-[#7d7d7d]">
              Target Technologies & Competencies
            </h2>
            <div className="flex flex-wrap gap-2">
              {project.skills.map((skill) => (
                <span
                  key={skill}
                  className="px-2.5 py-1 rounded-[4px] bg-[#fafafa] border border-[#ebebeb] text-xs font-mono text-[#171717]"
                >
                  {skill}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Milestones & Deliverables Roadmap */}
      <div className="p-6 rounded-[6px] border border-[#ebebeb] bg-[#ffffff] space-y-6">
        <div className="flex items-center justify-between pb-4 border-b border-[#ebebeb]">
          <div>
            <h2 className="text-base font-medium text-[#171717]">Milestones & Deliverables</h2>
            <p className="text-xs text-[#7d7d7d] mt-0.5">
              Structured roadmap required for verification sign-off.
            </p>
          </div>
          <span className="text-xs font-mono text-[#7d7d7d]">
            {project.milestones.length} Milestone{project.milestones.length !== 1 ? 's' : ''}
          </span>
        </div>

        {project.milestones.length === 0 ? (
          <p className="text-xs text-[#7d7d7d] italic">No milestones defined for this project.</p>
        ) : (
          <div className="space-y-4">
            {project.milestones.map((m, idx) => (
              <div
                key={m.id}
                className="p-4 rounded-[6px] border border-[#ebebeb] bg-[#fafafa] space-y-3"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-5 h-5 rounded-full bg-[#171717] text-[#ffffff] text-[11px] font-mono flex items-center justify-center font-medium">
                      {idx + 1}
                    </span>
                    <h3 className="text-sm font-medium text-[#171717]">{m.title}</h3>
                  </div>
                  <span className="text-xs font-mono text-[#7d7d7d] flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5" /> Due day {m.due_day_offset}
                  </span>
                </div>

                {m.description && (
                  <p className="text-xs text-[#4d4d4d] leading-relaxed pl-7">
                    {m.description}
                  </p>
                )}

                {m.tasks && m.tasks.length > 0 && (
                  <div className="pl-7 space-y-1.5 pt-1">
                    <span className="text-[11px] font-mono uppercase text-[#7d7d7d]">Sub-Tasks:</span>
                    <ul className="space-y-1">
                      {m.tasks.map((task) => (
                        <li key={task.id} className="text-xs text-[#4d4d4d] flex items-start gap-2">
                          <span className="text-[#7d7d7d]">•</span>
                          <div>
                            <span className="font-medium text-[#171717]">{task.title}</span>
                            {task.description && (
                              <span className="text-[#7d7d7d]"> — {task.description}</span>
                            )}
                          </div>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Application Action Section */}
      <div className="p-6 rounded-[6px] border border-[#ebebeb] bg-[#ffffff] space-y-4">
        <h2 className="text-base font-medium text-[#171717]">Apply for this Project</h2>

        {!user ? (
          <div className="p-4 rounded-[6px] bg-[#fafafa] border border-[#ebebeb] flex items-center justify-between">
            <span className="text-xs text-[#4d4d4d]">
              Sign in with an approved student account to apply and earn verification.
            </span>
            <Link
              to="/login"
              className="px-4 py-2 rounded-[6px] bg-[#171717] text-[#ffffff] text-xs font-medium hover:bg-[#000000]"
            >
              Sign In
            </Link>
          </div>
        ) : user.role !== 'student' ? (
          <div className="p-4 rounded-[6px] bg-[#fafafa] border border-[#ebebeb] text-xs text-[#7d7d7d]">
            Only registered student accounts may apply to projects. (Current role: <span className="font-mono text-[#171717]">{user.role}</span>)
          </div>
        ) : !user.email_verified ? (
          <div className="p-4 rounded-[6px] bg-[#fafafa] border border-[#ebebeb] text-xs text-[#7d7d7d] space-y-1">
            <p className="font-medium text-[#171717]">Email Verification Required (FR-AUTH-2)</p>
            <p>Please check your inbox and verify your email before applying to company projects.</p>
          </div>
        ) : applySuccess ? (
          <div className="p-4 rounded-[6px] border border-[#297a3a]/30 bg-[#297a3a]/5 flex items-start gap-3">
            <CheckCircle2 className="w-5 h-5 text-[#297a3a] shrink-0 mt-0.5" />
            <div className="space-y-1 text-xs">
              <p className="font-medium text-[#297a3a]">Application Submitted Successfully!</p>
              <p className="text-[#4d4d4d]">
                Your application has been received by <span className="font-medium text-[#171717]">{project.company.name}</span>. You can track its status and decisions in your Student Workspace.
              </p>
              <Link
                to="/student"
                className="inline-block mt-2 font-medium text-[#171717] underline"
              >
                Go to Student Workspace &rarr;
              </Link>
            </div>
          </div>
        ) : (
          <form onSubmit={handleApply} className="space-y-4">
            {applyError && (
              <div className="p-3 rounded-[4px] border border-[#ff4d4f]/30 bg-[#ff4d4f]/5 text-xs text-[#ff4d4f] flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{applyError}</span>
              </div>
            )}

            <div className="space-y-1.5">
              <label htmlFor="cover-note" className="block text-xs font-mono uppercase tracking-wider text-[#7d7d7d]">
                Cover Note / Relevant Background (Optional, max 2000 chars)
              </label>
              <textarea
                id="cover-note"
                rows={4}
                value={coverNote}
                onChange={(e) => setCoverNote(e.target.value)}
                maxLength={2000}
                placeholder="Explain why you're a great fit for this project, relevant coursework, or tools you've used..."
                className="w-full p-3 text-sm rounded-[6px] border border-[#ebebeb] bg-[#fafafa] text-[#171717] placeholder-[#a8a8a8] focus:outline-none focus:border-[#171717]"
              />
              <div className="text-[11px] font-mono text-[#7d7d7d] text-right">
                {coverNote.length} / 2000
              </div>
            </div>

            <div className="flex items-center justify-between pt-2">
              <span className="text-[11px] font-mono text-[#7d7d7d]">
                Max 3 active applications allowed per student (FR-APP-1)
              </span>
              <button
                type="submit"
                disabled={submitting}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-[6px] bg-[#171717] text-[#ffffff] text-xs font-medium hover:bg-[#000000] disabled:bg-[#8f8f8f] transition-colors"
              >
                <Send className="w-3.5 h-3.5" />
                {submitting ? 'Submitting Application...' : 'Submit Application'}
              </button>
            </div>
          </form>
        )}
      </div>

      {/* Mandatory Disclaimer */}
      <div className="p-4 rounded-[6px] border border-[#ebebeb] bg-[#ffffff] flex items-start gap-3">
        <Info className="w-4 h-4 text-[#7d7d7d] mt-0.5 shrink-0" />
        <div className="text-xs text-[#7d7d7d] leading-relaxed">
          <span className="font-medium text-[#171717]">Platform Guarantee & Policy: </span>
          A ProjectProof certificate is a platform record of verified project completion, not formal employment experience. The public verification page reads live cryptographic ledger data on every request.
        </div>
      </div>
    </div>
  );
};
