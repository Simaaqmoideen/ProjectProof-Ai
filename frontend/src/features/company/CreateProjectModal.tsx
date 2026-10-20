import React, { useState } from 'react';
import { apiRequest, ApiException } from '../../lib/api';
import {
  AlertCircle,
  Clock,
  Flame,
  Info,
  Plus,
  Trash2,
  X,
} from 'lucide-react';

interface TaskInput {
  title: string;
  description: string;
}

interface MilestoneInput {
  position: number;
  title: string;
  description: string;
  due_day_offset: number;
  tasks: TaskInput[];
}

interface CreateProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const CreateProjectModal: React.FC<CreateProjectModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState<'development' | 'data' | 'design' | 'other'>('development');
  const [difficulty, setDifficulty] = useState<'beginner' | 'intermediate' | 'advanced'>('intermediate');
  const [durationDays, setDurationDays] = useState(14);
  const [maxSelected, setMaxSelected] = useState(1);
  const [skillsInput, setSkillsInput] = useState('Python, FastAPI, PostgreSQL');
  const [milestones, setMilestones] = useState<MilestoneInput[]>([
    {
      position: 1,
      title: 'Environment & Core Architecture',
      description: 'Setup local tooling, initialize models and database connectivity.',
      due_day_offset: 5,
      tasks: [{ title: 'Implement base schemas', description: 'Validate request and response types.' }],
    },
    {
      position: 2,
      title: 'Feature Implementation & Integration',
      description: 'Complete core service endpoints and integration tests.',
      due_day_offset: 12,
      tasks: [{ title: 'Add test suite', description: 'Ensure test coverage.' }],
    },
  ]);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  // Client-side XP preview (BR-1: base = days * 10 * mult + ms * 5)
  const mult = difficulty === 'beginner' ? 0.8 : difficulty === 'intermediate' ? 1.0 : 1.3;
  const estimatedXp = Math.min(300, Math.round(durationDays * 10 * mult + milestones.length * 5));

  const addMilestone = () => {
    if (milestones.length >= 8) return;
    const nextPos = milestones.length + 1;
    setMilestones([
      ...milestones,
      {
        position: nextPos,
        title: `Milestone ${nextPos}`,
        description: '',
        due_day_offset: Math.min(durationDays, nextPos * 7),
        tasks: [],
      },
    ]);
  };

  const removeMilestone = (idx: number) => {
    const updated = milestones.filter((_, i) => i !== idx).map((m, i) => ({ ...m, position: i + 1 }));
    setMilestones(updated);
  };

  const addTask = (msIdx: number) => {
    const ms = milestones[msIdx];
    if (ms.tasks.length >= 10) return;
    const updated = [...milestones];
    updated[msIdx].tasks.push({ title: '', description: '' });
    setMilestones(updated);
  };

  const removeTask = (msIdx: number, taskIdx: number) => {
    const updated = [...milestones];
    updated[msIdx].tasks = updated[msIdx].tasks.filter((_, i) => i !== taskIdx);
    setMilestones(updated);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const skills = skillsInput
      .split(',')
      .map((s) => s.trim())
      .filter((s) => s.length > 0);

    const formattedMilestones = milestones.map((m) => ({
      position: m.position,
      title: m.title.trim(),
      description: m.description.trim() || null,
      due_day_offset: Number(m.due_day_offset),
      tasks: m.tasks.map((t) => ({
        title: t.title.trim(),
        description: t.description.trim() || null,
      })),
    }));

    try {
      await apiRequest('/companies/me/projects', {
        method: 'POST',
        body: JSON.stringify({
          title: title.trim(),
          description: description.trim(),
          category,
          difficulty,
          duration_days: Number(durationDays),
          max_selected: Number(maxSelected),
          skills,
          milestones: formattedMilestones,
        }),
      });
      onSuccess();
      onClose();
    } catch (err: any) {
      if (err instanceof ApiException) {
        setError(err.message);
      } else {
        setError(err.message || 'Failed to create project draft');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#000000]/40 backdrop-blur-sm overflow-y-auto">
      <div className="w-full max-w-2xl bg-[#ffffff] rounded-[6px] border border-[#ebebeb] shadow-xl my-8 overflow-hidden flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="p-5 border-b border-[#ebebeb] flex items-center justify-between">
          <div>
            <div className="text-[11px] font-mono text-[#7d7d7d] uppercase tracking-wider">
              Project Authoring (FR-PRJ-1)
            </div>
            <h2 className="text-lg font-medium text-[#171717]">Create New Project Draft</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-[4px] hover:bg-[#fafafa] text-[#7d7d7d] hover:text-[#171717] transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Form */}
        <form onSubmit={handleSubmit} className="p-6 overflow-y-auto space-y-5 flex-1">
          {error && (
            <div className="p-3 rounded-[4px] border border-[#ff4d4f]/30 bg-[#ff4d4f]/5 text-xs text-[#ff4d4f] flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Project Title */}
          <div className="space-y-1">
            <label className="block text-xs font-mono uppercase tracking-wider text-[#7d7d7d]">
              Project Title *
            </label>
            <input
              type="text"
              required
              minLength={3}
              maxLength={200}
              placeholder="e.g. Distributed Task Queue with Redis & FastAPI"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full px-3 py-2 text-sm rounded-[6px] border border-[#ebebeb] bg-[#fafafa] text-[#171717] focus:outline-none focus:border-[#171717]"
            />
          </div>

          {/* Description */}
          <div className="space-y-1">
            <label className="block text-xs font-mono uppercase tracking-wider text-[#7d7d7d]">
              Description & Deliverable Scope * (Min 10 characters)
            </label>
            <textarea
              required
              rows={3}
              minLength={10}
              placeholder="Describe what the student will construct, architecture expectations, and verification criteria..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full p-3 text-sm rounded-[6px] border border-[#ebebeb] bg-[#fafafa] text-[#171717] focus:outline-none focus:border-[#171717]"
            />
          </div>

          {/* Two-column selectors */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="block text-xs font-mono uppercase tracking-wider text-[#7d7d7d]">
                Category
              </label>
              <select
                value={category}
                onChange={(e: any) => setCategory(e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-[6px] border border-[#ebebeb] bg-[#fafafa] text-[#171717] focus:outline-none focus:border-[#171717]"
              >
                <option value="development">Development</option>
                <option value="data">Data Science & ML</option>
                <option value="design">Design & UI</option>
                <option value="other">Other</option>
              </select>
            </div>

            <div className="space-y-1">
              <label className="block text-xs font-mono uppercase tracking-wider text-[#7d7d7d]">
                Difficulty
              </label>
              <select
                value={difficulty}
                onChange={(e: any) => setDifficulty(e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-[6px] border border-[#ebebeb] bg-[#fafafa] text-[#171717] focus:outline-none focus:border-[#171717]"
              >
                <option value="beginner">Beginner (0.8x XP)</option>
                <option value="intermediate">Intermediate (1.0x XP)</option>
                <option value="advanced">Advanced (1.3x XP)</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="block text-xs font-mono uppercase tracking-wider text-[#7d7d7d]">
                Duration (Days: 1–120)
              </label>
              <input
                type="number"
                min={1}
                max={120}
                required
                value={durationDays}
                onChange={(e) => setDurationDays(Number(e.target.value))}
                className="w-full px-3 py-2 text-sm rounded-[6px] border border-[#ebebeb] bg-[#fafafa] text-[#171717] focus:outline-none focus:border-[#171717]"
              />
            </div>

            <div className="space-y-1">
              <label className="block text-xs font-mono uppercase tracking-wider text-[#7d7d7d]">
                Max Selected Students
              </label>
              <input
                type="number"
                min={1}
                max={50}
                required
                value={maxSelected}
                onChange={(e) => setMaxSelected(Number(e.target.value))}
                className="w-full px-3 py-2 text-sm rounded-[6px] border border-[#ebebeb] bg-[#fafafa] text-[#171717] focus:outline-none focus:border-[#171717]"
              />
            </div>
          </div>

          {/* Skills Input */}
          <div className="space-y-1">
            <label className="block text-xs font-mono uppercase tracking-wider text-[#7d7d7d]">
              Required Skills (Comma separated)
            </label>
            <input
              type="text"
              placeholder="e.g. Python, Docker, PostgreSQL, Redis"
              value={skillsInput}
              onChange={(e) => setSkillsInput(e.target.value)}
              className="w-full px-3 py-2 text-sm rounded-[6px] border border-[#ebebeb] bg-[#fafafa] text-[#171717] focus:outline-none focus:border-[#171717]"
            />
          </div>

          {/* XP Preview Card (Rule D-1 / T-PRJ-01: read-only) */}
          <div className="p-3 rounded-[6px] border border-[#ebebeb] bg-[#fafafa] flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Flame className="w-4 h-4 text-[#171717]" />
              <div>
                <span className="text-xs font-mono font-medium text-[#171717]">
                  Estimated Reward: ~{estimatedXp} XP
                </span>
                <p className="text-[11px] text-[#7d7d7d]">
                  xp_max is server-computed via formula (BR-1). Client cannot override it.
                </p>
              </div>
            </div>
            <span className="text-[11px] font-mono text-[#297a3a] px-2 py-0.5 rounded-[4px] bg-[#297a3a]/10">
              Formula Verified
            </span>
          </div>

          {/* Milestones Builder */}
          <div className="space-y-3 pt-2">
            <div className="flex items-center justify-between">
              <label className="block text-xs font-mono uppercase tracking-wider text-[#7d7d7d]">
                Milestones & Timeline ({milestones.length}/8)
              </label>
              {milestones.length < 8 && (
                <button
                  type="button"
                  onClick={addMilestone}
                  className="inline-flex items-center gap-1 text-xs font-mono text-[#171717] hover:underline"
                >
                  <Plus className="w-3.5 h-3.5" /> Add Milestone
                </button>
              )}
            </div>

            <div className="space-y-3">
              {milestones.map((m, mIdx) => (
                <div key={mIdx} className="p-3 rounded-[6px] border border-[#ebebeb] bg-[#fafafa] space-y-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-medium text-[#171717]">
                      M{m.position}
                    </span>
                    <input
                      type="text"
                      required
                      placeholder="Milestone Title"
                      value={m.title}
                      onChange={(e) => {
                        const copy = [...milestones];
                        copy[mIdx].title = e.target.value;
                        setMilestones(copy);
                      }}
                      className="flex-1 px-2.5 py-1 text-xs rounded-[4px] border border-[#ebebeb] bg-[#ffffff] text-[#171717]"
                    />
                    <div className="flex items-center gap-1 text-xs font-mono text-[#7d7d7d]">
                      <span>Due Day:</span>
                      <input
                        type="number"
                        min={1}
                        value={m.due_day_offset}
                        onChange={(e) => {
                          const copy = [...milestones];
                          copy[mIdx].due_day_offset = Number(e.target.value);
                          setMilestones(copy);
                        }}
                        className="w-14 px-1.5 py-1 text-xs rounded-[4px] border border-[#ebebeb] bg-[#ffffff] text-[#171717]"
                      />
                    </div>
                    {milestones.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeMilestone(mIdx)}
                        className="p-1 text-[#7d7d7d] hover:text-[#ff4d4f]"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>

                  <input
                    type="text"
                    placeholder="Milestone description (optional)"
                    value={m.description}
                    onChange={(e) => {
                      const copy = [...milestones];
                      copy[mIdx].description = e.target.value;
                      setMilestones(copy);
                    }}
                    className="w-full px-2.5 py-1 text-xs rounded-[4px] border border-[#ebebeb] bg-[#ffffff] text-[#171717]"
                  />

                  {/* Tasks for milestone */}
                  <div className="pl-4 space-y-1.5">
                    {m.tasks.map((t, tIdx) => (
                      <div key={tIdx} className="flex items-center gap-2">
                        <span className="text-[11px] text-[#7d7d7d] font-mono">•</span>
                        <input
                          type="text"
                          required
                          placeholder="Sub-task title"
                          value={t.title}
                          onChange={(e) => {
                            const copy = [...milestones];
                            copy[mIdx].tasks[tIdx].title = e.target.value;
                            setMilestones(copy);
                          }}
                          className="flex-1 px-2 py-0.5 text-xs rounded-[4px] border border-[#ebebeb] bg-[#ffffff] text-[#171717]"
                        />
                        <button
                          type="button"
                          onClick={() => removeTask(mIdx, tIdx)}
                          className="text-[#7d7d7d] hover:text-[#ff4d4f]"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </div>
                    ))}

                    {m.tasks.length < 10 && (
                      <button
                        type="button"
                        onClick={() => addTask(mIdx)}
                        className="text-[11px] font-mono text-[#7d7d7d] hover:text-[#171717] inline-flex items-center gap-1"
                      >
                        <Plus className="w-3 h-3" /> Add sub-task
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Footer action buttons */}
          <div className="pt-4 border-t border-[#ebebeb] flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-[6px] border border-[#ebebeb] bg-[#ffffff] text-xs font-medium text-[#4d4d4d] hover:bg-[#fafafa]"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 rounded-[6px] bg-[#171717] text-[#ffffff] text-xs font-medium hover:bg-[#000000] disabled:bg-[#8f8f8f]"
            >
              {loading ? 'Saving Draft...' : 'Save as Draft'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
