import React, { useState, useRef } from 'react';
import { supabase } from '../utils/supabase';

export default function ScanTab({ API_BASE, onProductAdded }) {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [scanResult, setScanResult] = useState(null);
  const [message, setMessage] = useState(null);
  const [brand, setBrand] = useState('');
  const [name, setName] = useState('');
  const [ing, setIng] = useState('');
  const [opened, setOpened] = useState('');
  const [expiryMonth, setExpiryMonth] = useState('');
  const [addAM, setAddAM] = useState(false);
  const [addPM, setAddPM] = useState(false);
  const ref = useRef(null);

  // Compute pao_months from opened date string and expiryMonth (YYYY-MM)
  const calcPaoMonths = (openedAt, expiry) => {
    if (!expiry) return null;
    const [expY, expM] = expiry.split('-').map(Number);
    const base = openedAt ? new Date(openedAt) : new Date();
    return (expY - base.getFullYear()) * 12 + (expM - (base.getMonth() + 1));
  };

  // Default expiry 12 months from today
  const nextYear12 = () => {
    const d = new Date();
    d.setMonth(d.getMonth() + 12);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
  };

  const onFile = e => {
    const f = e.target.files[0];
    if (f) { setFile(f); setPreview(URL.createObjectURL(f)); setScanResult(null); setMessage(null); }
  };

  const scan = async () => {
    if (!file) return;
    setLoading(true); setMessage(null); setScanResult(null);
    const fd = new FormData(); fd.append('file', file);
    try {
      const res = await fetch(`${API_BASE}/api/products/scan`, { method: 'POST', body: fd });
      if (res.ok) {
        const d = await res.json(); setScanResult(d);
        setBrand(d.brand || ''); setName(d.name || '');
        setIng(Array.isArray(d.active_ingredients) ? d.active_ingredients.join(', ') : d.active_ingredients || '');
        setOpened(new Date().toISOString().split('T')[0]);
        setExpiryMonth(nextYear12());
      } else {
        const e = await res.json(); setMessage({ ok: false, text: e.detail || 'Scan gagal.' });
      }
    } catch { setMessage({ ok: false, text: 'Koneksi gagal.' }); }
    finally { setLoading(false); }
  };

  const save = async e => {
    e.preventDefault();
    if (!brand || !name) { setMessage({ ok: false, text: 'Brand dan Nama wajib diisi.' }); return; }
    setLoading(true); setMessage(null);
    const paoMonths = calcPaoMonths(opened, expiryMonth);
    try {
      const { data: ins, error } = await supabase.from('products').insert([{
        brand, name, ingredients: ing,
        opened_at: opened || null,
        pao_months: paoMonths && paoMonths > 0 ? paoMonths : null
      }]).select();
      if (error) { setMessage({ ok: false, text: error.message }); return; }
      const id = ins[0].id;
      for (const rt of [addAM && 'AM', addPM && 'PM'].filter(Boolean)) {
        const { data: steps } = await supabase.from('routine_steps').select('*').eq('routine_type', rt);
        if (!(steps || []).find(s => s.product_id === id))
          await supabase.from('routine_steps').insert([{ product_id: id, routine_type: rt, step_order: (steps || []).length + 1 }]);
      }
      setMessage({ ok: true, text: `"${brand} — ${name}" berhasil disimpan ke Supabase.` });
      setFile(null); setPreview(null); setScanResult(null); setAddAM(false); setAddPM(false); setExpiryMonth('');
      if (onProductAdded) onProductAdded();
    } catch { setMessage({ ok: false, text: 'Gagal menyimpan.' }); }
    finally { setLoading(false); }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

      {/* ── Header ── */}
      <div>
        <p className="section-label" style={{ marginBottom: 4 }}>Gemini Vision AI</p>
        <h2 className="serif" style={{ margin: 0, fontSize: '1.4rem', fontWeight: 600, color: 'var(--text-hi)', letterSpacing: '-0.01em' }}>
          Scanner Produk
        </h2>
        <p style={{ margin: '6px 0 0', fontSize: '0.72rem', color: 'var(--text-lo)', lineHeight: 1.5 }}>
          Foto kemasan atau label skincare — AI mengekstrak brand, nama, dan bahan aktif secara otomatis.
        </p>
      </div>

      <hr className="rule" />

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

      {/* ── Upload zone ── */}
      <div className="s-card" style={{ padding: 20, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14 }}>
        <input type="file" accept="image/*" capture="environment" ref={ref} onChange={onFile} style={{ display: 'none' }} />

        {preview ? (
          <div style={{ position: 'relative', width: '100%', maxWidth: 280, borderRadius: 12, overflow: 'hidden', background: '#000', border: '1px solid var(--border)' }}>
            <img src={preview} alt="" style={{ width: '100%', display: 'block', maxHeight: 220, objectFit: 'cover' }} />
            {loading && <div className="laser-line" />}
            <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, height: '40%', background: 'linear-gradient(transparent, rgba(0,0,0,0.7))' }} />
          </div>
        ) : (
          <button onClick={() => ref.current.click()} className="btn btn-ghost"
            style={{ width: '100%', maxWidth: 280, height: 140, borderRadius: 12, flexDirection: 'column', gap: 10, border: '1px dashed rgba(201,168,76,0.3)', fontSize: '0.78rem', color: 'var(--text-lo)', background: 'rgba(201,168,76,0.04)' }}>
            <svg width="32" height="32" fill="none" stroke="currentColor" viewBox="0 0 24 24" style={{ opacity: 0.5 }}>
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"/>
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z"/>
            </svg>
            Tap untuk ambil atau pilih foto
          </button>
        )}

        <div style={{ display: 'flex', gap: 8, width: '100%', maxWidth: 280 }}>
          <button onClick={() => ref.current.click()} className="btn btn-ghost" style={{ flex: 1, padding: '11px', fontSize: '0.78rem' }}>
            {preview ? '↺ Ganti' : '📁 Pilih'}
          </button>
          {preview && !scanResult && (
            <button onClick={scan} disabled={loading} className="btn btn-gold" style={{ flex: 2, padding: '11px', fontSize: '0.78rem' }}>
              {loading ? 'Memindai…' : '✦ Scan dengan AI'}
            </button>
          )}
        </div>

        {loading && (
          <p style={{ margin: 0, fontSize: '0.7rem', color: 'var(--color-gold)', fontStyle: 'italic' }}>
            Gemini AI sedang mengidentifikasi produk…
          </p>
        )}
      </div>

      {/* ── Result form ── */}
      {scanResult && (
        <form onSubmit={save} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div className="s-card" style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, paddingBottom: 12, borderBottom: '1px solid var(--border-sub)' }}>
              <span className="tag tag-sage">AI Terdeteksi</span>
              <p style={{ margin: 0, fontSize: '0.7rem', color: 'var(--text-lo)' }}>Koreksi jika ada yang salah</p>
            </div>

            {/* Brand & Name */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
              {[['Merek', brand, setBrand, 'Hada Labo', true], ['Nama Produk', name, setName, 'Lotion', true]].map(([lbl, val, set, ph, req]) => (
                <div key={lbl}>
                  <p className="section-label" style={{ marginBottom: 5 }}>{lbl}</p>
                  <input className="s-input" value={val} onChange={e => set(e.target.value)} placeholder={ph} required={req} style={{ fontSize: '0.84rem' }} />
                </div>
              ))}
            </div>

            {/* Ingredients */}
            <div>
              <p className="section-label" style={{ marginBottom: 5 }}>Bahan Aktif</p>
              <textarea className="s-input" rows={3} value={ing} onChange={e => setIng(e.target.value)} placeholder="Niacinamide, Hyaluronic Acid…" style={{ resize: 'vertical', fontSize: '0.82rem', lineHeight: 1.5 }} />
            </div>

            {/* Dates */}
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
                  min={`${new Date().getFullYear()}-${String(new Date().getMonth() + 1).padStart(2, '0')}`}
                  placeholder="MM/YYYY"
                  style={{ fontSize: '0.82rem' }}
                />
              </div>
            </div>

            {/* Routine toggles */}
            <div style={{ paddingTop: 4, borderTop: '1px solid var(--border-sub)' }}>
              <p className="section-label" style={{ marginBottom: 8 }}>Tambahkan langsung ke jadwal:</p>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                {[['AM', addAM, setAddAM, '☀ Pagi', 'rgba(201,168,76,0.14)', '#C9A84C'], ['PM', addPM, setAddPM, '☽ Malam', 'rgba(155,143,212,0.14)', '#9B8FD4']].map(([k, v, set, lbl, bg, col]) => (
                  <button key={k} type="button" onClick={() => set(!v)} className="btn"
                    style={{ padding: '10px', fontSize: '0.78rem', fontWeight: v ? 700 : 500, background: v ? bg : 'var(--bg-raised)', border: `1px solid ${v ? col + '55' : 'var(--border-sub)'}`, color: v ? col : 'var(--text-lo)' }}>
                    {lbl}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <button type="submit" disabled={loading} className="btn btn-gold" style={{ width: '100%', padding: '14px', fontSize: '0.85rem' }}>
            {loading ? 'Menyimpan…' : '💾 Simpan ke Inventaris Cloud'}
          </button>
        </form>
      )}
    </div>
  );
}
