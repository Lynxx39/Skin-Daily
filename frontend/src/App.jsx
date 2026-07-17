import React, { useState, useEffect } from 'react';
import RoutineTab from './components/RoutineTab';
import ScanTab from './components/ScanTab';
import SafetyTab from './components/SafetyTab';
import InventoryTab from './components/InventoryTab';
import { supabase } from './utils/supabase';
import './App.css';
import './index.css';

const API_BASE = import.meta.env.VITE_API_URL || '';

const TABS = [
  {
    id: 'routine', label: 'Rutin',
    icon: <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"/></svg>,
    activePip: '#C9A84C',
  },
  {
    id: 'scan', label: 'Scan',
    icon: <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"/><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z"/></svg>,
    activePip: '#D4897A',
  },
  {
    id: 'safety', label: 'Safety',
    icon: <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/></svg>,
    activePip: '#7D9B76',
  },
  {
    id: 'inventory', label: 'Gudang',
    icon: <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"/></svg>,
    activePip: '#9B8FD4',
  },
];

export default function App() {
  const [activeTab, setActiveTab] = useState('routine');
  const [products, setProducts] = useState([]);
  const [routineAM, setRoutineAM] = useState([]);
  const [routinePM, setRoutinePM] = useState([]);
  const [loading, setLoading] = useState(true);
  const [theme, setTheme] = useState(() => localStorage.getItem('skindaily-theme') || 'dark');
  const [username, setUsername] = useState(() => localStorage.getItem('skindaily-username') || '');
  const [botUsername, setBotUsername] = useState('');

  // Apply theme to document root
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('skindaily-theme', theme);
  }, [theme]);

  const toggleTheme = () => setTheme(t => t === 'dark' ? 'light' : 'dark');

  const fetchProducts = async () => {
    if (!username) return;
    const { data } = await supabase.from('products').select('*').eq('username', username).order('brand');
    setProducts(data || []);
  };

  const fetchRoutines = async () => {
    if (!username) return;
    const mapSteps = d => (d || []).filter(s => s.products).map(s => ({
      step_order: s.step_order, id: s.products.id, step_id: s.id,
      brand: s.products.brand, name: s.products.name,
      ingredients: s.products.ingredients, opened_at: s.products.opened_at, pao_months: s.products.pao_months,
    }));
    const [{ data: am }, { data: pm }] = await Promise.all([
      supabase.from('routine_steps').select('*, products(*)').eq('routine_type', 'AM').eq('username', username).order('step_order'),
      supabase.from('routine_steps').select('*, products(*)').eq('routine_type', 'PM').eq('username', username).order('step_order'),
    ]);
    setRoutineAM(mapSteps(am)); setRoutinePM(mapSteps(pm));
  };

  const loadAllData = async (silent = false) => {
    if (!username) return;
    if (!silent) setLoading(true);
    await Promise.all([fetchProducts(), fetchRoutines()]);
    if (!silent) setLoading(false);
  };

  useEffect(() => {
    if (username) {
      const registerUser = async () => {
        try {
          const { data } = await supabase.from('users').select('username').eq('username', username);
          if (!data || data.length === 0) {
            await supabase.from('users').insert([{ username }]);
          }
        } catch (err) {
          console.error('Error verifying user:', err);
        }
      };
      registerUser();
      loadAllData();
      // Fetch bot username for Telegram deep link
      fetch(`${API_BASE}/api/bot-info`).then(r => r.json()).then(d => setBotUsername(d.username || '')).catch(() => {});
    }
  }, [username]);

  const handleLogout = () => {
    localStorage.removeItem('skindaily-username');
    setUsername('');
    setProducts([]);
    setRoutineAM([]);
    setRoutinePM([]);
  };

  const now = new Date();
  const hour = now.getHours();
  const greeting = hour < 12 ? 'Good Morning' : hour < 17 ? 'Good Afternoon' : 'Good Evening';

  if (!username) {
    return (
      <div style={{ maxWidth: 430, margin: '0 auto', minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20 }}>
        <div className="s-card" style={{ padding: 30, width: '100%', display: 'flex', flexDirection: 'column', gap: 20, textAlign: 'center', boxShadow: '0 8px 32px 0 rgba(0,0,0,0.2)' }}>
          <div>
            <h1 className="serif" style={{ margin: '0 0 6px', fontSize: '2.4rem', fontWeight: 700, color: 'var(--text-hi)', letterSpacing: '-0.02em' }}>
              Skindaily<span style={{ color: 'var(--color-gold)' }}>.</span>
            </h1>
            <p style={{ margin: 0, fontSize: '0.78rem', color: 'var(--text-lo)', lineHeight: 1.5 }}>
              Personal Skincare Tracker & Layering Safety Analyzer
            </p>
          </div>
          <hr className="rule" />
          <form onSubmit={e => {
            e.preventDefault();
            const val = e.target.usernameInput.value.trim().toLowerCase();
            if (val) {
              localStorage.setItem('skindaily-username', val);
              setUsername(val);
            }
          }} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div style={{ textAlign: 'left' }}>
              <p className="section-label" style={{ marginBottom: 6 }}>Username Baru / Lama</p>
              <input
                name="usernameInput"
                className="s-input"
                placeholder="Masukkan username Anda..."
                required
                pattern="^[a-zA-Z0-9_]+$"
                title="Hanya huruf, angka, dan underscore (tanpa spasi)"
                style={{ fontSize: '0.86rem', padding: '12px 14px' }}
              />
            </div>
            <button type="submit" className="btn btn-gold" style={{ width: '100%', padding: '13px', fontSize: '0.86rem' }}>
               Mulai Lacak Skincare ✦
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 430, margin: '0 auto', minHeight: '100vh', display: 'flex', flexDirection: 'column', position: 'relative' }}>

      {/* ── Header ── */}
      <header style={{
        padding: '20px 20px 16px',
        background: 'var(--bg-surface)',
        backdropFilter: 'blur(20px) saturate(140%)',
        WebkitBackdropFilter: 'blur(20px) saturate(140%)',
        borderBottom: '1px solid var(--border-sub)',
        borderBottomLeftRadius: 20,
        borderBottomRightRadius: 20,
        position: 'sticky', top: 0, zIndex: 40,
        boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.15)',
      }}>
        {/* Top row */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4, flexWrap: 'wrap' }}>
              <span className="live-dot" />
              <span style={{ fontSize: '0.6rem', fontWeight: 600, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--color-sage)' }}>
                User: {username}
              </span>
              <button onClick={handleLogout} className="btn-ghost" style={{ padding: '0 4px', fontSize: '0.6rem', border: 'none', background: 'none', color: '#D4736F', cursor: 'pointer', textDecoration: 'underline' }}>
                (Keluar)
              </button>
            </div>
            <h1 className="serif" style={{ margin: 0, fontSize: '1.6rem', fontWeight: 700, letterSpacing: '-0.02em', lineHeight: 1, color: 'var(--text-hi)' }}>
              Skindaily<span style={{ color: 'var(--color-gold)' }}>.</span>
            </h1>
            <p style={{ margin: '4px 0 0', fontSize: '0.68rem', color: 'var(--text-lo)', letterSpacing: '0.04em' }}>
              {greeting} — {now.toLocaleDateString('id-ID', { weekday: 'long', day: 'numeric', month: 'long' })}
            </p>
          </div>

          <div style={{ textAlign: 'right', display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 6 }}>
            <div style={{ display: 'flex', gap: 4 }}>
              {botUsername && <button onClick={() => window.open(`https://t.me/${botUsername}?start=${encodeURIComponent(username)}`, '_blank')} className="btn-theme" title="Buka Bot Telegram" style={{ width: 28, height: 28, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M21.198 2.433a2.242 2.242 0 0 0-1.022.215l-8.609 3.33c-2.068.8-4.133 1.598-5.724 2.21a405.15 405.15 0 0 1-2.849 1.09c-.42.147-.99.332-1.473.901-.728.855-.149 1.827.354 2.234.349.282.8.434 1.085.546l3.93 1.556c.238.725 1.4 4.267 1.593 4.85.103.31.21.513.367.69.075.085.163.157.266.213l.018.01.017.008c.22.104.44.13.612.118l.034-.001c.32-.038.579-.192.741-.33l2.082-1.96 4.329 3.3c.08.063.207.13.3.17a1.306 1.306 0 0 0 1.065.03c.482-.18.766-.575.893-.972l3.68-17.1c.116-.545.074-.98-.09-1.345-.33-.72-1.063-.878-1.399-.963Zm-.148 1.89-3.68 17.1c-.021.09-.043.131-.113.161a.274.274 0 0 1-.182.007l-5.096-3.886-.004-.003-2.756-2.102 12.09-9.292c.068-.06.137-.14.031-.12-.074.013-.154.069-.191.093L8.127 13.35l-.001.001-1.715-4.29-.002-.004-.001-.001-.002-.003 17.727-6.865c.043-.017.12-.04.166-.017.045.022.053.08.049.146Z"/></svg>
              </button>}
              <button onClick={toggleTheme} className="btn-theme" title={theme === 'dark' ? 'Ganti ke Tema Terang' : 'Ganti ke Tema Gelap'} style={{ width: 28, height: 28, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                {theme === 'dark' ? (
                  <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707M17.657 17.657l-.707-.707M6.343 6.343l-.707-.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"/>
                  </svg>
                ) : (
                  <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"/>
                  </svg>
                )}
              </button>
            </div>
            <p style={{ margin: 0, fontSize: '0.62rem', color: 'var(--text-lo)' }}>{products.length} produk</p>
          </div>
        </div>

        {/* Tab pills */}
        <div style={{ display: 'flex', gap: 4, marginTop: 16, background: 'var(--bg-raised)', border: '1px solid var(--border-sub)', backdropFilter: 'blur(8px)', borderRadius: 14, padding: 4 }}>
          {TABS.map(tab => {
            const active = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className="btn"
                style={{
                  flex: 1, padding: '8px 4px', borderRadius: 9,
                  background: active ? 'var(--bg-hover)' : 'transparent',
                  color: active ? 'var(--text-hi)' : 'var(--text-lo)',
                  fontSize: '0.62rem', fontWeight: active ? 700 : 500,
                  flexDirection: 'column', gap: 4,
                  border: active ? '1px solid var(--border)' : '1px solid transparent',
                  transition: 'all 0.2s ease',
                  letterSpacing: '0.04em',
                }}
              >
                <span style={{ opacity: active ? 1 : 0.6 }}>{tab.icon}</span>
                <span style={{ textTransform: 'uppercase', letterSpacing: '0.06em' }}>{tab.label}</span>
                {active && (
                  <span className="nav-pip" style={{ background: tab.activePip, boxShadow: `0 0 6px ${tab.activePip}` }} />
                )}
              </button>
            );
          })}
        </div>
      </header>

      {/* ── Content ── */}
      <main style={{ flex: 1, padding: '20px 16px 40px' }}>
        {loading ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12, paddingTop: 8 }}>
            {[100, 240, 160].map((h, i) => (
              <div key={i} className="skeleton" style={{ height: h }} />
            ))}
          </div>
        ) : (
          <div className="page-in" key={activeTab}>
            {activeTab === 'routine'   && <RoutineTab API_BASE={API_BASE} username={username} />}
            {activeTab === 'scan'      && <ScanTab API_BASE={API_BASE} username={username} onProductAdded={loadAllData} />}
            {activeTab === 'safety'    && <SafetyTab API_BASE={API_BASE} products={products} username={username} onCheckComplete={() => loadAllData(true)} />}
            {activeTab === 'inventory' && <InventoryTab API_BASE={API_BASE} products={products} username={username} fetchProducts={fetchProducts} routineAM={routineAM} routinePM={routinePM} fetchRoutines={fetchRoutines} />}
          </div>
        )}
      </main>



    </div>
  );
}
