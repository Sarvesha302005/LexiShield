import React, { useRef } from 'react';
import { ArrowRight } from 'lucide-react';
import HowItWorks from './HowItWorks';
import PromisesAndStats from './PromisesAndStats';
import FaqSection from './FaqSection';
import Reveal from './Reveal';

const WORKS_WITH = ['PayPal', 'Shopify', 'UPS', 'FedEx', 'USPS', 'Visa', 'Mastercard'];

const HEADLINE_LINES = [
  { text: 'Disputes resolved,', accent: false },
  { text: 'before they cost you.', accent: true },
];

// Splits the headline into words that blur-in one after another.
function AnimatedHeadline() {
  let wordIndex = 0;
  return (
    <h1
      className="hero-title text-4xl sm:text-6xl lg:text-7xl font-extrabold text-slate-900 mb-6 font-display"
      aria-label={HEADLINE_LINES.map((line) => line.text).join(' ')}
    >
      {HEADLINE_LINES.map((line) => (
        <span key={line.text} className={`block ${line.accent ? 'hero-accent text-sky-600' : ''}`} aria-hidden="true">
          {line.text.split(' ').map((word) => {
            const i = wordIndex++;
            return (
              <React.Fragment key={i}>
                <span className="hero-word" style={{ '--i': i }}>{word}</span>{' '}
              </React.Fragment>
            );
          })}
          {/* Identical copy on top that carries only the moving highlight */}
          {line.accent && <span className="hero-sheen">{line.text}</span>}
        </span>
      ))}
    </h1>
  );
}

export default function HomePage({ onNavigateAuth, onNavigateDashboard }) {
  const heroRef = useRef(null);

  // Feeds the cursor position to the hero's dot-grid spotlight.
  const handleHeroMove = (e) => {
    const hero = heroRef.current;
    if (!hero) return;
    const rect = hero.getBoundingClientRect();
    hero.style.setProperty('--mx', `${e.clientX - rect.left}px`);
    hero.style.setProperty('--my', `${e.clientY - rect.top}px`);
  };

  return (
    <div className="bg-white text-slate-900 min-h-screen flex flex-col">
      
      {/* 1. HERO SECTION: Eyebrow -> Headline -> Subtitle -> Works with */}
      <section ref={heroRef} onMouseMove={handleHeroMove} className="hero pt-24 pb-20 px-6 text-center">
        <div className="hero-spotlight" aria-hidden="true" />
        <div className="max-w-4xl mx-auto">

          {/* Eyebrow Chip */}
          <div className="hero-enter inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-white border border-sky-200 text-sky-700 text-xs font-semibold mb-8 shadow-xs">
            <span className="hero-dot" />
            <span className="font-mono uppercase tracking-wider text-[11px]">Real-Time PayPal Dispute Shield</span>
          </div>

          {/* Main Headline */}
          <AnimatedHeadline />

          {/* Subtitle */}
          <p
            className="hero-enter text-lg sm:text-xl text-slate-600 font-normal leading-relaxed max-w-2xl mx-auto"
            style={{ '--enter-delay': '550ms' }}
          >
            Deflect chargebacks, compile airtight evidence, and protect your capital.
          </p>

          {/* Works With Strip */}
          <div className="hero-enter mt-16" style={{ '--enter-delay': '700ms' }}>
            <p className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-4">
              Works with
            </p>
            <ul className="works-with">
              {WORKS_WITH.map((name) => (
                <li key={name}>{name}</li>
              ))}
            </ul>
          </div>

        </div>
      </section>

      {/* 2. HOW IT WORKS: pinned section, one dispute through three steps */}
      <HowItWorks />

      {/* 3. PROMISES & STATS: Internal PayPal + External Card Issuers */}
      <PromisesAndStats onExploreDashboard={onNavigateDashboard} />

      {/* 4. FAQs: Top questions answered with clean accordion */}
      <FaqSection />

      {/* 5. BOTTOM CTA BANNER */}
      <section className="py-20 bg-white border-t border-slate-200">
        <Reveal className="container mx-auto px-6 max-w-4xl">
          <div className="bg-gradient-to-r from-sky-50 via-indigo-50/50 to-blue-50 border border-sky-100 rounded-3xl p-8 sm:p-12 text-center shadow-xs">
            <h3 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight font-display mb-3">
              Ready to automate your dispute defense?
            </h3>
            <p className="text-slate-600 text-sm sm:text-base max-w-xl mx-auto mb-8">
              Connect your PayPal account or test our demo merchant environment in less than 60 seconds.
            </p>
            <div className="flex flex-wrap items-center justify-center gap-4">
              <button
                onClick={onNavigateAuth}
                className="px-7 py-3 rounded-xl font-bold text-sm text-white bg-sky-600 hover:bg-sky-500 active:scale-95 transition-all shadow-sm flex items-center gap-2"
              >
                <span>Connect with PayPal</span>
                <ArrowRight className="w-4 h-4" />
              </button>
              <button
                onClick={onNavigateDashboard}
                className="px-7 py-3 rounded-xl font-bold text-sm text-slate-700 bg-white hover:bg-slate-50 border border-slate-200 active:scale-95 transition-all shadow-xs"
              >
                Launch Demo Console
              </button>
            </div>
          </div>
        </Reveal>
      </section>

    </div>
  );
}
