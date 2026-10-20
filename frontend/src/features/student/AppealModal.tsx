/**
 * AppealModal — FR-EVL-7, BR-7
 * A modal component that allows a student to appeal a rejected/changes-requested evaluation.
 * Rules enforced server-side: 7-day window, one open appeal at a time.
 */
import React, { useState } from 'react';
import { apiRequest, ApiException } from '../../lib/api';

interface AppealModalProps {
  evaluationId: string;
  submissionVersion: number;
  onClose: () => void;
  onSuccess: () => void;
}

export const AppealModal: React.FC<AppealModalProps> = ({
  evaluationId,
  submissionVersion,
  onClose,
  onSuccess,
}) => {
  const [reason, setReason]   = useState('');
  const [busy, setBusy]       = useState(false);
  const [error, setError]     = useState<string | null>(null);

  const submit = async () => {
    if (!reason.trim()) { setError('Please provide a reason for the appeal.'); return; }
    setBusy(true); setError(null);
    try {
      await apiRequest(`/evaluations/${evaluationId}/appeal`, {
        method: 'POST',
        body: JSON.stringify({ reason: reason.trim() }),
      });
      onSuccess();
    } catch (e) {
      setError(e instanceof ApiException ? e.message : 'Appeal failed');
    } finally { setBusy(false); }
  };

  return (
    /* Backdrop */
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(23,23,23,0.5)', backdropFilter: 'blur(4px)' }}
      role="dialog"
      aria-modal="true"
      aria-label={`Appeal evaluation for submission v${submissionVersion}`}
      onClick={e => { if (e.target === e.currentTarget) onClose(); }}
    >
      {/* Modal */}
      <div
        className="w-full max-w-md rounded-[6px] p-6"
        style={{ background: '#ffffff', boxShadow: '0 0 0 1px rgba(0,0,0,0.12), 0 16px 48px rgba(0,0,0,0.12)' }}
      >
        <div className="flex items-start justify-between mb-4">
          <div>
            <p className="font-mono text-[11px] uppercase tracking-widest mb-1" style={{ color: '#8f8f8f' }}>
              FR-EVL-7 · Appeal
            </p>
            <h2 className="text-lg font-medium" style={{ color: '#171717' }}>
              Appeal Evaluation v{submissionVersion}
            </h2>
          </div>
          <button
            onClick={onClose}
            aria-label="Close appeal modal"
            className="font-mono text-lg leading-none"
            style={{ color: '#c9c9c9' }}
          >
            ✕
          </button>
        </div>

        {/* Info box */}
        <div className="mb-4 p-3 rounded-[6px]" style={{ background: '#fafafa', border: '1px solid #ebebeb' }}>
          <ul className="text-xs space-y-1" style={{ color: '#666666' }}>
            <li>▲ Appeals must be filed within <strong>7 days</strong> of evaluation.</li>
            <li>▲ Only one open appeal is allowed per evaluation.</li>
            <li>▲ An admin will review and may override the decision.</li>
          </ul>
        </div>

        {/* Reason textarea */}
        <div className="mb-4">
          <label
            htmlFor="appeal-reason"
            className="block font-mono text-[11px] uppercase tracking-widest mb-2"
            style={{ color: '#8f8f8f' }}
          >
            Reason <span style={{ color: '#c4231c' }}>*</span>
          </label>
          <textarea
            id="appeal-reason"
            rows={5}
            value={reason}
            onChange={e => setReason(e.target.value)}
            placeholder="Explain why you are appealing this evaluation…"
            className="w-full text-sm px-3 py-2 rounded-[6px] outline-none resize-y"
            style={{ border: '1px solid #ebebeb', background: '#fafafa', color: '#171717' }}
            maxLength={2000}
          />
          <p className="mt-1 font-mono text-[10px] text-right" style={{ color: '#c9c9c9' }}>
            {reason.length}/2000
          </p>
        </div>

        {error && (
          <div className="mb-4 px-3 py-2 rounded-[6px] font-mono text-xs"
            style={{ background: '#fef2f2', color: '#c4231c', border: '1px solid #fecaca' }}>
            {error}
          </div>
        )}

        <div className="flex gap-3">
          <button
            onClick={submit}
            disabled={busy || !reason.trim()}
            className="flex-1 py-2.5 text-sm rounded-[6px] transition-opacity"
            style={{ background: '#171717', color: '#ffffff', opacity: busy || !reason.trim() ? 0.5 : 1 }}
          >
            {busy ? 'Submitting…' : 'Submit Appeal'}
          </button>
          <button
            onClick={onClose}
            className="px-4 py-2.5 text-sm rounded-[6px]"
            style={{ border: '1px solid #ebebeb', color: '#4d4d4d' }}
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
};

export default AppealModal;
