/**
 * StudentPortfolioPage — FR-STU-10
 *
 * Displays a student's verified project history:
 *  - Newest first
 *  - Each entry shows company, skills, public summary, completion date, XP, verification link
 *  - Revoked records stay listed with a Revoked label
 *  - This is the same page a recruiter sees when a profile is public (FR-REC-2)
 *
 * Route: /student/portfolio (own), /students/:id/portfolio (public / recruiter)
 *
 * "This is a platform verification record, not formal employment experience."
 * (AGENTS.md — must appear on every portfolio and verification page)
 */

import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  AlertCircle,
  Award,
  BadgeCheck,
  Building2,
  Calendar,
  Check,
  ChevronRight,
  Copy,
  ExternalLink,
  Loader2,
  QrCode,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Star,
  Zap,
} from 'lucide-react';
import { useAuth } from '../../lib/auth-context';
import { ApiException, apiRequest } from '../../lib/api';

// ─── Types (matching backend PortfolioItem schema) ───────────────────────────

interface PortfolioItem {
  verification_id: string;
  qr_token: string;
  status: 'issued' | 'revoked';
  xp_awarded: number | null;
  issued_at: string | null;
  revoked_at: string | null;
  project_title: string;
  category: string | null;
  difficulty: string;
  duration_days: number;
  company_name: string;
  completed_at: string | null;
  public_summary: string | null;
  skills: string[];
}

interface PortfolioResponse {
  items: PortfolioItem[];
  total: number;
}

interface StudentProfile {
  full_name: string;
  is_public: boolean;
  show_full_name_on_verification: boolean;
}

interface DashboardStats {
  xp: number;
  level: number;
  verified_projects: number;
  completion_rate: number;
  badges: Array<{ name: string; description: string }>;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

const DIFFICULTY_COLORS: Record<string, string> = {
  beginner: 'bg-[#e6f9ec] text-[#0a7d33]',
  intermediate: 'bg-[#e6f0ff] text-[#1c4e9d]',
  advanced: 'bg-[#fff2e6] text-[#a05000]',
  expert: 'bg-[#fbe8e8] text-[#9b1c1c]',
};

function formatDate(iso: string | null): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-GB', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

// ─── Sub-components ───────────────────────────────────────────────────────────

const StatCard: React.FC<{ label: string; value: string | number; icon: React.ReactNode }> = ({
  label,
  value,
  icon,
}) => (
  <div className="flex flex-col items-center gap-1 px-5 py-4 border border-[#ebebeb] rounded-[6px] bg-white">
    <div className="text-[#7d7d7d]">{icon}</div>
    <span className="text-xl font-semibold text-[#171717]">{value}</span>
    <span className="text-xs text-[#7d7d7d] text-center">{label}</span>
  </div>
);

interface ResumeBulletsModalProps {
  item: PortfolioItem | null;
  onClose: () => void;
}

const ResumeBulletsModal: React.FC<ResumeBulletsModalProps> = ({ item, onClose }) => {
  const [loading, setLoading] = useState(false);
  const [bullets, setBullets] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!item) return;
    let isMounted = true;
    setLoading(true);
    setError(null);
    setCopied(false);

    apiRequest<{ ai: { label: string }; result: { bullets: string[] } }>(
      '/ai/rewrite/resume-bullets',
      {
        method: 'POST',
        body: JSON.stringify({ certificate_id: item.verification_id }),
      }
    )
      .then((res) => {
        if (isMounted) {
          setBullets(res.result.bullets || []);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err instanceof ApiException ? err.message : 'Failed to generate resume bullets');
        }
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [item]);

  if (!item) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(bullets.join('\n\n'));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm">
      <div className="bg-white rounded-[8px] max-w-lg w-full p-6 shadow-xl border border-[#ebebeb] space-y-4">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Sparkles className="w-4 h-4 text-[#297a3a]" />
              <h3 className="font-semibold text-[#171717] text-base">STAR Resume Bullets</h3>
              <span className="font-mono text-[10px] px-1.5 py-0.5 rounded-[4px] bg-[#f5f5f5] text-[#737373] border border-[#e5e5e5]">
                AI draft
              </span>
            </div>
            <p className="text-xs text-[#7d7d7d]">{item.project_title}</p>
          </div>
          <button
            onClick={onClose}
            className="text-[#8f8f8f] hover:text-[#171717] text-lg font-mono"
            aria-label="Close modal"
          >
            ✕
          </button>
        </div>

        <div className="px-3 py-2 rounded-[6px] bg-[#ebebeb] text-[11px] text-[#4d4d4d]">
          Platform record, not formal employment. Bullets are grounded strictly in your verified certificate facts.
        </div>

        {loading && (
          <div className="py-12 flex flex-col items-center justify-center gap-2">
            <Loader2 className="w-6 h-6 animate-spin text-[#297a3a]" />
            <p className="font-mono text-xs text-[#8f8f8f]">Formatting STAR bullets from verified record…</p>
          </div>
        )}

        {error && (
          <div className="p-3 rounded-[6px] bg-[#fef2f2] text-xs text-[#c4231c] border border-[#fecaca] font-mono">
            {error}
          </div>
        )}

        {!loading && !error && bullets.length > 0 && (
          <div className="space-y-3">
            <ul className="space-y-2.5">
              {bullets.map((bullet, idx) => (
                <li
                  key={idx}
                  className="p-3 rounded-[6px] bg-[#fafafa] border border-[#ebebeb] text-xs leading-relaxed text-[#171717]"
                >
                  {bullet}
                </li>
              ))}
            </ul>

            <div className="flex justify-between items-center pt-2">
              <button
                onClick={handleCopy}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-[6px] text-xs font-mono uppercase bg-[#171717] text-white tracking-wider"
              >
                {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                {copied ? 'Copied!' : 'Copy Bullets'}
              </button>
              <button
                onClick={onClose}
                className="px-3 py-1.5 rounded-[6px] text-xs font-mono uppercase border border-[#ebebeb] text-[#4d4d4d]"
              >
                Done
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

const PortfolioCard: React.FC<{
  item: PortfolioItem;
  isOwn?: boolean;
  onGenerateBullets?: (item: PortfolioItem) => void;
}> = ({ item, isOwn, onGenerateBullets }) => {
  const isRevoked = item.status === 'revoked';
  const displayDate = item.completed_at ?? item.issued_at;

  return (
    <div
      className={`border rounded-[6px] overflow-hidden ${
        isRevoked ? 'border-[#f5c6c6] bg-[#fff8f8]' : 'border-[#ebebeb] bg-white'
      }`}
    >
      <div className="px-5 py-4">
        <div className="flex items-start justify-between gap-3 flex-wrap">
          <div className="flex-1">
            <div className="flex items-center gap-2 flex-wrap mb-1">
              {isRevoked ? (
                <span className="flex items-center gap-1 text-xs font-mono uppercase px-2 py-0.5 rounded-full bg-[#fbe8e8] text-[#9b1c1c]">
                  <ShieldAlert className="w-3 h-3" /> Revoked
                </span>
              ) : (
                <span className="flex items-center gap-1 text-xs font-mono uppercase px-2 py-0.5 rounded-full bg-[#e6f9ec] text-[#0a7d33]">
                  <ShieldCheck className="w-3 h-3" /> Verified
                </span>
              )}
              <span
                className={`text-xs font-mono uppercase px-2 py-0.5 rounded-full ${
                  DIFFICULTY_COLORS[item.difficulty] ?? 'bg-[#ebebeb] text-[#4d4d4d]'
                }`}
              >
                {item.difficulty}
              </span>
              {item.category && (
                <span className="text-xs text-[#7d7d7d]">{item.category}</span>
              )}
            </div>

            <h2 className="text-base font-semibold text-[#171717] mb-0.5">{item.project_title}</h2>

            <div className="flex items-center gap-1 text-xs text-[#7d7d7d] mb-3 flex-wrap">
              <Building2 className="w-3 h-3" />
              <span>{item.company_name}</span>
              {displayDate && (
                <>
                  <span className="mx-1">·</span>
                  <Calendar className="w-3 h-3" />
                  <span>{formatDate(displayDate)}</span>
                </>
              )}
              {item.xp_awarded != null && (
                <>
                  <span className="mx-1">·</span>
                  <Zap className="w-3 h-3 text-[#f59e0b]" />
                  <span className="text-[#f59e0b] font-medium">+{item.xp_awarded} XP</span>
                </>
              )}
            </div>

            {item.public_summary && !isRevoked && (
              <p className="text-sm text-[#4d4d4d] leading-relaxed mb-3">{item.public_summary}</p>
            )}

            {/* Skills (string list from backend) */}
            {item.skills.length > 0 && !isRevoked && (
              <div className="flex flex-wrap gap-1.5">
                {item.skills.map((s) => (
                  <span
                    key={s}
                    className="text-xs px-2 py-0.5 rounded-full bg-[#ebebeb] text-[#4d4d4d] border border-[#e0e0e0]"
                  >
                    {s}
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Verification & Actions */}
          <div className="flex flex-col items-end gap-2">
            <Link
              to={`/verify/${item.qr_token}`}
              id={`verify-link-${item.verification_id}`}
              className="flex items-center gap-1.5 text-xs text-[#297a3a] hover:underline"
              target="_blank"
              rel="noopener noreferrer"
            >
              <QrCode className="w-3.5 h-3.5" />
              Verify
              <ExternalLink className="w-3 h-3" />
            </Link>

            {isOwn && !isRevoked && onGenerateBullets && (
              <button
                onClick={() => onGenerateBullets(item)}
                className="flex items-center gap-1 text-xs text-[#171717] px-2.5 py-1 rounded-[6px] border border-[#ebebeb] bg-[#fafafa] hover:bg-white transition-colors"
                title="Generate STAR resume bullets from verified record"
              >
                <Sparkles className="w-3 h-3 text-[#297a3a]" />
                Resume Bullets
              </button>
            )}

            <span className="text-[10px] font-mono text-[#a8a8a8] text-right break-all max-w-[120px]">
              {item.verification_id}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

// ─── Main Page ────────────────────────────────────────────────────────────────

export const StudentPortfolioPage: React.FC = () => {
  const { user } = useAuth();
  const { id } = useParams<{ id?: string }>();

  const isOwn = !id;
  const portfolioEndpoint = isOwn ? '/students/me/portfolio' : `/students/${id}/portfolio`;
  const profileEndpoint = isOwn ? '/students/me' : null;
  const dashboardEndpoint = isOwn ? '/students/me/dashboard' : null;

  const [items, setItems] = useState<PortfolioItem[]>([]);
  const [profile, setProfile] = useState<StudentProfile | null>(null);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [bulletModalItem, setBulletModalItem] = useState<PortfolioItem | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const promises: Promise<any>[] = [
          apiRequest<PortfolioResponse>(portfolioEndpoint),
        ];
        if (profileEndpoint) promises.push(apiRequest<StudentProfile>(profileEndpoint));
        if (dashboardEndpoint) promises.push(apiRequest<DashboardStats>(dashboardEndpoint));

        const [portfolioRes, profileRes, dashRes] = await Promise.all(promises);

        setItems(portfolioRes.items ?? []);
        if (profileRes) setProfile(profileRes);
        if (dashRes) setStats(dashRes);
      } catch (e) {
        if (e instanceof ApiException) {
          setError(e.status === 404 ? 'Portfolio not found or profile is private.' : e.message);
        } else {
          setError('Failed to load portfolio.');
        }
      } finally {
        setLoading(false);
      }
    })();
  }, [portfolioEndpoint, profileEndpoint, dashboardEndpoint]);

  if (loading) {
    return (
      <div className="min-h-[50vh] flex items-center justify-center">
        <Loader2 className="w-5 h-5 animate-spin text-[#7d7d7d]" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-16 text-center">
        <AlertCircle className="w-8 h-8 text-[#a8a8a8] mx-auto mb-3" />
        <p className="text-sm text-[#7d7d7d]">{error}</p>
      </div>
    );
  }

  // Name display per FR-STU-6
  const rawName = profile?.full_name ?? 'Student';
  const displayName =
    profile?.show_full_name_on_verification !== false
      ? rawName
      : `${rawName[0] ?? '?'}.`;

  const verified = items.filter((i) => i.status === 'issued');
  const revoked = items.filter((i) => i.status === 'revoked');

  return (
    <div className="max-w-4xl mx-auto px-4 py-10">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div>
            <h1 className="text-2xl font-semibold text-[#171717] tracking-tight">
              {displayName}
            </h1>
            <p className="text-sm text-[#7d7d7d] mt-0.5">Project portfolio on ProjectProof AI</p>
          </div>
          {isOwn && (
            <Link
              to="/student/profile"
              id="edit-profile-link"
              className="flex items-center gap-1.5 px-3 py-1.5 border border-[#ebebeb] text-sm rounded-[6px] bg-white hover:bg-[#fafafa] transition-colors"
            >
              Edit profile <ChevronRight className="w-3.5 h-3.5" />
            </Link>
          )}
        </div>

        {/* Disclaimer — required on all portfolio/certificate pages (AGENTS.md) */}
        <div className="mt-4 flex items-start gap-2 px-3 py-2 rounded-[6px] bg-[#ebebeb] text-xs text-[#4d4d4d]">
          <ShieldCheck className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
          <span>
            This is a platform verification record that a project was completed on ProjectProof AI.
            It is <strong>not</strong> formal employment experience.
          </span>
        </div>
      </div>

      {/* Stats (own view only — fetched from dashboard) */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
          <StatCard
            label="Total XP"
            value={stats.xp.toLocaleString()}
            icon={<Zap className="w-4 h-4 text-[#f59e0b]" />}
          />
          <StatCard
            label="Level"
            value={stats.level}
            icon={<Star className="w-4 h-4" />}
          />
          <StatCard
            label="Verified projects"
            value={stats.verified_projects}
            icon={<ShieldCheck className="w-4 h-4 text-[#0a7d33]" />}
          />
          <StatCard
            label="Completion rate"
            value={`${Math.round(stats.completion_rate)}%`}
            icon={<Award className="w-4 h-4" />}
          />
        </div>
      )}

      {/* Badges */}
      {stats?.badges && stats.badges.length > 0 && (
        <div className="mb-8">
          <h2 className="text-sm font-medium text-[#4d4d4d] mb-3">Badges</h2>
          <div className="flex flex-wrap gap-2">
            {stats.badges.map((b) => (
              <div
                key={b.name}
                title={b.description}
                className="flex items-center gap-1.5 px-3 py-1.5 border border-[#ebebeb] rounded-full bg-white text-xs text-[#171717]"
              >
                <BadgeCheck className="w-3.5 h-3.5 text-[#0a7d33]" />
                {b.name}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Verified projects */}
      <div className="mb-8">
        <h2 className="text-sm font-medium text-[#4d4d4d] mb-3">
          Verified project history
          {verified.length > 0 && (
            <span className="ml-2 text-[#7d7d7d] font-normal">({verified.length})</span>
          )}
        </h2>

        {verified.length === 0 ? (
          <div className="text-center py-12 border border-[#ebebeb] rounded-[6px] bg-[#fafafa]">
            <ShieldCheck className="w-8 h-8 text-[#c9c9c9] mx-auto mb-2" />
            <p className="text-sm text-[#7d7d7d]">No verified projects yet.</p>
            {isOwn && (
              <Link
                to="/projects"
                className="mt-3 inline-flex items-center gap-1 text-sm text-[#297a3a] hover:underline"
              >
                Browse open projects <ChevronRight className="w-3.5 h-3.5" />
              </Link>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            {verified.map((item) => (
              <PortfolioCard
                key={item.verification_id}
                item={item}
                isOwn={isOwn}
                onGenerateBullets={setBulletModalItem}
              />
            ))}
          </div>
        )}
      </div>

      {/* Revoked records (always shown with label per FR-STU-10) */}
      {revoked.length > 0 && (
        <div>
          <h2 className="text-sm font-medium text-[#4d4d4d] mb-3">
            Revoked records
            <span className="ml-2 text-[#7d7d7d] font-normal">({revoked.length})</span>
          </h2>
          <div className="space-y-3">
            {revoked.map((item) => (
              <PortfolioCard key={item.verification_id} item={item} isOwn={isOwn} />
            ))}
          </div>
        </div>
      )}

      {/* STAR Resume Bullets Modal (FR-RWD-4) */}
      <ResumeBulletsModal
        item={bulletModalItem}
        onClose={() => setBulletModalItem(null)}
      />
    </div>
  );
};

export default StudentPortfolioPage;
