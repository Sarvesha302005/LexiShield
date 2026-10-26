import React, { useState } from 'react';
import { Shield, Wallet, KeyRound, ArrowRight, CheckCircle2, ChevronDown, Eye, EyeOff, Loader2 } from 'lucide-react';

const BRAND_POINTS = [
  'Understands every new dispute the moment it arrives',
  'Gathers tracking, photos and order proof automatically',
  'Resolves with the buyer, or submits a complete evidence file',
];

// The one-click option signs in to the preset Apex Electronics merchant account.
const ONE_CLICK_PROFILE = {
  merchant_id: 'merch_apex_us_01',
  business_name: 'Apex Electronics Store (US)',
  paypal_account: 'merchant-sandbox-apex@lexishield.io',
  mode: 'SANDBOX_AUTHENTICATED',
};

function Field({ id, label, optional, error, children }) {
  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium text-slate-700 mb-1.5">
        {label}
        {optional && <span className="font-normal text-slate-400"> (optional)</span>}
      </label>
      {children}
      {error && <p id={`${id}-error`} className="auth-error">{error}</p>}
    </div>
  );
}

export default function AuthPage({ onConnectSuccess, onNavigateDashboard }) {
  const [showKeys, setShowKeys] = useState(false);
  const [keys, setKeys] = useState({ clientId: '', clientSecret: '', webhookId: '', store: '' });
  const [errors, setErrors] = useState({});
  const [showSecret, setShowSecret] = useState(false);
  const [pending, setPending] = useState(null); // 'paypal' | 'keys' | null
  const [connected, setConnected] = useState(false);

  const isBusy = pending !== null || connected;

  const finish = (profile, source) => {
    setPending(source);
    setTimeout(() => {
      setPending(null);
      setConnected(true);
      setTimeout(() => {
        onConnectSuccess(profile);
        onNavigateDashboard();
      }, 700);
    }, 900);
  };

  const handleOneClick = () => finish(ONE_CLICK_PROFILE, 'paypal');

  const handleKeysSubmit = (e) => {
    e.preventDefault();
    const found = {};
    if (!keys.clientId.trim()) found.clientId = 'Enter your PayPal client ID.';
    if (!keys.clientSecret.trim()) found.clientSecret = 'Enter your PayPal client secret.';
    setErrors(found);
    if (Object.keys(found).length > 0) return;

    finish(
      {
        merchant_id: 'merch_custom_01',
        business_name: keys.store.trim() || 'Custom Merchant Store',
        paypal_account: 'paypal-sandbox@merchant.com',
        mode: 'BYOK_AUTHENTICATED',
      },
      'keys'
    );
  };

  const update = (field) => (e) => {
    setKeys((prev) => ({ ...prev, [field]: e.target.value }));
    if (errors[field]) setErrors((prev) => ({ ...prev, [field]: undefined }));
  };

  const inputProps = (field) => ({
    id: `auth-${field}`,
    value: keys[field],
    onChange: update(field),
    disabled: isBusy,
    'aria-invalid': errors[field] ? true : undefined,
    'aria-describedby': errors[field] ? `auth-${field}-error` : undefined,
    className: `auth-input ${errors[field] ? 'auth-input-error' : ''}`,
  });

  return (
    <div className="auth-page">

      {/* Form column */}
      <div className="auth-form-col">
        <div className="auth-form-wrap">

          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-sky-600 to-indigo-600 flex items-center justify-center shadow-md mb-6">
            <Shield className="w-5 h-5 text-white" />
          </div>

          <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight font-display">Sign in to LexiShield</h1>
          <p className="text-slate-600 mt-2 mb-8">
            Connect your PayPal merchant account to start resolving disputes automatically.
          </p>

          {connected && (
            <div className="mb-6 p-4 rounded-xl bg-emerald-50 border border-emerald-200 flex items-center gap-3 animate-fade-in" role="status">
              <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
              <p className="text-sm text-emerald-900">
                <span className="font-semibold">Connected.</span> Taking you to your dashboard…
              </p>
            </div>
          )}

          {/* One-click connect */}
          <button type="button" onClick={handleOneClick} disabled={isBusy} className="auth-btn auth-btn-primary">
            {pending === 'paypal' ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Connecting…</span>
              </>
            ) : (
              <>
                <Wallet className="w-4 h-4" />
                <span>Continue with PayPal</span>
              </>
            )}
          </button>
          <p className="text-xs text-slate-500 text-center mt-2.5">One click. No keys or setup needed.</p>

          <div className="auth-divider">
            <span>or</span>
          </div>

          {/* Bring your own keys */}
          <button
            type="button"
            onClick={() => setShowKeys((v) => !v)}
            disabled={isBusy}
            aria-expanded={showKeys}
            aria-controls="auth-keys"
            className="auth-btn auth-btn-secondary"
          >
            <KeyRound className="w-4 h-4 text-sky-600" />
            <span>Use your own API keys</span>
            <ChevronDown className={`auth-chevron w-4 h-4 text-slate-400 ${showKeys ? 'auth-chevron-open' : ''}`} />
          </button>

          <div id="auth-keys" className={`auth-collapse ${showKeys ? 'auth-collapse-open' : ''}`}>
            <div className="auth-collapse-inner">
              <form onSubmit={handleKeysSubmit} noValidate className="space-y-4 pt-6">
                <Field id="auth-clientId" label="PayPal client ID" error={errors.clientId}>
                  <input type="text" autoComplete="off" spellCheck={false} placeholder="AYSq3RDGsmBLJE-otTkBtM..." {...inputProps('clientId')} />
                </Field>

                <Field id="auth-clientSecret" label="PayPal client secret" error={errors.clientSecret}>
                  <div className="relative">
                    <input
                      type={showSecret ? 'text' : 'password'}
                      autoComplete="off"
                      spellCheck={false}
                      placeholder="Paste your client secret"
                      {...inputProps('clientSecret')}
                    />
                    <button
                      type="button"
                      onClick={() => setShowSecret((v) => !v)}
                      className="auth-eye"
                      aria-label={showSecret ? 'Hide client secret' : 'Show client secret'}
                    >
                      {showSecret ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </Field>

                <Field id="auth-webhookId" label="Webhook ID" optional>
                  <input type="text" autoComplete="off" spellCheck={false} placeholder="WH-2WR32451HC0233532-67976317FL4543714" {...inputProps('webhookId')} />
                </Field>

                <Field id="auth-store" label="Shopify store domain" optional>
                  <input type="text" autoComplete="off" spellCheck={false} placeholder="your-store.myshopify.com" {...inputProps('store')} />
                </Field>

                <p className="text-xs text-slate-500 leading-relaxed">
                  Find these in the PayPal Developer Dashboard under Apps &amp; Credentials.
                </p>

                <button type="submit" disabled={isBusy} className="auth-btn auth-btn-dark">
                  {pending === 'keys' ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Verifying keys…</span>
                    </>
                  ) : (
                    <>
                      <span>Connect with keys</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </form>
            </div>
          </div>

          <p className="text-xs text-slate-500 mt-8 leading-relaxed text-center">
            By continuing, you agree to LexiShield’s Terms of Service and Privacy Policy.
          </p>

        </div>
      </div>

      {/* Brand column (desktop only) */}
      <aside className="auth-brand" aria-hidden="true">
        <div className="auth-brand-inner">
          <p className="text-sm font-semibold text-sky-200 uppercase tracking-widest mb-6">LexiShield</p>
          <h2 className="auth-brand-title font-display">
            Disputes resolved,
            <span className="block text-sky-200">before they cost you.</span>
          </h2>
          <ul className="space-y-4 mt-10">
            {BRAND_POINTS.map((point) => (
              <li key={point} className="flex items-start gap-3 text-sky-100">
                <CheckCircle2 className="w-5 h-5 text-sky-300 shrink-0" />
                <span>{point}</span>
              </li>
            ))}
          </ul>
        </div>
      </aside>

    </div>
  );
}
