import React, { useRef } from 'react';

// Card with a cursor-following border glow and a slight 3D tilt.
export default function SpotlightCard({ children, className = '' }) {
  const ref = useRef(null);

  const handleMove = (e) => {
    const el = ref.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    el.style.setProperty('--mx', `${x}px`);
    el.style.setProperty('--my', `${y}px`);
    el.style.setProperty('--rx', `${(0.5 - y / rect.height) * 6}deg`);
    el.style.setProperty('--ry', `${(x / rect.width - 0.5) * 6}deg`);
  };

  const handleLeave = () => {
    const el = ref.current;
    if (!el) return;
    el.style.setProperty('--rx', '0deg');
    el.style.setProperty('--ry', '0deg');
  };

  return (
    <div ref={ref} onMouseMove={handleMove} onMouseLeave={handleLeave} className={`spotlight-card ${className}`}>
      {children}
    </div>
  );
}
