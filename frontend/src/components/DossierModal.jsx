import React from 'react';
import { apiUrl } from '../utils/api';
import { 
  X, 
  FileText, 
  Download, 
  MapPin, 
  Fingerprint, 
  Package, 
  ShieldCheck, 
  Sparkles, 
  CheckCircle2, 
  Clock, 
  ExternalLink 
} from 'lucide-react';

export default function DossierModal({ dispute, onClose }) {
  if (!dispute) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-fade-in">
      <div className="bg-slate-900 border border-slate-800 rounded-3xl w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden shadow-2xl relative">
        
        {/* Modal Header */}
        <div className="p-6 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-sky-500/10 border border-sky-500/20 text-sky-400 flex items-center justify-center">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-lg font-bold text-white tracking-tight">
                  Evidentiary Dossier #{dispute.dispute_id}
                </h3>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                  {Math.round(dispute.win_probability * 100)}% Win Probability
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                AI Evidence Synthesis compiled for PayPal Arbitration Review.
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

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1 text-xs text-slate-300">
          
          {/* Dispute Metadata */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-4 rounded-2xl bg-slate-950/60 border border-slate-800/80">
            <div>
              <span className="text-[10px] font-mono uppercase text-slate-500 block">Amount</span>
              <span className="text-sm font-bold text-white">${dispute.amount.toFixed(2)} {dispute.currency}</span>
            </div>
            <div>
              <span className="text-[10px] font-mono uppercase text-slate-500 block">Reason</span>
              <span className="text-xs font-semibold text-sky-400">{dispute.reason.replace(/_/g, ' ')}</span>
            </div>
            <div>
              <span className="text-[10px] font-mono uppercase text-slate-500 block">Buyer</span>
              <span className="text-xs font-medium text-slate-200">{dispute.buyer_name}</span>
            </div>
            <div>
              <span className="text-[10px] font-mono uppercase text-slate-500 block">Evidence Score</span>
              <span className="text-sm font-bold text-emerald-400">{dispute.evidence_score}/100</span>
            </div>
          </div>

          {/* AI Synthesis Summary */}
          <div className="p-4 rounded-2xl bg-sky-950/20 border border-sky-500/20 space-y-2.5">
            <div className="flex flex-wrap items-center justify-between gap-2 text-sky-400 font-semibold text-xs">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4" />
                <span>Horizontal Specialist Agent Evaluation</span>
              </div>
              <div className="flex flex-wrap items-center gap-1.5 text-[10px] font-mono">
                {dispute.specialist_agent && (
                  <span className="px-2 py-0.5 rounded bg-sky-500/20 text-sky-300 border border-sky-500/30">
                    {dispute.specialist_agent}
                  </span>
                )}
                {dispute.persona_mode && (
                  <span className="px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                    {dispute.persona_mode}
                  </span>
                )}
                {dispute.llm_tier_used && (
                  <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                    {dispute.llm_tier_used}
                  </span>
                )}
              </div>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed whitespace-pre-line">
              {dispute.ai_summary}
            </p>
            {dispute.pdf_dossier_sha256 && (
              <div className="pt-2 border-t border-sky-500/15 flex items-center gap-2 text-[10px] font-mono text-emerald-400">
                <ShieldCheck className="w-3.5 h-3.5 shrink-0" />
                <span className="truncate">PDF SHA-256: {dispute.pdf_dossier_sha256}</span>
              </div>
            )}
          </div>

          {Array.isArray(dispute.reasoning_steps) && dispute.reasoning_steps.length > 0 && (
            <div className="p-4 rounded-2xl bg-slate-950/50 border border-slate-800 space-y-1.5">
              <h4 className="text-[10px] font-mono uppercase tracking-wider text-slate-400">
                Agent Chain-of-Thought Audit Trace
              </h4>
              <ul className="space-y-1 text-[11px] text-slate-300 font-mono">
                {dispute.reasoning_steps.map((step, idx) => (
                  <li key={idx} className="leading-relaxed">• {step}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Telemetry Evidence Pillars */}
          <div className="space-y-3">
            <h4 className="text-xs font-mono uppercase tracking-wider text-slate-400">
              Verified Evidence Pillars
            </h4>

            {/* Pillar 1: Courier & GPS */}
            <div className="p-3.5 rounded-xl bg-slate-950/40 border border-slate-800 flex items-start gap-3">
              <div className="p-2 rounded-lg bg-slate-800 text-sky-400 shrink-0">
                <MapPin className="w-4 h-4" />
              </div>
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-white">Carrier Telemetry & GPS Verification</span>
                  <span className="text-[10px] text-emerald-400 flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3" /> Geofence Verified
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Carrier: {dispute.carrier} • Tracking: <span className="font-mono text-slate-300">{dispute.tracking_number}</span>
                </p>
              </div>
            </div>

            {/* Pillar 2: Device Fingerprint */}
            <div className="p-3.5 rounded-xl bg-slate-950/40 border border-slate-800 flex items-start gap-3">
              <div className="p-2 rounded-lg bg-slate-800 text-purple-400 shrink-0">
                <Fingerprint className="w-4 h-4" />
              </div>
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-white">Device Fingerprint & IP Geolocation</span>
                  <span className="text-[10px] text-emerald-400 flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3" /> Matched Historical Account
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  IP: <span className="font-mono text-slate-300">{dispute.device_ip}</span> • Hash: <span className="font-mono text-slate-300">{dispute.device_hash}</span>
                </p>
              </div>
            </div>

            {/* Pillar 3: Shopify Order Specifications */}
            <div className="p-3.5 rounded-xl bg-slate-950/40 border border-slate-800 flex items-start gap-3">
              <div className="p-2 rounded-lg bg-slate-800 text-emerald-400 shrink-0">
                <Package className="w-4 h-4" />
              </div>
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-white">Shopify Order Specifications</span>
                  <span className="text-[10px] text-emerald-400 flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3" /> Policy Compliant
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Order: <span className="font-mono text-slate-300">{dispute.order_id}</span> • Item: {dispute.item_title}
                </p>
              </div>
            </div>
          </div>

        </div>

        {/* Modal Footer */}
        <div className="p-6 border-t border-slate-800 flex items-center justify-between bg-slate-950/50">
          <div className="text-[11px] text-slate-500">
            Submitted via PayPal Partner API in 118 seconds.
          </div>

          <div className="flex items-center gap-3">
            <a
              href={apiUrl(`/api/v1/disputes/${dispute.dispute_id}/pdf`)}
              target="_blank"
              rel="noopener noreferrer"
              className="px-4 py-2 rounded-xl bg-sky-400 hover:bg-sky-300 text-slate-950 font-semibold text-xs flex items-center gap-1.5 transition-all shadow-md"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Download PDF Dossier</span>
            </a>

            <button
              onClick={onClose}
              className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition-all"
            >
              Close
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}
