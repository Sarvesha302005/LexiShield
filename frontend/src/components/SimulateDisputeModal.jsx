import React, { useState } from 'react';
import { X, Plus, AlertCircle, Bot, Zap, CheckCircle2 } from 'lucide-react';
import { mapApiDispute } from '../utils/disputes';

export default function SimulateDisputeModal({ onClose, onSimulate }) {
  const [scenario, setScenario] = useState('unauthorized');
  const [buyerName, setBuyerName] = useState('Marcus Vance');
  const [buyerEmail, setBuyerEmail] = useState('marcus.vance@gmail.com');
  const [amount, setAmount] = useState('249.99');
  const [itemTitle, setItemTitle] = useState('Bose QuietComfort 45 Headphones');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleScenarioChange = (e) => {
    const s = e.target.value;
    setScenario(s);
    if (s === 'unauthorized') {
      setBuyerName('Marcus Vance');
      setBuyerEmail('marcus.vance@gmail.com');
      setAmount('249.99');
      setItemTitle('Bose QuietComfort 45 Headphones');
    } else if (s === 'not_received') {
      setBuyerName('Samantha Cole');
      setBuyerEmail('samantha.cole@outlook.com');
      setAmount('135.00');
      setItemTitle('Wireless Barcode Scanner (USB-C)');
    } else if (s === 'billing') {
      setBuyerName('Sophia Chen');
      setBuyerEmail('sophia.chen@enterprise.io');
      setAmount('79.00');
      setItemTitle('LexiShield Security Suite (1-Seat Pro Annual)');
    } else {
      setBuyerName('Jordan Lee');
      setBuyerEmail('jordan.lee@techcorp.io');
      setAmount('499.00');
      setItemTitle('Keychron Q1 Pro Custom Keyboard');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);

    const reasonCode = scenario === 'unauthorized'
      ? 'UNAUTHORISED'
      : scenario === 'not_received'
      ? 'MERCHANDISE_OR_SERVICE_NOT_RECEIVED'
      : scenario === 'billing'
      ? 'CANCELED_RECURRING_BILLING'
      : 'MERCHANDISE_OR_SERVICE_NOT_AS_DESCRIBED';

    try {
      const resp = await fetch('/api/v1/disputes/simulate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          customer_name: buyerName,
          customer_email: buyerEmail,
          reason: reasonCode,
          stage: 'CLAIM',
          amount: parseFloat(amount) || 199.99,
        }),
      });
      if (resp.ok) {
        const record = await resp.json();
        onSimulate(mapApiDispute(record, { buyer_name: buyerName, buyer_email: buyerEmail, item_title: itemTitle }));
        setIsSubmitting(false);
        onClose();
        return;
      }
    } catch {
      // Fallback cleanly to local preview simulation if backend is offline
    }

    setTimeout(() => {
      const newDisputeId = `PP-D-${Math.floor(849300 + Math.random() * 900)}`;
      const specialistMap = {
        unauthorized: 'FraudAgent',
        not_received: 'INRAgent',
        billing: 'BillingAgent',
        not_as_described: 'SNADAgent',
      };
      const simulatedRecord = {
        dispute_id: newDisputeId,
        buyer_email: buyerEmail,
        buyer_name: buyerName,
        amount: parseFloat(amount) || 199.99,
        currency: 'USD',
        reason: reasonCode,
        stage: 'CLAIM',
        pipeline_status: scenario === 'not_received' ? 'AUTO_NEGOTIATING' : 'DEFENDED',
        win_probability: scenario === 'unauthorized' ? 0.96 : scenario === 'not_received' ? 0.91 : scenario === 'billing' ? 0.92 : 0.78,
        created_at: new Date().toISOString(),
        evidence_score: 95,
        fee_saved: 15.0,
        tracking_number: '1Z' + Math.random().toString().slice(2, 18),
        carrier: 'UPS Next Day Air',
        device_ip: '64.233.160.1',
        device_hash: 'd41d8cd98f00b204',
        buyer_sentiment: 'New Claim Ingested',
        order_id: `SHP-${Math.floor(99300 + Math.random() * 500)}`,
        item_title: itemTitle,
        ai_summary: `Horizontal agent (${specialistMap[scenario] || 'DisputeSupervisor'}) triggered for ${reasonCode}. Telemetry verified and PDF dossier compiled.`,
        action_taken: 'DEFEND_AUTONOMOUS',
        specialist_agent: specialistMap[scenario] || 'DisputeSupervisor',
        persona_mode: 'ADVERSARIAL_LEGAL_DEFENSE',
        llm_tier_used: 'TIER_3_DETERMINISTIC_HEURISTIC',
        reasoning_steps: [],
      };

      onSimulate(simulatedRecord);
      setIsSubmitting(false);
      onClose();
    }, 450);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-fade-in">
      <div className="bg-slate-900 border border-slate-800 rounded-3xl w-full max-w-lg overflow-hidden shadow-2xl relative">
        
        {/* Header */}
        <div className="p-6 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-center justify-center">
              <Zap className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white tracking-tight">
                Simulate PayPal Webhook
              </h3>
              <p className="text-xs text-slate-400">
                Inject test dispute event into the live defense pipeline.
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4 text-xs">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Dispute Simulation Scenario
            </label>
            <select
              value={scenario}
              onChange={handleScenarioChange}
              className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950/80 border border-slate-800 text-xs text-white focus:outline-none focus:border-sky-500"
            >
              <option value="unauthorized">Friendly Fraud (Unauthorized purchase by household member)</option>
              <option value="not_received">Item Not Received (Delivered to secure locker)</option>
              <option value="not_as_described">Item Not As Described (High-value return claim)</option>
              <option value="billing">Canceled Recurring / SaaS Billing (Clickwrap + active sessions)</option>
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Buyer Name
              </label>
              <input
                type="text"
                required
                value={buyerName}
                onChange={(e) => setBuyerName(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950/80 border border-slate-800 text-xs text-white focus:outline-none focus:border-sky-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Dispute Amount ($)
              </label>
              <input
                type="number"
                step="0.01"
                required
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950/80 border border-slate-800 text-xs text-white focus:outline-none focus:border-sky-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Buyer Email
            </label>
            <input
              type="email"
              required
              value={buyerEmail}
              onChange={(e) => setBuyerEmail(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950/80 border border-slate-800 text-xs text-white focus:outline-none focus:border-sky-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Product / Item Title
            </label>
            <input
              type="text"
              required
              value={itemTitle}
              onChange={(e) => setItemTitle(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950/80 border border-slate-800 text-xs text-white focus:outline-none focus:border-sky-500"
            />
          </div>

          <div className="pt-2">
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-3 px-4 rounded-xl font-semibold text-slate-950 bg-sky-400 hover:bg-sky-300 transition-all shadow-[0_0_20px_rgba(56,189,248,0.3)] active:scale-95 flex items-center justify-center gap-2"
            >
              {isSubmitting ? (
                <span>Synthesizing Evidence & Defending...</span>
              ) : (
                <>
                  <Zap className="w-4 h-4" />
                  <span>Trigger Inbound Webhook</span>
                </>
              )}
            </button>
          </div>
        </form>

      </div>
    </div>
  );
}
