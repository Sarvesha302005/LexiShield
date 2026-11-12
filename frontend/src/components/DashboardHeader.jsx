import React, { useState, useEffect, useRef } from 'react';
import { Shield, ChevronDown, LogOut, Globe } from 'lucide-react';

// App header for the signed-in dashboard: brand, connected store, and the account menu.
export default function DashboardHeader({ merchantProfile, onNavigate }) {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const menuRef = useRef(null);

  const name = merchantProfile.business_name || 'My store';
  const initials = name
    .split(/\s+/)
    .filter((w) => /^[A-Za-z]/.test(w))
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join('');

  // Close the menu on an outside click or Escape.
  useEffect(() => {
    if (!isMenuOpen) return undefined;
    const onPointerDown = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) setIsMenuOpen(false);
    };
    const onKeyDown = (e) => {
      if (e.key === 'Escape') setIsMenuOpen(false);
    };
    document.addEventListener('pointerdown', onPointerDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('pointerdown', onPointerDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [isMenuOpen]);

  return (
    <header className="app-header">
      <div className="container mx-auto px-6 h-16 flex items-center justify-between gap-4">

        <div className="flex items-center gap-4 min-w-0">
          <button
            type="button"
            onClick={() => onNavigate('home')}
            className="flex items-center gap-2.5 shrink-0"
            aria-label="LexiShield home"
          >
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-sky-600 to-indigo-600 flex items-center justify-center shadow-sm">
              <Shield className="w-4 h-4 text-white" />
            </div>
            <span className="hidden sm:block font-extrabold text-base text-slate-900 tracking-tight font-display">LexiShield</span>
          </button>

          <span className="app-header-divider" aria-hidden="true" />

          <div className="min-w-0">
            <p className="text-sm font-semibold text-slate-900 truncate">{name}</p>
            <p className="flex items-center gap-1.5 text-xs text-slate-500">
              <span className="app-status-dot" aria-hidden="true" />
              Connected to PayPal
            </p>
          </div>
        </div>

        <div className="relative" ref={menuRef}>
          <button
            type="button"
            onClick={() => setIsMenuOpen((v) => !v)}
            aria-haspopup="menu"
            aria-expanded={isMenuOpen}
            className="app-account-btn"
          >
            <span className="app-avatar">{initials || 'M'}</span>
            <ChevronDown className={`w-4 h-4 text-slate-500 transition-colors ${isMenuOpen ? 'text-slate-900' : ''}`} />
          </button>

          {isMenuOpen && (
            <div className="app-menu" role="menu">
              <div className="px-3 py-2.5 border-b border-slate-100">
                <p className="text-sm font-semibold text-slate-900 truncate">{name}</p>
                <p className="text-xs text-slate-500 truncate">{merchantProfile.paypal_account}</p>
              </div>
              <button type="button" role="menuitem" className="app-menu-item" onClick={() => onNavigate('home')}>
                <Globe className="w-4 h-4" />
                <span>Back to website</span>
              </button>
              <button type="button" role="menuitem" className="app-menu-item" onClick={() => onNavigate('auth')}>
                <LogOut className="w-4 h-4" />
                <span>Sign out</span>
              </button>
            </div>
          )}
        </div>

      </div>
    </header>
  );
}
