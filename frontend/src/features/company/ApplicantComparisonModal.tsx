import React, { useEffect, useState } from 'react';
import { apiRequest } from '../../lib/api';
import {
  AlertCircle,
  Award,
  CheckCircle2,
  ChevronRight,
  Flame,
  GitBranch,
  ShieldCheck,
  UserCheck,
  X,
  Zap,
} from 'lucide-react';

interface ComparisonApplicant {
  application_id: string;
  status: string;
  student: {
    user_id: string;
    full_name: string;
    headline: string | null;
    college: string | null;
    graduation_year: number | null;
    verified_projects_count: number;
    xp: number;
  };
  cover_note: string | null;
  match_score: number;
  match_breakdown: {
    skill_match: number;
    level_alignment: number;
    coursework_overlap: number;
    category_alignment: number;
  };
  missing_skills: string[];
  verified_projects_count: number;
  xp: number;
}

interface ComparisonData {
  project_id: string;
  project_title: string;
  applicants: ComparisonApplicant[];
}

interface ApplicantComparisonModalProps {
  isOpen: boolean;
  projectId: string;
  onClose: () => void;
  onSelectApplicant: (appId: string) => Promise<void>;
}

export const ApplicantComparisonModal: React.FC<ApplicantComparisonModalProps> = ({
  isOpen,
  projectId,
  onClose,
  onSelectApplicant,
}) => {
  const [data, setData] = useState<ComparisonData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectingId, setSelectingId] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen || !projectId) return;
    const fetchComparison = async () => {
      setLoading(true);
      setError(null);
      try {
        const resp = await apiRequest<ComparisonData>(`/projects/${projectId}/applications/compare`);
        setData(resp);
      } catch (err: any) {
        setError(err.message || 'Failed to load comparison data');
      } finally {
        setLoading(false);
      }
    };
    fetchComparison();
  }, [isOpen, projectId]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#000000]/50 backdrop-blur-sm overflow-x-auto">
      <div className="w-full max-w-6xl bg-[#ffffff] rounded-[6px] border border-[#ebebeb] shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="p-5 border-b border-[#ebebeb] flex items-center justify-between">
          <div>
            <div className="text-[11px] font-mono text-[#7d7d7d] uppercase tracking-wider">
              Side-by-Side Candidate Evaluation (FR-APP-7)
            </div>
            <h2 className="text-lg font-medium text-[#171717]">
              Compare Applicants — {data?.project_title || 'Project'}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-[4px] hover:bg-[#fafafa] text-[#7d7d7d] hover:text-[#171717] transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto flex-1 space-y-6">
          {loading ? (
            <div className="py-16 text-center">
              <span className="font-mono text-xs text-[#7d7d7d] animate-pulse">
                Computing multi-candidate skill matrix...
              </span>
            </div>
          ) : error ? (
            <div className="p-4 rounded-[6px] bg-[#ff4d4f]/5 border border-[#ff4d4f]/30 text-xs text-[#ff4d4f]">
              {error}
            </div>
          ) : !data || data.applicants.length === 0 ? (
            <div className="p-12 text-center text-xs text-[#7d7d7d] space-y-2">
              <UserCheck className="w-8 h-8 text-[#a8a8a8] mx-auto" />
              <p>No applied candidates to compare at this time.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {data.applicants.map((cand, idx) => (
                <div
                  key={cand.application_id}
                  className={`p-5 rounded-[6px] border flex flex-col justify-between space-y-4 ${
                    idx === 0
                      ? 'border-[#171717] bg-[#ffffff] ring-1 ring-[#171717]'
                      : 'border-[#ebebeb] bg-[#fafafa]'
                  }`}
                >
                  <div className="space-y-4">
                    {/* Top Rank Badge */}
                    <div className="flex items-center justify-between">
                      <span className="px-2 py-0.5 rounded-[4px] bg-[#171717] text-[#ffffff] font-mono text-[11px] font-medium">
                        Rank #{idx + 1}
                      </span>
                      <span className="text-xs font-mono font-medium text-[#297a3a] flex items-center gap-1">
                        <Zap className="w-3.5 h-3.5" />
                        {cand.match_score}% Match
                      </span>
                    </div>

                    {/* Student Info */}
                    <div>
                      <h3 className="text-base font-medium text-[#171717]">
                        {cand.student.full_name}
                      </h3>
                      <p className="text-xs text-[#7d7d7d] mt-0.5">
                        {cand.student.headline || 'Student Engineer'}
                      </p>
                      <div className="text-[11px] font-mono text-[#4d4d4d] mt-1">
                        {cand.student.college} • Class of {cand.student.graduation_year || 'N/A'}
                      </div>
                    </div>

                    {/* Proof Records */}
                    <div className="grid grid-cols-2 gap-2 p-2.5 rounded-[4px] bg-[#ffffff] border border-[#ebebeb] text-center text-xs font-mono">
                      <div>
                        <div className="text-[#7d7d7d] text-[10px] uppercase">Verified Proofs</div>
                        <div className="font-medium text-[#171717] text-sm">
                          {cand.verified_projects_count}
                        </div>
                      </div>
                      <div>
                        <div className="text-[#7d7d7d] text-[10px] uppercase">Total XP</div>
                        <div className="font-medium text-[#171717] text-sm flex items-center justify-center gap-0.5">
                          <Flame className="w-3 h-3 text-[#171717]" /> {cand.xp}
                        </div>
                      </div>
                    </div>

                    {/* Breakdown */}
                    <div className="space-y-1.5 text-xs font-mono">
                      <div className="text-[11px] text-[#7d7d7d] uppercase tracking-wider">
                        Score Breakdown (BR-3):
                      </div>
                      <div className="flex justify-between text-[#4d4d4d]">
                        <span>Skill Overlap:</span>
                        <span className="font-medium text-[#171717]">
                          {cand.match_breakdown.skill_match}%
                        </span>
                      </div>
                      <div className="flex justify-between text-[#4d4d4d]">
                        <span>Level Alignment:</span>
                        <span className="font-medium text-[#171717]">
                          {cand.match_breakdown.level_alignment}%
                        </span>
                      </div>
                      <div className="flex justify-between text-[#4d4d4d]">
                        <span>Coursework Overlap:</span>
                        <span className="font-medium text-[#171717]">
                          {cand.match_breakdown.coursework_overlap}%
                        </span>
                      </div>
                    </div>

                    {/* Missing Skills */}
                    {cand.missing_skills.length > 0 ? (
                      <div className="space-y-1">
                        <div className="text-[11px] font-mono text-[#7d7d7d] uppercase">
                          Skill Gaps to Mentor:
                        </div>
                        <div className="flex flex-wrap gap-1">
                          {cand.missing_skills.map((s) => (
                            <span
                              key={s}
                              className="px-1.5 py-0.5 rounded-[3px] bg-[#ebebeb] text-[10px] font-mono text-[#666666]"
                            >
                              {s}
                            </span>
                          ))}
                        </div>
                      </div>
                    ) : (
                      <div className="text-[11px] font-mono text-[#297a3a] flex items-center gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5" /> All required skills covered
                      </div>
                    )}

                    {/* Cover Note */}
                    {cand.cover_note && (
                      <div className="space-y-1 pt-1 border-t border-[#ebebeb]">
                        <span className="text-[11px] font-mono uppercase text-[#7d7d7d]">
                          Cover Note:
                        </span>
                        <p className="text-xs text-[#4d4d4d] italic line-clamp-3">
                          "{cand.cover_note}"
                        </p>
                      </div>
                    )}
                  </div>

                  {/* Select CTA */}
                  <div className="pt-3 border-t border-[#ebebeb]">
                    <button
                      onClick={async () => {
                        setSelectingId(cand.application_id);
                        await onSelectApplicant(cand.application_id);
                        setSelectingId(null);
                        onClose();
                      }}
                      disabled={selectingId === cand.application_id}
                      className="w-full py-2 rounded-[6px] bg-[#171717] text-[#ffffff] text-xs font-medium hover:bg-[#000000] disabled:bg-[#8f8f8f] transition-colors"
                    >
                      {selectingId === cand.application_id
                        ? 'Selecting...'
                        : 'Select Candidate (FR-APP-5)'}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
