import React, { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import Reveal from './Reveal';

export default function FaqSection() {
  const [openIndex, setOpenIndex] = useState(0);

  const faqs = [
    {
      question: "How does LexiShield detect and resolve disputes automatically?",
      answer: "LexiShield connects via real-time webhooks to ingest dispute events within 800ms. It immediately correlates courier GPS telemetry (UPS, FedEx, USPS), store order fulfillment logs, and device fingerprints to either open an autonomous mediation dialogue with the buyer or compile an airtight evidentiary rebuttal PDF submitted directly to PayPal."
    },
    {
      question: "What is the difference between internal PayPal disputes and external card chargebacks?",
      answer: "Internal disputes are filed directly inside PayPal (Inquiry and Claim stages) by PayPal account holders. External chargebacks originate from card issuing banks (Chase, Citi, Capital One via Visa/Mastercard networks). LexiShield defends internal claims through PayPal APIs and deflects external chargebacks 24–72 hours in advance through Ethoca and Verifi network alerts before they turn into formal chargebacks."
    },
    {
      question: "How does the engine eliminate the $15 non-refundable dispute fee?",
      answer: "PayPal only levies the $15 dispute surcharge once an inquiry escalates to a formal Claim or when an external chargeback is registered. By de-escalating confused buyers during the inquiry phase or executing automated pre-dispute refunds within the 48-hour Ethoca/Verifi window, LexiShield completely avoids the $15 penalty."
    },
    {
      question: "What evidence is compiled in the evidentiary rebuttal dossier?",
      answer: "The engine compiles courier GPS geofence scans (verifying package delivery within 15ft of front door), carrier recipient signatures, courier porch photos, browser canvas/WebGL device hashes, residential ISP geolocation matching, and accepted store checkout RMA terms into a court-ready ReportLab PDF."
    },
    {
      question: "Can I manually review high-value claims before evidence is submitted?",
      answer: "Yes. LexiShield includes a Human-in-the-Loop (HITL) operational queue. Any dispute exceeding your custom dollar threshold (e.g., $300) or with borderline win probabilities is flagged for rapid 1-click operational review, allowing you to approve AI offers or override to full defense."
    },
    {
      question: "How fast is onboarding with PayPal Sandbox and live accounts?",
      answer: "Connecting takes under 60 seconds. You can explore immediately using our 1-click Demo Sandbox session, or connect your own PayPal REST API client credentials and Shopify webhook listener."
    }
  ];

  return (
    <section id="faq" className="py-20 bg-white">
      <div className="container mx-auto px-6 max-w-4xl">
        
        {/* Section Header */}
        <Reveal className="text-center max-w-2xl mx-auto mb-12">
          <span className="text-xs font-mono font-bold uppercase tracking-widest text-sky-600 bg-sky-50 px-3 py-1 rounded-full border border-sky-200">
            Frequently Asked Questions
          </span>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-900 mt-4 tracking-tight font-display">
            Everything You Need to Know
          </h2>
          <p className="text-slate-600 mt-2 text-sm sm:text-base">
            Transparent answers regarding autonomous dispute resolution and merchant capital protection.
          </p>
        </Reveal>

        {/* Accordion List */}
        <Reveal className="space-y-4" delay={100}>
          {faqs.map((faq, idx) => {
            const isOpen = openIndex === idx;
            return (
              <div
                key={idx}
                className={`border rounded-2xl transition-all overflow-hidden ${
                  isOpen 
                    ? 'border-sky-300 bg-slate-50/60 shadow-xs' 
                    : 'border-slate-200 bg-white hover:border-slate-300'
                }`}
              >
                <button
                  onClick={() => setOpenIndex(isOpen ? -1 : idx)}
                  aria-expanded={isOpen}
                  className="w-full py-5 px-6 text-left flex items-center justify-between gap-4 select-none"
                >
                  <span className="font-bold text-slate-900 text-sm sm:text-base font-display">
                    {faq.question}
                  </span>
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 transition-colors ${
                    isOpen ? 'bg-sky-600 text-white' : 'bg-slate-100 text-slate-500'
                  }`}>
                    {isOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                  </div>
                </button>

                {isOpen && (
                  <div className="px-6 pb-6 text-xs sm:text-sm text-slate-600 leading-relaxed border-t border-slate-100 pt-3 animate-fade-in text-left">
                    {faq.answer}
                  </div>
                )}
              </div>
            );
          })}
        </Reveal>

      </div>
    </section>
  );
}
