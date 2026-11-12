import React, { useState, useEffect, useRef } from 'react';
import {
  Inbox,
  Sparkles,
  MapPin,
  Camera,
  Package,
  Fingerprint,
  CheckCircle2,
  ShieldCheck,
  MessageSquare,
} from 'lucide-react';

const prefersReducedMotion = () =>
  typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

// Advances through `timings` (ms after activation) while active; returns how many have fired.
// Resets after the slide has faded out so the sequence replays on the next visit.
function useSequence(active, timings) {
  const [phase, setPhase] = useState(0);
  useEffect(() => {
    if (!active) {
      const id = setTimeout(() => setPhase(0), 450);
      return () => clearTimeout(id);
    }
    if (prefersReducedMotion()) {
      setPhase(timings.length);
      return undefined;
    }
    const ids = timings.map((t, i) => setTimeout(() => setPhase(i + 1), t));
    return () => ids.forEach(clearTimeout);
  }, [active, timings]);
  return phase;
}

function useTypewriter(text, start, speed = 26) {
  const [count, setCount] = useState(0);
  useEffect(() => {
    if (!start) {
      setCount(0);
      return undefined;
    }
    if (prefersReducedMotion()) {
      setCount(text.length);
      return undefined;
    }
    const id = setInterval(() => {
      setCount((c) => {
        if (c >= text.length) {
          clearInterval(id);
          return c;
        }
        return c + 1;
      });
    }, speed);
    return () => clearInterval(id);
  }, [text, start, speed]);
  return text.slice(0, count);
}

// Becomes true once the element has scrolled into view (used for the mobile layout).
function useInViewOnce() {
  const ref = useRef(null);
  const [inView, setInView] = useState(false);
  useEffect(() => {
    const node = ref.current;
    if (!node || !('IntersectionObserver' in window)) {
      setInView(true);
      return undefined;
    }
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setInView(true);
          observer.disconnect();
        }
      },
      { threshold: 0.4 }
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);
  return [ref, inView];
}

// One dispute followed end to end: Sarah M. says her $189.50 headphones never arrived.

const STEP_ONE_TIMINGS = [1100, 2400];
const INSIGHT = 'Likely delivered, but not found by the buyer';

function UnderstandVisual({ active }) {
  const phase = useSequence(active, STEP_ONE_TIMINGS);
  const typed = useTypewriter(INSIGHT, phase >= 1);
  const fields = [
    ['Buyer', 'Sarah M.'],
    ['Amount', '$189.50'],
    ['Reason', 'Item not received'],
    ['Item', 'Wireless headphones'],
  ];

  return (
    <div className={`hiw-panel ${active ? 'is-playing' : ''}`}>
      <span className="hiw-scan" aria-hidden="true" />
      <div className="flex items-center justify-between border-b border-slate-100 pb-4 mb-4">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-800">
          <Inbox className="w-4 h-4 text-sky-600" />
          <span>New PayPal dispute</span>
        </div>
        <span className="text-xs text-slate-500">{phase >= 1 ? 'Analyzed' : 'Analyzing…'}</span>
      </div>

      <div className="grid grid-cols-2 gap-3 mb-4">
        {fields.map(([label, value], i) => (
          <div key={label} className="hiw-field hiw-stagger" style={{ '--i': i }}>
            <span className="hiw-label">{label}</span>
            <span className="hiw-value">{value}</span>
          </div>
        ))}
      </div>

      <div className={`hiw-appear p-4 rounded-xl bg-sky-50 border border-sky-200 flex items-start gap-3 ${phase >= 1 ? 'is-in' : ''}`}>
        <Sparkles className="w-5 h-5 text-sky-600 shrink-0" />
        <div className="text-sm flex-1">
          <p className="hiw-typed font-semibold text-slate-900">
            <span className="hiw-typed-ghost" aria-hidden="true">{INSIGHT}</span>
            <span>
              {typed}
              {phase === 1 && <span className="hiw-caret" aria-hidden="true" />}
            </span>
          </p>
          <p className={`hiw-appear text-slate-600 mt-1 ${phase >= 2 ? 'is-in' : ''}`}>
            Next step: talk to the buyer before escalating.
          </p>
        </div>
      </div>
    </div>
  );
}

const EVIDENCE = [
  { icon: MapPin, title: 'Delivered to front porch', detail: 'UPS · Oct 18, 2:14 PM' },
  { icon: Camera, title: 'Carrier delivery photo', detail: 'Package at the front door' },
  { icon: Package, title: 'Shipped to address on file', detail: 'Matches the PayPal account' },
  { icon: Fingerprint, title: 'Familiar device', detail: 'Same device as 4 earlier orders' },
];
const STEP_TWO_TIMINGS = [300, 750, 1200, 1650];

function GatherVisual({ active }) {
  const collected = useSequence(active, STEP_TWO_TIMINGS);
  const isComplete = collected === EVIDENCE.length;

  return (
    <div className="hiw-panel">
      <div className="flex items-center justify-between border-b border-slate-100 pb-4 mb-4">
        <span className="text-sm font-semibold text-slate-800">Evidence for Sarah M.</span>
        <span
          className={`hiw-counter text-xs font-semibold px-2.5 py-1 rounded-full border ${
            isComplete ? 'text-emerald-700 bg-emerald-50 border-emerald-200' : 'text-slate-600 bg-slate-50 border-slate-200'
          }`}
        >
          {collected} of {EVIDENCE.length} collected
        </span>
      </div>

      <div className="space-y-3">
        {EVIDENCE.map(({ icon: Icon, title, detail }, i) => {
          const isIn = collected > i;
          return (
            <div
              key={title}
              className={`hiw-evidence flex items-center gap-3 p-3 rounded-xl bg-slate-50 border border-slate-100 ${isIn ? 'is-in' : ''}`}
            >
              <div className="w-9 h-9 rounded-lg bg-white border border-slate-200 flex items-center justify-center shrink-0">
                <Icon className="w-4 h-4 text-sky-600" />
              </div>
              <div className="flex-1 text-sm">
                <p className="font-semibold text-slate-900">{title}</p>
                <p className="text-slate-500 text-xs mt-0.5">{detail}</p>
              </div>
              <CheckCircle2 className="hiw-check w-5 h-5 text-emerald-600 shrink-0" />
            </div>
          );
        })}
      </div>
    </div>
  );
}

const STEP_THREE_TIMINGS = [200, 1000, 2300, 2800];

function ResolveVisual({ active }) {
  const phase = useSequence(active, STEP_THREE_TIMINGS);

  return (
    <div className="hiw-panel">
      <div className="flex items-center gap-2 border-b border-slate-100 pb-4 mb-4 text-sm font-semibold text-slate-800">
        <MessageSquare className="w-4 h-4 text-sky-600" />
        <span>Conversation with Sarah M.</span>
      </div>

      <div className="space-y-3 mb-4">
        <div className={`hiw-bubble hiw-bubble-out hiw-pop ${phase >= 1 ? 'is-in' : ''}`}>
          Hi Sarah, UPS shows your headphones were left on your front porch on Oct 18 at 2:14 PM. Here’s the
          carrier photo. Could they be somewhere nearby?
        </div>
        <div className="hiw-reply">
          <div className={`hiw-typing hiw-pop ${phase === 2 ? 'is-in' : ''}`} aria-hidden="true">
            <span /><span /><span />
          </div>
          <div className={`hiw-bubble hiw-bubble-in hiw-pop ${phase >= 3 ? 'is-in' : ''}`}>
            Found them behind the planter, sorry! Closing the dispute now.
          </div>
        </div>
      </div>

      <div className={`hiw-appear p-4 rounded-xl bg-emerald-50 border border-emerald-200 flex items-center gap-3 ${phase >= 4 ? 'is-in' : ''}`}>
        <ShieldCheck className="w-5 h-5 text-emerald-600 shrink-0" />
        <div className="text-sm">
          <p className="font-semibold text-emerald-900">Buyer closed the dispute</p>
          <p className="text-emerald-700 mt-0.5">No refund issued, no dispute fee charged.</p>
        </div>
      </div>
    </div>
  );
}

const steps = [
  {
    step: '01',
    headline: 'Understand the claim',
    subhead: 'Reads every new dispute the moment it arrives and works out what the buyer actually needs.',
    Visual: UnderstandVisual,
  },
  {
    step: '02',
    headline: 'Gather the proof',
    subhead: 'Pulls tracking, delivery photos, order details and device history automatically.',
    Visual: GatherVisual,
  },
  {
    step: '03',
    headline: 'Resolve it, or win it',
    subhead: 'Shows the buyer the proof to close it amicably. If they don’t, a complete evidence file goes to PayPal.',
    Visual: ResolveVisual,
  },
];

function MobileStep({ item }) {
  const [ref, inView] = useInViewOnce();
  const { Visual } = item;
  return (
    <div ref={ref} className="space-y-4">
      <div>
        <span className="font-mono text-sm font-bold text-sky-600">{item.step}</span>
        <h3 className="text-xl font-bold text-slate-900 font-display mt-1">{item.headline}</h3>
        <p className="text-sm text-slate-600 leading-relaxed mt-2">{item.subhead}</p>
      </div>
      <Visual active={inView} />
    </div>
  );
}

export default function HowItWorks() {
  const trackRef = useRef(null);
  const stepRefs = useRef([]);
  const [activeIndex, setActiveIndex] = useState(0);
  // Sequences only play once the pinned section is actually on screen.
  const [isEngaged, setIsEngaged] = useState(false);

  // Pick the active step from how far the pinned track has been scrolled through,
  // and grow the progress rail continuously alongside it.
  useEffect(() => {
    let frame = null;
    const update = () => {
      frame = null;
      const track = trackRef.current;
      if (!track) return;
      const rect = track.getBoundingClientRect();
      const scrollable = rect.height - window.innerHeight;
      if (scrollable <= 0) return;
      setIsEngaged(rect.top < window.innerHeight * 0.5 && rect.bottom > window.innerHeight * 0.5);
      const progress = Math.min(Math.max(-rect.top / scrollable, 0), 0.999);
      const idx = Math.floor(progress * steps.length);
      setActiveIndex(idx);

      const stepEl = stepRefs.current[idx];
      if (stepEl) {
        const within = progress * steps.length - idx;
        track.style.setProperty('--hiw-fill', `${stepEl.offsetTop + within * stepEl.offsetHeight}px`);
      }
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
  }, []);

  const scrollToStep = (idx) => {
    const track = trackRef.current;
    if (!track) return;
    const scrollable = track.offsetHeight - window.innerHeight;
    const top = track.getBoundingClientRect().top + window.scrollY;
    window.scrollTo({ top: top + (scrollable * (idx + 0.5)) / steps.length, behavior: 'smooth' });
  };

  const header = (
    <div className="text-center max-w-2xl mx-auto mb-10">
      <span className="text-xs font-mono font-bold uppercase tracking-widest text-sky-600 bg-sky-50 px-3 py-1 rounded-full border border-sky-200">
        How It Works
      </span>
      <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-900 mt-4 tracking-tight font-display">
        From new dispute to closed case
      </h2>
      <p className="text-slate-600 mt-2 text-sm sm:text-base">
        Follow one real-world claim through LexiShield’s three automated steps.
      </p>
    </div>
  );

  return (
    <section id="how-it-works" className="pt-6 pb-20">
      <div className="container mx-auto px-6 max-w-5xl">

        {/* Desktop: section pins while the steps change */}
        <div ref={trackRef} className="hiw-track" style={{ '--hiw-steps': steps.length }}>
          <div className="hiw-pin">
            {header}
            <div className="grid lg:grid-cols-12 gap-12 items-center w-full">

              {/* Step list with a progress rail that fills as you scroll */}
              <div className="hiw-steps-wrap lg:col-span-5">
                <span className="hiw-rail" aria-hidden="true">
                  <span className="hiw-rail-fill" />
                </span>
                <ol className="hiw-steps space-y-2">
                  {steps.map((item, idx) => {
                    const isActive = idx === activeIndex;
                    return (
                      <li key={item.step} ref={(el) => { stepRefs.current[idx] = el; }}>
                        <button
                          type="button"
                          onClick={() => scrollToStep(idx)}
                          aria-current={isActive ? 'step' : undefined}
                          className={`hiw-step ${isActive ? 'hiw-step-active' : ''}`}
                        >
                          <span className="font-mono text-sm font-bold text-sky-600">{item.step}</span>
                          <span className="block text-xl font-bold text-slate-900 font-display mt-1">
                            {item.headline}
                          </span>
                          <span className="hiw-step-body text-sm text-slate-600 leading-relaxed">
                            {item.subhead}
                          </span>
                        </button>
                      </li>
                    );
                  })}
                </ol>
              </div>

              {/* Visual: crossfades between steps, each plays its own sequence */}
              <div className="lg:col-span-7 hiw-stage">
                {steps.map(({ step, Visual }, idx) => (
                  <div
                    key={step}
                    className={`hiw-slide ${idx === activeIndex ? 'hiw-slide-active' : ''}`}
                    aria-hidden={idx !== activeIndex}
                  >
                    <Visual active={isEngaged && idx === activeIndex} />
                  </div>
                ))}
              </div>

            </div>
          </div>
        </div>

        {/* Mobile: steps one after another, each plays when scrolled into view */}
        <div className="hiw-mobile">
          {header}
          <div className="space-y-12">
            {steps.map((item) => (
              <MobileStep key={item.step} item={item} />
            ))}
          </div>
        </div>

      </div>
    </section>
  );
}
