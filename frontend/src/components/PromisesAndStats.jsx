import React from 'react';
import { ShieldCheck, CreditCard, CheckCircle2 } from 'lucide-react';
import Reveal from './Reveal';
import SpotlightCard from './SpotlightCard';

export default function PromisesAndStats({ onExploreDashboard }) {
  return (
    <section id="coverage" className="py-20 bg-slate-50/70 border-y border-slate-200/80">
      <div className="container mx-auto px-6 max-w-5xl">
        
        {/* Section Header */}
        <Reveal className="text-center max-w-2xl mx-auto mb-12">
          <span className="text-xs font-mono font-bold uppercase tracking-widest text-indigo-600 bg-indigo-50 px-3 py-1 rounded-full border border-indigo-200">
            Enterprise Coverage
          </span>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-900 mt-4 tracking-tight font-display">
            Dual-Layer Dispute Protection
          </h2>
          <p className="text-slate-600 mt-2 text-sm sm:text-base">
            Automated defense across both internal PayPal claims and external card network chargebacks.
          </p>
        </Reveal>

        {/* 2 Main Dual-Layer Promises Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          
          {/* Card 1: Internal PayPal Disputes */}
          <Reveal delay={0} className="h-full">
            <SpotlightCard className="h-full bg-white border border-slate-200 rounded-3xl p-8 shadow-xs hover:shadow-md space-y-5 text-left">
              <div className="w-12 h-12 rounded-2xl bg-blue-50 border border-blue-200 text-blue-600 flex items-center justify-center shadow-xs">
                <ShieldCheck className="w-6 h-6" />
              </div>

              <div>
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-blue-100 text-blue-700">
                    INTERNAL DEFENSE
                  </span>
                  <span className="text-xs font-mono text-slate-400">PayPal Platform</span>
                </div>
                <h3 className="text-xl font-bold text-slate-900 mt-2 font-display">
                  PayPal Inquiry & Claim Resolution
                </h3>
              </div>

              <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
                Directly connects to PayPal dispute endpoints to automatically submit court-admissible evidentiary dossiers with carrier geofence scans in under 120 seconds.
              </p>

              <div className="space-y-2.5 pt-2 border-t border-slate-100 text-xs">
                <div className="flex items-center gap-2 text-slate-700 font-medium">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span>Enforces strict PayPal Seller Protection criteria ($750+ signature rules)</span>
                </div>
                <div className="flex items-center gap-2 text-slate-700 font-medium">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span>Autonomous conversational de-escalation bot during the Inquiry stage</span>
                </div>
                <div className="flex items-center gap-2 text-slate-700 font-medium">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span>Prevents capital reserve freezes and merchant account restrictions</span>
                </div>
              </div>
            </SpotlightCard>
          </Reveal>

          {/* Card 2: External Card Issuer Chargebacks */}
          <Reveal delay={120} className="h-full">
            <SpotlightCard className="h-full bg-white border border-slate-200 rounded-3xl p-8 shadow-xs hover:shadow-md space-y-5 text-left">
              <div className="w-12 h-12 rounded-2xl bg-indigo-50 border border-indigo-200 text-indigo-600 flex items-center justify-center shadow-xs">
                <CreditCard className="w-6 h-6" />
              </div>

              <div>
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-indigo-100 text-indigo-700">
                    EXTERNAL DEFENSE
                  </span>
                  <span className="text-xs font-mono text-slate-400">Card Issuing Banks</span>
                </div>
                <h3 className="text-xl font-bold text-slate-900 mt-2 font-display">
                  Pre-Chargeback Network Deflection
                </h3>
              </div>

              <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
                Listens to Ethoca Consumer Clarity and Verifi RDR alerts 24–72 hours prior to formal chargeback creation, issuing automated zero-fee refunds to prevent penalties.
              </p>

              <div className="space-y-2.5 pt-2 border-t border-slate-100 text-xs">
                <div className="flex items-center gap-2 text-slate-700 font-medium">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span>Deflects bank inquiries before they count against your dispute ratio</span>
                </div>
                <div className="flex items-center gap-2 text-slate-700 font-medium">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span>Completely eliminates the $15 non-refundable dispute surcharge</span>
                </div>
                <div className="flex items-center gap-2 text-slate-700 font-medium">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span>Visa, Mastercard & American Express card network integration</span>
                </div>
              </div>
            </SpotlightCard>
          </Reveal>

        </div>

      </div>
    </section>
  );
}
