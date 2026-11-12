import React, { useState, useEffect, useLayoutEffect, useRef } from 'react';
import { Shield, ArrowRight } from 'lucide-react';

const SECTION_LINKS = [
  { id: 'how-it-works', label: 'How it works' },
  { id: 'coverage', label: 'Coverage' },
  { id: 'faq', label: 'FAQ' },
];

// A section counts as current once its top passes this line below the navbar.
const SPY_OFFSET = 120;

export default function Navbar({ onNavigate, currentView }) {
  const [isScrolled, setIsScrolled] = useState(false);
  const [activeId, setActiveId] = useState(null);
  const [indicator, setIndicator] = useState({ left: 0, width: 0, visible: false });
  const linkRefs = useRef({});

  // Track scroll position for the compact navbar and the current section.
  useEffect(() => {
    let frame = null;
    const update = () => {
      frame = null;
      setIsScrolled(window.scrollY > 8);
      if (currentView !== 'home') {
        setActiveId(null);
        return;
      }
      let current = null;
      for (const { id } of SECTION_LINKS) {
        const rect = document.getElementById(id)?.getBoundingClientRect();
        if (rect && rect.top <= SPY_OFFSET && rect.bottom > SPY_OFFSET) current = id;
      }
      setActiveId(current);
    };
    const onScroll = () => {
      if (frame === null) frame = requestAnimationFrame(update);
    };
    update();
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll);
    return () => {
      window.removeEventListener('scroll', onScroll);
      window.removeEventListener('resize', onScroll);
      if (frame !== null) cancelAnimationFrame(frame);
    };
  }, [currentView]);

  // Slide the highlight pill under the active link.
  useLayoutEffect(() => {
    const link = activeId && linkRefs.current[activeId];
    if (link) {
      setIndicator({ left: link.offsetLeft, width: link.offsetWidth, visible: true });
    } else {
      setIndicator((prev) => ({ ...prev, visible: false }));
    }
  }, [activeId]);

  return (
    <header className={`site-nav sticky top-0 z-50 border-b ${isScrolled ? 'site-nav-scrolled' : ''}`}>
      <div className="site-nav-inner container mx-auto px-6 flex items-center justify-between">

        {/* Brand Logo */}
        <button
          type="button"
          onClick={() => onNavigate('home')}
          className="flex items-center gap-2.5 cursor-pointer select-none group"
        >
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-sky-600 to-indigo-600 flex items-center justify-center shadow-md group-hover:scale-105 transition-all">
            <Shield className="w-5 h-5 text-white" />
          </div>
          <div className="flex items-center gap-1.5">
            <span className="font-extrabold text-lg text-slate-900 tracking-tight font-display">
              LexiShield
            </span>
            <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-sky-100 text-sky-700 border border-sky-200">
              AI
            </span>
          </div>
        </button>

        {/* Section Links */}
        <nav className="relative hidden md:flex items-center gap-1" aria-label="Homepage sections">
          <span
            className={`nav-indicator ${indicator.visible ? 'nav-indicator-visible' : ''}`}
            style={{ transform: `translateX(${indicator.left}px)`, width: indicator.width }}
            aria-hidden="true"
          />
          {SECTION_LINKS.map(({ id, label }) => (
            <a
              key={id}
              ref={(el) => { linkRefs.current[id] = el; }}
              href={`/#${id}`}
              onClick={(e) => {
                e.preventDefault();
                onNavigate('home', id);
              }}
              aria-current={activeId === id ? 'location' : undefined}
              className={`nav-link text-sm font-medium ${activeId === id ? 'nav-link-active' : ''}`}
            >
              {label}
            </a>
          ))}
        </nav>

        {/* Right Action: Connect with PayPal */}
        <div>
          <button
            onClick={() => onNavigate('auth')}
            className="px-5 py-2.5 rounded-xl text-xs font-semibold text-white bg-sky-600 hover:bg-sky-500 active:scale-95 transition-all shadow-sm flex items-center gap-2"
          >
            <span>Connect with PayPal</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

      </div>
    </header>
  );
}
