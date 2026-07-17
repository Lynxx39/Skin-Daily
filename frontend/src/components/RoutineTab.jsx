import React, { useState, useEffect } from 'react';
import { supabase } from '../utils/supabase';

export default function RoutineTab({ API_BASE }) {
  const [routineType, setRoutineType] = useState('AM');
  const [steps, setSteps] = useState([]);
  const [checked, setChecked] = useState({});
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);

  const expiryInfo = (opened, months) => {
    if (!opened || !months) return null;
    const openDate = new Date(opened);
    const expDate = new Date(openDate);
    expDate.setMonth(expDate.getMonth() + parseInt(months));
    const now = new Date();
    const daysLeft = Math.floor((expDate - now) / 86400000);
    const label = expDate.toLocaleDateString('id-ID', { day: 'numeric', month: 'short', year: 'numeric' });
    return { daysLeft, expired: daysLeft < 0, urgent: daysLeft >= 0 && daysLeft <= 30, label };
  };

  const load = async (type) => {
    setLoading(true); setMessage(null);
    try {
      const res = await fetch(`${API_BASE}/api/routine?routine_type=${type}`);
      const data = await res.json();
      const steps_data = data.steps || [];
      const mapped = steps_data.map(s => ({
        step_order: s.step_order, id: s.id, step_id: s.step_id,
        brand: s.brand, name: s.name, ingredients: s.ingredients,
        frequency_notes: s.frequency_notes,
        expiry: { daysLeft: s.days_remaining, expired: s.is_expired, urgent: s.days_remaining >= 0 && s.days_remaining <= 30, label: s.label },
      }));
      setSteps(mapped);
      setChecked(Object.fromEntries(mapped.map(s => [s.id, false])));
    } catch (e) { console.error(e); setMessage({ ok: false, text: 'Gagal memuat rutinitas.' }); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(routineType); }, [routineType]);

  const toggle = id => setChecked(p => ({ ...p, [id]: !p[id] }));

  const save = async () => {
    if (!steps.length) return;
    setSaving(true); setMessage(null);
    const logs = steps.map(s => ({ product_id: s.id, status: checked[s.id] ? 'COMPLETED' : 'SKIPPED' }));
    try {
      await supabase.from('routine_logs').insert(logs);
      await fetch(`${API_BASE}/api/routine/log`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(logs) });
      const done = logs.filter(l => l.status === 'COMPLETED').length;
      setMessage({ ok: true, text: `${done} dari ${steps.length} produk dicatat. Laporan dikirim ke Telegram.` });
    } catch { setMessage({ ok: false, text: 'Gagal menyimpan. Coba lagi.' }); }
    finally { setSaving(false); }
  };

  const completedCount = Object.values(checked).filter(Boolean).length;
  const progress = steps.length ? (completedCount / steps.length) * 100 : 0;
  const isAM = routineType === 'AM';
  const expiring = steps.filter(s => s.expiry && (s.expiry.expired || s.expiry.urgent));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

      {/* ── Toggle AM/PM ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
        {[['AM', '☀', 'rgba(201,168,76,0.14)', '#C9A84C'], ['PM', '☽', 'rgba(100,80,160,0.14)', '#9B8FD4']].map(([t, emoji, bg, col]) => (
          <button key={t} onClick={() => setRoutineType(t)} className="btn"
            style={{ padding: '14px 0', fontSize: '0.8rem', fontWeight: 700, letterSpacing: '0.06em',
              background: routineType === t ? bg : 'var(--bg-surface)',
              border: `1px solid ${routineType === t ? col + '55' : 'var(--border-sub)'}`,
              color: routineType === t ? col : 'var(--text-lo)',
              boxShadow: routineType === t ? `0 4px 20px ${col}22` : 'none',
            }}>
            <span style={{ marginRight: 6, fontSize: '1rem' }}>{emoji}</span>
            {t === 'AM' ? 'Pagi — AM' : 'Malam — PM'}
          </button>
        ))}
      </div>

      {/* ── Header block ── */}
      <div className="s-card" style={{ padding: 20 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <p className="section-label" style={{ marginBottom: 4 }}>{isAM ? 'Morning Routine' : 'Night Routine'}</p>
            <h2 className="serif" style={{ margin: 0, fontSize: '1.3rem', fontWeight: 600, color: 'var(--text-hi)', letterSpacing: '-0.01em' }}>
              {isAM ? 'Rutinitas Pagi' : 'Rutinitas Malam'}
            </h2>
          </div>
          <div style={{ textAlign: 'right' }}>
            <span className={`tag ${isAM ? 'tag-gold' : 'tag-muted'}`} style={{ color: isAM ? '#C9A84C' : '#9B8FD4', background: isAM ? 'rgba(201,168,76,0.1)' : 'rgba(155,143,212,0.12)', borderColor: isAM ? 'rgba(201,168,76,0.25)' : 'rgba(155,143,212,0.25)' }}>
              {completedCount}/{steps.length} selesai
            </span>
          </div>
        </div>

        {/* Progress */}
        {steps.length > 0 && (
          <div style={{ marginTop: 14 }}>
            <div className="progress-track">
              <div className="progress-fill" style={{ width: `${progress}%`, background: isAM ? 'linear-gradient(90deg,#C9A84C,#D4897A)' : 'linear-gradient(90deg,#9B8FD4,#7B6DB4)' }} />
            </div>
          </div>
        )}
      </div>

      {/* ── Expiry warning ── */}
      {expiring.length > 0 && (
        <div className="s-card hazard" style={{ padding: '12px 16px', borderColor: 'rgba(212,118,59,0.3)' }}>
          <p style={{ margin: '0 0 8px', fontSize: '0.72rem', fontWeight: 700, color: 'var(--color-warn)' }}>
            ⚠ Peringatan Masa PAO
          </p>
          {expiring.map(s => (
            <div key={s.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 4 }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-mid)', fontWeight: 500 }}>{s.brand} {s.name}</span>
              <span className={`tag ${s.expiry.expired ? 'tag-danger' : 'tag-warn'}`}>
                {s.expiry.expired ? `Exp ${s.expiry.label}` : s.expiry.label}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* ── Message ── */}
      {message && (
        <div style={{ padding: '10px 14px', borderRadius: 10, fontSize: '0.78rem', fontWeight: 500, lineHeight: 1.5,
          background: message.ok ? 'rgba(125,155,118,0.1)' : 'rgba(184,84,80,0.1)',
          border: `1px solid ${message.ok ? 'rgba(125,155,118,0.25)' : 'rgba(184,84,80,0.25)'}`,
          color: message.ok ? '#9BBF94' : '#D4736F',
        }}>
          {message.text}
        </div>
      )}

      {/* ── Step list ── */}
      {loading ? (
        [90, 90, 90].map((h, i) => <div key={i} className="skeleton" style={{ height: h }} />)
      ) : steps.length === 0 ? (
        <div className="s-card" style={{ padding: '40px 20px', textAlign: 'center' }}>
          <p className="serif" style={{ fontSize: '1.3rem', color: 'var(--text-lo)', margin: '0 0 8px', fontStyle: 'italic' }}>Belum ada jadwal</p>
          <p style={{ fontSize: '0.72rem', color: 'var(--text-tiny)', margin: 0 }}>
            Tambahkan produk ke rutinitas {routineType} melalui tab Gudang.
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {steps.map((step, idx) => {
            const isDone = checked[step.id];
            return (
              <div
                key={step.id}
                onClick={() => toggle(step.id)}
                className={`s-card s-card-hover`}
                style={{
                  padding: '14px 16px',
                  cursor: 'pointer',
                  display: 'flex', alignItems: 'center', gap: 14,
                  background: isDone ? 'rgba(125,155,118,0.06)' : 'var(--bg-surface)',
                  borderColor: isDone ? 'rgba(125,155,118,0.2)' : 'var(--border-sub)',
                  transition: 'all 0.25s ease',
                  userSelect: 'none',
                }}
              >
                {/* Index */}
                <span style={{
                  minWidth: 28, height: 28, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: '0.7rem', fontFamily: "'Playfair Display', serif", fontWeight: 600, flexShrink: 0,
                  background: isDone ? 'rgba(125,155,118,0.12)' : 'var(--bg-raised)',
                  color: isDone ? 'var(--color-sage)' : 'var(--text-lo)',
                  border: `1px solid ${isDone ? 'rgba(125,155,118,0.2)' : 'var(--border-sub)'}`,
                }}>
                  {idx + 1}
                </span>

                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
                    <span style={{
                      fontSize: '0.88rem', fontWeight: 600, color: isDone ? 'var(--text-lo)' : 'var(--text-hi)',
                      textDecoration: isDone ? 'line-through' : 'none',
                      textDecorationColor: 'var(--text-lo)',
                      transition: 'all 0.2s',
                      overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis',
                    }}>
                      {step.brand}
                    </span>
                    {step.expiry && (
                      <span className={`tag ${step.expiry.expired ? 'tag-danger' : step.expiry.urgent ? 'tag-warn' : 'tag-sage'}`}>
                        {step.expiry.label}
                      </span>
                    )}
                  </div>
                  <p style={{ margin: 0, fontSize: '0.72rem', color: 'var(--text-lo)', fontWeight: 400, overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis' }}>
                    {step.name}
                  </p>
                  {step.ingredients && (
                    <p style={{ margin: '4px 0 0', fontSize: '0.6rem', color: 'var(--text-tiny)', letterSpacing: '0.03em', overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis' }}>
                      {step.ingredients}
                    </p>
                  )}
                  {step.frequency_notes && (
                    <p style={{ margin: '4px 0 0', fontSize: '0.65rem', color: 'var(--text-mid)', fontStyle: 'italic', fontWeight: 500 }}>
                      📅 {step.frequency_notes}
                    </p>
                  )}
                </div>

                <div className={`check-circle ${isDone ? 'done' : ''}`}>
                  {isDone && (
                    <svg width="12" height="12" fill="white" viewBox="0 0 20 20">
                      <path d="M0 11l2-2 5 5L18 3l2 2L7 18z"/>
                    </svg>
                  )}
                </div>
              </div>
            );
          })}

          <hr className="rule" style={{ margin: '4px 0' }} />

          <button onClick={save} disabled={saving || !steps.length} className="btn btn-gold"
            style={{ width: '100%', padding: '14px', fontSize: '0.85rem' }}>
            {saving ? 'Menyimpan...' : '📋 Simpan Log & Kirim Telegram'}
          </button>
        </div>
      )}
    </div>
  );
}
