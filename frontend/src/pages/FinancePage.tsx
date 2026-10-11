import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useMemo, useState, type FormEvent } from 'react';
import { useLocation } from 'react-router-dom';
import { api } from '../api/client';
import { studentsApi } from '../api/resources';
import { useAuth } from '../context/AuthContext';

type Tab = 'fees' | 'payments' | 'expenses';

export function FinancePage() {
  const { schoolContext } = useAuth();
  const canManage = (schoolContext?.permissions ?? []).includes('finance.manage');
  const location = useLocation();
  const qc = useQueryClient();

  const initialTab: Tab = location.pathname.includes('/payments')
    ? 'payments'
    : location.pathname.includes('/expenses')
      ? 'expenses'
      : 'fees';
  const [tab, setTab] = useState<Tab>(initialTab);

  const [feeForm, setFeeForm] = useState({
    student: '',
    title: 'رسوم سنوية',
    amount: '',
    academic_year: '2025-2026',
  });
  const [paymentForm, setPaymentForm] = useState({
    student: '',
    fee: '',
    amount: '',
    payment_date: new Date().toISOString().slice(0, 10),
    method: 'CASH',
    reference: '',
    notes: '',
  });
  const [expenseForm, setExpenseForm] = useState({
    title: '',
    category: 'GENERAL',
    amount: '',
    expense_date: new Date().toISOString().slice(0, 10),
    notes: '',
  });
  const [error, setError] = useState('');

  const summary = useQuery({
    queryKey: ['finance-summary'],
    queryFn: async () => (await api.get('/finance/accounts/summary/')).data,
    enabled: canManage,
  });
  const fees = useQuery({
    queryKey: ['fees'],
    queryFn: async () => (await api.get('/finance/fees/', { params: { page_size: 200 } })).data,
    enabled: canManage,
  });
  const payments = useQuery({
    queryKey: ['payments'],
    queryFn: async () => (await api.get('/finance/payments/', { params: { page_size: 200 } })).data,
    enabled: canManage,
  });
  const expenses = useQuery({
    queryKey: ['expenses'],
    queryFn: async () => (await api.get('/finance/expenses/', { params: { page_size: 200 } })).data,
    enabled: canManage,
  });
  const students = useQuery({
    queryKey: ['students-finance'],
    queryFn: () => studentsApi.list({ page_size: '200', status: 'ACTIVE' }),
    enabled: canManage,
  });

  const feeRows = fees.data?.results ?? fees.data ?? [];
  const paymentRows = payments.data?.results ?? payments.data ?? [];
  const expenseRows = expenses.data?.results ?? expenses.data ?? [];

  const feesForStudent = useMemo(() => {
    if (!paymentForm.student) return feeRows;
    return feeRows.filter((f: { student: number }) => String(f.student) === paymentForm.student);
  }, [feeRows, paymentForm.student]);

  const createFee = useMutation({
    mutationFn: async () =>
      api.post('/finance/fees/', {
        ...feeForm,
        student: Number(feeForm.student),
        amount: feeForm.amount,
      }),
    onSuccess: async () => {
      setFeeForm({ student: '', title: 'رسوم سنوية', amount: '', academic_year: '2025-2026' });
      setError('');
      await qc.invalidateQueries({ queryKey: ['fees'] });
      await qc.invalidateQueries({ queryKey: ['finance-summary'] });
    },
    onError: () => setError('تعذر إضافة الرسوم.'),
  });

  const createPayment = useMutation({
    mutationFn: async () =>
      api.post('/finance/payments/', {
        student: Number(paymentForm.student),
        fee: Number(paymentForm.fee),
        amount: paymentForm.amount,
        payment_date: paymentForm.payment_date,
        method: paymentForm.method,
        reference: paymentForm.reference,
        notes: paymentForm.notes,
      }),
    onSuccess: async () => {
      setPaymentForm({
        student: paymentForm.student,
        fee: '',
        amount: '',
        payment_date: new Date().toISOString().slice(0, 10),
        method: 'CASH',
        reference: '',
        notes: '',
      });
      setError('');
      await qc.invalidateQueries({ queryKey: ['payments'] });
      await qc.invalidateQueries({ queryKey: ['fees'] });
      await qc.invalidateQueries({ queryKey: ['finance-summary'] });
    },
    onError: (err: unknown) => {
      const data = (err as { response?: { data?: Record<string, unknown> } })?.response?.data;
      const msg = data?.detail || data?.student || data?.fee || data?.amount || 'تعذر تسجيل الدفعة.';
      setError(Array.isArray(msg) ? String(msg[0]) : String(msg));
    },
  });

  const createExpense = useMutation({
    mutationFn: async () =>
      api.post('/finance/expenses/', {
        ...expenseForm,
        amount: expenseForm.amount,
      }),
    onSuccess: async () => {
      setExpenseForm({
        title: '',
        category: 'GENERAL',
        amount: '',
        expense_date: new Date().toISOString().slice(0, 10),
        notes: '',
      });
      setError('');
      await qc.invalidateQueries({ queryKey: ['expenses'] });
      await qc.invalidateQueries({ queryKey: ['finance-summary'] });
    },
    onError: () => setError('تعذر إضافة المصروف.'),
  });

  if (!canManage) {
    return (
      <div className="page">
        <header className="page-header">
          <h2>المالية</h2>
          <p className="muted">إدارة الرسوم والمدفوعات متاحة لإدارة المدرسة فقط.</p>
        </header>
      </div>
    );
  }

  return (
    <div className="page">
      <header className="page-header">
        <h2>المالية</h2>
        <p className="muted">رسوم · تسجيل دفعات الطلاب · مصروفات</p>
      </header>

      <section className="stats-grid">
        <article className="stat-tile">
          <span>إجمالي الرسوم</span>
          <strong>{summary.data?.total_fees ?? 0}</strong>
        </article>
        <article className="stat-tile">
          <span>المدفوع</span>
          <strong>{summary.data?.paid ?? 0}</strong>
        </article>
        <article className="stat-tile">
          <span>المتبقي</span>
          <strong>{summary.data?.outstanding ?? 0}</strong>
        </article>
        <article className="stat-tile">
          <span>المصروفات</span>
          <strong>{summary.data?.expenses ?? 0}</strong>
        </article>
      </section>

      <div className="tabs">
        <button type="button" className={tab === 'fees' ? 'tab active' : 'tab'} onClick={() => setTab('fees')}>
          الرسوم
        </button>
        <button
          type="button"
          className={tab === 'payments' ? 'tab active' : 'tab'}
          onClick={() => setTab('payments')}
        >
          تسجيل دفعة
        </button>
        <button
          type="button"
          className={tab === 'expenses' ? 'tab active' : 'tab'}
          onClick={() => setTab('expenses')}
        >
          المصروفات
        </button>
      </div>

      {error && <div className="alert error">{error}</div>}

      {tab === 'fees' && (
        <>
          <form
            className="panel form-grid"
            onSubmit={(e: FormEvent) => {
              e.preventDefault();
              createFee.mutate();
            }}
          >
            <h3>إضافة رسوم لطالب</h3>
            <label>
              الطالب *
              <select
                required
                value={feeForm.student}
                onChange={(e) => setFeeForm({ ...feeForm, student: e.target.value })}
              >
                <option value="">اختر</option>
                {(students.data?.results ?? []).map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.full_name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              المبلغ *
              <input
                required
                type="number"
                min="0"
                step="0.01"
                value={feeForm.amount}
                onChange={(e) => setFeeForm({ ...feeForm, amount: e.target.value })}
              />
            </label>
            <label>
              العنوان
              <input
                value={feeForm.title}
                onChange={(e) => setFeeForm({ ...feeForm, title: e.target.value })}
              />
            </label>
            <label>
              العام الدراسي
              <input
                value={feeForm.academic_year}
                onChange={(e) => setFeeForm({ ...feeForm, academic_year: e.target.value })}
              />
            </label>
            <div className="form-actions">
              <button className="btn btn-primary" type="submit" disabled={createFee.isPending}>
                حفظ الرسوم
              </button>
            </div>
          </form>

          <div className="panel table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>الطالب</th>
                  <th>العنوان</th>
                  <th>المبلغ</th>
                  <th>المدفوع</th>
                  <th>المتبقي</th>
                </tr>
              </thead>
              <tbody>
                {feeRows.map(
                  (f: {
                    id: number;
                    student_name: string;
                    title: string;
                    amount: string;
                    paid_amount: string;
                    remaining_amount: string;
                  }) => (
                    <tr key={f.id}>
                      <td>{f.student_name}</td>
                      <td>{f.title}</td>
                      <td>{f.amount}</td>
                      <td>{f.paid_amount}</td>
                      <td>{f.remaining_amount}</td>
                    </tr>
                  ),
                )}
                {feeRows.length === 0 && (
                  <tr>
                    <td colSpan={5} className="muted">
                      لا توجد رسوم بعد.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}

      {tab === 'payments' && (
        <>
          <form
            className="panel form-grid"
            onSubmit={(e: FormEvent) => {
              e.preventDefault();
              createPayment.mutate();
            }}
          >
            <h3>تسجيل دفعة لطالب</h3>
            <label>
              الطالب *
              <select
                required
                value={paymentForm.student}
                onChange={(e) =>
                  setPaymentForm({ ...paymentForm, student: e.target.value, fee: '' })
                }
              >
                <option value="">اختر</option>
                {(students.data?.results ?? []).map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.full_name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              الرسوم *
              <select
                required
                value={paymentForm.fee}
                onChange={(e) => {
                  const fee = feesForStudent.find((f: { id: number }) => String(f.id) === e.target.value) as
                    | { id: number; remaining_amount?: string | number }
                    | undefined;
                  setPaymentForm({
                    ...paymentForm,
                    fee: e.target.value,
                    amount:
                      fee?.remaining_amount != null && Number(fee.remaining_amount) > 0
                        ? String(fee.remaining_amount)
                        : paymentForm.amount,
                  });
                }}
              >
                <option value="">اختر الرسوم</option>
                {feesForStudent.map(
                  (f: {
                    id: number;
                    title: string;
                    remaining_amount: string | number;
                    amount: string | number;
                  }) => (
                    <option key={f.id} value={f.id}>
                      {f.title} — متبقي {f.remaining_amount} / {f.amount}
                    </option>
                  ),
                )}
              </select>
            </label>
            <label>
              المبلغ *
              <input
                required
                type="number"
                min="0.01"
                step="0.01"
                value={paymentForm.amount}
                onChange={(e) => setPaymentForm({ ...paymentForm, amount: e.target.value })}
              />
            </label>
            <label>
              التاريخ *
              <input
                required
                type="date"
                value={paymentForm.payment_date}
                onChange={(e) => setPaymentForm({ ...paymentForm, payment_date: e.target.value })}
              />
            </label>
            <label>
              طريقة الدفع
              <select
                value={paymentForm.method}
                onChange={(e) => setPaymentForm({ ...paymentForm, method: e.target.value })}
              >
                <option value="CASH">نقداً</option>
                <option value="CARD">بطاقة</option>
                <option value="BANK">تحويل بنكي</option>
                <option value="OTHER">أخرى</option>
              </select>
            </label>
            <label>
              المرجع / رقم الإيصال
              <input
                value={paymentForm.reference}
                onChange={(e) => setPaymentForm({ ...paymentForm, reference: e.target.value })}
              />
            </label>
            <label className="full">
              ملاحظات
              <input
                value={paymentForm.notes}
                onChange={(e) => setPaymentForm({ ...paymentForm, notes: e.target.value })}
              />
            </label>
            <div className="form-actions">
              <button className="btn btn-primary" type="submit" disabled={createPayment.isPending}>
                تسجيل الدفعة
              </button>
            </div>
            {paymentForm.student && feesForStudent.length === 0 && (
              <p className="muted full">لا توجد رسوم لهذا الطالب. أضف رسوماً أولاً من تبويب الرسوم.</p>
            )}
          </form>

          <div className="panel table-wrap">
            <h3>سجل المدفوعات</h3>
            <table className="data-table">
              <thead>
                <tr>
                  <th>الطالب</th>
                  <th>المبلغ</th>
                  <th>التاريخ</th>
                  <th>الطريقة</th>
                  <th>المرجع</th>
                </tr>
              </thead>
              <tbody>
                {paymentRows.map(
                  (p: {
                    id: number;
                    student_name: string;
                    amount: string;
                    payment_date: string;
                    method: string;
                    reference: string;
                  }) => (
                    <tr key={p.id}>
                      <td>{p.student_name}</td>
                      <td>{p.amount}</td>
                      <td>{p.payment_date}</td>
                      <td>{p.method}</td>
                      <td>{p.reference || '—'}</td>
                    </tr>
                  ),
                )}
                {paymentRows.length === 0 && (
                  <tr>
                    <td colSpan={5} className="muted">
                      لا توجد مدفوعات بعد.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}

      {tab === 'expenses' && (
        <>
          <form
            className="panel form-grid"
            onSubmit={(e: FormEvent) => {
              e.preventDefault();
              createExpense.mutate();
            }}
          >
            <h3>إضافة مصروف</h3>
            <label>
              العنوان *
              <input
                required
                value={expenseForm.title}
                onChange={(e) => setExpenseForm({ ...expenseForm, title: e.target.value })}
              />
            </label>
            <label>
              المبلغ *
              <input
                required
                type="number"
                min="0.01"
                step="0.01"
                value={expenseForm.amount}
                onChange={(e) => setExpenseForm({ ...expenseForm, amount: e.target.value })}
              />
            </label>
            <label>
              التاريخ *
              <input
                required
                type="date"
                value={expenseForm.expense_date}
                onChange={(e) => setExpenseForm({ ...expenseForm, expense_date: e.target.value })}
              />
            </label>
            <label>
              الفئة
              <input
                value={expenseForm.category}
                onChange={(e) => setExpenseForm({ ...expenseForm, category: e.target.value })}
              />
            </label>
            <div className="form-actions">
              <button className="btn btn-primary" type="submit" disabled={createExpense.isPending}>
                حفظ
              </button>
            </div>
          </form>

          <div className="panel table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>العنوان</th>
                  <th>المبلغ</th>
                  <th>التاريخ</th>
                  <th>الفئة</th>
                </tr>
              </thead>
              <tbody>
                {expenseRows.map(
                  (x: {
                    id: number;
                    title: string;
                    amount: string;
                    expense_date: string;
                    category: string;
                  }) => (
                    <tr key={x.id}>
                      <td>{x.title}</td>
                      <td>{x.amount}</td>
                      <td>{x.expense_date}</td>
                      <td>{x.category}</td>
                    </tr>
                  ),
                )}
                {expenseRows.length === 0 && (
                  <tr>
                    <td colSpan={4} className="muted">
                      لا توجد مصروفات بعد.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
