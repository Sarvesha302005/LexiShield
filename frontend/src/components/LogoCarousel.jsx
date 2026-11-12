import React, { useState, useEffect } from 'react';
import { BRAND_LOGOS as LOGOS } from '../data/brandLogos';

const PER_PAGE = 4;
const HOLD_MS = 3000;
const SLIDE_MS = 700;

const PAGES = Array.from({ length: Math.ceil(LOGOS.length / PER_PAGE) }, (_, i) =>
  LOGOS.slice(i * PER_PAGE, (i + 1) * PER_PAGE)
);

const prefersReducedMotion = () =>
  typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

// Wordmark logos already spell the brand name, so they're shown without a text label.
// The SVG markup is static, reviewed data from brandLogos.js.
function Logo({ name, viewBox, body, wordmark }) {
  return (
    <li className={`logo-item ${wordmark ? 'logo-item-wordmark' : ''}`}>
      <svg viewBox={viewBox} aria-hidden="true" dangerouslySetInnerHTML={{ __html: body }} />
      <span className={wordmark ? 'sr-only' : undefined}>{name}</span>
    </li>
  );
}

// Shows four logos at a time; every few seconds the row slides left to the next four.
// A copy of the first page sits at the end so the loop always moves left, then snaps back unseen.
export default function LogoCarousel() {
  const [index, setIndex] = useState(0);
  const [isAnimated, setIsAnimated] = useState(true);
  const [isPaused, setIsPaused] = useState(false);
  const [reducedMotion] = useState(prefersReducedMotion);

  useEffect(() => {
    if (reducedMotion || isPaused || PAGES.length < 2) return undefined;
    if (index === PAGES.length) {
      // On the copy of page one: once the slide finishes, jump to the real page one without animating.
      const id = setTimeout(() => {
        setIsAnimated(false);
        setIndex(0);
      }, SLIDE_MS);
      return () => clearTimeout(id);
    }
    const id = setTimeout(() => {
      setIsAnimated(true);
      setIndex((i) => i + 1);
    }, HOLD_MS);
    return () => clearTimeout(id);
  }, [index, isPaused, reducedMotion]);

  if (reducedMotion) {
    return (
      <ul className="logo-static">
        {LOGOS.map((logo) => <Logo key={logo.name} {...logo} />)}
      </ul>
    );
  }

  const slides = [...PAGES, PAGES[0]];
  const activePage = index % PAGES.length;

  return (
    <div
      className="logo-carousel"
      onMouseEnter={() => setIsPaused(true)}
      onMouseLeave={() => setIsPaused(false)}
    >
      <div className="logo-viewport">
        <div
          className="logo-track"
          style={{
            transform: `translateX(-${index * 100}%)`,
            transition: isAnimated ? `transform ${SLIDE_MS}ms cubic-bezier(0.65, 0, 0.35, 1)` : 'none',
          }}
        >
          {slides.map((page, i) => (
            <ul key={i} className="logo-slide" aria-hidden={i === PAGES.length ? true : undefined}>
              {page.map((logo) => <Logo key={logo.name} {...logo} />)}
            </ul>
          ))}
        </div>
      </div>

      <div className="logo-dots" aria-hidden="true">
        {PAGES.map((_, i) => (
          <span key={i} className={`logo-dot ${i === activePage ? 'logo-dot-active' : ''}`} />
        ))}
      </div>
    </div>
  );
}
