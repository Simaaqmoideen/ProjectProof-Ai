/**
 * StudentWorkspacePage — FR-WRK-1 to 8
 * Route: /student/applications/:id/workspace
 */
import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { apiRequest, ApiException } from '../../lib/api';
import { useAuth } from '../../lib/auth-context';

// ─── Types ────────────────────────────────────────────────────────────────────

interface TaskItem {
  id: string;
  milestone_id: string;
  title: string;
  description: string | null;
  order_index: number;
  is_personal: boolean;
  status: 'todo' | 'in_progress' | 'done';
  completed_at: string | null;
}

interface CheckinItem {
  id: string;
  milestone_id: string;
  note: string | null;
  evidence_url: string | null;
  status: 'submitted' | 'accepted' | 'needs_work';
  submitted_at: string;
  reviewed_at: string | null;
  review_note: string | null;
}

interface Milestone {
  id: string;
  title: string;
  due_day_offset: number;
  due_date: string | null;
  is_overdue: boolean;
  tasks: TaskItem[];
  checkins: CheckinItem[];
}

interface SubmissionSummary {
  id: string;
  version: number;
  repo_url: string | null;
  file_key: string | null;
  notes: string | null;
  submitted_at: string;
}

interface WorkspaceData {
  application_id: string;
  project_id: string;
  project_title: string;
  project_difficulty: string;
  project_duration_days: number;
  company_name: string;
  student_id: string;
  student_name: string;
  status: string;
  started_at: string | null;
  due_at: string | null;
  milestones: Milestone[];
  submissions: SubmissionSummary[];
}

// ─── Status helpers ────────────────────────────────────────────────────────────

const APP_STATUS: Record<string, { icon: string; label: string; color: string }> = {
  in_progress:        { icon: '◉', label: 'In Progress',       color: '#171717' },
  changes_requested:  { icon: '△', label: 'Changes Requested', color: '#7d7d7d' },
  completed:          { icon: '✓', label: 'Completed',         color: '#297a3a' },
  failed:             { icon: '✕', label: 'Failed',            color: '#c4231c' },
  submitted:          { icon: '◯', label: 'Submitted',         color: '#7d7d7d' },
};

const CHECKIN_STATUS: Record<string, { icon: string; label: string; color: string }> = {
  submitted:  { icon: '◯', label: 'Pending Review', color: '#7d7d7d' },
  accepted:   { icon: '✓', label: 'Accepted',       color: '#297a3a' },
  needs_work: { icon: '△', label: 'Needs Work',     color: '#8f8f8f' },
};

function fmtDate(iso: string | null): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
}

// ─── TaskRow component ────────────────────────────────────────────────────────

interface TaskRowProps {
  task: TaskItem;
  applicationId: string;
  onUpdated: () => void;
  isReadOnly: boolean;
  onDelete?: (taskId: string) => void;
}

const TaskRow: React.FC<TaskRowProps> = ({ task, applicationId, onUpdated, isReadOnly, onDelete }) => {
  const [updating, setUpdating] = useState(false);

  const cycleStatus = async () => {
    if (isReadOnly || updating) return;
    const next =
      task.status === 'todo'        ? 'in_progress' :
      task.status === 'in_progress' ? 'done'        : 'todo';
    setUpdating(true);
    try {
      await apiRequest(`/applications/${applicationId}/tasks/${task.id}/progress`, {
        method: 'PUT',
        body: JSON.stringify({ status: next }),
      });
      onUpdated();
    } catch { /* ignore */ } finally { setUpdating(false); }
  };

  const checkIcon  = task.status === 'done' ? '✓' : task.status === 'in_progress' ? '◉' : '○';
  const checkColor = task.status === 'done' ? '#297a3a' : task.status === 'in_progress' ? '#171717' : '#c9c9c9';

  return (
    <div
      className="flex items-start gap-3 py-2 px-3 rounded-[6px] group"
      style={{ background: task.status === 'done' ? '#fafafa' : 'transparent' }}
    >
      <button
        onClick={cycleStatus}
        disabled={isReadOnly || updating}
        aria-label={`Toggle task: ${task.title}`}
        style={{ color: checkColor, fontSize: '16px', lineHeight: 1, flexShrink: 0, marginTop: 2 }}
        className="font-mono transition-colors disabled:cursor-default cursor-pointer"
      >
        {updating ? '…' : checkIcon}
      </button>
      <div className="flex-1 min-w-0">
        <span
          className="text-sm"
          style={{
            color: task.status === 'done' ? '#8f8f8f' : '#171717',
            textDecoration: task.status === 'done' ? 'line-through' : 'none',
          }}
        >
          {task.title}
        </span>
        {task.is_personal && (
          <span className="ml-2 font-mono uppercase text-[10px] tracking-wider" style={{ color: '#8f8f8f' }}>
            personal
          </span>
        )}
      </div>
      {task.is_personal && onDelete && !isReadOnly && (
        <button
          onClick={() => onDelete(task.id)}
          aria-label="Delete personal task"
          className="opacity-0 group-hover:opacity-100 transition-opacity text-xs font-mono"
          style={{ color: '#c9c9c9' }}
        >
          ✕
        </button>
      )}
    </div>
  );
};

// ─── Main Page ─────────────────────────────────────────────────────────────────

export const WorkspacePage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [workspace, setWorkspace]       = useState<WorkspaceData | null>(null);
  const [loading, setLoading]           = useState(true);
  const [error, setError]               = useState<string | null>(null);
  const [expandedMs, setExpandedMs]     = useState<Set<string>>(new Set());

  // Check-in state
  const [checkinMid, setCheckinMid]     = useState<string | null>(null);
  const [checkinNote, setCheckinNote]   = useState('');
  const [checkinUrl, setCheckinUrl]     = useState('');
  const [checkinBusy, setCheckinBusy]   = useState(false);
  const [checkinErr, setCheckinErr]     = useState<string | null>(null);

  // Personal task state
  const [taskMid, setTaskMid]           = useState<string | null>(null);
  const [taskTitle, setTaskTitle]       = useState('');
  const [taskBusy, setTaskBusy]         = useState(false);

  // Submission state
  const [showSubForm, setShowSubForm]   = useState(false);
  const [subRepo, setSubRepo]           = useState('');
  const [subNotes, setSubNotes]         = useState('');
  const [subBusy, setSubBusy]           = useState(false);
  const [subErr, setSubErr]             = useState<string | null>(null);

  // AI Mentor state (FR-WRK-5)
  const [mentorMid, setMentorMid]       = useState<string>('');
  const [mentorMsg, setMentorMsg]       = useState('');
  const [mentorBusy, setMentorBusy]     = useState(false);
  const [mentorErr, setMentorErr]       = useState<string | null>(null);
  const [mentorChatHistory, setMentorChatHistory] = useState<Array<{
    q: string;
    ans: string;
    nextSteps: string[];
    time: string;
  }>>([]);

  const fetchWorkspace = useCallback(async () => {
    if (!id) return;
    try {
      const data = await apiRequest<WorkspaceData>(`/applications/${id}/workspace`);
      setWorkspace(data);
      if (data.milestones.length > 0) {
        setExpandedMs(prev => { const s = new Set(prev); s.add(data.milestones[0].id); return s; });
        setMentorMid(prev => prev || data.milestones[0].id);
      }
    } catch (e) {
      setError(e instanceof ApiException ? e.message : 'Failed to load workspace');
    } finally { setLoading(false); }
  }, [id]);

  useEffect(() => { fetchWorkspace(); }, [fetchWorkspace]);

  const askMentor = async () => {
    if (!id || !mentorMsg.trim() || !mentorMid) return;
    setMentorBusy(true);
    setMentorErr(null);
    try {
      const res = await apiRequest<{
        ai: { label: string };
        result: { response: string; suggested_next_steps: string[] };
      }>('/ai/mentor/chat', {
        method: 'POST',
        body: JSON.stringify({
          application_id: id,
          milestone_id: mentorMid,
          message: mentorMsg.trim(),
        }),
      });
      setMentorChatHistory(prev => [
        {
          q: mentorMsg.trim(),
          ans: res.result.response,
          nextSteps: res.result.suggested_next_steps || [],
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
        ...prev,
      ]);
      setMentorMsg('');
    } catch (e) {
      setMentorErr(e instanceof ApiException ? e.message : 'Mentor consultation failed');
    } finally {
      setMentorBusy(false);
    }
  };

  const toggleMs = (mid: string) =>
    setExpandedMs(prev => { const s = new Set(prev); s.has(mid) ? s.delete(mid) : s.add(mid); return s; });

  const submitCheckin = async () => {
    if (!id || !checkinMid) return;
    setCheckinBusy(true); setCheckinErr(null);
    try {
      await apiRequest(`/applications/${id}/checkins`, {
        method: 'POST',
        body: JSON.stringify({ milestone_id: checkinMid, note: checkinNote || null, evidence_url: checkinUrl || null }),
      });
      setCheckinMid(null); setCheckinNote(''); setCheckinUrl('');
      fetchWorkspace();
    } catch (e) { setCheckinErr(e instanceof ApiException ? e.message : 'Failed'); }
    finally { setCheckinBusy(false); }
  };

  const createTask = async (milestoneId: string) => {
    if (!id || !taskTitle.trim()) return;
    setTaskBusy(true);
    try {
      await apiRequest(`/applications/${id}/milestones/${milestoneId}/tasks`, {
        method: 'POST',
        body: JSON.stringify({ title: taskTitle.trim() }),
      });
      setTaskMid(null); setTaskTitle(''); fetchWorkspace();
    } catch { /* ignore */ } finally { setTaskBusy(false); }
  };

  const deleteTask = async (taskId: string) => {
    if (!id) return;
    try { await apiRequest(`/applications/${id}/tasks/${taskId}`, { method: 'DELETE' }); fetchWorkspace(); }
    catch { /* ignore */ }
  };

  const submitDeliverable = async () => {
    if (!id) return;
    if (!subRepo.trim()) { setSubErr('Repository URL is required.'); return; }
    setSubBusy(true); setSubErr(null);
    try {
      await apiRequest(`/applications/${id}/submissions`, {
        method: 'POST',
        body: JSON.stringify({ repo_url: subRepo.trim(), notes: subNotes || null }),
      });
      setShowSubForm(false); setSubRepo(''); setSubNotes(''); fetchWorkspace();
    } catch (e) { setSubErr(e instanceof ApiException ? e.message : 'Submission failed'); }
    finally { setSubBusy(false); }
  };

  const isReadOnly = !workspace || (workspace.status !== 'in_progress' && workspace.status !== 'changes_requested');
  const canSubmit  = !isReadOnly && (workspace?.submissions ?? []).length < 3;

  // ── Render ──────────────────────────────────────────────────────────────────

  if (loading) return (
    <div className="min-h-[50vh] flex items-center justify-center">
      <span className="font-mono text-xs" style={{ color: '#8f8f8f' }}>Loading workspace…</span>
    </div>
  );

  if (error || !workspace) return (
    <div className="max-w-xl mx-auto px-6 py-16 text-center">
      <p className="font-mono text-sm" style={{ color: '#c4231c' }}>{error || 'Workspace not found.'}</p>
      <button onClick={() => navigate(-1)} className="mt-4 text-sm underline" style={{ color: '#4d4d4d' }}>
        Go back
      </button>
    </div>
  );

  const appSt = APP_STATUS[workspace.status] ?? { icon: '◯', label: workspace.status, color: '#7d7d7d' };

  return (
    <div className="max-w-[1280px] mx-auto px-6 py-10">
      {/* ── Header ── */}
      <div className="mb-8">
        <button
          onClick={() => navigate('/student')}
          className="font-mono text-xs uppercase tracking-wider mb-4 flex items-center gap-1"
          style={{ color: '#8f8f8f' }}
        >
          ← Dashboard
        </button>
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <p className="font-mono text-[11px] uppercase tracking-widest mb-1" style={{ color: '#8f8f8f' }}>
              {workspace.company_name}
            </p>
            <h1 className="text-[30px] font-normal leading-tight" style={{ letterSpacing: '-1.5px', color: '#171717' }}>
              {workspace.project_title}
            </h1>
            <div className="flex items-center gap-4 mt-2">
              <span className="font-mono text-[11px] uppercase tracking-widest" style={{ color: '#8f8f8f' }}>
                {workspace.project_difficulty} · {workspace.project_duration_days}d
              </span>
              <span
                className="flex items-center gap-1 font-mono text-[11px] uppercase tracking-widest"
                style={{ color: appSt.color }}
                aria-label={`Status: ${appSt.label}`}
              >
                <span aria-hidden="true">{appSt.icon}</span>
                <span>{appSt.label}</span>
              </span>
            </div>
          </div>
          {workspace.due_at && (
            <div className="px-4 py-3 rounded-[6px] text-right"
              style={{ background: '#ffffff', boxShadow: '0 0 0 1px rgba(0,0,0,0.08), 0 0 0 2px #fafafa' }}>
              <p className="font-mono text-[10px] uppercase tracking-widest mb-1" style={{ color: '#8f8f8f' }}>Due</p>
              <p className="text-sm font-medium" style={{ color: '#171717' }}>{fmtDate(workspace.due_at)}</p>
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* ── Milestones ── */}
        <div className="lg:col-span-2 space-y-4">
          <h2 className="font-mono text-[11px] uppercase tracking-widest mb-2" style={{ color: '#8f8f8f' }}>
            Milestone Roadmap
          </h2>

          {workspace.milestones.length === 0 && (
            <p className="text-sm" style={{ color: '#8f8f8f' }}>No milestones defined for this project.</p>
          )}

          {workspace.milestones.map((m, idx) => {
            const isExpanded = expandedMs.has(m.id);
            const doneCount  = m.tasks.filter(t => t.status === 'done').length;
            const total      = m.tasks.length;
            const pct        = total > 0 ? Math.round((doneCount / total) * 100) : 0;

            return (
              <div key={m.id} className="rounded-[6px] overflow-hidden"
                style={{ background: '#ffffff', boxShadow: '0 0 0 1px rgba(0,0,0,0.08), 0 0 0 2px #fafafa' }}>

                {/* Milestone header */}
                <button
                  onClick={() => toggleMs(m.id)}
                  className="w-full flex items-center justify-between px-4 py-3 text-left"
                  aria-expanded={isExpanded}
                  aria-controls={`ms-${m.id}`}
                >
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-[11px] uppercase" style={{ color: '#c9c9c9' }}>M{idx + 1}</span>
                    <span className="text-sm font-medium" style={{ color: m.is_overdue ? '#c4231c' : '#171717' }}>
                      {m.title}
                    </span>
                    {m.is_overdue && (
                      <span className="font-mono text-[10px] uppercase tracking-widest px-1.5 py-0.5 rounded-[4px]"
                        style={{ background: '#fef2f2', color: '#c4231c', border: '1px solid #fecaca' }}>
                        Overdue
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-3">
                    {total > 0 && (
                      <span className="font-mono text-[11px]" style={{ color: '#8f8f8f' }}>{doneCount}/{total}</span>
                    )}
                    {m.due_date && (
                      <span className="font-mono text-[11px]" style={{ color: '#c9c9c9' }}>{fmtDate(m.due_date)}</span>
                    )}
                    <span className="font-mono text-[13px]" style={{ color: '#8f8f8f' }}>
                      {isExpanded ? '▲' : '▼'}
                    </span>
                  </div>
                </button>

                {/* Progress bar */}
                {total > 0 && (
                  <div className="h-[2px] w-full" style={{ background: '#ebebeb' }}>
                    <div className="h-full transition-all duration-300"
                      style={{ width: `${pct}%`, background: pct === 100 ? '#297a3a' : '#171717' }} />
                  </div>
                )}

                {/* Body */}
                {isExpanded && (
                  <div id={`ms-${m.id}`} className="border-t px-4 py-3 space-y-1" style={{ borderColor: '#ebebeb' }}>
                    {/* Tasks */}
                    {m.tasks.length === 0 && (
                      <p className="text-xs py-2" style={{ color: '#c9c9c9' }}>No tasks.</p>
                    )}
                    {m.tasks.map(task => (
                      <TaskRow
                        key={task.id}
                        task={task}
                        applicationId={workspace.application_id}
                        onUpdated={fetchWorkspace}
                        isReadOnly={isReadOnly}
                        onDelete={task.is_personal ? deleteTask : undefined}
                      />
                    ))}

                    {/* Add personal task */}
                    {!isReadOnly && (
                      taskMid === m.id ? (
                        <div className="flex items-center gap-2 mt-2 pl-3">
                          <input
                            autoFocus
                            id={`new-task-${m.id}`}
                            value={taskTitle}
                            onChange={e => setTaskTitle(e.target.value)}
                            onKeyDown={e => {
                              if (e.key === 'Enter') createTask(m.id);
                              if (e.key === 'Escape') { setTaskMid(null); setTaskTitle(''); }
                            }}
                            placeholder="Task title…"
                            className="flex-1 text-sm px-2 py-1 rounded-[6px] outline-none"
                            style={{ border: '1px solid #ebebeb', background: '#fafafa', color: '#171717' }}
                          />
                          <button
                            onClick={() => createTask(m.id)}
                            disabled={taskBusy || !taskTitle.trim()}
                            className="px-3 py-1 text-xs rounded-[6px] font-mono uppercase tracking-wider"
                            style={{ background: '#171717', color: '#ffffff', opacity: taskBusy ? 0.5 : 1 }}
                          >
                            {taskBusy ? '…' : 'Add'}
                          </button>
                          <button
                            onClick={() => { setTaskMid(null); setTaskTitle(''); }}
                            className="text-xs font-mono"
                            style={{ color: '#c9c9c9' }}
                          >
                            Cancel
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => { setTaskMid(m.id); setTaskTitle(''); }}
                          className="mt-1 ml-3 text-xs font-mono uppercase tracking-wider flex items-center gap-1"
                          style={{ color: '#c9c9c9' }}
                        >
                          + Add personal task
                        </button>
                      )
                    )}

                    <div className="my-3 border-t" style={{ borderColor: '#ebebeb' }} />

                    {/* Check-ins */}
                    <div>
                      <p className="font-mono text-[10px] uppercase tracking-widest mb-2" style={{ color: '#8f8f8f' }}>
                        Check-ins
                      </p>
                      {m.checkins.length === 0 && (
                        <p className="text-xs" style={{ color: '#c9c9c9' }}>No check-ins yet.</p>
                      )}
                      {m.checkins.map(ci => {
                        const cs = CHECKIN_STATUS[ci.status] ?? CHECKIN_STATUS.submitted;
                        return (
                          <div key={ci.id} className="mb-2 p-3 rounded-[6px]"
                            style={{ background: '#fafafa', border: '1px solid #ebebeb' }}>
                            <div className="flex items-center justify-between mb-1">
                              <span
                                className="flex items-center gap-1 font-mono text-[10px] uppercase tracking-widest"
                                style={{ color: cs.color }}
                              >
                                <span aria-hidden="true">{cs.icon}</span>
                                <span>{cs.label}</span>
                              </span>
                              <span className="font-mono text-[10px]" style={{ color: '#c9c9c9' }}>
                                {fmtDate(ci.submitted_at)}
                              </span>
                            </div>
                            {ci.note && <p className="text-xs mt-1" style={{ color: '#4d4d4d' }}>{ci.note}</p>}
                            {ci.evidence_url && (
                              <a href={ci.evidence_url} target="_blank" rel="noopener noreferrer"
                                className="text-xs underline mt-1 block" style={{ color: '#297a3a' }}>
                                Evidence ↗
                              </a>
                            )}
                            {ci.review_note && (
                              <p className="text-xs mt-2 pt-2 border-t" style={{ borderColor: '#ebebeb', color: '#8f8f8f' }}>
                                <span className="font-mono uppercase text-[10px] tracking-wider">Review: </span>
                                {ci.review_note}
                              </p>
                            )}
                          </div>
                        );
                      })}

                      {/* Check-in form */}
                      {!isReadOnly && (
                        checkinMid === m.id ? (
                          <div className="mt-3 space-y-2">
                            <textarea
                              rows={3}
                              value={checkinNote}
                              onChange={e => setCheckinNote(e.target.value)}
                              placeholder="Describe your progress…"
                              className="w-full text-sm px-3 py-2 rounded-[6px] outline-none resize-none"
                              style={{ border: '1px solid #ebebeb', background: '#fafafa', color: '#171717' }}
                            />
                            <input
                              type="url"
                              value={checkinUrl}
                              onChange={e => setCheckinUrl(e.target.value)}
                              placeholder="Evidence URL (optional)"
                              className="w-full text-sm px-3 py-2 rounded-[6px] outline-none"
                              style={{ border: '1px solid #ebebeb', background: '#fafafa', color: '#171717' }}
                            />
                            {checkinErr && (
                              <p className="text-xs font-mono" style={{ color: '#c4231c' }}>{checkinErr}</p>
                            )}
                            <div className="flex gap-2">
                              <button
                                onClick={submitCheckin}
                                disabled={checkinBusy}
                                className="px-4 py-2 text-sm rounded-[6px] transition-opacity"
                                style={{ background: '#171717', color: '#ffffff', opacity: checkinBusy ? 0.5 : 1 }}
                              >
                                {checkinBusy ? 'Submitting…' : 'Submit Check-in'}
                              </button>
                              <button
                                onClick={() => { setCheckinMid(null); setCheckinErr(null); }}
                                className="px-4 py-2 text-sm rounded-[6px]"
                                style={{ border: '1px solid #ebebeb', color: '#4d4d4d' }}
                              >
                                Cancel
                              </button>
                            </div>
                          </div>
                        ) : (
                          <button
                            onClick={() => setCheckinMid(m.id)}
                            className="mt-2 px-3 py-1.5 text-xs rounded-[6px] font-mono uppercase tracking-wider"
                            style={{ border: '1px solid #ebebeb', color: '#4d4d4d' }}
                          >
                            + Check-in
                          </button>
                        )
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* ── Sidebar ── */}
        <div className="space-y-6">
          {/* Deliverables */}
          <div className="rounded-[6px] p-4"
            style={{ background: '#ffffff', boxShadow: '0 0 0 1px rgba(0,0,0,0.08), 0 0 0 2px #fafafa' }}>
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-mono text-[11px] uppercase tracking-widest" style={{ color: '#8f8f8f' }}>
                Deliverables
              </h3>
              <span className="font-mono text-[11px]" style={{ color: '#c9c9c9' }}>
                {workspace.submissions.length}/3
              </span>
            </div>

            {workspace.submissions.length === 0 && (
              <p className="text-xs mb-3" style={{ color: '#c9c9c9' }}>No submissions yet.</p>
            )}
            {workspace.submissions.map(sub => (
              <div key={sub.id} className="mb-3 pb-3 border-b last:border-0" style={{ borderColor: '#ebebeb' }}>
                <div className="flex items-center justify-between mb-1">
                  <span className="font-mono text-[11px] uppercase tracking-widest" style={{ color: '#171717' }}>
                    v{sub.version}
                  </span>
                  <span className="font-mono text-[10px]" style={{ color: '#c9c9c9' }}>
                    {fmtDate(sub.submitted_at)}
                  </span>
                </div>
                {sub.repo_url && (
                  <a href={sub.repo_url} target="_blank" rel="noopener noreferrer"
                    className="text-xs underline" style={{ color: '#297a3a' }}>
                    Repository ↗
                  </a>
                )}
                {sub.notes && <p className="text-xs mt-1" style={{ color: '#8f8f8f' }}>{sub.notes}</p>}
              </div>
            ))}

            {canSubmit && !showSubForm && (
              <button
                onClick={() => setShowSubForm(true)}
                className="w-full py-2 text-sm rounded-[6px] font-mono uppercase tracking-wider mt-2"
                style={{ background: '#171717', color: '#ffffff' }}
              >
                Submit Deliverable
              </button>
            )}

            {canSubmit && showSubForm && (
              <div className="space-y-2 mt-3">
                <input
                  type="url"
                  value={subRepo}
                  onChange={e => setSubRepo(e.target.value)}
                  placeholder="https://github.com/you/repo"
                  className="w-full text-sm px-3 py-2 rounded-[6px] outline-none"
                  style={{ border: '1px solid #ebebeb', background: '#fafafa', color: '#171717' }}
                />
                <textarea
                  rows={2}
                  value={subNotes}
                  onChange={e => setSubNotes(e.target.value)}
                  placeholder="Notes (optional)"
                  className="w-full text-sm px-3 py-2 rounded-[6px] outline-none resize-none"
                  style={{ border: '1px solid #ebebeb', background: '#fafafa', color: '#171717' }}
                />
                {subErr && <p className="text-xs font-mono" style={{ color: '#c4231c' }}>{subErr}</p>}
                <div className="flex gap-2">
                  <button
                    onClick={submitDeliverable}
                    disabled={subBusy}
                    className="flex-1 py-2 text-sm rounded-[6px]"
                    style={{ background: '#171717', color: '#ffffff', opacity: subBusy ? 0.5 : 1 }}
                  >
                    {subBusy ? 'Submitting…' : 'Submit'}
                  </button>
                  <button
                    onClick={() => { setShowSubForm(false); setSubErr(null); }}
                    className="px-3 py-2 text-sm rounded-[6px]"
                    style={{ border: '1px solid #ebebeb', color: '#4d4d4d' }}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}

            {workspace.submissions.length >= 3 && (
              <p className="text-xs font-mono uppercase tracking-wider mt-3" style={{ color: '#8f8f8f' }}>
                Maximum 3 submissions reached
              </p>
            )}
          </div>

          {/* AI Mentor Card (FR-WRK-5) */}
          {user?.role === 'student' && (
            <div className="rounded-[6px] p-4"
              style={{ background: '#ffffff', boxShadow: '0 0 0 1px rgba(0,0,0,0.08), 0 0 0 2px #fafafa' }}>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-1.5">
                  <span className="font-mono text-sm" style={{ color: '#297a3a' }}>✦</span>
                  <h3 className="font-mono text-[11px] uppercase tracking-widest" style={{ color: '#171717' }}>
                    AI Mentor
                  </h3>
                </div>
                <span className="font-mono text-[10px] px-1.5 py-0.5 rounded-[4px]"
                  style={{ background: '#f5f5f5', color: '#737373', border: '1px solid #e5e5e5' }}>
                  AI draft
                </span>
              </div>
              <p className="text-xs mb-3" style={{ color: '#737373' }}>
                Socratic guidance & hints for your active milestones. Company only sees exchange count.
              </p>

              {/* Milestone selector */}
              {workspace.milestones.length > 0 && (
                <div className="mb-2">
                  <label className="block font-mono text-[10px] uppercase tracking-wider mb-1" style={{ color: '#8f8f8f' }}>
                    Context Milestone
                  </label>
                  <select
                    value={mentorMid}
                    onChange={e => setMentorMid(e.target.value)}
                    className="w-full text-xs px-2.5 py-1.5 rounded-[6px] outline-none"
                    style={{ border: '1px solid #ebebeb', background: '#fafafa', color: '#171717' }}
                  >
                    {workspace.milestones.map((m, idx) => (
                      <option key={m.id} value={m.id}>
                        M{idx + 1}: {m.title}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Chat history list */}
              {mentorChatHistory.length > 0 && (
                <div className="space-y-2 mb-3 max-h-48 overflow-y-auto pr-1">
                  {mentorChatHistory.map((item, i) => (
                    <div key={i} className="p-2.5 rounded-[6px] text-xs space-y-1.5"
                      style={{ background: '#fafafa', border: '1px solid #ebebeb' }}>
                      <div className="flex justify-between items-center text-[10px] font-mono" style={{ color: '#8f8f8f' }}>
                        <span className="font-semibold text-[#171717]">You</span>
                        <span>{item.time}</span>
                      </div>
                      <p style={{ color: '#4d4d4d' }}>{item.q}</p>
                      <div className="pt-1.5 border-t border-[#ebebeb]">
                        <div className="flex items-center gap-1 text-[10px] font-mono mb-1" style={{ color: '#297a3a' }}>
                          <span>✦ Socratic Hint</span>
                        </div>
                        <p className="leading-relaxed" style={{ color: '#171717' }}>{item.ans}</p>
                        {item.nextSteps && item.nextSteps.length > 0 && (
                          <div className="mt-1.5">
                            <p className="font-mono text-[10px] uppercase tracking-wider" style={{ color: '#8f8f8f' }}>
                              Suggested steps:
                            </p>
                            <ul className="list-disc list-inside mt-0.5 space-y-0.5" style={{ color: '#525252' }}>
                              {item.nextSteps.map((step, idx) => (
                                <li key={idx}>{step}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Question input */}
              <div className="space-y-2">
                <textarea
                  rows={2}
                  value={mentorMsg}
                  onChange={e => setMentorMsg(e.target.value)}
                  placeholder="Ask about design, architecture, or edge cases…"
                  className="w-full text-xs px-2.5 py-1.5 rounded-[6px] outline-none resize-none"
                  style={{ border: '1px solid #ebebeb', background: '#fafafa', color: '#171717' }}
                />
                {mentorErr && (
                  <p className="text-xs font-mono" style={{ color: '#c4231c' }}>{mentorErr}</p>
                )}
                <button
                  onClick={askMentor}
                  disabled={mentorBusy || !mentorMsg.trim()}
                  className="w-full py-1.5 text-xs rounded-[6px] font-mono uppercase tracking-wider"
                  style={{
                    background: '#171717',
                    color: '#ffffff',
                    opacity: mentorBusy || !mentorMsg.trim() ? 0.5 : 1,
                  }}
                >
                  {mentorBusy ? 'Consulting Mentor…' : 'Ask AI Mentor'}
                </button>
              </div>
            </div>
          )}

          {/* Project info */}
          <div className="rounded-[6px] p-4"
            style={{ background: '#ffffff', boxShadow: '0 0 0 1px rgba(0,0,0,0.08), 0 0 0 2px #fafafa' }}>
            <h3 className="font-mono text-[11px] uppercase tracking-widest mb-3" style={{ color: '#8f8f8f' }}>
              Project Info
            </h3>
            <dl className="space-y-2 text-sm">
              {[
                ['Company',    workspace.company_name],
                ['Difficulty', workspace.project_difficulty],
                ['Duration',   `${workspace.project_duration_days} days`],
                ['Started',    fmtDate(workspace.started_at)],
                ['Due',        fmtDate(workspace.due_at)],
                ['Milestones', String(workspace.milestones.length)],
              ].map(([label, val]) => (
                <div key={label} className="flex justify-between gap-2">
                  <dt className="font-mono text-[11px] uppercase tracking-widest" style={{ color: '#8f8f8f' }}>
                    {label}
                  </dt>
                  <dd className="text-right" style={{ color: '#171717' }}>{val}</dd>
                </div>
              ))}
            </dl>
          </div>
        </div>
      </div>
    </div>
  );
};

export default WorkspacePage;
