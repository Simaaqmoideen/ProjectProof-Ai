import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../lib/auth-context';
import { apiRequest } from '../../lib/api';
import { StatusBadge } from '../../components/StatusBadge';
import {
  Briefcase,
  Building2,
  Calendar,
  CheckCircle2,
  ChevronRight,
  Filter,
  Flame,
  Info,
  Layers,
  Search,
  Sparkles,
  Zap,
} from 'lucide-react';

interface ProjectMilestone {
  id: string;
  position: number;
  title: string;
  due_day_offset: number;
}

interface ProjectItem {
  id: string;
  title: string;
  description: string;
  category: string;
  difficulty: string;
  duration_days: number;
  xp_max: number;
  max_selected: number;
  status: string;
  company: {
    id: string;
    name: string;
    website: string | null;
    status: string;
    trust_score: number;
  };
  skills: string[];
  milestones: ProjectMilestone[];
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

interface RecommendedItem {
  project: ProjectItem;
  recommendation_score: number;
  match_score: number;
  reason: string;
}

export const ProjectsBrowsePage: React.FC = () => {
  const { user } = useAuth();
  const [projects, setProjects] = useState<ProjectItem[]>([]);
  const [recommended, setRecommended] = useState<RecommendedItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  // Filters
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState<string>('all');
  const [difficulty, setDifficulty] = useState<string>('all');

  const fetchProjects = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (category !== 'all') params.set('category', category);
      if (difficulty !== 'all') params.set('difficulty', difficulty);
      if (search.trim()) params.set('search', search.trim());

      const data = await apiRequest<{ items: ProjectItem[]; total: number }>(
        `/projects?${params.toString()}`
      );
      setProjects(data.items);
      setTotal(data.total);

      // If student is logged in, also fetch recommendations
      if (user?.role === 'student' && user.email_verified) {
        try {
          const recs = await apiRequest<RecommendedItem[]>('/projects/recommended/list');
          setRecommended(recs.slice(0, 3));
        } catch (e) {
          // Non-blocking
          console.error('Failed to load recommendations:', e);
        }
      }
    } catch (err) {
      console.error('Failed to fetch projects:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, [category, difficulty]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchProjects();
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header */}
      <div className="pb-6 border-b border-[#ebebeb]">
        <div className="flex items-center gap-2 mb-1">
          <span className="font-mono text-[11px] tracking-wider uppercase text-[#7d7d7d]">
            Project Catalog
          </span>
          <span className="text-[#ebebeb]">•</span>
          <span className="font-mono text-[11px] text-[#297a3a] flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-[#297a3a]" /> Real-World Tasks
          </span>
        </div>
        <h1 className="text-2xl sm:text-3xl font-normal text-[#171717] tracking-tight">
          Verified Project Directory
        </h1>
        <p className="mt-1 text-sm text-[#4d4d4d] max-w-2xl">
          Complete production-grade challenges posted by vetted companies. Earn verifiable credentials backed by live cryptographic proof.
        </p>
      </div>

      {/* Recommended Projects (Student Only) */}
      {user?.role === 'student' && recommended.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-[#171717]" />
            <h2 className="text-sm font-medium text-[#171717] font-mono uppercase tracking-wider">
              Recommended for You
            </h2>
            <span className="text-xs text-[#7d7d7d] font-mono">(Algorithm BR-10)</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {recommended.map((rec) => (
              <div
                key={`rec-${rec.project.id}`}
                className="p-4 rounded-[6px] border border-[#171717] bg-[#ffffff] shadow-sm flex flex-col justify-between space-y-3"
              >
                <div>
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="font-mono text-[#297a3a] font-medium flex items-center gap-1">
                      <Zap className="w-3.5 h-3.5" /> {rec.recommendation_score} Rec Score
                    </span>
                    <span className="font-mono text-[#7d7d7d]">
                      {rec.match_score}% Skill Match
                    </span>
                  </div>
                  <h3 className="text-sm font-medium text-[#171717] line-clamp-1">
                    {rec.project.title}
                  </h3>
                  <p className="text-xs text-[#7d7d7d] mt-1 line-clamp-2">
                    {rec.reason}
                  </p>
                </div>
                <div className="pt-2 border-t border-[#ebebeb] flex items-center justify-between">
                  <span className="text-xs font-mono text-[#171717]">
                    +{rec.project.xp_max} XP
                  </span>
                  <Link
                    to={`/projects/${rec.project.id}`}
                    className="inline-flex items-center gap-1 text-xs font-medium text-[#171717] hover:underline"
                  >
                    View <ChevronRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="p-4 rounded-[6px] border border-[#ebebeb] bg-[#ffffff] space-y-4">
        <form onSubmit={handleSearchSubmit} className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-[#7d7d7d] absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search by project title, skill or keywords..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-2 text-sm rounded-[6px] border border-[#ebebeb] bg-[#fafafa] text-[#171717] placeholder-[#a8a8a8] focus:outline-none focus:border-[#171717] transition-colors"
            />
          </div>
          <button
            type="submit"
            className="px-4 py-2 rounded-[6px] bg-[#171717] text-[#ffffff] text-sm font-medium hover:bg-[#000000] transition-colors shrink-0"
          >
            Search
          </button>
        </form>

        <div className="flex flex-wrap items-center gap-4 text-xs pt-2 border-t border-[#ebebeb]">
          <div className="flex items-center gap-2">
            <span className="text-[#7d7d7d] font-mono uppercase tracking-wider">Category:</span>
            {['all', 'development', 'data', 'design', 'other'].map((c) => (
              <button
                key={c}
                type="button"
                onClick={() => setCategory(c)}
                className={`px-2.5 py-1 rounded-[4px] capitalize transition-colors ${
                  category === c
                    ? 'bg-[#171717] text-[#ffffff]'
                    : 'bg-[#fafafa] text-[#666666] hover:text-[#171717] border border-[#ebebeb]'
                }`}
              >
                {c}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <span className="text-[#7d7d7d] font-mono uppercase tracking-wider">Difficulty:</span>
            {['all', 'beginner', 'intermediate', 'advanced'].map((d) => (
              <button
                key={d}
                type="button"
                onClick={() => setDifficulty(d)}
                className={`px-2.5 py-1 rounded-[4px] capitalize transition-colors ${
                  difficulty === d
                    ? 'bg-[#171717] text-[#ffffff]'
                    : 'bg-[#fafafa] text-[#666666] hover:text-[#171717] border border-[#ebebeb]'
                }`}
              >
                {d}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Projects Grid */}
      {loading ? (
        <div className="py-16 text-center">
          <span className="font-mono text-xs text-[#7d7d7d] animate-pulse">
            Querying open projects...
          </span>
        </div>
      ) : projects.length === 0 ? (
        <div className="p-12 text-center border border-[#ebebeb] rounded-[6px] bg-[#ffffff] space-y-3">
          <Briefcase className="w-8 h-8 text-[#a8a8a8] mx-auto" />
          <h3 className="text-sm font-medium text-[#171717]">No open projects found</h3>
          <p className="text-xs text-[#7d7d7d] max-w-sm mx-auto">
            Try adjusting your search query, difficulty level, or category filter to find available challenges.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center justify-between text-xs text-[#7d7d7d] font-mono">
            <span>Showing {projects.length} of {total} open project{total !== 1 ? 's' : ''}</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {projects.map((p) => {
              return (
                <div
                  key={p.id}
                  className="p-5 rounded-[6px] border border-[#ebebeb] bg-[#ffffff] hover:border-[#171717] transition-all flex flex-col justify-between space-y-4"
                >
                  <div className="space-y-3">
                    {/* Top Row: Company & Badges */}
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <Building2 className="w-4 h-4 text-[#7d7d7d] shrink-0" />
                        <span className="text-xs font-medium text-[#171717]">
                          {p.company.name}
                        </span>
                        <span className="text-[#ebebeb]">•</span>
                        <span className="text-[11px] font-mono text-[#7d7d7d]" title="Company Trust Score (BR-6)">
                          Trust {p.company.trust_score}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 rounded-[4px] border border-[#ebebeb] bg-[#fafafa] text-[11px] font-mono text-[#4d4d4d] capitalize">
                          {p.difficulty}
                        </span>
                        {p.match && (
                          <span
                            className="px-2 py-0.5 rounded-[4px] bg-[#297a3a]/10 text-[#297a3a] text-[11px] font-mono font-medium"
                            title={`Match breakdown: Skill ${p.match.breakdown.skill_match}%, Level ${p.match.breakdown.level_alignment}%, Coursework ${p.match.breakdown.coursework_overlap}%, Category ${p.match.breakdown.category_alignment}%`}
                          >
                            {p.match.score}% Match
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Title & Description */}
                    <div>
                      <h2 className="text-base font-medium text-[#171717] leading-snug">
                        <Link to={`/projects/${p.id}`} className="hover:underline">
                          {p.title}
                        </Link>
                      </h2>
                      <p className="mt-1 text-xs text-[#4d4d4d] line-clamp-2 leading-relaxed">
                        {p.description}
                      </p>
                    </div>

                    {/* Skills */}
                    {p.skills.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 pt-1">
                        {p.skills.map((skill) => (
                          <span
                            key={skill}
                            className="px-2 py-0.5 rounded-[3px] bg-[#fafafa] border border-[#ebebeb] text-[11px] font-mono text-[#4d4d4d]"
                          >
                            {skill}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Bottom Stats & CTA */}
                  <div className="pt-3 border-t border-[#ebebeb] flex items-center justify-between">
                    <div className="flex items-center gap-4 text-xs font-mono text-[#7d7d7d]">
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3.5 h-3.5" />
                        {p.duration_days} days
                      </span>
                      <span className="flex items-center gap-1 font-medium text-[#171717]">
                        <Flame className="w-3.5 h-3.5 text-[#171717]" />
                        +{p.xp_max} XP
                      </span>
                    </div>

                    <Link
                      to={`/projects/${p.id}`}
                      className="inline-flex items-center gap-1 px-3 py-1.5 rounded-[4px] bg-[#171717] text-[#ffffff] text-xs font-medium hover:bg-[#000000] transition-colors"
                    >
                      View & Apply <ChevronRight className="w-3.5 h-3.5" />
                    </Link>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Mandatory Disclaimer */}
      <div className="p-4 rounded-[6px] border border-[#ebebeb] bg-[#ffffff] flex items-start gap-3">
        <Info className="w-4 h-4 text-[#7d7d7d] mt-0.5 shrink-0" />
        <div className="text-xs text-[#7d7d7d] leading-relaxed">
          <span className="font-medium text-[#171717]">Platform Rule & Policy: </span>
          A ProjectProof certificate is a platform record of verified project completion, not formal employment experience. The public verification page reads live cryptographic ledger data on every request.
        </div>
      </div>
    </div>
  );
};
