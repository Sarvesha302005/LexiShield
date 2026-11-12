const configuredBase = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '');
const isVercelHost =
  typeof window !== 'undefined' && window.location.hostname.endsWith('.vercel.app');
const DEFAULT_RENDER_BACKEND = 'https://lexishield-pdf0.onrender.com';

export const API_BASE_URL =
  configuredBase || (isVercelHost ? DEFAULT_RENDER_BACKEND : '');

/**
 * Resolves an API path against the Render backend when running on Vercel
 * (bypassing edge proxy timeouts on cold starts or long LLM calls),
 * while staying same-origin locally and on Render.
 */
export const apiUrl = (path) => `${API_BASE_URL}${path}`;

