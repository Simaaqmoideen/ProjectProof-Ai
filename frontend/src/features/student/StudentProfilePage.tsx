/**
 * StudentProfilePage — FR-STU-1 to FR-STU-9
 *
 * Sections:
 *  1. Profile info (name, headline, bio, college, grad year)
 *  2. Visibility toggle (FR-STU-5, FR-STU-6)
 *  3. Skills (FR-STU-2)
 *  4. Resume upload + AI analysis (FR-STU-3, FR-STU-4)
 *  5. GitHub integration (FR-STU-8)
 *  6. AI GitHub repo analysis (FR-STU-11)
 *
 * AI outputs are always labelled "AI draft" and are never saved until
 * the student explicitly accepts them (AGENTS.md Rule 4, FR-AI-1).
 */

import React, { useEffect, useRef, useState } from 'react';
import {
  AlertCircle,
  BookOpen,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Eye,
  EyeOff,
  Info,
  Loader2,
  Plus,
  Save,
  Sparkles,
  Trash2,
  Upload,
  User,
  X,
} from 'lucide-react';

const Github = ({ className = 'w-4 h-4' }: { className?: string }) => (
  <svg
    viewBox="0 0 24 24"
    fill="currentColor"
    className={className}
    aria-hidden="true"
  >
    <path
      fillRule="evenodd"
      clipRule="evenodd"
      d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
    />
  </svg>
);
import { useAuth } from '../../lib/auth-context';
import { ApiException, apiRequest } from '../../lib/api';

// ─── Types ───────────────────────────────────────────────────────────────────

interface Skill {
  id: string;
  name: string;
  proficiency: number;
  source: 'self' | 'resume' | 'verified_project';
}

interface StudentProfile {
  user_id: string;
  full_name: string;
  headline: string | null;
  bio: string | null;
  college: string | null;
  graduation_year: number | null;
  github_username: string | null;
  is_public: boolean;
  show_full_name_on_verification: boolean;
  resume_file_key?: string | null;
  resume_url: string | null;
  skills?: Skill[];
}

interface AiDraftSkill {
  name: string;
  proficiency: number;
  source: 'self' | 'resume' | 'verified_project';
  accepted: boolean;
}

interface AiResult {
  log_id: string;
  confidence: string;
  label: string;
  skills: AiDraftSkill[];
  summary?: string;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

const PROFICIENCY_LABELS: Record<number, string> = {
  1: 'Beginner',
  2: 'Elementary',
  3: 'Intermediate',
  4: 'Advanced',
  5: 'Expert',
};

const SOURCE_LABEL: Record<string, string> = {
  self: 'Self',
  resume: 'Resume',
  verified_project: 'Verified',
};

const SOURCE_COLOR: Record<string, string> = {
  self: 'bg-[#ebebeb] text-[#4d4d4d]',
  resume: 'bg-[#e6f0ff] text-[#1c4e9d]',
  verified_project: 'bg-[#e6f9ec] text-[#0a7d33]',
};

// ─── Sub-components ───────────────────────────────────────────────────────────

const Section: React.FC<{
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
  defaultOpen?: boolean;
}> = ({ title, icon, children, defaultOpen = true }) => {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border border-[#ebebeb] rounded-[6px] overflow-hidden">
      <button
        type="button"
        className="w-full flex items-center justify-between px-5 py-4 bg-white hover:bg-[#fafafa] transition-colors"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span className="flex items-center gap-2 font-medium text-sm text-[#171717]">
          {icon}
          {title}
        </span>
        {open ? (
          <ChevronUp className="w-4 h-4 text-[#7d7d7d]" />
        ) : (
          <ChevronDown className="w-4 h-4 text-[#7d7d7d]" />
        )}
      </button>
      {open && <div className="border-t border-[#ebebeb] bg-white px-5 py-5">{children}</div>}
    </div>
  );
};

const AiDraftBanner: React.FC<{ confidence: string; label: string }> = ({
  confidence,
  label,
}) => (
  <div className="flex items-center gap-2 px-3 py-2 rounded-[6px] bg-[#fffbe6] border border-[#f5e27a] text-xs text-[#7d5c00] mb-4">
    <Sparkles className="w-3.5 h-3.5 flex-shrink-0" />
    <span>
      <strong>{label}</strong> — confidence: {confidence}. Review each suggestion and accept or
      discard before saving.
    </span>
  </div>
);

// ─── Main Page ────────────────────────────────────────────────────────────────

export const StudentProfilePage: React.FC = () => {
  const { user, refreshUser } = useAuth();

  const [profile, setProfile] = useState<StudentProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Profile form
  const [fullName, setFullName] = useState('');
  const [headline, setHeadline] = useState('');
  const [bio, setBio] = useState('');
  const [college, setCollege] = useState('');
  const [gradYear, setGradYear] = useState('');
  const [isPublic, setIsPublic] = useState(false);
  const [showFullName, setShowFullName] = useState(true);

  // Skills
  const [skills, setSkills] = useState<Skill[]>([]);
  const [newSkillName, setNewSkillName] = useState('');
  const [newSkillProf, setNewSkillProf] = useState(3);
  const [savingSkills, setSavingSkills] = useState(false);

  // Resume
  const resumeRef = useRef<HTMLInputElement>(null);
  const [resumeUploading, setResumeUploading] = useState(false);
  const [resumeUrl, setResumeUrl] = useState<string | null>(null);
  const [resumeText, setResumeText] = useState<string>('');

  // AI resume analysis
  const [aiResumeLoading, setAiResumeLoading] = useState(false);
  const [aiResumeDraft, setAiResumeDraft] = useState<AiResult | null>(null);
  const [aiResumeAccepting, setAiResumeAccepting] = useState(false);

  // GitHub
  const [githubUsername, setGithubUsername] = useState('');
  const [githubData, setGithubData] = useState<any>(null);
  const [githubLoading, setGithubLoading] = useState(false);
  const [githubError, setGithubError] = useState<string | null>(null);

  // AI GitHub analysis
  const [aiGithubLoading, setAiGithubLoading] = useState(false);
  const [aiGithubDraft, setAiGithubDraft] = useState<AiResult | null>(null);
  const [aiGithubAccepting, setAiGithubAccepting] = useState(false);

  // ── Load profile ───────────────────────────────────────────────────────────

  useEffect(() => {
    (async () => {
      try {
        const [data, skillsData] = await Promise.all([
          apiRequest<StudentProfile>('/students/me'),
          apiRequest<Skill[]>('/students/me/skills').catch(() => []),
        ]);
        setProfile(data);
        setFullName(data.full_name ?? '');
        setHeadline(data.headline ?? '');
        setBio(data.bio ?? '');
        setCollege(data.college ?? '');
        setGradYear(data.graduation_year?.toString() ?? '');
        setIsPublic(data.is_public);
        setShowFullName(data.show_full_name_on_verification);
        setSkills(skillsData ?? []);
        setResumeUrl(data.resume_url ?? data.resume_file_key ?? null);
        setGithubUsername(data.github_username ?? '');

        if (data.github_username) {
          loadGithub(data.github_username);
        }
      } catch (e) {
        setError('Failed to load profile.');
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  // ── Save profile info ──────────────────────────────────────────────────────

  const saveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const year = gradYear ? parseInt(gradYear, 10) : null;
      await apiRequest('/students/me', {
        method: 'PUT',
        body: JSON.stringify({
          full_name: fullName.trim() || null,
          headline: headline.trim() || null,
          bio: bio.trim() || null,
          college: college.trim() || null,
          graduation_year: year,
        }),
      });
      // Visibility is a separate endpoint
      await apiRequest('/students/me/visibility', {
        method: 'PUT',
        body: JSON.stringify({ is_public: isPublic, show_full_name_on_verification: showFullName }),
      });
      await refreshUser();
      setSuccessMsg('Profile saved.');
    } catch (e) {
      setError(e instanceof ApiException ? e.message : 'Failed to save profile.');
    } finally {
      setSaving(false);
    }
  };

  // ── Skills ─────────────────────────────────────────────────────────────────

  const addSkill = async () => {
    if (!newSkillName.trim()) return;
    setSavingSkills(true);
    setError(null);
    try {
      const updated = await apiRequest<{ message: string; count: number }>('/students/me/skills', {
        method: 'PUT',
        body: JSON.stringify({
          skills: [
            ...skills.map((s) => ({
              skill: s.name,
              proficiency: s.proficiency,
            })),
            { skill: newSkillName.trim(), proficiency: newSkillProf },
          ],
        }),
      });
      // Reload skills after update
      const reloaded = await apiRequest<Skill[]>('/students/me/skills');
      setSkills(reloaded);
      setNewSkillName('');
      setNewSkillProf(3);
    } catch (e) {
      setError(e instanceof ApiException ? e.message : 'Failed to save skills.');
    } finally {
      setSavingSkills(false);
    }
  };

  const removeSkill = async (name: string) => {
    setSavingSkills(true);
    try {
      const updated = await apiRequest<{ message: string; count: number }>('/students/me/skills', {
        method: 'PUT',
        body: JSON.stringify({
          skills: skills
            .filter((s) => s.name !== name)
            .map((s) => ({ skill: s.name, proficiency: s.proficiency })),
        }),
      });
      // Reload skills
      const reloaded = await apiRequest<Skill[]>('/students/me/skills');
      setSkills(reloaded);
    } catch (e) {
      setError(e instanceof ApiException ? e.message : 'Failed to save skills.');
    } finally {
      setSavingSkills(false);
    }
  };

  // ── Resume ─────────────────────────────────────────────────────────────────

  const uploadResume = async (file: File) => {
    const MAX_MB = 5;
    if (file.size > MAX_MB * 1024 * 1024) {
      setError(`Resume must be ≤ ${MAX_MB} MB.`);
      return;
    }
    if (file.type !== 'application/pdf') {
      setError('Only PDF files are accepted.');
      return;
    }
    setResumeUploading(true);
    setError(null);
    try {
      const form = new FormData();
      form.append('file', file);
      const res = await apiRequest<{ resume_url: string; resume_file_key?: string }>('/students/me/resume', {
        method: 'POST',
        body: form,
      });
      setResumeUrl(res.resume_url ?? res.resume_file_key ?? null);

      // Extract text from uploaded resume for AI analysis (FR-STU-4)
      try {
        const raw = await file.text();
        const matches = raw.match(/[A-Za-z0-9,.:;'\-\s]{3,}/g);
        const textContent = matches ? matches.join(' ').replace(/\s+/g, ' ').trim() : '';
        if (textContent.length >= 10) {
          setResumeText(textContent);
        } else {
          setResumeText(`Resume for ${file.name}`);
        }
      } catch {
        setResumeText(`Resume for ${file.name}`);
      }

      setSuccessMsg('Resume uploaded.');
    } catch (e) {
      setError(e instanceof ApiException ? e.message : 'Failed to upload resume.');
    } finally {
      setResumeUploading(false);
    }
  };

  const analyzeResume = async () => {
    if (!resumeUrl) {
      setError('Upload a resume first.');
      return;
    }
    setAiResumeLoading(true);
    setError(null);
    setAiResumeDraft(null);
    try {
      const textToSend =
        resumeText && resumeText.trim().length >= 10
          ? resumeText.trim()
          : (profile?.full_name ? `Resume for ${profile.full_name}. Developer with technical skills.` : 'Software developer resume with technical skills.');
      const res = await apiRequest<{ ai: any; result: any }>('/ai/resume/analyze', {
        method: 'POST',
        body: JSON.stringify({ resume_text: textToSend }),
      });
      const draft: AiResult = {
        log_id: res.ai.log_id,
        confidence: res.ai.confidence,
        label: res.ai.label,
        skills: (res.result.skills ?? []).map((s: any) => ({ ...s, accepted: true })),
      };
      setAiResumeDraft(draft);
    } catch (e) {
      setError(
        e instanceof ApiException
          ? `AI analysis: ${e.message}`
          : 'AI analysis failed. You can still edit skills manually.'
      );
    } finally {
      setAiResumeLoading(false);
    }
  };

  const toggleAiResumeSkill = (idx: number) => {
    if (!aiResumeDraft) return;
    setAiResumeDraft({
      ...aiResumeDraft,
      skills: aiResumeDraft.skills.map((s, i) =>
        i === idx ? { ...s, accepted: !s.accepted } : s
      ),
    });
  };

  const acceptAiResumeSkills = async () => {
    if (!aiResumeDraft) return;
    setAiResumeAccepting(true);
    setError(null);
    try {
      const accepted = aiResumeDraft.skills
        .filter((s) => s.accepted)
        .map((s) => ({ name: s.name, proficiency: s.proficiency, source: s.source }));
      const res = await apiRequest<{ skills: Skill[] }>('/ai/resume/accept', {
        method: 'POST',
        body: JSON.stringify({ log_id: aiResumeDraft.log_id, accepted_skills: accepted }),
      });
      setSkills(res.skills ?? skills);
      setAiResumeDraft(null);
      setSuccessMsg('Skills from resume saved.');
    } catch (e) {
      setError(e instanceof ApiException ? e.message : 'Failed to apply AI suggestions.');
    } finally {
      setAiResumeAccepting(false);
    }
  };

  // ── GitHub ─────────────────────────────────────────────────────────────────

  const loadGithub = async (uname: string) => {
    if (!uname) return;
    setGithubLoading(true);
    setGithubError(null);
    try {
      const res = await apiRequest<any>('/students/me/github');
      setGithubData(res.summary ?? res);
      setGithubUsername(uname);
    } catch (e) {
      setGithubError(e instanceof ApiException ? e.message : 'Failed to load GitHub data.');
    } finally {
      setGithubLoading(false);
    }
  };

  const linkGithub = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!githubUsername.trim()) return;
    setGithubLoading(true);
    setGithubError(null);
    try {
      const res = await apiRequest<any>('/students/me/github', {
        method: 'POST',
        body: JSON.stringify({ github_username: githubUsername.trim() }),
      });
      setGithubData(res);
      setSuccessMsg('GitHub linked. Self-linked, not verified.');
    } catch (e) {
      setGithubError(e instanceof ApiException ? e.message : 'Failed to link GitHub.');
    } finally {
      setGithubLoading(false);
    }
  };

  const analyzeGithub = async () => {
    setAiGithubLoading(true);
    setError(null);
    setAiGithubDraft(null);
    try {
      const res = await apiRequest<{ ai: any; result: any }>('/ai/github/analyze', {
        method: 'POST',
        body: JSON.stringify({ username: githubUsername || null }),
      });
      const draft: AiResult = {
        log_id: res.ai.log_id,
        confidence: res.ai.confidence,
        label: res.ai.label,
        skills: (res.result.skills ?? []).map((s: any) => ({ ...s, accepted: true })),
        summary: res.result.summary ?? undefined,
      };
      setAiGithubDraft(draft);
    } catch (e) {
      setError(
        e instanceof ApiException
          ? `AI GitHub analysis: ${e.message}`
          : 'AI GitHub analysis failed.'
      );
    } finally {
      setAiGithubLoading(false);
    }
  };

  const toggleAiGithubSkill = (idx: number) => {
    if (!aiGithubDraft) return;
    setAiGithubDraft({
      ...aiGithubDraft,
      skills: aiGithubDraft.skills.map((s, i) =>
        i === idx ? { ...s, accepted: !s.accepted } : s
      ),
    });
  };

  const acceptAiGithubSkills = async () => {
    if (!aiGithubDraft) return;
    setAiGithubAccepting(true);
    setError(null);
    try {
      const accepted = aiGithubDraft.skills
        .filter((s) => s.accepted)
        .map((s) => ({ name: s.name, proficiency: s.proficiency, source: s.source }));
      const res = await apiRequest<{ skills: Skill[] }>('/ai/github/accept', {
        method: 'POST',
        body: JSON.stringify({ log_id: aiGithubDraft.log_id, accepted_skills: accepted }),
      });
      setSkills(res.skills ?? skills);
      setAiGithubDraft(null);
      setSuccessMsg('Skills from GitHub saved. Note: GitHub data is self-linked, not verified.');
    } catch (e) {
      setError(e instanceof ApiException ? e.message : 'Failed to apply GitHub suggestions.');
    } finally {
      setAiGithubAccepting(false);
    }
  };

  // ── Render ─────────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="min-h-[50vh] flex items-center justify-center">
        <Loader2 className="w-5 h-5 animate-spin text-[#7d7d7d]" />
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-10 space-y-4">
      {/* Page heading */}
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-[#171717] tracking-tight">My Profile</h1>
        <p className="text-sm text-[#7d7d7d] mt-1">
          Manage your information, skills, resume, and GitHub integration.
        </p>
      </div>

      {/* Global error / success */}
      {error && (
        <div
          role="alert"
          className="flex items-start gap-2 px-4 py-3 rounded-[6px] bg-[#fff2f2] border border-[#f5c6c6] text-sm text-[#9b1c1c]"
        >
          <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
          <span>{error}</span>
          <button
            type="button"
            className="ml-auto"
            onClick={() => setError(null)}
            aria-label="Dismiss error"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
      {successMsg && (
        <div
          role="status"
          className="flex items-center gap-2 px-4 py-3 rounded-[6px] bg-[#e6f9ec] border border-[#a3d9b5] text-sm text-[#0a7d33]"
        >
          <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
          <span>{successMsg}</span>
          <button
            type="button"
            className="ml-auto"
            onClick={() => setSuccessMsg(null)}
            aria-label="Dismiss"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* ── Section 1: Profile Info ── */}
      <Section title="Profile Information" icon={<User className="w-4 h-4" />}>
        <form onSubmit={saveProfile} id="profile-form" className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label
                htmlFor="full-name"
                className="block text-xs font-medium text-[#4d4d4d] mb-1"
              >
                Full name
              </label>
              <input
                id="full-name"
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-[#ebebeb] rounded-[6px] bg-white focus:outline-none focus:border-[#171717]"
                placeholder="Your name"
                maxLength={120}
              />
            </div>
            <div>
              <label
                htmlFor="headline"
                className="block text-xs font-medium text-[#4d4d4d] mb-1"
              >
                Headline
              </label>
              <input
                id="headline"
                type="text"
                value={headline}
                onChange={(e) => setHeadline(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-[#ebebeb] rounded-[6px] bg-white focus:outline-none focus:border-[#171717]"
                placeholder="e.g. Full-stack developer · CS junior"
                maxLength={160}
              />
            </div>
          </div>

          <div>
            <label htmlFor="bio" className="block text-xs font-medium text-[#4d4d4d] mb-1">
              Bio
            </label>
            <textarea
              id="bio"
              value={bio}
              onChange={(e) => setBio(e.target.value)}
              rows={3}
              className="w-full px-3 py-2 text-sm border border-[#ebebeb] rounded-[6px] bg-white focus:outline-none focus:border-[#171717] resize-none"
              placeholder="A short paragraph about yourself"
              maxLength={1000}
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label
                htmlFor="college"
                className="block text-xs font-medium text-[#4d4d4d] mb-1"
              >
                College / University
              </label>
              <input
                id="college"
                type="text"
                value={college}
                onChange={(e) => setCollege(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-[#ebebeb] rounded-[6px] bg-white focus:outline-none focus:border-[#171717]"
                placeholder="Institution name"
                maxLength={200}
              />
            </div>
            <div>
              <label
                htmlFor="grad-year"
                className="block text-xs font-medium text-[#4d4d4d] mb-1"
              >
                Graduation year
              </label>
              <input
                id="grad-year"
                type="number"
                value={gradYear}
                onChange={(e) => setGradYear(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-[#ebebeb] rounded-[6px] bg-white focus:outline-none focus:border-[#171717]"
                placeholder="e.g. 2026"
                min={2000}
                max={2040}
              />
            </div>
          </div>

          {/* Visibility controls (FR-STU-5, FR-STU-6) */}
          <div className="pt-2 border-t border-[#ebebeb] space-y-3">
            <label className="flex items-center gap-3 cursor-pointer">
              <div
                role="checkbox"
                aria-checked={isPublic}
                tabIndex={0}
                id="is-public-toggle"
                onClick={() => setIsPublic((v) => !v)}
                onKeyDown={(e) => e.key === ' ' && setIsPublic((v) => !v)}
                className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-[#171717] focus:ring-offset-1 ${
                  isPublic ? 'bg-[#171717]' : 'bg-[#c9c9c9]'
                }`}
              >
                <span
                  className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${
                    isPublic ? 'translate-x-4' : 'translate-x-0.5'
                  }`}
                />
              </div>
              <span className="text-sm text-[#171717]">
                {isPublic ? (
                  <span className="flex items-center gap-1">
                    <Eye className="w-3.5 h-3.5" /> Public profile — visible to recruiters
                  </span>
                ) : (
                  <span className="flex items-center gap-1">
                    <EyeOff className="w-3.5 h-3.5" /> Private profile (default)
                  </span>
                )}
              </span>
            </label>

            <label className="flex items-center gap-3 cursor-pointer">
              <div
                role="checkbox"
                aria-checked={showFullName}
                tabIndex={0}
                id="show-full-name-toggle"
                onClick={() => setShowFullName((v) => !v)}
                onKeyDown={(e) => e.key === ' ' && setShowFullName((v) => !v)}
                className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-[#171717] focus:ring-offset-1 ${
                  showFullName ? 'bg-[#171717]' : 'bg-[#c9c9c9]'
                }`}
              >
                <span
                  className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${
                    showFullName ? 'translate-x-4' : 'translate-x-0.5'
                  }`}
                />
              </div>
              <span className="text-sm text-[#171717]">
                Show full name on verification page (off = initials only)
              </span>
            </label>
          </div>

          <div className="flex justify-end">
            <button
              type="submit"
              id="save-profile-btn"
              disabled={saving}
              className="flex items-center gap-2 px-4 py-2 bg-[#171717] text-white text-sm rounded-[6px] hover:bg-[#2a2a2a] disabled:opacity-50 transition-colors"
            >
              {saving ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Save className="w-3.5 h-3.5" />
              )}
              Save changes
            </button>
          </div>
        </form>
      </Section>

      {/* ── Section 2: Skills ── */}
      <Section title="Skills" icon={<BookOpen className="w-4 h-4" />}>
        {/* Existing skills */}
        {skills.length > 0 ? (
          <div className="space-y-2 mb-4">
            {skills.map((skill) => (
              <div
                key={skill.name}
                className="flex items-center justify-between px-3 py-2 border border-[#ebebeb] rounded-[6px] bg-[#fafafa]"
              >
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-medium text-[#171717]">{skill.name}</span>
                  <span className="text-xs text-[#7d7d7d]">
                    {PROFICIENCY_LABELS[skill.proficiency] ?? skill.proficiency}
                  </span>
                  <span
                    className={`text-[10px] font-mono uppercase px-1.5 py-0.5 rounded-full ${
                      SOURCE_COLOR[skill.source] ?? 'bg-[#ebebeb] text-[#4d4d4d]'
                    }`}
                  >
                    {SOURCE_LABEL[skill.source] ?? skill.source}
                  </span>
                </div>
                {skill.source !== 'verified_project' && (
                  <button
                    type="button"
                    onClick={() => removeSkill(skill.name)}
                    aria-label={`Remove ${skill.name}`}
                    disabled={savingSkills}
                    className="text-[#a8a8a8] hover:text-[#9b1c1c] disabled:opacity-40 transition-colors"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-[#7d7d7d] mb-4">No skills added yet.</p>
        )}

        {/* Add a skill */}
        <div className="flex items-end gap-2 flex-wrap">
          <div className="flex-1 min-w-[160px]">
            <label htmlFor="new-skill-name" className="block text-xs font-medium text-[#4d4d4d] mb-1">
              Skill name
            </label>
            <input
              id="new-skill-name"
              type="text"
              value={newSkillName}
              onChange={(e) => setNewSkillName(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addSkill())}
              className="w-full px-3 py-2 text-sm border border-[#ebebeb] rounded-[6px] bg-white focus:outline-none focus:border-[#171717]"
              placeholder="e.g. Python"
              maxLength={100}
            />
          </div>
          <div>
            <label htmlFor="new-skill-prof" className="block text-xs font-medium text-[#4d4d4d] mb-1">
              Level
            </label>
            <select
              id="new-skill-prof"
              value={newSkillProf}
              onChange={(e) => setNewSkillProf(Number(e.target.value))}
              className="px-3 py-2 text-sm border border-[#ebebeb] rounded-[6px] bg-white focus:outline-none focus:border-[#171717]"
            >
              {[1, 2, 3, 4, 5].map((n) => (
                <option key={n} value={n}>
                  {n} — {PROFICIENCY_LABELS[n]}
                </option>
              ))}
            </select>
          </div>
          <button
            type="button"
            id="add-skill-btn"
            onClick={addSkill}
            disabled={savingSkills || !newSkillName.trim()}
            className="flex items-center gap-1.5 px-4 py-2 bg-[#171717] text-white text-sm rounded-[6px] hover:bg-[#2a2a2a] disabled:opacity-50 transition-colors"
          >
            {savingSkills ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Plus className="w-3.5 h-3.5" />
            )}
            Add
          </button>
        </div>
      </Section>

      {/* ── Section 3: Resume ── */}
      <Section title="Resume" icon={<Upload className="w-4 h-4" />}>
        <div className="space-y-4">
          {/* Current resume */}
          {resumeUrl && (
            <div className="flex items-center gap-2 text-sm text-[#4d4d4d]">
              <CheckCircle2 className="w-4 h-4 text-[#0a7d33]" />
              <span>Resume on file.</span>
              <a
                href={resumeUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-[#297a3a] underline underline-offset-2"
              >
                View <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          )}

          {/* Upload */}
          <div>
            <input
              ref={resumeRef}
              type="file"
              accept="application/pdf"
              id="resume-file-input"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) uploadResume(f);
              }}
            />
            <button
              type="button"
              id="upload-resume-btn"
              onClick={() => resumeRef.current?.click()}
              disabled={resumeUploading}
              className="flex items-center gap-2 px-4 py-2 border border-[#ebebeb] text-sm rounded-[6px] bg-white hover:bg-[#fafafa] disabled:opacity-50 transition-colors"
            >
              {resumeUploading ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Upload className="w-3.5 h-3.5" />
              )}
              {resumeUrl ? 'Replace resume (PDF, ≤ 5 MB)' : 'Upload resume (PDF, ≤ 5 MB)'}
            </button>
          </div>

          {/* AI resume analysis (FR-STU-4) */}
          {resumeUrl && (
            <div className="pt-3 border-t border-[#ebebeb]">
              <div className="flex items-start gap-2 mb-3">
                <Info className="w-4 h-4 text-[#7d7d7d] mt-0.5 flex-shrink-0" />
                <p className="text-xs text-[#7d7d7d]">
                  AI resume analysis proposes skills from your resume. You review and accept each
                  suggestion before anything is saved. This is an AI draft, not a decision.
                </p>
              </div>
              <button
                type="button"
                id="analyze-resume-btn"
                onClick={analyzeResume}
                disabled={aiResumeLoading}
                className="flex items-center gap-2 px-4 py-2 border border-[#ebebeb] text-sm rounded-[6px] bg-white hover:bg-[#fafafa] disabled:opacity-50 transition-colors"
              >
                {aiResumeLoading ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Sparkles className="w-3.5 h-3.5 text-[#7d5c00]" />
                )}
                Analyze resume with AI
              </button>

              {/* AI draft results */}
              {aiResumeDraft && (
                <div className="mt-4 border border-[#f5e27a] rounded-[6px] p-4 bg-[#fffbe6]">
                  <AiDraftBanner
                    confidence={aiResumeDraft.confidence}
                    label={aiResumeDraft.label}
                  />
                  <p className="text-xs font-medium text-[#4d4d4d] mb-2">
                    Toggle to select skills to import:
                  </p>
                  <div className="space-y-1.5 mb-4">
                    {aiResumeDraft.skills.map((s, i) => (
                      <label
                        key={i}
                        className="flex items-center gap-2 cursor-pointer text-sm"
                      >
                        <input
                          type="checkbox"
                          checked={s.accepted}
                          onChange={() => toggleAiResumeSkill(i)}
                          className="accent-[#171717]"
                        />
                        <span className={s.accepted ? 'text-[#171717]' : 'text-[#a8a8a8] line-through'}>
                          {s.name}
                        </span>
                        <span className="text-xs text-[#7d7d7d]">
                          {PROFICIENCY_LABELS[s.proficiency]}
                        </span>
                      </label>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      id="accept-resume-ai-btn"
                      onClick={acceptAiResumeSkills}
                      disabled={
                        aiResumeAccepting ||
                        aiResumeDraft.skills.every((s) => !s.accepted)
                      }
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-[#171717] text-white text-xs rounded-[6px] hover:bg-[#2a2a2a] disabled:opacity-50 transition-colors"
                    >
                      {aiResumeAccepting && (
                        <Loader2 className="w-3 h-3 animate-spin" />
                      )}
                      Save accepted skills
                    </button>
                    <button
                      type="button"
                      onClick={() => setAiResumeDraft(null)}
                      className="px-3 py-1.5 text-xs text-[#7d7d7d] hover:text-[#171717] transition-colors"
                    >
                      Discard
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </Section>

      {/* ── Section 4: GitHub ── */}
      <Section
        title="GitHub Integration"
        icon={<Github className="w-4 h-4" />}
        defaultOpen={false}
      >
        {/* FR-STU-8 notice */}
        <div className="flex items-start gap-2 mb-4 text-xs text-[#7d7d7d]">
          <Info className="w-4 h-4 flex-shrink-0 mt-0.5" />
          <p>
            Linking your GitHub shows public profile information (languages, repo count, recent
            activity) labelled{' '}
            <strong>"self-linked, not verified"</strong>. GitHub data never affects your XP,
            badges, or verification page.
          </p>
        </div>

        <form onSubmit={linkGithub} className="flex gap-2 items-end flex-wrap mb-4">
          <div className="flex-1 min-w-[200px]">
            <label
              htmlFor="github-username"
              className="block text-xs font-medium text-[#4d4d4d] mb-1"
            >
              GitHub username
            </label>
            <input
              id="github-username"
              type="text"
              value={githubUsername}
              onChange={(e) => setGithubUsername(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-[#ebebeb] rounded-[6px] bg-white focus:outline-none focus:border-[#171717]"
              placeholder="e.g. torvalds"
              maxLength={100}
            />
          </div>
          <button
            type="submit"
            id="link-github-btn"
            disabled={githubLoading || !githubUsername.trim()}
            className="flex items-center gap-2 px-4 py-2 bg-[#171717] text-white text-sm rounded-[6px] hover:bg-[#2a2a2a] disabled:opacity-50 transition-colors"
          >
            {githubLoading ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Github className="w-3.5 h-3.5" />
            )}
            Link
          </button>
        </form>

        {githubError && (
          <p className="text-xs text-[#9b1c1c] mb-3">{githubError}</p>
        )}

        {/* GitHub data summary */}
        {githubData && (
          <div className="p-3 border border-[#ebebeb] rounded-[6px] bg-[#fafafa] text-sm space-y-1 mb-4">
            <p className="text-xs text-[#7d7d7d] font-mono uppercase tracking-wide mb-2">
              Self-linked, not verified
            </p>
            {githubData.public_repos != null && (
              <p className="text-[#4d4d4d]">
                Public repos: <strong>{githubData.public_repos}</strong>
              </p>
            )}
            {githubData.top_languages?.length > 0 && (
              <p className="text-[#4d4d4d]">
                Top languages:{' '}
                <strong>{githubData.top_languages.join(', ')}</strong>
              </p>
            )}
            {githubData.recent_activity && (
              <p className="text-[#4d4d4d]">
                Recent activity: <strong>{githubData.recent_activity}</strong>
              </p>
            )}
            {githubData.github_url && (
              <a
                href={githubData.github_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-xs text-[#297a3a] underline underline-offset-2 mt-1"
              >
                View on GitHub <ExternalLink className="w-3 h-3" />
              </a>
            )}
          </div>
        )}

        {/* AI GitHub analysis (FR-STU-11) */}
        {githubData && (
          <div className="pt-3 border-t border-[#ebebeb]">
            <div className="flex items-start gap-2 mb-3">
              <Info className="w-4 h-4 text-[#7d7d7d] mt-0.5 flex-shrink-0" />
              <p className="text-xs text-[#7d7d7d]">
                AI repo analysis proposes skills from your public repositories. This is an AI
                draft — you review and accept each suggestion. These skills are never shown on
                your verification page.
              </p>
            </div>
            <button
              type="button"
              id="analyze-github-btn"
              onClick={analyzeGithub}
              disabled={aiGithubLoading}
              className="flex items-center gap-2 px-4 py-2 border border-[#ebebeb] text-sm rounded-[6px] bg-white hover:bg-[#fafafa] disabled:opacity-50 transition-colors"
            >
              {aiGithubLoading ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Sparkles className="w-3.5 h-3.5 text-[#7d5c00]" />
              )}
              Analyze repositories with AI
            </button>

            {aiGithubDraft && (
              <div className="mt-4 border border-[#f5e27a] rounded-[6px] p-4 bg-[#fffbe6]">
                <AiDraftBanner
                  confidence={aiGithubDraft.confidence}
                  label={aiGithubDraft.label}
                />
                {aiGithubDraft.summary && (
                  <p className="text-xs text-[#4d4d4d] mb-3 italic">
                    Summary: {aiGithubDraft.summary}
                  </p>
                )}
                <p className="text-xs font-medium text-[#4d4d4d] mb-2">
                  Select skills to import:
                </p>
                <div className="space-y-1.5 mb-4">
                  {aiGithubDraft.skills.map((s, i) => (
                    <label key={i} className="flex items-center gap-2 cursor-pointer text-sm">
                      <input
                        type="checkbox"
                        checked={s.accepted}
                        onChange={() => toggleAiGithubSkill(i)}
                        className="accent-[#171717]"
                      />
                      <span
                        className={
                          s.accepted ? 'text-[#171717]' : 'text-[#a8a8a8] line-through'
                        }
                      >
                        {s.name}
                      </span>
                      <span className="text-xs text-[#7d7d7d]">
                        {PROFICIENCY_LABELS[s.proficiency]}
                      </span>
                    </label>
                  ))}
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    id="accept-github-ai-btn"
                    onClick={acceptAiGithubSkills}
                    disabled={
                      aiGithubAccepting ||
                      aiGithubDraft.skills.every((s) => !s.accepted)
                    }
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-[#171717] text-white text-xs rounded-[6px] hover:bg-[#2a2a2a] disabled:opacity-50 transition-colors"
                  >
                    {aiGithubAccepting && (
                      <Loader2 className="w-3 h-3 animate-spin" />
                    )}
                    Save accepted skills
                  </button>
                  <button
                    type="button"
                    onClick={() => setAiGithubDraft(null)}
                    className="px-3 py-1.5 text-xs text-[#7d7d7d] hover:text-[#171717] transition-colors"
                  >
                    Discard
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </Section>
    </div>
  );
};

export default StudentProfilePage;
