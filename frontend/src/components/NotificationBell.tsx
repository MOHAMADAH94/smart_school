import { useEffect, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { notificationsApi, type AppNotification } from '../api/resources';
import { useAuth } from '../context/AuthContext';

const typeLabel: Record<string, string> = {
  SYSTEM: 'نظام',
  ATTENDANCE: 'حضور',
  PAYMENT: 'مدفوعات',
  ANNOUNCEMENT: 'إعلان',
  TRANSPORT: 'نقل',
  ACADEMIC: 'أكاديمي',
};

function timeAgo(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'الآن';
  if (mins < 60) return `قبل ${mins} د`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `قبل ${hours} س`;
  const days = Math.floor(hours / 24);
  return `قبل ${days} ي`;
}

export function NotificationBell() {
  const { schoolContext } = useAuth();
  const features = new Set(schoolContext?.features ?? []);
  const canView = (schoolContext?.permissions ?? []).includes('notifications.view');
  const enabled = canView && features.has('notifications');
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  const unread = useQuery({
    queryKey: ['notifications-unread'],
    queryFn: () => notificationsApi.unreadCount(),
    enabled,
    refetchInterval: 60_000,
    refetchIntervalInBackground: false,
  });

  const recent = useQuery({
    queryKey: ['notifications-recent'],
    queryFn: () => notificationsApi.list({ page_size: '8' }),
    enabled: enabled && open,
  });

  const markRead = useMutation({
    mutationFn: (id: number) => notificationsApi.markRead(id),
    onMutate: async (id) => {
      await qc.cancelQueries({ queryKey: ['notifications-recent'] });
      await qc.cancelQueries({ queryKey: ['notifications-unread'] });
      qc.setQueryData(['notifications-recent'], (old: any) => {
        if (!old?.results) return old;
        return {
          ...old,
          results: old.results.map((n: AppNotification) =>
            n.id === id ? { ...n, is_read: true } : n,
          ),
        };
      });
      qc.setQueryData(['notifications-unread'], (c: number | undefined) =>
        typeof c === 'number' ? Math.max(0, c - 1) : c,
      );
    },
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ['notifications-unread'] });
      await qc.invalidateQueries({ queryKey: ['notifications-recent'] });
      await qc.invalidateQueries({ queryKey: ['notifications'] });
    },
  });

  const markAll = useMutation({
    mutationFn: () => notificationsApi.markAllRead(),
    onMutate: async () => {
      await qc.cancelQueries({ queryKey: ['notifications-recent'] });
      qc.setQueryData(['notifications-recent'], (old: any) => {
        if (!old?.results) return old;
        return {
          ...old,
          results: old.results.map((n: AppNotification) => ({ ...n, is_read: true })),
        };
      });
      qc.setQueryData(['notifications-unread'], 0);
    },
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ['notifications-unread'] });
      await qc.invalidateQueries({ queryKey: ['notifications-recent'] });
      await qc.invalidateQueries({ queryKey: ['notifications'] });
    },
    onError: async () => {
      await qc.invalidateQueries({ queryKey: ['notifications-unread'] });
      await qc.invalidateQueries({ queryKey: ['notifications-recent'] });
    },
  });

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', onDocClick);
    return () => document.removeEventListener('mousedown', onDocClick);
  }, []);

  if (!enabled) return null;

  const count = unread.data ?? 0;
  const items: AppNotification[] = recent.data?.results ?? [];

  return (
    <div className="notif-root" ref={rootRef}>
      <button
        type="button"
        className="icon-btn"
        aria-label="الإشعارات"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path
            d="M12 3a6 6 0 0 0-6 6v2.2c0 .7-.2 1.4-.6 2L4 16h16l-1.4-2.8c-.4-.6-.6-1.3-.6-2V9a6 6 0 0 0-6-6Z"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinejoin="round"
          />
          <path d="M9.5 18a2.5 2.5 0 0 0 5 0" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
        </svg>
        {count > 0 && <span className="notif-badge">{count > 99 ? '99+' : count}</span>}
      </button>

      {open && (
        <div className="notif-panel" role="dialog" aria-label="قائمة الإشعارات">
          <div className="notif-panel-head">
            <strong>الإشعارات</strong>
            <div className="row-actions">
              {count > 0 && (
                <button type="button" className="link-btn" onClick={() => markAll.mutate()}>
                  تعليم الكل كمقروء
                </button>
              )}
              <Link to="/notifications" className="link-btn" onClick={() => setOpen(false)}>
                عرض الكل
              </Link>
            </div>
          </div>
          <div className="notif-list">
            {items.map((n) => (
              <button
                key={n.id}
                type="button"
                className={`notif-item${n.is_read ? '' : ' unread'}`}
                onClick={() => {
                  if (!n.is_read) markRead.mutate(n.id);
                }}
              >
                <div className="notif-item-top">
                  <span className={`notif-type type-${n.type.toLowerCase()}`}>
                    {typeLabel[n.type] || n.type}
                  </span>
                  <span className="muted">{timeAgo(n.created_at)}</span>
                </div>
                {n.audience_label && (
                  <span className="notif-type" style={{ justifySelf: 'start' }}>
                    {n.audience_label}
                  </span>
                )}
                <strong>{n.title}</strong>
                {n.body && <p>{n.body}</p>}
              </button>
            ))}
            {items.length === 0 && <p className="muted notif-empty">لا توجد إشعارات حالياً.</p>}
          </div>
        </div>
      )}
    </div>
  );
}
