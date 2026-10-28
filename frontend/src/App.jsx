import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import HomePage from './components/HomePage';
import AuthPage from './components/AuthPage';
import DashboardPage from './components/DashboardPage';
import { 
  INITIAL_DISPUTES, 
  INITIAL_CHAT_CONVERSATIONS, 
  INITIAL_MERCHANT_PROFILE 
} from './data/mockData';

export default function App() {
  // Determine initial view from window.location.pathname
  const getInitialView = () => {
    const path = window.location.pathname;
    if (path === '/auth' || path === '/login') return 'auth';
    if (path === '/dashboard') return 'dashboard';
    return 'home';
  };

  const [currentView, setCurrentView] = useState(getInitialView);
  const [disputes, setDisputes] = useState(INITIAL_DISPUTES);
  const [merchantProfile, setMerchantProfile] = useState(INITIAL_MERCHANT_PROFILE);
  const [chatConversations, setChatConversations] = useState(INITIAL_CHAT_CONVERSATIONS);

  // Sync browser back/forward buttons
  useEffect(() => {
    const handlePopState = () => {
      setCurrentView(getInitialView());
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  // Try to load any live disputes from FastAPI backend if available
  useEffect(() => {
    async function fetchBackendData() {
      try {
        const res = await fetch('/api/v1/disputes');
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data) && data.length > 0) {
            // Map backend schema to UI format if needed
            const mapped = data.map(item => ({
              dispute_id: item.dispute_id,
              buyer_email: item.evidence_dossier?.buyer_email || 'customer@lexishield.io',
              buyer_name: item.evidence_dossier?.buyer_name || 'Verified Buyer',
              amount: item.amount || 199.99,
              currency: item.currency || 'USD',
              reason: item.dispute_reason || 'UNAUTHORIZED_TRANSACTION',
              stage: item.dispute_stage || 'CLAIM',
              pipeline_status: item.pipeline_status || 'DEFENDED',
              win_probability: item.win_probability || 0.92,
              created_at: item.created_at || new Date().toISOString(),
              evidence_score: item.evidence_score || 94,
              fee_saved: 15.0,
              tracking_number: item.evidence_dossier?.tracking_number || '1Z9999999999999999',
              carrier: item.evidence_dossier?.carrier || 'UPS',
              device_ip: item.evidence_dossier?.device_ip || '127.0.0.1',
              device_hash: item.evidence_dossier?.device_hash || 'hash_verified',
              buyer_sentiment: 'Active Case',
              order_id: item.evidence_dossier?.order_id || 'SHP-LIVE',
              item_title: item.evidence_dossier?.item_title || 'Commercial Electronics',
              ai_summary: item.arbitration_decision?.rationale || 'Synthesized evidence rebuttal.',
              action_taken: item.action_taken || 'DEFEND'
            }));
            setDisputes(prev => {
              // Combine unique by dispute_id
              const existingIds = new Set(prev.map(d => d.dispute_id));
              const newItems = mapped.filter(d => !existingIds.has(d.dispute_id));
              return [...newItems, ...prev];
            });
          }
        }
      } catch (err) {
        // Backend offline or fallback to mock
        console.log("Using local mock dataset for disputes.");
      }
    }
    fetchBackendData();
  }, []);

  const navigateTo = (view, sectionId) => {
    setCurrentView(view);
    const path = view === 'home' ? '/' : `/${view}`;
    window.history.pushState(null, '', sectionId ? `${path}#${sectionId}` : path);
    if (!sectionId) {
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }
    // Wait a frame so the home view is rendered before scrolling to the section
    requestAnimationFrame(() => {
      document.getElementById(sectionId)?.scrollIntoView({ behavior: 'smooth' });
    });
  };

  const handleConnectSuccess = (authData) => {
    setMerchantProfile(prev => ({
      ...prev,
      business_name: authData.business_name || prev.business_name,
      paypal_account: authData.paypal_account || prev.paypal_account,
    }));
  };

  const handleAddDispute = (newDispute) => {
    setDisputes(prev => [newDispute, ...prev]);
    // Also create initial chat thread for this dispute
    setChatConversations(prev => ({
      ...prev,
      [newDispute.dispute_id]: [
        {
          sender: 'buyer',
          name: newDispute.buyer_name,
          time: 'Just now',
          text: `I noticed a charge of $${newDispute.amount.toFixed(2)} for "${newDispute.item_title}". I did not authorize this purchase!`
        },
        {
          sender: 'bot',
          name: 'LexiShield AI Defense Bot',
          time: 'Seconds later',
          text: `Hello ${newDispute.buyer_name.split(' ')[0]}, LexiShield has initiated automated arbitration. Tracking ${newDispute.tracking_number} via ${newDispute.carrier} shows signed delivery to your address. We are reviewing this dispute now.`
        }
      ]
    }));

    // Update merchant stats
    setMerchantProfile(prev => ({
      ...prev,
      dispute_fees_saved: prev.dispute_fees_saved + 15.0,
      total_defended_count: prev.total_defended_count + 1,
      protected_volume: prev.protected_volume + newDispute.amount
    }));
  };

  const handleSendMessage = (disputeId, messageObj) => {
    setChatConversations(prev => ({
      ...prev,
      [disputeId]: [...(prev[disputeId] || []), messageObj]
    }));
  };

  const handleSimulateBuyerReply = (disputeId) => {
    const disp = disputes.find(d => d.dispute_id === disputeId);
    const buyerName = disp ? disp.buyer_name : "Buyer";
    
    setTimeout(() => {
      const sampleReplies = [
        "I just asked my spouse, and turns out they ordered this yesterday without telling me! How do I cancel the dispute on PayPal?",
        "Okay, I found the package behind the planter on the porch. The courier hid it well. Thank you for providing the carrier delivery photo!",
        "I still want to return this. Can you send the pre-paid RMA shipping label so I can drop it off at UPS tomorrow?"
      ];
      const randomReply = sampleReplies[Math.floor(Math.random() * sampleReplies.length)];

      handleSendMessage(disputeId, {
        sender: 'buyer',
        name: buyerName,
        time: 'Just now',
        text: randomReply
      });
    }, 500);
  };

  return (
    <div className="min-h-screen bg-white text-slate-900 flex flex-col font-sans selection:bg-sky-100 selection:text-sky-900">
      
      {/* Top Navigation Bar */}
      <Navbar onNavigate={navigateTo} currentView={currentView} />

      {/* Main Content Area */}
      <main className="flex-1">
        {currentView === 'home' && (
          <HomePage
            onNavigateAuth={() => navigateTo('auth')}
            onNavigateDashboard={() => navigateTo('dashboard')}
          />
        )}

        {currentView === 'auth' && (
          <AuthPage
            onConnectSuccess={handleConnectSuccess}
            onNavigateDashboard={() => navigateTo('dashboard')}
          />
        )}

        {currentView === 'dashboard' && (
          <DashboardPage
            disputes={disputes}
            onAddDispute={handleAddDispute}
            merchantProfile={merchantProfile}
            chatConversations={chatConversations}
            onSendMessage={handleSendMessage}
            onSimulateBuyerReply={handleSimulateBuyerReply}
          />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-slate-50 py-8 text-center text-xs text-slate-500">
        <div className="container mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="font-bold text-slate-800">LexiShield</span>
            <span>• Autonomous Dispute Resolution Engine</span>
          </div>
          <div className="text-[11px] text-slate-500">
            Enterprise PayPal Dispute Defense & Pre-Chargeback Deflection
          </div>
        </div>
      </footer>

    </div>
  );
}
