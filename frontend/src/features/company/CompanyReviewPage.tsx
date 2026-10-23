/**
 * CompanyReviewPage — FR-EVL-1 to 7, FR-WRK-3
 * Route: /company/submissions/:submissionId/review
 * Shows submission details, check-ins to review, and evaluation rubric form.
 * Note: Certificates are issued server-side; this page never renders a "Verified" state from local data.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { apiRequest, ApiException } from '../../lib/api';

// ─── Types ─────────────────────────────────────────────────────────────────────

interface SubmissionDetail {
  id: string;
  application_id: string;
  version: number;
  repo_url: string | null;
  file_key: string | null;
  notes: string | null;
  submitted_at: string;
}

interface EvaluationResult {
  id: string;
  overall_score: number;
  decision: 'approved' | 'changes_requested' | 'rejected';
  feedback: string;
  public_summary: string | null;
  used_ai_draft: boolean;
  evaluated_at: string;
}

// ─── Helpers ───────────────────────────────────────────────────────────────────

const DECISION_CONFIG = {
  approved:          { icon: '✓', label: 'Approved',          color: '#297a3a', bg: '#f0fdf4' },
  changes_requested: { icon: '△', label: 'Changes Requested', color: '#7d7d7d', bg: '#fafafa' },
  rejected:          { icon: '✕', label: 'Rejected',          color: '#c4231c', bg: '#fef2f2' },
};

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
}

// ─── RubricRow component ────────────────────────────────────────────────────────

interface RubricRowProps {
  label: string;
  field: string;
  value: number;
  onChange: (field: string, val: number) => void;
}

const RubricRow: React.FC<RubricRowProps> = ({ label, field, value, onChange }) => (
  <div className="flex items-center gap-4 py-2">
    <label
      htmlFor={`rubric-${field}`}
      className="flex-1 text-sm"
      style={{ color: '#4d4d4d' }}
    >
      {label}
    </label>
    <div className="flex items-center gap-2">
      <input
        id={`rubric-${field}`}
        type="range"
        min={0}
        max={100}
        step={5}
        value={value}
        onChange={e => onChange(field, Number(e.target.value))}
        className="w-28 accent-[#171717]"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={value}
      />
      <span className="font-mono text-sm w-8 text-right" style={{ color: '#171717' }}>{value}</span>
    </div>
  </div>
);

// ─── Main Page ─────────────────────────────────────────────────────────────────

export const CompanyReviewPage: React.FC = () => {
  const { submissionId } = useParams<{ submissionId: string }>();
  const navigate = useNavigate();

  const [submission, setSubmission] = useState<SubmissionDetail | null>(null);
  const [evaluation, setEvaluation] = useState<EvaluationResult | null>(null);
  const [loading, setLoading]       = useState(true);
  const [error, setError]           = useState<string | null>(null);

  // Rubric fields (FR-EVL-2 — scores are company's subjective assessment)
  const [rubric, setRubric]         = useState<Record<string, number>>({
    code_quality:    70,
    documentation:  70,
    requirements:   70,
    testing:        70,
  });
  const [decision, setDecision]     = useState<'approved' | 'changes_requested' | 'rejected'>('approved');
  const [feedback, setFeedback]     = useState('');
  const [publicSummary, setPublicSummary] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitSuccess, setSubmitSuccess] = useState(false);

  // Phase 7: AI Feedback Drafter (FR-EVL-5) & Mentor Usage (FR-WRK-5)
  const [usedAiDraft, setUsedAiDraft] = useState(false);
  const [showAiDrafter, setShowAiDrafter] = useState(false);
  const [roughNotes, setRoughNotes] = useState('');
  const [draftingBusy, setDraftingBusy] = useState(false);
  const [draftErr, setDraftErr] = useState<string | null>(null);
  const [mentorUsage, setMentorUsage] = useState<{ total_exchanges: number; note: string } | null>(null);

  const fetchData = useCallback(async () => {
    if (!submissionId) return;
    try {
      const sub = await apiRequest<SubmissionDetail>(`/submissions/${submissionId}`);
      setSubmission(sub);

      // Check if already evaluated
      try {
        const ev = await apiRequest<EvaluationResult>(`/submissions/${submissionId}/evaluation`);
        setEvaluation(ev);
      } catch { /* not yet evaluated */ }

      // Fetch student mentor usage (FR-WRK-5)
      if (sub.application_id) {
        try {
          const usage = await apiRequest<{ total_exchanges: number; note: string }>(
            `/applications/${sub.application_id}/mentor-usage`
          );
          setMentorUsage(usage);
        } catch { /* mentor usage optional */ }
      }
    } catch (e) {
      setError(e instanceof ApiException ? e.message : 'Failed to load submission');
    } finally { setLoading(false); }
  }, [submissionId]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const updateRubric = (field: string, val: number) =>
    setRubric(prev => ({ ...prev, [field]: val }));

  // Draft feedback with AI (FR-EVL-5)
  const draftFeedbackWithAi = async () => {
    if (!submissionId || !roughNotes.trim()) return;
    setDraftingBusy(true);
    setDraftErr(null);
    try {
      const res = await apiRequest<{
        ai: { label: string };
        result: {
          strengths: string[];
          improvements: string[];
          next_steps: string[];
          suggested_public_summary: string;
        };
      }>('/ai/evaluations/draft-feedback', {
        method: 'POST',
        body: JSON.stringify({
          submission_id: submissionId,
          rough_notes: roughNotes.trim(),
          rubric_scores: rubric,
        }),
      });

      const structuredFeedback = [
        'Strengths:',
        ...(res.result.strengths || []).map(s => `- ${s}`),
        '',
        'Areas for Improvement:',
        ...(res.result.improvements || []).map(i => `- ${i}`),
        '',
        'Next Steps:',
        ...(res.result.next_steps || []).map(n => `- ${n}`),
      ].join('\n');

      setFeedback(structuredFeedback);
      if (res.result.suggested_public_summary) {
        setPublicSummary(res.result.suggested_public_summary);
      }
      setUsedAiDraft(true);
      setShowAiDrafter(false);
    } catch (e) {
      setDraftErr(e instanceof ApiException ? e.message : 'AI drafting failed');
    } finally {
      setDraftingBusy(false);
    }
  };

  // Overall score = average of rubric fields, clamped 0–100
  const overallScore = Math.round(
    Object.values(rubric).reduce((a, b) => a + b, 0) / Object.keys(rubric).length
  );

  // FR-EVL-3: Approved requires overall_score >= 60
  const approveBlocked = decision === 'approved' && overallScore < 60;

  const submitEvaluation = async () => {
    if (!submissionId) return;
    if (!feedback.trim()) { setSubmitError('Feedback is required.'); return; }
    if (approveBlocked) { setSubmitError('Score must be ≥ 60 to approve.'); return; }

    setSubmitting(true);
    setSubmitError(null);
    try {
      await apiRequest(`/submissions/${submissionId}/evaluation`, {
        method: 'POST',
        body: JSON.stringify({
          rubric_scores: rubric,
          overall_score: overallScore,
          feedback: feedback.trim(),
          public_summary: publicSummary.trim() || null,
          decision,
          used_ai_draft: usedAiDraft,
        }),
      });
      setSubmitSuccess(true);
      fetchData(); // reload to show result
    } catch (e) {
      setSubmitError(e instanceof ApiException ? e.message : 'Evaluation failed');
    } finally { setSubmitting(false); }
  };

  // ── Render ──────────────────────────────────────────────────────────────────

  if (loading) return (
    <div className="min-h-[50vh] flex items-center justify-center">
      <span className="font-mono text-xs" style={{ color: '#8f8f8f' }}>Loading review…</span>
    </div>
  );

  if (error || !submission) return (
    <div className="max-w-xl mx-auto px-6 py-16 text-center">
      <p className="font-mono text-sm" style={{ color: '#c4231c' }}>{error || 'Submission not found.'}</p>
      <button onClick={() => navigate(-1)} className="mt-4 text-sm underline" style={{ color: '#4d4d4d' }}>
        Go back
      </button>
    </div>
  );

  return (
    <div className="max-w-[1280px] mx-auto px-6 py-10">
      {/* ── Header ── */}
      <div className="mb-8">
        <button
          onClick={() => navigate('/company')}
          className="font-mono text-xs uppercase tracking-wider mb-4 flex items-center gap-1"
          style={{ color: '#8f8f8f' }}
        >
          ← Dashboard
        </button>
        <p className="font-mono text-[11px] uppercase tracking-widest mb-1" style={{ color: '#8f8f8f' }}>
          Submission Review
        </p>
        <h1 className="text-[30px] font-normal leading-tight" style={{ letterSpacing: '-1.5px', color: '#171717' }}>
          Submission v{submission.version}
        </h1>
        <p className="font-mono text-[11px] uppercase tracking-widest mt-1" style={{ color: '#8f8f8f' }}>
          Submitted {fmtDate(submission.submitted_at)}
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* ── Left: Submission info + evaluation form ── */}
        <div className="lg:col-span-2 space-y-6">

          {/* Submission details card */}
          <div className="rounded-[6px] p-5"
            style={{ background: '#ffffff', boxShadow: '0 0 0 1px rgba(0,0,0,0.08), 0 0 0 2px #fafafa' }}>
            <h2 className="font-mono text-[11px] uppercase tracking-widest mb-4" style={{ color: '#8f8f8f' }}>
              Deliverable
            </h2>
            {submission.repo_url ? (
              <div className="flex items-center gap-3 py-3 px-4 rounded-[6px]"
                style={{ background: '#fafafa', border: '1px solid #ebebeb' }}>
                <span className="font-mono text-sm" style={{ color: '#171717' }}>▲</span>
                <div className="flex-1 min-w-0">
                  <p className="font-mono text-[11px] uppercase tracking-widest mb-1" style={{ color: '#8f8f8f' }}>
                    Repository
                  </p>
                  <a
                    href={submission.repo_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm underline break-all"
                    style={{ color: '#297a3a' }}
                  >
                    {submission.repo_url}
                  </a>
                </div>
              </div>
            ) : (
              <p className="text-sm" style={{ color: '#8f8f8f' }}>File submission (no URL)</p>
            )}
            {submission.notes && (
              <div className="mt-4 pt-4 border-t" style={{ borderColor: '#ebebeb' }}>
                <p className="font-mono text-[11px] uppercase tracking-widest mb-2" style={{ color: '#8f8f8f' }}>
                  Student Notes
                </p>
                <p className="text-sm" style={{ color: '#4d4d4d' }}>{submission.notes}</p>
              </div>
            )}
          </div>

          {/* Already evaluated */}
          {evaluation ? (
            <div className="rounded-[6px] p-5"
              style={{ background: '#ffffff', boxShadow: '0 0 0 1px rgba(0,0,0,0.08), 0 0 0 2px #fafafa' }}>
              <h2 className="font-mono text-[11px] uppercase tracking-widest mb-4" style={{ color: '#8f8f8f' }}>
                Evaluation Result
              </h2>

              {/* Decision badge */}
              {(() => {
                const dc = DECISION_CONFIG[evaluation.decision];
                return (
                  <div className="flex items-center gap-3 mb-4 p-3 rounded-[6px]"
                    style={{ background: dc.bg, border: `1px solid ${dc.color}22` }}>
                    <span className="font-mono text-lg" style={{ color: dc.color }} aria-hidden="true">
                      {dc.icon}
                    </span>
                    <div>
                      <p className="font-mono text-[11px] uppercase tracking-widest" style={{ color: dc.color }}>
                        {dc.label}
                      </p>
                      <p className="font-mono text-2xl font-medium mt-0.5" style={{ color: '#171717' }}>
                        {evaluation.overall_score}<span className="text-sm font-normal" style={{ color: '#8f8f8f' }}>/100</span>
                      </p>
                    </div>
                  </div>
                );
              })()}

              {/* Feedback */}
              <div className="mb-4">
                <p className="font-mono text-[11px] uppercase tracking-widest mb-2" style={{ color: '#8f8f8f' }}>
                  Feedback
                </p>
                <p className="text-sm" style={{ color: '#4d4d4d', whiteSpace: 'pre-wrap' }}>{evaluation.feedback}</p>
              </div>

              {evaluation.public_summary && (
                <div className="mt-4 pt-4 border-t" style={{ borderColor: '#ebebeb' }}>
                  <p className="font-mono text-[11px] uppercase tracking-widest mb-2" style={{ color: '#8f8f8f' }}>
                    Public Summary
                  </p>
                  <p className="text-sm" style={{ color: '#4d4d4d' }}>{evaluation.public_summary}</p>
                </div>
              )}

              {evaluation.used_ai_draft && (
                <p className="mt-3 font-mono text-[10px] uppercase tracking-widest" style={{ color: '#c9c9c9' }}>
                  AI draft — reviewed and accepted by evaluator
                </p>
              )}

              <p className="mt-2 font-mono text-[10px]" style={{ color: '#c9c9c9' }}>
                Evaluated {fmtDate(evaluation.evaluated_at)}
              </p>
            </div>
          ) : (
            /* Evaluation form */
            <div className="rounded-[6px] p-5"
              style={{ background: '#ffffff', boxShadow: '0 0 0 1px rgba(0,0,0,0.08), 0 0 0 2px #fafafa' }}>
              <h2 className="font-mono text-[11px] uppercase tracking-widest mb-4" style={{ color: '#8f8f8f' }}>
                Evaluation
              </h2>

              {/* Rubric scores */}
              <div className="mb-6">
                <p className="font-mono text-[11px] uppercase tracking-widest mb-3" style={{ color: '#8f8f8f' }}>
                  Rubric Scores
                </p>
                <div className="divide-y" style={{ borderColor: '#ebebeb' }}>
                  <RubricRow label="Code Quality"    field="code_quality"   value={rubric.code_quality}   onChange={updateRubric} />
                  <RubricRow label="Documentation"   field="documentation"  value={rubric.documentation}  onChange={updateRubric} />
                  <RubricRow label="Requirements Met" field="requirements"  value={rubric.requirements}   onChange={updateRubric} />
                  <RubricRow label="Testing"          field="testing"       value={rubric.testing}        onChange={updateRubric} />
                </div>

                {/* Overall score display */}
                <div className="mt-4 p-3 rounded-[6px] flex items-center justify-between"
                  style={{ background: '#fafafa', border: '1px solid #ebebeb' }}>
                  <span className="font-mono text-[11px] uppercase tracking-widest" style={{ color: '#8f8f8f' }}>
                    Overall Score
                  </span>
                  <span
                    className="font-mono text-2xl"
                    style={{ color: overallScore >= 60 ? '#171717' : '#c4231c' }}
                    aria-live="polite"
                    aria-label={`Overall score: ${overallScore} out of 100`}
                  >
                    {overallScore}<span className="text-sm" style={{ color: '#8f8f8f' }}>/100</span>
                  </span>
                </div>
                {overallScore < 60 && decision === 'approved' && (
                  <p className="mt-2 font-mono text-[10px] uppercase tracking-widest" style={{ color: '#c4231c' }}>
                    Score must be ≥ 60 to approve
                  </p>
                )}
              </div>

              {/* Decision */}
              <div className="mb-6">
                <p className="font-mono text-[11px] uppercase tracking-widest mb-3" style={{ color: '#8f8f8f' }}>
                  Decision
                </p>
                <div className="flex gap-2 flex-wrap" role="group" aria-label="Evaluation decision">
                  {(Object.keys(DECISION_CONFIG) as Array<keyof typeof DECISION_CONFIG>).map(opt => {
                    const dc = DECISION_CONFIG[opt];
                    const selected = decision === opt;
                    return (
                      <button
                        key={opt}
                        id={`decision-${opt}`}
                        onClick={() => setDecision(opt)}
                        aria-pressed={selected}
                        className="flex items-center gap-2 px-3 py-2 rounded-[6px] text-sm transition-all"
                        style={{
                          border: selected ? `1px solid ${dc.color}` : '1px solid #ebebeb',
                          background: selected ? dc.bg : '#fafafa',
                          color: selected ? dc.color : '#4d4d4d',
                          fontFamily: 'inherit',
                        }}
                      >
                        <span aria-hidden="true">{dc.icon}</span>
                        {dc.label}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* AI Feedback Drafter Trigger (FR-EVL-5) */}
              <div className="mb-4 p-3.5 rounded-[6px] border border-[#ebebeb]" style={{ background: '#fafafa' }}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm" style={{ color: '#297a3a' }}>✦</span>
                    <span className="font-mono text-xs uppercase tracking-wider" style={{ color: '#171717' }}>
                      AI Feedback Drafter
                    </span>
                    <span className="font-mono text-[10px] px-1.5 py-0.5 rounded-[4px]"
                      style={{ background: '#f5f5f5', color: '#737373', border: '1px solid #e5e5e5' }}>
                      AI draft
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => setShowAiDrafter(!showAiDrafter)}
                    className="font-mono text-xs uppercase tracking-wider underline"
                    style={{ color: '#297a3a' }}
                  >
                    {showAiDrafter ? 'Hide Drafter' : 'Draft with AI'}
                  </button>
                </div>

                {showAiDrafter && (
                  <div className="mt-3 space-y-2.5 pt-3 border-t border-[#ebebeb]">
                    <p className="text-xs" style={{ color: '#737373' }}>
                      Enter your rough reviewer notes (observations, bugs, code style). AI will synthesize structured feedback and a public summary grounded strictly in your notes.
                    </p>
                    <textarea
                      rows={3}
                      value={roughNotes}
                      onChange={e => setRoughNotes(e.target.value)}
                      placeholder="e.g. Great tests and structure. Missed pagination on list endpoint. Strong error handling..."
                      className="w-full text-xs px-3 py-2 rounded-[6px] outline-none"
                      style={{ border: '1px solid #ebebeb', background: '#ffffff', color: '#171717' }}
                    />
                    {draftErr && (
                      <p className="text-xs font-mono" style={{ color: '#c4231c' }}>{draftErr}</p>
                    )}
                    <button
                      type="button"
                      onClick={draftFeedbackWithAi}
                      disabled={draftingBusy || !roughNotes.trim()}
                      className="px-3 py-1.5 text-xs rounded-[6px] font-mono uppercase tracking-wider"
                      style={{
                        background: '#171717',
                        color: '#ffffff',
                        opacity: draftingBusy || !roughNotes.trim() ? 0.5 : 1,
                      }}
                    >
                      {draftingBusy ? 'Synthesizing Feedback…' : 'Generate Structured Draft'}
                    </button>
                  </div>
                )}
              </div>

              {/* Feedback */}
              <div className="mb-4">
                <div className="flex items-center justify-between mb-2">
                  <label
                    htmlFor="eval-feedback"
                    className="block font-mono text-[11px] uppercase tracking-widest"
                    style={{ color: '#8f8f8f' }}
                  >
                    Feedback <span style={{ color: '#c4231c' }}>*</span>
                  </label>
                  {usedAiDraft && (
                    <span className="font-mono text-[10px] px-1.5 py-0.5 rounded-[4px]"
                      style={{ background: '#f5f5f5', color: '#737373', border: '1px solid #e5e5e5' }}>
                      AI draft (review and accept)
                    </span>
                  )}
                </div>
                <textarea
                  id="eval-feedback"
                  rows={6}
                  value={feedback}
                  onChange={e => setFeedback(e.target.value)}
                  placeholder="Detailed feedback for the student…"
                  className="w-full text-sm px-3 py-2 rounded-[6px] outline-none resize-y"
                  style={{ border: '1px solid #ebebeb', background: '#fafafa', color: '#171717' }}
                />
              </div>

              {/* Public summary (appears on certificate if approved) */}
              <div className="mb-6">
                <label
                  htmlFor="eval-public"
                  className="block font-mono text-[11px] uppercase tracking-widest mb-2"
                  style={{ color: '#8f8f8f' }}
                >
                  Public Summary
                  <span className="ml-1 normal-case text-[10px]" style={{ color: '#c9c9c9' }}>
                    (shown on certificate — platform record, not employment)
                  </span>
                </label>
                <textarea
                  id="eval-public"
                  rows={3}
                  value={publicSummary}
                  onChange={e => setPublicSummary(e.target.value)}
                  placeholder="Brief public summary of the student's work…"
                  className="w-full text-sm px-3 py-2 rounded-[6px] outline-none resize-none"
                  style={{ border: '1px solid #ebebeb', background: '#fafafa', color: '#171717' }}
                />
              </div>

              {submitError && (
                <div className="mb-4 px-3 py-2 rounded-[6px] font-mono text-xs" style={{ background: '#fef2f2', color: '#c4231c', border: '1px solid #fecaca' }}>
                  {submitError}
                </div>
              )}
              {submitSuccess && (
                <div className="mb-4 px-3 py-2 rounded-[6px] font-mono text-xs" style={{ background: '#f0fdf4', color: '#297a3a', border: '1px solid #bbf7d0' }}>
                  ✓ Evaluation submitted successfully
                </div>
              )}

              <button
                onClick={submitEvaluation}
                disabled={submitting || approveBlocked}
                className="w-full py-3 text-sm rounded-[6px] font-medium transition-opacity"
                style={{ background: '#171717', color: '#ffffff', opacity: submitting || approveBlocked ? 0.5 : 1 }}
              >
                {submitting ? 'Submitting…' : 'Submit Evaluation'}
              </button>

              <p className="mt-3 text-xs text-center" style={{ color: '#c9c9c9' }}>
                This action is final. The student will be notified immediately.
              </p>
            </div>
          )}
        </div>

        {/* ── Sidebar ── */}
        <div className="space-y-6">
          {/* Quick info */}
          <div className="rounded-[6px] p-4"
            style={{ background: '#ffffff', boxShadow: '0 0 0 1px rgba(0,0,0,0.08), 0 0 0 2px #fafafa' }}>
            <h3 className="font-mono text-[11px] uppercase tracking-widest mb-3" style={{ color: '#8f8f8f' }}>
              Submission Info
            </h3>
            <dl className="space-y-2 text-sm">
              {[
                ['Version',   `v${submission.version}`],
                ['Submitted', fmtDate(submission.submitted_at)],
              ].map(([label, val]) => (
                <div key={label} className="flex justify-between gap-2">
                  <dt className="font-mono text-[11px] uppercase tracking-widest" style={{ color: '#8f8f8f' }}>{label}</dt>
                  <dd style={{ color: '#171717' }}>{val}</dd>
                </div>
              ))}
            </dl>
          </div>

          {/* Student Mentor Usage (FR-WRK-5) */}
          {mentorUsage && (
            <div className="rounded-[6px] p-4"
              style={{ background: '#ffffff', boxShadow: '0 0 0 1px rgba(0,0,0,0.08), 0 0 0 2px #fafafa' }}>
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-mono text-[11px] uppercase tracking-widest" style={{ color: '#8f8f8f' }}>
                  AI Mentor Usage
                </h3>
                <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded-[4px]"
                  style={{ background: '#fafafa', border: '1px solid #ebebeb', color: '#171717' }}>
                  {mentorUsage.total_exchanges} exchanges
                </span>
              </div>
              <p className="text-xs leading-relaxed" style={{ color: '#737373' }}>
                {mentorUsage.note}
              </p>
            </div>
          )}

          {/* Evaluation guide */}
          <div className="rounded-[6px] p-4"
            style={{ background: '#171717' }}>
            <p className="font-mono text-[11px] uppercase tracking-widest mb-3" style={{ color: '#c9c9c9' }}>
              Evaluation Guide
            </p>
            <ul className="space-y-2 text-xs" style={{ color: '#8f8f8f' }}>
              <li><span style={{ color: '#297a3a' }}>✓ Approved</span> — Score ≥ 60. Certificate issued automatically.</li>
              <li><span style={{ color: '#7d7d7d' }}>△ Changes Requested</span> — Student may resubmit once within 7 days.</li>
              <li><span style={{ color: '#c4231c' }}>✕ Rejected</span> — Project closed, no resubmission.</li>
            </ul>
            <p className="mt-3 text-[10px] font-mono" style={{ color: '#666666' }}>
              A certificate is a platform record, not formal employment experience.
            </p>
          </div>

          {/* View workspace link */}
          {submission.application_id && (
            <button
              onClick={() => navigate(`/company/applications/${submission.application_id}/review`)}
              className="w-full py-2 text-sm rounded-[6px] text-left px-4 font-mono uppercase tracking-wider"
              style={{ border: '1px solid #ebebeb', color: '#4d4d4d' }}
            >
              View All Check-ins ↗
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default CompanyReviewPage;
