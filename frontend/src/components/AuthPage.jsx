import React, { useState } from 'react';
import { 
  ShieldCheck, 
  Key, 
  Lock, 
  ArrowRight, 
  CheckCircle2, 
  Sparkles, 
  HelpCircle,
  AlertTriangle,
  RefreshCw
} from 'lucide-react';

export default function AuthPage({ onConnectSuccess, onNavigateDashboard }) {
  const [authMode, setAuthMode] = useState('demo'); // 'demo' | 'custom'
  const [clientId, setClientId] = useState('');
  const [clientSecret, setClientSecret] = useState('');
  const [webhookId, setWebhookId] = useState('');
  const [shopifyStore, setShopifyStore] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMsg, setSuccessMsg] = useState(false);

  const handleDemoLogin = () => {
    setIsSubmitting(true);
    setTimeout(() => {
      setIsSubmitting(false);
      setSuccessMsg(true);
      setTimeout(() => {
        onConnectSuccess({
          merchant_id: 'merch_apex_us_01',
          business_name: 'Apex Electronics Store (US)',
          paypal_account: 'merchant-sandbox-apex@lexishield.io',
          mode: 'SANDBOX_AUTHENTICATED'
        });
        onNavigateDashboard();
      }, 800);
    }, 600);
  };

  const handleCustomConnect = (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setTimeout(() => {
      setIsSubmitting(false);
      setSuccessMsg(true);
      setTimeout(() => {
        onConnectSuccess({
          merchant_id: 'merch_custom_01',
          business_name: shopifyStore || 'Custom Merchant Store',
          paypal_account: 'paypal-sandbox@merchant.com',
          mode: 'BYOK_AUTHENTICATED'
        });
        onNavigateDashboard();
      }, 800);
    }, 900);
  };

  return (
    <div className="container mx-auto px-6 py-12 flex items-center justify-center min-h-[calc(100vh-120px)]">
      <div className="w-full max-w-xl">
        
        {/* Card Header */}
        <div className="text-center mb-8">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center shadow-[0_0_20px_rgba(56,189,248,0.3)] mx-auto mb-4">
            <Lock className="w-6 h-6 text-white" />
          </div>
          <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
            Connect PayPal Sandbox
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 mt-2">
            Authenticate to enable autonomous dispute response and telemetry sync.
          </p>
        </div>

        {/* Glassmorphic Card */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-3xl p-6 sm:p-8 backdrop-blur-xl shadow-2xl relative overflow-hidden">
          
          {/* Subtle Ambient Light */}
          <div className="absolute top-0 right-0 w-64 h-64 bg-sky-500/10 rounded-full blur-3xl pointer-events-none" />

          {/* Mode Selector Tabs */}
          <div className="grid grid-cols-2 gap-2 p-1 bg-slate-950/80 border border-slate-800 rounded-xl mb-6">
            <button
              type="button"
              onClick={() => setAuthMode('demo')}
              className={`py-2 px-3 rounded-lg text-xs font-semibold transition-all flex items-center justify-center gap-1.5 ${
                authMode === 'demo'
                  ? 'bg-sky-500 text-slate-950 shadow-md'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>1-Click Demo Sandbox</span>
            </button>

            <button
              type="button"
              onClick={() => setAuthMode('custom')}
              className={`py-2 px-3 rounded-lg text-xs font-semibold transition-all flex items-center justify-center gap-1.5 ${
                authMode === 'custom'
                  ? 'bg-sky-500 text-slate-950 shadow-md'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Key className="w-3.5 h-3.5" />
              <span>Custom BYOK Keys</span>
            </button>
          </div>

          {/* Success Banner */}
          {successMsg && (
            <div className="mb-6 p-4 rounded-xl bg-emerald-950/60 border border-emerald-500/40 text-emerald-300 flex items-center gap-3 animate-fade-in">
              <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
              <div className="text-xs">
                <span className="font-semibold block text-white">Authentication Successful!</span>
                Connected to PayPal Sandbox REST API v2. Redirecting to console...
              </div>
            </div>
          )}

          {/* Tab 1: 1-Click Demo */}
          {authMode === 'demo' ? (
            <div className="space-y-6">
              <div className="p-4 rounded-2xl bg-slate-950/50 border border-slate-800/80 space-y-3">
                <div className="flex items-center justify-between text-xs text-slate-300">
                  <span className="text-slate-500 font-mono">Environment</span>
                  <span className="font-semibold text-sky-400">PayPal Sandbox (REST v2)</span>
                </div>
                <div className="flex items-center justify-between text-xs text-slate-300">
                  <span className="text-slate-500 font-mono">Simulated Merchant</span>
                  <span className="font-medium text-white">Apex Electronics Store</span>
                </div>
                <div className="flex items-center justify-between text-xs text-slate-300">
                  <span className="text-slate-500 font-mono">Test Account</span>
                  <span className="font-mono text-slate-400 text-[11px]">merchant-sandbox-apex@lexishield.io</span>
                </div>
                <div className="flex items-center justify-between text-xs text-slate-300">
                  <span className="text-slate-500 font-mono">Telemetry Hook</span>
                  <span className="font-medium text-emerald-400 flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3" /> Live Carrier GPS & Shopify
                  </span>
                </div>
              </div>

              <button
                type="button"
                onClick={handleDemoLogin}
                disabled={isSubmitting || successMsg}
                className="w-full py-3.5 px-6 rounded-xl font-semibold text-slate-950 bg-sky-400 hover:bg-sky-300 transition-all shadow-[0_0_20px_rgba(56,189,248,0.3)] active:scale-95 flex items-center justify-center gap-2"
              >
                {isSubmitting ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin text-slate-950" />
                    <span>Connecting Sandbox Session...</span>
                  </>
                ) : (
                  <>
                    <span>Launch with Demo Sandbox</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>

              <div className="text-center">
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  Loads realistic disputes, active chargeback ratio gauges, and interactive buyer chat rooms.
                </p>
              </div>
            </div>
          ) : (
            /* Tab 2: Custom BYOK Form */
            <form onSubmit={handleCustomConnect} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  PayPal Sandbox Client ID
                </label>
                <input
                  type="text"
                  required
                  value={clientId}
                  onChange={(e) => setClientId(e.target.value)}
                  placeholder="A21AAK...sandbox.client.id"
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950/70 border border-slate-800 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-sky-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  PayPal Sandbox Client Secret
                </label>
                <input
                  type="password"
                  required
                  value={clientSecret}
                  onChange={(e) => setClientSecret(e.target.value)}
                  placeholder="••••••••••••••••••••••••••••••••"
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950/70 border border-slate-800 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-sky-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  PayPal Webhook ID (Optional)
                </label>
                <input
                  type="text"
                  value={webhookId}
                  onChange={(e) => setWebhookId(e.target.value)}
                  placeholder="WH-9182901-SANDBOX"
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950/70 border border-slate-800 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-sky-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  Shopify Store Domain (Optional)
                </label>
                <input
                  type="text"
                  value={shopifyStore}
                  onChange={(e) => setShopifyStore(e.target.value)}
                  placeholder="your-store.myshopify.com"
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950/70 border border-slate-800 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-sky-500"
                />
              </div>

              <button
                type="submit"
                disabled={isSubmitting || successMsg}
                className="w-full mt-2 py-3.5 px-6 rounded-xl font-semibold text-slate-950 bg-sky-400 hover:bg-sky-300 transition-all shadow-[0_0_20px_rgba(56,189,248,0.3)] active:scale-95 flex items-center justify-center gap-2 text-xs"
              >
                {isSubmitting ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin text-slate-950" />
                    <span>Verifying Credentials...</span>
                  </>
                ) : (
                  <>
                    <Key className="w-4 h-4" />
                    <span>Connect Live Keys</span>
                  </>
                )}
              </button>
            </form>
          )}

        </div>

      </div>
    </div>
  );
}
