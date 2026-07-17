import React, { useState } from 'react';

const STATUS_CFG = {
  AMAN:       { cls: 'result-aman',   color: '#9BBF94', icon: '✓', label: 'Aman Digunakan' },
  'HATI-HATI':{ cls: 'result-hati',   color: '#D4763B', icon: '!', label: 'Perlu Hati-hati' },
  BAHAYA:     { cls: 'result-bahaya', color: '#D4736F', icon: '✕', label: 'Berbahaya' },
};

export default function SafetyTab({ API_BASE, products, onCheckComplete }) {
  const [idA, setIdA] = useState('');
  const [idB, setIdB] = useState('');
  const [loading, setLoading] = useState(false);
  const [loadingAll, setLoadingAll] = useState(false);
  const [loadingApply, setLoadingApply] = useState(false);
  const [result, setResult] = useState(null);
  const [resultAll, setResultAll] = useState(null);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  const checkTwo = async () => {
    if (!idA || !idB || idA === idB) { setError('Pilih dua produk yang berbeda.'); return; }
    setLoading(true); setError(null); setResult(null); setResultAll(null);
    try {
      const res = await fetch(`${API_BASE}/api/products/check-safety?id_a=${idA}&id_b=${idB}`);
      if (res.ok) { setResult(await res.json()); if (onCheckComplete) onCheckComplete(); }
      else { const e = await res.json(); setError(e.detail || 'Analisis gagal.'); }
    } catch { setError('Koneksi gagal.'); }
    finally { setLoading(false); }
  };

  const checkAll = async () => {
    setLoadingAll(true); setError(null); setResult(null); setResultAll(null);
    try {
      const res = await fetch(`${API_BASE}/api/products/check-safety-all`);
      if (res.ok) { setResultAll(await res.json()); if (onCheckComplete) onCheckComplete(); }
      else { const e = await res.json(); setError(e.detail || 'Analisis gagal.'); }
    } catch { setError('Koneksi gagal.'); }
    finally { setLoadingAll(false); }
  };

  const applyRecommendation = async () => {
    setLoadingApply(true); setError(null); setSuccessMsg(null);
    try {
      const res = await fetch(`${API_BASE}/api/routine/apply-ai-recommendation`, { method: 'POST' });
      if (res.ok) {
        setSuccessMsg('✓ Rutinitas berhasil diperbarui dengan rekomendasi AI!');
        setTimeout(() => setSuccessMsg(null), 4000);
      } else { const e = await res.json(); setError(e.detail || 'Gagal menerapkan rekomendasi.'); }
    } catch { setError('Koneksi gagal.'); }
    finally { setLoadingApply(false); }
  };

  const prodA = products.find(p => p.id === parseInt(idA));
  const prodB = products.find(p => p.id === parseInt(idB));

  const Select = ({ value, onChange, label, exclude }) => (
    <div>
      <p className="section-label" style={{ marginBottom: 6 }}>{label}</p>
      <select value={value} onChange={e => onChange(e.target.value)} className="s-input">
        <option value="">— Pilih Produk —</option>
        {products.filter(p => p.id !== parseInt(exclude)).map(p => (
          <option key={p.id} value={p.id}>{p.brand} — {p.name}</option>
        ))}
      </select>
    </div>
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

      {/* ── Header ── */}
      <div>
        <p className="section-label" style={{ marginBottom: 4 }}>AI Safety Analysis</p>
        <h2 className="serif" style={{ margin: 0, fontSize: '1.4rem', fontWeight: 600, color: 'var(--text-hi)', letterSpacing: '-0.01em' }}>
          Cek Keamanan Layering
        </h2>
        <p style={{ margin: '6px 0 0', fontSize: '0.72rem', color: 'var(--text-lo)', lineHeight: 1.5 }}>
          Gemini AI menganalisis interaksi bahan aktif antar produk skincare Anda.
        </p>
      </div>

      <hr className="rule" />

      {/* ── Panel 1: Dua Produk ── */}
      <div className="s-card" style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 14 }}>
        {/* Label panel */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <p className="section-label" style={{ marginBottom: 2 }}>Mode 1 — Spesifik</p>
            <p style={{ margin: 0, fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-hi)' }}>
              Cek 2 Produk vs Produk
            </p>
          </div>
          <span className="tag tag-gold">Pilihan</span>
        </div>
        <p style={{ margin: 0, fontSize: '0.7rem', color: 'var(--text-lo)', lineHeight: 1.5 }}>
          Pilih dua produk spesifik untuk dicek apakah aman digunakan bersamaan dalam satu sesi.
        </p>

        <hr className="rule" />

        <Select value={idA} onChange={setIdA} label="Produk A" exclude={idB} />

        {/* VS Divider */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ flex: 1, height: 1, background: 'var(--border-sub)' }} />
          <span className="serif" style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-lo)', fontStyle: 'italic', padding: '4px 10px', borderRadius: 6, background: 'var(--bg-raised)', border: '1px solid var(--border-sub)' }}>
            vs
          </span>
          <div style={{ flex: 1, height: 1, background: 'var(--border-sub)' }} />
        </div>

        <Select value={idB} onChange={setIdB} label="Produk B" exclude={idA} />

        <button onClick={checkTwo} disabled={loading || loadingAll || !idA || !idB} className="btn btn-gold"
          style={{ width: '100%', padding: '13px', fontSize: '0.84rem' }}>
          {loading ? 'Menganalisis…' : '🔬 Cek Keamanan 2 Produk'}
        </button>
      </div>

      {/* ── Panel 2: Semua Produk ── */}
      <div className="s-card" style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 14 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <p className="section-label" style={{ marginBottom: 2 }}>Mode 2 — Menyeluruh</p>
            <p style={{ margin: 0, fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-hi)' }}>
              Analisis Seluruh Inventaris
            </p>
          </div>
          <span className="tag tag-sage">Lengkap</span>
        </div>
        <p style={{ margin: 0, fontSize: '0.7rem', color: 'var(--text-lo)', lineHeight: 1.5 }}>
          AI akan memeriksa <strong style={{ color: 'var(--text-mid)' }}>semua {products.length} produk</strong> sekaligus — menemukan semua konflik yang ada, lalu merekomendasikan pembagian rutinitas <strong style={{ color: 'var(--text-mid)' }}>AM & PM</strong> yang paling optimal untuk semua koleksi Anda.
        </p>

        <button onClick={checkAll} disabled={loading || loadingAll || products.length < 2} className="btn btn-sage"
          style={{ width: '100%', padding: '13px', fontSize: '0.84rem' }}>
          {loadingAll ? 'Memproses semua produk…' : `🧬 Analisis ${products.length} Produk Sekaligus`}
        </button>

        {products.length < 2 && (
          <p style={{ margin: 0, fontSize: '0.68rem', color: 'var(--text-lo)', textAlign: 'center' }}>
            Butuh minimal 2 produk di inventaris.
          </p>
        )}
      </div>

      {/* ── Error ── */}
      {error && (
        <div style={{ padding: '10px 14px', borderRadius: 10, fontSize: '0.78rem', background: 'rgba(184,84,80,0.1)', border: '1px solid rgba(184,84,80,0.25)', color: '#D4736F' }}>
          {error}
        </div>
      )}

      {/* ── Success ── */}
      {successMsg && (
        <div style={{ padding: '10px 14px', borderRadius: 10, fontSize: '0.78rem', background: 'rgba(125,155,118,0.1)', border: '1px solid rgba(125,155,118,0.3)', color: '#7D9B76' }}>
          {successMsg}
        </div>
      )}

      {/* ── Loading ── */}
      {(loading || loadingAll) && (
        <div className="s-card" style={{ padding: '28px 20px', textAlign: 'center' }}>
          <p className="serif" style={{ margin: '0 0 6px', fontSize: '1.1rem', fontStyle: 'italic', color: 'var(--text-mid)' }}>
            {loadingAll ? 'Memproses seluruh inventaris…' : 'Mengevaluasi kompatibilitas…'}
          </p>
          <p style={{ margin: 0, fontSize: '0.7rem', color: 'var(--text-lo)' }}>
            Gemini AI sedang bekerja
          </p>
        </div>
      )}

      {/* ── Result: 2 products ── */}
      {result && (() => {
        const cfg = STATUS_CFG[result.status] || STATUS_CFG.AMAN;
        return (
          <div className={`s-card ${cfg.cls}`} style={{ padding: 20, borderRadius: 16 }}>
            {/* Status header */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 14 }}>
              <div style={{ width: 36, height: 36, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', background: cfg.color + '25', border: `1px solid ${cfg.color}45`, fontSize: '1rem', fontWeight: 800, color: cfg.color, flexShrink: 0, fontFamily: 'serif' }}>
                {cfg.icon}
              </div>
              <div>
                <p className="section-label" style={{ marginBottom: 2, color: cfg.color + 'cc' }}>Hasil Analisis AI</p>
                <p style={{ margin: 0, fontSize: '0.88rem', fontWeight: 700, color: cfg.color }}>{cfg.label}</p>
              </div>
            </div>
            <hr className="rule" style={{ marginBottom: 12 }} />
            <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--text-mid)', lineHeight: 1.7, fontWeight: 400 }}>
              {result.reason}
            </p>

            {/* Compared products */}
            {(prodA || prodB) && (
              <div style={{ marginTop: 14, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                {[['A', prodA], ['B', prodB]].map(([lbl, p]) => p && (
                  <div key={lbl} style={{ background: 'rgba(0,0,0,0.25)', borderRadius: 10, padding: '10px 12px' }}>
                    <p className="section-label" style={{ marginBottom: 4 }}>Produk {lbl}</p>
                    <p style={{ margin: 0, fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-hi)' }}>{p.brand}</p>
                    <p style={{ margin: '2px 0 0', fontSize: '0.65rem', color: 'var(--text-lo)', lineHeight: 1.4 }}>
                      {p.ingredients || '—'}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })()}

      {/* ── Result: All products ── */}
      {resultAll && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>

          {/* Summary card */}
          <div className="s-card" style={{ padding: 20 }}>
            <p className="section-label" style={{ marginBottom: 4 }}>Laporan Menyeluruh</p>
            <h3 className="serif" style={{ margin: '0 0 4px', fontSize: '1.2rem', fontWeight: 600, color: 'var(--text-hi)' }}>
              Analisis {products.length} Produk
            </h3>
            {resultAll.conflicts?.length > 0 ? (
              <p style={{ margin: 0, fontSize: '0.72rem', color: 'var(--color-warn)' }}>
                {resultAll.conflicts.length} konflik ditemukan dari seluruh kombinasi produk Anda.
              </p>
            ) : (
              <p style={{ margin: 0, fontSize: '0.72rem', color: 'var(--color-sage)' }}>
                Tidak ada konflik serius ditemukan. Koleksi Anda aman!
              </p>
            )}
          </div>

          {/* Conflicts */}
          {resultAll.conflicts?.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {resultAll.conflicts.map((c, i) => {
                const cfg = STATUS_CFG[c.status] || STATUS_CFG['HATI-HATI'];
                return (
                  <div key={i} className={`s-card ${cfg.cls}`} style={{ padding: '14px 16px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8, marginBottom: 6 }}>
                      <p style={{ margin: 0, fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-hi)', flex: 1, lineHeight: 1.4 }}>
                        {c.product_a} <span style={{ color: 'var(--text-lo)' }}>×</span> {c.product_b}
                      </p>
                      <span style={{ fontSize: '0.6rem', fontWeight: 700, padding: '3px 8px', borderRadius: 6, background: cfg.color + '22', color: cfg.color, whiteSpace: 'nowrap', border: `1px solid ${cfg.color}44` }}>
                        {c.status}
                      </span>
                    </div>
                    <p style={{ margin: 0, fontSize: '0.73rem', color: 'var(--text-lo)', lineHeight: 1.55 }}>{c.reason}</p>
                  </div>
                );
              })}
            </div>
          )}

          {/* Recommendation */}
          {resultAll.recommendation && (
            <div className="s-card" style={{ padding: 20, background: 'rgba(125,155,118,0.05)', borderColor: 'rgba(125,155,118,0.2)' }}>
              <p className="section-label" style={{ marginBottom: 6, color: 'var(--color-sage)' }}>💡 Rekomendasi Rutinitas AI</p>
              <p style={{ margin: 0, fontSize: '0.78rem', color: 'var(--text-mid)', lineHeight: 1.75, whiteSpace: 'pre-line' }}>
                {resultAll.recommendation}
              </p>
              <button onClick={applyRecommendation} disabled={loadingApply} className="btn btn-sage"
                style={{ width: '100%', padding: '11px 14px', fontSize: '0.84rem', marginTop: 14 }}>
                {loadingApply ? 'Menerapkan…' : '✓ Terapkan Rekomendasi'}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
