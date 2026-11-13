/**
 * NotificationsPage — FR-NTF-1
 *
 * In-app notification center. Displays all notifications for the
 * current user, with mark-as-read and mark-all-read controls.
 *
 * Notification types covered (FR-NTF-1):
 *  - application_received, selected, rejected
 *  - milestone_due, milestone_overdue
 *  - submission_received, evaluation_done
 *  - appeal_outcome
 *  - certificate_issued, certificate_revoked
 */

import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  AlertCircle,
  Award,
  Bell,
  BellOff,
  CheckCircle2,
  ChevronRight,
  Clock,
  FileCheck,
  Loader2,
  MessageSquare,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  X,
} from 'lucide-react';
import { ApiException, apiRequest } from '../../lib/api';

// ─── Types ────────────────────────────────────────────────────────────────────

interface Notification {
  id: string;
  type: string;
  title: string;
  body: string;
  is_read: boolean;
  created_at: string;
  link?: string | null;
}

interface NotificationPage {
  items: Notification[];
  total: number;
  has_more: boolean;
}

// ─── Icon mapping ─────────────────────────────────────────────────────────────

const TYPE_ICON: Record<string, React.ReactNode> = {
  application_received: <MessageSquare className="w-4 h-4 text-[#1c4e9d]" />,
  selected: <CheckCircle2 className="w-4 h-4 text-[#0a7d33]" />,
  rejected: <X className="w-4 h-4 text-[#9b1c1c]" />,
  milestone_due: <Clock className="w-4 h-4 text-[#a05000]" />,
  milestone_overdue: <AlertCircle className="w-4 h-4 text-[#9b1c1c]" />,
  submission_received: <FileCheck className="w-4 h-4 text-[#1c4e9d]" />,
  evaluation_done: <CheckCircle2 className="w-4 h-4 text-[#0a7d33]" />,
  appeal_outcome: <AlertCircle className="w-4 h-4 text-[#a05000]" />,
  certificate_issued: <ShieldCheck className="w-4 h-4 text-[#0a7d33]" />,
  certificate_revoked: <ShieldAlert className="w-4 h-4 text-[#9b1c1c]" />,
};

function getIcon(type: string): React.ReactNode {
  return TYPE_ICON[type] ?? <Bell className="w-4 h-4 text-[#7d7d7d]" />;
}

function formatRelative(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(ms / 60_000);
  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
}

// ─── Single notification row ──────────────────────────────────────────────────

const NotificationRow: React.FC<{
  notif: Notification;
  onRead: (id: string) => void;
}> = ({ notif, onRead }) => {
  const icon = getIcon(notif.type);
  const content = (
    <div
      className={`flex items-start gap-3 px-4 py-3.5 border-b border-[#ebebeb] transition-colors ${
        notif.is_read ? 'bg-white' : 'bg-[#fafffe]'
      } hover:bg-[#fafafa]`}
    >
      {/* Unread dot */}
      <div className="mt-0.5 flex-shrink-0 w-5 flex justify-center">
        {!notif.is_read && (
          <span className="w-1.5 h-1.5 rounded-full bg-[#171717] mt-1.5 block" />
        )}
      </div>

      {/* Icon */}
      <div className="flex-shrink-0 mt-0.5">{icon}</div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <p
          className={`text-sm leading-snug ${
            notif.is_read ? 'text-[#4d4d4d]' : 'font-medium text-[#171717]'
          }`}
        >
          {notif.title}
        </p>
        <p className="text-xs text-[#7d7d7d] mt-0.5 leading-relaxed">{notif.body}</p>
        <p className="text-[10px] font-mono text-[#a8a8a8] mt-1">{formatRelative(notif.created_at)}</p>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 flex-shrink-0">
        {notif.link && <ChevronRight className="w-3.5 h-3.5 text-[#c9c9c9]" />}
        {!notif.is_read && (
          <button
            type="button"
            aria-label="Mark as read"
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              onRead(notif.id);
            }}
            className="text-[#a8a8a8] hover:text-[#171717] transition-colors"
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
          </button>
        )}
      </div>
    </div>
  );

  if (notif.link) {
    return (
      <Link
        to={notif.link}
        id={`notif-${notif.id}`}
        onClick={() => !notif.is_read && onRead(notif.id)}
        className="block no-underline"
      >
        {content}
      </Link>
    );
  }

  return (
    <div id={`notif-${notif.id}`} onClick={() => !notif.is_read && onRead(notif.id)}>
      {content}
    </div>
  );
};

// ─── Main Page ────────────────────────────────────────────────────────────────

export const NotificationsPage: React.FC = () => {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [offset, setOffset] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [markingAll, setMarkingAll] = useState(false);

  const PAGE_SIZE = 20;

  const load = useCallback(async (off: number, append: boolean) => {
    if (off === 0) setLoading(true);
    else setLoadingMore(true);
    setError(null);

    try {
      const res = await apiRequest<NotificationPage>(
        `/notifications?limit=${PAGE_SIZE}&offset=${off}`
      );
      const items = res.items ?? [];
      setNotifications((prev) => (append ? [...prev, ...items] : items));
      setHasMore(res.has_more ?? false);
      setOffset(off + items.length);
    } catch (e) {
      setError(e instanceof ApiException ? e.message : 'Failed to load notifications.');
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }, []);

  useEffect(() => {
    load(0, false);
  }, [load]);

  const markRead = async (id: string) => {
    try {
      await apiRequest(`/notifications/${id}/read`, { method: 'POST' });
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
    } catch {
      // Silent fail; user can refresh
    }
  };

  const markAllRead = async () => {
    setMarkingAll(true);
    try {
      await apiRequest('/notifications/read-all', { method: 'POST' });
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    } catch (e) {
      setError(e instanceof ApiException ? e.message : 'Failed to mark all as read.');
    } finally {
      setMarkingAll(false);
    }
  };

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  return (
    <div className="max-w-2xl mx-auto px-4 py-10">
      {/* Header */}
      <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-semibold text-[#171717] flex items-center gap-2">
            <Bell className="w-5 h-5" />
            Notifications
            {unreadCount > 0 && (
              <span className="text-xs font-mono px-1.5 py-0.5 rounded-full bg-[#171717] text-white">
                {unreadCount}
              </span>
            )}
          </h1>
          <p className="text-xs text-[#7d7d7d] mt-0.5">
            Application updates, milestones, evaluations, and certificates.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            id="refresh-notifications-btn"
            onClick={() => load(0, false)}
            disabled={loading}
            aria-label="Refresh"
            className="p-1.5 border border-[#ebebeb] rounded-[6px] text-[#7d7d7d] hover:text-[#171717] hover:bg-[#fafafa] transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </button>

          {unreadCount > 0 && (
            <button
              type="button"
              id="mark-all-read-btn"
              onClick={markAllRead}
              disabled={markingAll}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs border border-[#ebebeb] rounded-[6px] bg-white hover:bg-[#fafafa] text-[#4d4d4d] disabled:opacity-50 transition-colors"
            >
              {markingAll ? (
                <Loader2 className="w-3 h-3 animate-spin" />
              ) : (
                <CheckCircle2 className="w-3 h-3" />
              )}
              Mark all read
            </button>
          )}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div
          role="alert"
          className="flex items-center gap-2 px-4 py-3 mb-4 rounded-[6px] bg-[#fff2f2] border border-[#f5c6c6] text-sm text-[#9b1c1c]"
        >
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
          <button
            type="button"
            onClick={() => setError(null)}
            className="ml-auto"
            aria-label="Dismiss"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Loading skeleton */}
      {loading && (
        <div className="border border-[#ebebeb] rounded-[6px] overflow-hidden">
          {[...Array(5)].map((_, i) => (
            <div
              key={i}
              className="flex items-start gap-3 px-4 py-3.5 border-b border-[#ebebeb] last:border-b-0"
            >
              <div className="w-5 flex justify-center">
                <div className="w-1.5 h-1.5 rounded-full bg-[#ebebeb] mt-1.5 animate-pulse" />
              </div>
              <div className="w-4 h-4 rounded-full bg-[#ebebeb] animate-pulse mt-0.5" />
              <div className="flex-1 space-y-1.5">
                <div className="h-3.5 bg-[#ebebeb] rounded animate-pulse w-2/3" />
                <div className="h-3 bg-[#ebebeb] rounded animate-pulse w-full" />
                <div className="h-2.5 bg-[#ebebeb] rounded animate-pulse w-1/4" />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Notification list */}
      {!loading && (
        <>
          {notifications.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 border border-[#ebebeb] rounded-[6px] bg-[#fafafa]">
              <BellOff className="w-8 h-8 text-[#c9c9c9] mb-3" />
              <p className="text-sm text-[#7d7d7d]">No notifications yet.</p>
            </div>
          ) : (
            <div className="border border-[#ebebeb] rounded-[6px] overflow-hidden divide-y divide-[#ebebeb]">
              {notifications.map((n) => (
                <NotificationRow key={n.id} notif={n} onRead={markRead} />
              ))}
            </div>
          )}

          {/* Load more */}
          {hasMore && (
            <div className="flex justify-center mt-4">
              <button
                type="button"
                id="load-more-notifications-btn"
                onClick={() => load(offset, true)}
                disabled={loadingMore}
                className="flex items-center gap-2 px-4 py-2 border border-[#ebebeb] text-sm rounded-[6px] bg-white hover:bg-[#fafafa] disabled:opacity-50 transition-colors"
              >
                {loadingMore ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <RefreshCw className="w-3.5 h-3.5" />
                )}
                Load more
              </button>
            </div>
          )}
        </>
      )}

      {/* Badge info */}
      {notifications.length > 0 && (
        <p className="text-center text-[10px] font-mono text-[#a8a8a8] mt-6">
          Showing {notifications.length} notifications
        </p>
      )}
    </div>
  );
};

export default NotificationsPage;
