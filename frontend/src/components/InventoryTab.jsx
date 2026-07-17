import React, { useState } from 'react';
import { supabase } from '../utils/supabase';

export default function InventoryTab({ API_BASE, products, username, fetchProducts, routineAM, routinePM, fetchRoutines }) {
  const [brand, setBrand] = useState('');
  const [name, setName] = useState('');
  const [ing, setIng] = useState('');
  const [opened, setOpened] = useState('');
  const [expiryMonth, setExpiryMonth] = useState('');
  const [saving, setSaving] = useState(false);
  const [detecting, setDetecting] = useState(false);
  const [msg, setMsg] = useState(null);
  const [showForm, setShowForm] = useState(false);

  // Default expiry = 12 months from today in YYYY-MM format
  const defaultExpiry = () => {
    const d = new Date();
    d.setMonth(d.getMonth() + 12);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
  };

  // Compute pao_months from opened_at date and expiryMonth (YYYY-MM)
  const calcPaoMonths = (openedAt, expiry) => {
    if (!expiry) return null;
    const [expY, expM] = expiry.split('-').map(Number);
    const base = openedAt ? new Date(openedAt) : new Date();
    return (expY - base.getFullYear()) * 12 + (expM - (base.getMonth() + 1));
  };

  const detectIng = async () => {
    if (!brand || !name) { setMsg({ ok: false, text: 'Isi Merek dan Nama dulu.' }); return; }
    setDetecting(true); setMsg(null);
    try {
      const res = await fetch(`${API_BASE}/api/products/analyze-ingredients?brand=${encodeURIComponent(brand)}&name=${encodeURIComponent(name)}`);
      if (res.ok) {
        const d = await res.json();
        if (d.ingredients) { setIng(d.ingredients); setMsg({ ok: true, text: `Terdeteksi: ${d.ingredients}` }); }
        else setMsg({ ok: false, text: 'AI tidak dapat mendeteksi. Isi manual.' });
      } else setMsg({ ok: false, text: 'Gagal menghubungi AI.' });
    } catch { setMsg({ ok: false, text: 'Koneksi gagal.' }); }
    finally { setDetecting(false); }
  };

  const addProduct = async e => {
    e.preventDefault();
    if (!brand || !name) { setMsg({ ok: false, text: 'Brand dan Nama wajib.' }); return; }
    if (!username) { setMsg({ ok: false, text: 'Username wajib.' }); return; }
    setSaving(true); setMsg(null);
    const paoMonths = calcPaoMonths(opened, expiryMonth);
    try {
      const { error } = await supabase.from('products').insert([{
        brand, name, ingredients: ing,
        opened_at: opened || null,
        pao_months: paoMonths && paoMonths > 0 ? paoMonths : null,
        username
      }]);
      if (!error) {
        setMsg({ ok: true, text: `"${brand} — ${name}" tersimpan.` });
        setBrand(''); setName(''); setIng(''); setOpened(''); setExpiryMonth(''); setShowForm(false);
        fetchProducts();
      } else setMsg({ ok: false, text: error.message });
    } catch { setMsg({ ok: false, text: 'Gagal.' }); }
    finally { setSaving(false); }
  };

  const deleteProd = async id => {
    if (!window.confirm('Hapus produk ini dari cloud?')) return;
    await supabase.from('routine_steps').delete().eq('product_id', id);
    await supabase.from('routine_logs').delete().eq('product_id', id);
    await supabase.from('products').delete().eq('id', id);
    fetchProducts(); fetchRoutines();
  };

  const toggleRoutine = async (productId, rt) => {
    if (!username) return;
    const { data: existing } = await supabase.from('routine_steps').select('*').eq('product_id', productId).eq('routine_type', rt).eq('username', username);
    if (existing?.length > 0) {
      await supabase.from('routine_steps').delete().eq('product_id', productId).eq('routine_type', rt).eq('username', username);
    } else {
      const { data: all } = await supabase.from('routine_steps').select('*').eq('routine_type', rt).eq('username', username);
      await supabase.from('routine_steps').insert([{ product_id: productId, routine_type: rt, step_order: (all || []).length + 1, username }]);
    }
    fetchRoutines();
  };

  const getExpiry = prod => {
    if (!prod.opened_at || !prod.pao_months) return null;
    const expDate = new Date(prod.opened_at);
    expDate.setMonth(expDate.getMonth() + parseInt(prod.pao_months));
    const daysLeft = Math.floor((expDate - new Date()) / 86400000);
    const label = expDate.toLocaleDateString('id-ID', { day: 'numeric', month: 'short', year: 'numeric' });
    return { daysLeft, expired: daysLeft < 0, urgent: daysLeft >= 0 && daysLeft <= 30, label };
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

      {/* ── Header ── */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div>
          <p className="section-label" style={{ marginBottom: 4 }}>Cloud Storage</p>
          <h2 className="serif" style={{ margin: 0, fontSize: '1.4rem', fontWeight: 600, color: 'var(--text-hi)', letterSpacing: '-0.01em' }}>
            Gudang Skincare
          </h2>
          <p style={{ margin: '4px 0 0', fontSize: '0.68rem', color: 'var(--text-lo)' }}>
            {products.length} produk tersimpan di Supabase
          </p>
        </div>
        <button onClick={() => { setShowForm(!showForm); setMsg(null); }} className="btn btn-gold"
          style={{ padding: '8px 16px', fontSize: '0.78rem', marginTop: 4, flexShrink: 0 }}>
          {showForm ? '✕ Tutup' : '+ Tambah'}
        </button>
      </div>

      <hr className="rule" />

      {/* ── Add form ── */}
      {showForm && (
        <form onSubmit={addProduct} className="s-card" style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 14 }}>
          <p style={{ margin: 0, fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-hi)' }}>Tambah Produk Baru</p>

          {msg && (
            <div style={{ padding: '8px 12px', borderRadius: 8, fontSize: '0.74rem',
              background: msg.ok ? 'rgba(125,155,118,0.1)' : 'rgba(184,84,80,0.1)',
              border: `1px solid ${msg.ok ? 'rgba(125,155,118,0.25)' : 'rgba(184,84,80,0.25)'}`,
              color: msg.ok ? '#9BBF94' : '#D4736F',
            }}>
              {msg.text}
            </div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <div>
              <p className="section-label" style={{ marginBottom: 5 }}>Merek</p>
              <input className="s-input" value={brand} onChange={e => setBrand(e.target.value)} placeholder="Hada Labo" required style={{ fontSize: '0.84rem' }} />
            </div>
            <div>
              <p className="section-label" style={{ marginBottom: 5 }}>Nama Produk</p>
              <input className="s-input" value={name} onChange={e => setName(e.target.value)} placeholder="Lotion" required style={{ fontSize: '0.84rem' }} />
            </div>
          </div>

          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 5 }}>
              <p className="section-label" style={{ margin: 0 }}>Bahan Aktif</p>
              <button type="button" onClick={detectIng} disabled={detecting} className="btn btn-ghost"
                style={{ padding: '4px 10px', fontSize: '0.62rem', borderRadius: 6, border: '1px solid var(--border)' }}>
                {detecting ? 'Mendeteksi…' : '✦ Deteksi AI'}
              </button>
            </div>
            <input className="s-input" value={ing} onChange={e => setIng(e.target.value)} placeholder="Hyaluronic Acid, Niacinamide…" style={{ fontSize: '0.82rem' }} />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <div>
              <p className="section-label" style={{ marginBottom: 5 }}>Tgl Dibuka</p>
              <input type="date" className="s-input" value={opened} onChange={e => setOpened(e.target.value)} style={{ fontSize: '0.82rem' }} />
            </div>
            <div>
              <p className="section-label" style={{ marginBottom: 5 }}>Kadaluarsa (Bln/Thn)</p>
              <input
                type="month"
                className="s-input"
                value={expiryMonth}
                onChange={e => setExpiryMonth(e.target.value)}
                min={`${new Date().getFullYear()}-${String(new Date().getMonth() + 1).padStart(2,'0')}`}
                placeholder="MM/YYYY"
                style={{ fontSize: '0.82rem' }}
              />
            </div>
          </div>

          <button type="submit" disabled={saving} className="btn btn-gold" style={{ width: '100%', padding: '13px', fontSize: '0.84rem' }}>
            {saving ? 'Menyimpan…' : '💾 Simpan ke Cloud'}
          </button>
        </form>
      )}

      {/* ── Product list ── */}
      {products.length === 0 ? (
        <div className="s-card" style={{ padding: '40px 20px', textAlign: 'center' }}>
          <p className="serif" style={{ fontSize: '1.2rem', color: 'var(--text-lo)', fontStyle: 'italic', margin: '0 0 8px' }}>
            Inventaris masih kosong
          </p>
          <p style={{ margin: 0, fontSize: '0.7rem', color: 'var(--text-tiny)' }}>
            Tap "+ Tambah" atau gunakan Scanner AI untuk mulai.
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          {products.map((prod, idx) => {
            const inAM = routineAM.some(s => s.id === prod.id);
            const inPM = routinePM.some(s => s.id === prod.id);
            const expiry = getExpiry(prod);
            const isLast = idx === products.length - 1;

            return (
              <div key={prod.id} style={{
                padding: '16px 0',
                borderBottom: isLast ? 'none' : '1px solid var(--border-sub)',
              }}>
                {/* Top row */}
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'flex-start' }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    {/* Expiry badge */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4, flexWrap: 'wrap' }}>
                      <span style={{ fontSize: '0.88rem', fontWeight: 600, color: 'var(--text-hi)', overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis' }}>
                        {prod.brand}
                      </span>
                      {expiry && (
                        <span className={`tag ${expiry.expired ? 'tag-danger' : expiry.urgent ? 'tag-warn' : 'tag-sage'}`}>
                          {expiry.expired ? `Kadaluarsa ${expiry.label}` : `Exp ${expiry.label}`}
                        </span>
                      )}
                    </div>
                    <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--text-mid)', fontWeight: 400 }}>
                      {prod.name}
                    </p>
                    {prod.ingredients && (
                      <p style={{ margin: '5px 0 0', fontSize: '0.62rem', color: 'var(--text-lo)', letterSpacing: '0.02em', overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis' }}>
                        {prod.ingredients}
                      </p>
                    )}
                    {prod.opened_at && (
                      <p style={{ margin: '2px 0 0', fontSize: '0.6rem', color: 'var(--text-tiny)' }}>
                        Dibuka {prod.opened_at}
                      </p>
                    )}
                  </div>

                  {/* Delete */}
                  <button onClick={() => deleteProd(prod.id)} className="btn btn-danger"
                    style={{ width: 32, height: 32, borderRadius: 8, padding: 0, flexShrink: 0, border: '1px solid rgba(184,84,80,0.2)' }}>
                    <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                    </svg>
                  </button>
                </div>

                {/* Routine toggles */}
                <div style={{ display: 'flex', gap: 6, marginTop: 10 }}>
                  <span style={{ fontSize: '0.6rem', color: 'var(--text-tiny)', alignSelf: 'center', textTransform: 'uppercase', letterSpacing: '0.08em', flexShrink: 0 }}>Jadwal:</span>
                  {[['AM', inAM, '☀ Pagi', '#C9A84C', 'rgba(201,168,76,0.14)'], ['PM', inPM, '☽ Malam', '#9B8FD4', 'rgba(155,143,212,0.14)']].map(([k, active, lbl, col, bg]) => (
                    <button key={k} onClick={() => toggleRoutine(prod.id, k)} className="btn"
                      style={{ padding: '5px 12px', borderRadius: 8, fontSize: '0.65rem', fontWeight: active ? 700 : 500,
                        background: active ? bg : 'var(--bg-raised)',
                        border: `1px solid ${active ? col + '44' : 'var(--border-sub)'}`,
                        color: active ? col : 'var(--text-lo)',
                      }}>
                      {lbl}
                    </button>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
