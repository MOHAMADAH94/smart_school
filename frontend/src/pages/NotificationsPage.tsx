import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { api } from '../api/client';
import { notificationsApi, type AppNotification } from '../api/resources';
import { PaginationBar } from '../components/PaginationBar';
import { useAuth } from '../context/AuthContext';
import { isSchoolManager } from '../utils/roles';

const PAGE_SIZE = 20;

const typeLabel: Record<string, string> = {
  SYSTEM: 'نظام',
  ATTENDANCE: 'حضور',
  GRADE: 'درجات',
  PAYMENT: 'مدفوعات',
  ANNOUNCEMENT: 'إعلان',
  TRANSPORT: 'نقل',
  SUBSCRIPTION: 'اشتراك',
  ACADEMIC: 'أكاديمي',
};

const audienceLabel: Record<string, string> = {
  ALL: 'الجميع',
  TEACHERS: 'المعلمون فقط',
  PARENTS: 'أولياء الأمور فقط',
  MANAGERS: 'الإدارة فقط',
  USER: 'مستخدم محدد',
};

export function NotificationsPage() {
  const { schoolContext } = useAuth();
  const canManage =
    isSchoolManager(schoolContext?.membership?.role) &&
    (schoolContext?.permissions ?? []).includes('notifications.manage');
  const features = new Set(schoolContext?.features ?? []);
  const qc = useQueryClient();
  const [filter, setFilter] = useState<'all' | 'unread'>('all');
  const [type, setType] = useState('');
  const [audienceFilter, setAudienceFilter] = useState('');
  const [page, setPage] = useState(1);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    title: '',
    body: '',
    type: 'ANNOUNCEMENT',
    audience: 'ALL',
  });

  const enabled = features.has('notifications');

  const list = useQuery({
    queryKey: ['notifications', filter, type, audienceFilter, page],
    queryFn: () =>
      notificationsApi.list({
        page: String(page),
        page_size: String(PAGE_SIZE),
        ...(filter === 'unread' ? { is_read: 'false' } : {}),
        ...(type ? { type } : {}),
        ...(audienceFilter ? { audience: audienceFilter } : {}),
      }),
    enabled,
  });

  const markRead = useMutation({
    mutationFn: (id: number) => notificationsApi.markRead(id),
    onMutate: async (id) => {
      await qc.cancelQueries({ queryKey: ['notifications'] });
      await qc.cancelQueries({ queryKey: ['notifications-unread'] });
      await qc.cancelQueries({ queryKey: ['notifications-recent'] });
      qc.setQueriesData({ queryKey: ['notifications'] }, (old: any) => {
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
      await qc.invalidateQueries({ queryKey: ['notifications'] });
      await qc.invalidateQueries({ queryKey: ['notifications-unread'] });
      await qc.invalidateQueries({ queryKey: ['notifications-recent'] });
    },
  });

  const markAll = useMutation({
    mutationFn: () => notificationsApi.markAllRead(),
    onMutate: async () => {
      await qc.cancelQueries({ queryKey: ['notifications'] });
      qc.setQueriesData({ queryKey: ['notifications'] }, (old: any) => {
        if (!old?.results) return old;
        return {
          ...old,
          results: old.results.map((n: AppNotification) => ({ ...n, is_read: true })),
        };
      });
      qc.setQueryData(['notifications-unread'], 0);
    },
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ['notifications'] });
      await qc.invalidateQueries({ queryKey: ['notifications-unread'] });
      await qc.invalidateQueries({ queryKey: ['notifications-recent'] });
    },
    onError: async () => {
      await qc.invalidateQueries({ queryKey: ['notifications'] });
      await qc.invalidateQueries({ queryKey: ['notifications-unread'] });
    },
  });

  const prefs = useQuery({
    queryKey: ['notification-preferences'],
    queryFn: async () => (await api.get('/notifications/preferences/')).data,
    enabled,
  });

  const savePref = useMutation({
    mutationFn: async (item: { category: string; enabled: boolean }) =>
      (await api.put('/notifications/preferences/', item)).data,
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ['notification-preferences'] });
    },
  });

  const createMutation = useMutation({
    mutationFn: () => notificationsApi.create(form),
    onSuccess: async () => {
      setShowForm(false);
      setForm({ title: '', body: '', type: 'ANNOUNCEMENT', audience: 'ALL' });
      await qc.invalidateQueries({ queryKey: ['notifications'] });
      await qc.invalidateQueries({ queryKey: ['notifications-unread'] });
      await qc.invalidateQueries({ queryKey: ['notifications-recent'] });
    },
  });

  function onCreate(e: FormEvent) {
    e.preventDefault();
    createMutation.mutate();
  }

  if (!enabled) {
    return (
      <div className="page">
        <header className="page-header">
          <h2>الإشعارات</h2>
          <p className="muted">ميزة الإشعارات غير مفعّلة في باقة الاشتراك الحالية.</p>
        </header>
      </div>
    );
  }

  const rows = list.data?.results ?? [];

  return (
    <div className="page">
      <header className="page-header row-between">
        <div>
          <h2>الإشعارات</h2>
          <p className="muted">أرسل للجميع أو للمعلمين أو لأولياء الأمور حسب الحاجة</p>
        </div>
        <div className="row-actions">
          <button
            type="button"
            className="btn btn-ghost"
            disabled={markAll.isPending}
            onClick={() => markAll.mutate()}
          >
            {markAll.isPending ? 'جاري التحديث...' : 'تعليم الكل كمقروء'}
          </button>
          {canManage && (
            <button type="button" className="btn btn-primary" onClick={() => setShowForm(true)}>
              إشعار جديد
            </button>
          )}
        </div>
      </header>

      <div className="toolbar">
        <select
          value={filter}
          onChange={(e) => {
            setFilter(e.target.value as 'all' | 'unread');
            setPage(1);
          }}
        >
          <option value="all">الكل</option>
          <option value="unread">غير المقروء</option>
        </select>
        <select
          value={type}
          onChange={(e) => {
            setType(e.target.value);
            setPage(1);
          }}
        >
          <option value="">كل الأنواع</option>
          {Object.entries(typeLabel).map(([k, v]) => (
            <option key={k} value={k}>
              {v}
            </option>
          ))}
        </select>
        {canManage && (
          <select
            value={audienceFilter}
            onChange={(e) => {
              setAudienceFilter(e.target.value);
              setPage(1);
            }}
          >
            <option value="">كل المستهدفين</option>
            {Object.entries(audienceLabel)
              .filter(([k]) => k !== 'USER')
              .map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
          </select>
        )}
      </div>

      {showForm && canManage && (
        <form className="panel form-grid" onSubmit={onCreate}>
          <h3>إرسال إشعار</h3>
          <label>
            العنوان *
            <input
              required
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
            />
          </label>
          <label>
            المستهدفون *
            <select
              required
              value={form.audience}
              onChange={(e) => setForm({ ...form, audience: e.target.value })}
            >
              <option value="ALL">الجميع</option>
              <option value="TEACHERS">المعلمون فقط</option>
              <option value="PARENTS">أولياء الأمور فقط</option>
              <option value="MANAGERS">الإدارة فقط</option>
            </select>
          </label>
          <label>
            النوع
            <select
              value={form.type}
              onChange={(e) => setForm({ ...form, type: e.target.value })}
            >
              {Object.entries(typeLabel).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>
          </label>
          <label className="full">
            المحتوى
            <input
              value={form.body}
              onChange={(e) => setForm({ ...form, body: e.target.value })}
            />
          </label>
          <div className="form-actions">
            <button className="btn btn-primary" type="submit" disabled={createMutation.isPending}>
              إرسال
            </button>
            <button className="btn btn-ghost" type="button" onClick={() => setShowForm(false)}>
              إلغاء
            </button>
          </div>
        </form>
      )}

      <div className="notif-page-list">
        {rows.map((n) => (
          <article key={n.id} className={`panel notif-card${n.is_read ? '' : ' unread'}`}>
            <div className="row-between">
              <div>
                <div className="row-actions" style={{ marginBottom: '0.35rem' }}>
                  <span className={`notif-type type-${n.type.toLowerCase()}`}>
                    {typeLabel[n.type] || n.type}
                  </span>
                  <span className="notif-type">
                    {n.audience_label || audienceLabel[n.audience || 'ALL'] || n.audience}
                  </span>
                </div>
                <h3>{n.title}</h3>
                <p className="muted">{n.body || '—'}</p>
                <small className="muted">{new Date(n.created_at).toLocaleString('ar')}</small>
              </div>
              {!n.is_read && (
                <button type="button" className="btn btn-ghost" onClick={() => markRead.mutate(n.id)}>
                  تعليم كمقروء
                </button>
              )}
            </div>
          </article>
        ))}
        {rows.length === 0 && (
          <section className="panel">
            <p className="muted">لا توجد إشعارات.</p>
          </section>
        )}
      </div>
      <PaginationBar
        page={page}
        pageSize={PAGE_SIZE}
        count={list.data?.count ?? 0}
        onPageChange={setPage}
        label="إشعار"
      />

      <section className="panel" style={{ marginTop: '1rem' }}>
        <h3>تفضيلات الإشعارات</h3>
        <p className="muted">إعلانات المدرسة إلزامية ولا يمكن إيقافها.</p>
        <ul className="simple-list">
          {(prefs.data?.preferences ?? []).map(
            (p: { category: string; label: string; enabled: boolean; mandatory: boolean }) => (
              <li key={p.category} className="row-between">
                <span>{p.label}</span>
                <label>
                  <input
                    type="checkbox"
                    checked={p.enabled}
                    disabled={p.mandatory || savePref.isPending}
                    onChange={(e) =>
                      savePref.mutate({ category: p.category, enabled: e.target.checked })
                    }
                  />{' '}
                  مفعّل
                </label>
              </li>
            ),
          )}
        </ul>
      </section>
    </div>
  );
}
