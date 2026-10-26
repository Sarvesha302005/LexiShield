import React, { useState, useMemo } from 'react';
import { 
  ShieldCheck, 
  AlertTriangle, 
  TrendingUp, 
  DollarSign, 
  Search, 
  Filter, 
  MessageSquare, 
  FileText, 
  ExternalLink, 
  Plus, 
  Send, 
  Sparkles, 
  CheckCircle2, 
  Clock, 
  X, 
  ChevronDown, 
  ChevronUp, 
  ArrowUpDown, 
  Info, 
  Bot,
  User,
  ShoppingBag,
  MapPin,
  Fingerprint
} from 'lucide-react';
import DossierModal from './DossierModal';
import SimulateDisputeModal from './SimulateDisputeModal';

export default function DashboardPage({ 
  disputes, 
  onAddDispute, 
  merchantProfile, 
  chatConversations, 
  onSendMessage, 
  onSimulateBuyerReply 
}) {
  // Navigation inside dashboard: 'radar' (Dispute Table) or 'chat' (Buyer Chat Center)
  const [activeTab, setActiveTab] = useState('radar');
  
  // Table search & filters
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [sortField, setSortField] = useState('created_at');
  const [sortOrder, setSortOrder] = useState('desc'); // 'asc' | 'desc'

  // Selected dispute for modals & chat
  const [selectedDisputeForDossier, setSelectedDisputeForDossier] = useState(null);
  const [activeChatDisputeId, setActiveChatDisputeId] = useState(disputes[0]?.dispute_id || 'PP-D-849201');
  const [chatInput, setChatInput] = useState('');
  const [isSimulateModalOpen, setIsSimulateModalOpen] = useState(false);
  const [isGeneratingAiReply, setIsGeneratingAiReply] = useState(false);

  // Filter & Sort Disputes for Custom Table (NO AG GRID)
  const filteredDisputes = useMemo(() => {
    return disputes
      .filter(item => {
        // Status filter
        if (statusFilter === 'ACTION_REQUIRED') {
          if (!['FLAGGED_HITL', 'AUTO_NEGOTIATING'].includes(item.pipeline_status)) return false;
        } else if (statusFilter === 'DEFENDED') {
          if (!['DEFENDED', 'RESOLVED_WON'].includes(item.pipeline_status)) return false;
        } else if (statusFilter === 'RESOLVED') {
          if (!['RESOLVED_WON', 'CONCEDED'].includes(item.pipeline_status)) return false;
        }

        // Search filter
        if (searchQuery.trim()) {
          const q = searchQuery.toLowerCase();
          const matchId = item.dispute_id.toLowerCase().includes(q);
          const matchBuyer = item.buyer_name.toLowerCase().includes(q) || item.buyer_email.toLowerCase().includes(q);
          const matchItem = item.item_title.toLowerCase().includes(q);
          const matchReason = item.reason.toLowerCase().includes(q);
          return matchId || matchBuyer || matchItem || matchReason;
        }
        return true;
      })
      .sort((a, b) => {
        let valA = a[sortField];
        let valB = b[sortField];
        if (typeof valA === 'string') {
          valA = valA.toLowerCase();
          valB = valB.toLowerCase();
        }
        if (valA < valB) return sortOrder === 'asc' ? -1 : 1;
        if (valA > valB) return sortOrder === 'asc' ? 1 : -1;
        return 0;
      });
  }, [disputes, searchQuery, statusFilter, sortField, sortOrder]);

  const handleSort = (field) => {
    if (sortField === field) {
      setSortOrder(prev => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortOrder('desc');
    }
  };

  const activeChatDispute = disputes.find(d => d.dispute_id === activeChatDisputeId) || disputes[0];
  const currentChatMessages = chatConversations[activeChatDisputeId] || [];

  const handleSendChatMessage = (e) => {
    e?.preventDefault();
    if (!chatInput.trim()) return;
    onSendMessage(activeChatDisputeId, {
      sender: 'bot',
      name: 'Merchant Operations',
      time: 'Just now',
      text: chatInput.trim()
    });
    setChatInput('');
  };

  const handleAiAutoReply = () => {
    if (!activeChatDispute) return;
    setIsGeneratingAiReply(true);
    setTimeout(() => {
      let suggestedText = "";
      if (activeChatDispute.reason.includes("UNAUTHORIZED")) {
        suggestedText = `Hello ${activeChatDispute.buyer_name.split(' ')[0]}, our automated security audit confirms the order was placed with device ID ${activeChatDispute.device_hash.substring(0, 8)} from your residential IP. The UPS tracking (${activeChatDispute.tracking_number}) shows delivery to your verified front door. Please confirm if a family member authorized this order.`;
      } else if (activeChatDispute.reason.includes("NOT_RECEIVED")) {
        suggestedText = `Hi ${activeChatDispute.buyer_name.split(' ')[0]}, we verified the courier GPS scan for ${activeChatDispute.tracking_number}. Delivery was marked complete yesterday. We have requested a carrier driver inspection report and sent an alert to your local depot.`;
      } else {
        suggestedText = `Hello ${activeChatDispute.buyer_name.split(' ')[0]}, we want to resolve your concern regarding "${activeChatDispute.item_title}". We can provide a return shipping label with zero restocking fees or issue an immediate partial credit. Let us know what you prefer.`;
      }
      setChatInput(suggestedText);
      setIsGeneratingAiReply(false);
    }, 600);
  };

  return (
    <div className="container mx-auto px-4 sm:px-6 py-8">
      
      {/* Merchant Profile Banner */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-3xl p-6 mb-8 backdrop-blur-xl shadow-xl flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center shadow-lg shrink-0">
            <ShoppingBag className="w-6 h-6 text-white" />
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-xl font-bold text-white tracking-tight">
                {merchantProfile.business_name}
              </h2>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                PayPal Sandbox Active
              </span>
            </div>
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-400 mt-1">
              <span>Store: <strong className="text-slate-300">{merchantProfile.shopify_domain}</strong></span>
              <span>Account: <strong className="text-slate-300 font-mono text-[11px]">{merchantProfile.paypal_account}</strong></span>
              <span className="text-sky-400 font-medium">Autonomous Defense: ON</span>
            </div>
          </div>
        </div>

        <button
          onClick={() => setIsSimulateModalOpen(true)}
          className="px-4 py-2.5 rounded-xl font-semibold text-xs text-slate-950 bg-sky-400 hover:bg-sky-300 transition-all shadow-[0_0_15px_rgba(56,189,248,0.25)] flex items-center gap-2 shrink-0 active:scale-95"
        >
          <Plus className="w-4 h-4" />
          <span>Simulate Inbound Dispute</span>
        </button>
      </div>

      {/* Metrics Row: Chargeback Ratio & Fee Avoidance */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-8">
        
        {/* Metric 1: Chargeback Ratio */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 hover:border-slate-700 transition-all">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
            <span>Chargeback Ratio</span>
            <span className="font-mono text-[11px] text-emerald-400 font-semibold">Target &lt; 1.00%</span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-white tracking-tight">
              {merchantProfile.chargeback_ratio}%
            </span>
            <span className="text-xs text-emerald-400 font-medium flex items-center">
              ✓ Low Risk
            </span>
          </div>
          {/* Progress bar */}
          <div className="w-full h-1.5 bg-slate-800 rounded-full mt-3 overflow-hidden">
            <div 
              className="h-full bg-emerald-400 rounded-full" 
              style={{ width: `${(merchantProfile.chargeback_ratio / 1.0) * 100}%` }}
            />
          </div>
          <div className="text-[10px] text-slate-500 mt-1.5 flex justify-between">
            <span>Current: 0.42%</span>
            <span>PayPal Cutoff: 1.00%</span>
          </div>
        </div>

        {/* Metric 2: Dispute Fees Saved */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 hover:border-slate-700 transition-all">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
            <span>Dispute Fees Saved</span>
            <DollarSign className="w-4 h-4 text-sky-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-white tracking-tight">
              ${merchantProfile.dispute_fees_saved.toLocaleString('en-US', { minimumFractionDigits: 2 })}
            </span>
          </div>
          <p className="text-[11px] text-slate-400 mt-2">
            Avoided $15.00 PayPal dispute surcharge on 142 deflected claims.
          </p>
        </div>

        {/* Metric 3: Win Rate */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 hover:border-slate-700 transition-all">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
            <span>AI Defense Win Rate</span>
            <TrendingUp className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-white tracking-tight">
              {merchantProfile.win_rate}%
            </span>
            <span className="text-xs text-slate-400">of claims</span>
          </div>
          <p className="text-[11px] text-slate-400 mt-2">
            Based on 142 total defended PayPal dispute dossiers.
          </p>
        </div>

        {/* Metric 4: Protected Volume */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 hover:border-slate-700 transition-all">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
            <span>Protected GMV</span>
            <ShieldCheck className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-white tracking-tight">
              ${merchantProfile.protected_volume.toLocaleString('en-US', { minimumFractionDigits: 2 })}
            </span>
          </div>
          <p className="text-[11px] text-slate-400 mt-2">
            Capital safely released from PayPal 180-day reserves.
          </p>
        </div>

      </div>

      {/* Tabs Navigation: Dispute Radar vs Buyer Chat Center */}
      <div className="flex items-center gap-3 border-b border-slate-800 pb-4 mb-6">
        <button
          onClick={() => setActiveTab('radar')}
          className={`px-4 py-2 rounded-xl text-xs font-semibold transition-all flex items-center gap-2 ${
            activeTab === 'radar'
              ? 'bg-sky-400 text-slate-950 shadow-md'
              : 'text-slate-400 hover:text-white bg-slate-900/60'
          }`}
        >
          <FileText className="w-3.5 h-3.5" />
          <span>Dispute Radar ({disputes.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('chat')}
          className={`px-4 py-2 rounded-xl text-xs font-semibold transition-all flex items-center gap-2 ${
            activeTab === 'chat'
              ? 'bg-sky-400 text-slate-950 shadow-md'
              : 'text-slate-400 hover:text-white bg-slate-900/60'
          }`}
        >
          <MessageSquare className="w-3.5 h-3.5" />
          <span>Dispute Chat Center</span>
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
        </button>
      </div>

      {/* VIEW 1: CUSTOM DISPUTE RADAR TABLE (NO AG GRID) */}
      {activeTab === 'radar' && (
        <div className="space-y-4">
          
          {/* Table Controls Bar */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
            
            {/* Search Input */}
            <div className="relative flex-1 max-w-md">
              <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-3" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search by Dispute ID, buyer name, item, or reason..."
                className="w-full pl-9 pr-4 py-2 rounded-xl bg-slate-900/80 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-sky-500 transition-colors"
              />
              {searchQuery && (
                <button 
                  onClick={() => setSearchQuery('')}
                  className="absolute right-3 top-2.5 text-slate-500 hover:text-slate-300"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>

            {/* Filter Pills */}
            <div className="flex flex-wrap items-center gap-2">
              <button
                onClick={() => setStatusFilter('ALL')}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  statusFilter === 'ALL'
                    ? 'bg-slate-700 text-white'
                    : 'text-slate-400 hover:text-slate-200 bg-slate-900/60'
                }`}
              >
                All ({disputes.length})
              </button>
              <button
                onClick={() => setStatusFilter('ACTION_REQUIRED')}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  statusFilter === 'ACTION_REQUIRED'
                    ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                    : 'text-slate-400 hover:text-slate-200 bg-slate-900/60'
                }`}
              >
                Action Required
              </button>
              <button
                onClick={() => setStatusFilter('DEFENDED')}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  statusFilter === 'DEFENDED'
                    ? 'bg-sky-500/20 text-sky-300 border border-sky-500/40'
                    : 'text-slate-400 hover:text-slate-200 bg-slate-900/60'
                }`}
              >
                Defended
              </button>
              <button
                onClick={() => setStatusFilter('RESOLVED')}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  statusFilter === 'RESOLVED'
                    ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                    : 'text-slate-400 hover:text-slate-200 bg-slate-900/60'
                }`}
              >
                Resolved
              </button>
            </div>

          </div>

          {/* Native React Dispute Radar Table (Replacing AG Grid) */}
          <div className="bg-slate-900/70 border border-slate-800 rounded-2xl overflow-hidden backdrop-blur-xl shadow-xl">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-slate-800 bg-slate-950/60 text-slate-400 font-mono text-[11px] uppercase tracking-wider">
                    <th 
                      onClick={() => handleSort('dispute_id')}
                      className="py-3 px-4 cursor-pointer hover:text-white select-none"
                    >
                      <div className="flex items-center gap-1.5">
                        <span>Dispute ID</span>
                        <ArrowUpDown className="w-3 h-3 text-slate-500" />
                      </div>
                    </th>
                    <th 
                      onClick={() => handleSort('buyer_name')}
                      className="py-3 px-4 cursor-pointer hover:text-white select-none"
                    >
                      <div className="flex items-center gap-1.5">
                        <span>Buyer & Contact</span>
                        <ArrowUpDown className="w-3 h-3 text-slate-500" />
                      </div>
                    </th>
                    <th 
                      onClick={() => handleSort('amount')}
                      className="py-3 px-4 cursor-pointer hover:text-white select-none"
                    >
                      <div className="flex items-center gap-1.5">
                        <span>Amount & Item</span>
                        <ArrowUpDown className="w-3 h-3 text-slate-500" />
                      </div>
                    </th>
                    <th className="py-3 px-4">Dispute Reason</th>
                    <th className="py-3 px-4">Pipeline Status</th>
                    <th 
                      onClick={() => handleSort('win_probability')}
                      className="py-3 px-4 cursor-pointer hover:text-white select-none"
                    >
                      <div className="flex items-center gap-1.5">
                        <span>P(Win)</span>
                        <ArrowUpDown className="w-3 h-3 text-slate-500" />
                      </div>
                    </th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-slate-300">
                  {filteredDisputes.length === 0 ? (
                    <tr>
                      <td colSpan="7" className="text-center py-10 text-slate-500">
                        No disputes matching current filter criteria.
                      </td>
                    </tr>
                  ) : (
                    filteredDisputes.map(dispute => {
                      const isHighWin = dispute.win_probability >= 0.85;
                      const isMediumWin = dispute.win_probability >= 0.5 && dispute.win_probability < 0.85;

                      return (
                        <tr 
                          key={dispute.dispute_id}
                          className="hover:bg-slate-800/40 transition-colors group"
                        >
                          {/* Dispute ID & Stage */}
                          <td className="py-3.5 px-4">
                            <div className="font-mono font-semibold text-white">
                              {dispute.dispute_id}
                            </div>
                            <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 mt-1 inline-block">
                              {dispute.stage}
                            </span>
                          </td>

                          {/* Buyer Name & Email */}
                          <td className="py-3.5 px-4">
                            <div className="font-medium text-slate-200">
                              {dispute.buyer_name}
                            </div>
                            <div className="text-[11px] text-slate-500 truncate max-w-[160px]">
                              {dispute.buyer_email}
                            </div>
                          </td>

                          {/* Amount & Item Title */}
                          <td className="py-3.5 px-4">
                            <div className="font-bold text-white">
                              ${dispute.amount.toFixed(2)} {dispute.currency}
                            </div>
                            <div className="text-[11px] text-slate-400 truncate max-w-[180px]">
                              {dispute.item_title}
                            </div>
                          </td>

                          {/* Reason */}
                          <td className="py-3.5 px-4">
                            <span className="text-[11px] text-slate-300 font-medium">
                              {dispute.reason.replace(/_/g, ' ')}
                            </span>
                          </td>

                          {/* Status Badge */}
                          <td className="py-3.5 px-4">
                            <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-semibold ${
                              dispute.pipeline_status === 'RESOLVED_WON' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30' :
                              dispute.pipeline_status === 'DEFENDED' ? 'bg-sky-500/10 text-sky-400 border border-sky-500/30' :
                              dispute.pipeline_status === 'AUTO_NEGOTIATING' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/30' :
                              dispute.pipeline_status === 'FLAGGED_HITL' ? 'bg-rose-500/10 text-rose-400 border border-rose-500/30' :
                              'bg-slate-800 text-slate-400'
                            }`}>
                              <span className="w-1.5 h-1.5 rounded-full bg-current" />
                              {dispute.pipeline_status.replace(/_/g, ' ')}
                            </span>
                          </td>

                          {/* Win Probability */}
                          <td className="py-3.5 px-4">
                            <div className="flex items-center gap-2">
                              <span className={`font-mono font-bold ${
                                isHighWin ? 'text-emerald-400' :
                                isMediumWin ? 'text-amber-400' :
                                'text-rose-400'
                              }`}>
                                {Math.round(dispute.win_probability * 100)}%
                              </span>
                              <div className="w-12 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                                <div 
                                  className={`h-full ${
                                    isHighWin ? 'bg-emerald-400' :
                                    isMediumWin ? 'bg-amber-400' :
                                    'bg-rose-400'
                                  }`}
                                  style={{ width: `${Math.round(dispute.win_probability * 100)}%` }}
                                />
                              </div>
                            </div>
                          </td>

                          {/* Actions */}
                          <td className="py-3.5 px-4 text-right">
                            <div className="flex items-center justify-end gap-2">
                              <button
                                onClick={() => setSelectedDisputeForDossier(dispute)}
                                className="px-2.5 py-1 rounded-lg bg-sky-500/10 hover:bg-sky-500/20 text-sky-300 border border-sky-500/30 transition-all text-[11px] font-medium flex items-center gap-1"
                              >
                                <FileText className="w-3 h-3" />
                                <span>Dossier</span>
                              </button>

                              <button
                                onClick={() => {
                                  setActiveChatDisputeId(dispute.dispute_id);
                                  setActiveTab('chat');
                                }}
                                className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-all text-[11px] font-medium flex items-center gap-1"
                              >
                                <MessageSquare className="w-3 h-3" />
                                <span>Chat</span>
                              </button>
                            </div>
                          </td>

                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>

            {/* Table Footer */}
            <div className="py-3 px-4 border-t border-slate-800 text-[11px] text-slate-500 flex items-center justify-between">
              <span>Showing {filteredDisputes.length} of {disputes.length} disputes</span>
              <span className="font-mono">React Native Table Engine • High Speed</span>
            </div>
          </div>

        </div>
      )}

      {/* VIEW 2: DISPUTE CHAT CENTER WITH DISPUTED BUYERS */}
      {activeTab === 'chat' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 bg-slate-900/70 border border-slate-800 rounded-3xl overflow-hidden backdrop-blur-xl shadow-2xl min-h-[580px]">
          
          {/* Left Column: Disputed Buyer List */}
          <div className="lg:col-span-4 border-b lg:border-b-0 lg:border-r border-slate-800 bg-slate-950/40 p-4 flex flex-col">
            <div className="text-xs font-mono uppercase tracking-wider text-slate-400 mb-3 px-2 flex items-center justify-between">
              <span>Disputed Buyers</span>
              <span className="text-[10px] bg-slate-800 px-2 py-0.5 rounded text-slate-300">{disputes.length} active</span>
            </div>

            <div className="space-y-2 overflow-y-auto max-h-[500px] pr-1">
              {disputes.map(d => {
                const isSelected = d.dispute_id === activeChatDisputeId;
                const hasConv = !!chatConversations[d.dispute_id];
                
                return (
                  <div
                    key={d.dispute_id}
                    onClick={() => setActiveChatDisputeId(d.dispute_id)}
                    className={`p-3 rounded-2xl cursor-pointer transition-all border ${
                      isSelected
                        ? 'bg-sky-500/10 border-sky-500/40 shadow-sm'
                        : 'bg-slate-900/60 border-slate-800/80 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-semibold text-xs text-white truncate max-w-[140px]">
                        {d.buyer_name}
                      </span>
                      <span className="font-mono text-[11px] font-bold text-sky-400">
                        ${d.amount.toFixed(2)}
                      </span>
                    </div>

                    <div className="text-[11px] text-slate-400 truncate mb-2">
                      {d.item_title}
                    </div>

                    <div className="flex items-center justify-between text-[10px]">
                      <span className="font-mono text-slate-500">{d.dispute_id}</span>
                      <span className={`px-1.5 py-0.5 rounded font-medium ${
                        d.buyer_sentiment.includes('Frustrated') ? 'bg-rose-500/20 text-rose-300' :
                        d.buyer_sentiment.includes('Resolved') ? 'bg-emerald-500/20 text-emerald-300' :
                        'bg-amber-500/20 text-amber-300'
                      }`}>
                        {d.buyer_sentiment}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Right Column: Chat Conversation Thread */}
          <div className="lg:col-span-8 flex flex-col justify-between p-6">
            
            {/* Chat Header */}
            {activeChatDispute && (
              <div className="border-b border-slate-800 pb-4 mb-4 flex flex-wrap items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-base font-bold text-white">
                      {activeChatDispute.buyer_name}
                    </h3>
                    <span className="font-mono text-xs text-slate-400">({activeChatDispute.buyer_email})</span>
                  </div>
                  <div className="text-xs text-slate-400 mt-0.5 flex items-center gap-3">
                    <span>Order: <strong className="text-slate-300">{activeChatDispute.order_id}</strong></span>
                    <span>Carrier: <strong className="text-slate-300">{activeChatDispute.carrier}</strong></span>
                    <span>Tracking: <strong className="text-slate-300 font-mono text-[11px]">{activeChatDispute.tracking_number}</strong></span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setSelectedDisputeForDossier(activeChatDispute)}
                    className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium flex items-center gap-1.5 transition-all"
                  >
                    <FileText className="w-3.5 h-3.5 text-sky-400" />
                    <span>View Dossier</span>
                  </button>
                </div>
              </div>
            )}

            {/* Chat Message Bubble Thread */}
            <div className="flex-1 overflow-y-auto space-y-4 pr-2 max-h-[360px] mb-4">
              {currentChatMessages.length === 0 ? (
                <div className="text-center py-12 text-slate-500 text-xs">
                  No previous chat history for this dispute. Start the dialogue below!
                </div>
              ) : (
                currentChatMessages.map((msg, idx) => {
                  const isBot = msg.sender === 'bot';
                  return (
                    <div 
                      key={idx} 
                      className={`flex flex-col ${isBot ? 'items-end' : 'items-start'}`}
                    >
                      <div className="flex items-center gap-1.5 mb-1 text-[10px] text-slate-500">
                        {isBot ? (
                          <>
                            <span className="font-semibold text-sky-400">{msg.name}</span>
                            <span>• {msg.time}</span>
                          </>
                        ) : (
                          <>
                            <span className="font-semibold text-slate-300">{msg.name}</span>
                            <span>• {msg.time}</span>
                          </>
                        )}
                      </div>

                      <div className={`p-3.5 rounded-2xl max-w-[85%] text-xs leading-relaxed ${
                        isBot 
                          ? 'bg-sky-500/20 text-sky-100 border border-sky-500/30 rounded-tr-none' 
                          : 'bg-slate-800 text-slate-200 border border-slate-700 rounded-tl-none'
                      }`}>
                        {msg.text}
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            {/* AI Assistant Quick Actions & Send Box */}
            <div className="space-y-3 pt-3 border-t border-slate-800">
              
              <div className="flex flex-wrap items-center justify-between gap-2">
                <button
                  type="button"
                  onClick={handleAiAutoReply}
                  disabled={isGeneratingAiReply}
                  className="px-3 py-1.5 rounded-lg bg-sky-500/10 hover:bg-sky-500/20 text-sky-300 border border-sky-500/30 text-xs font-medium flex items-center gap-1.5 transition-all"
                >
                  <Sparkles className="w-3.5 h-3.5 text-sky-400" />
                  <span>{isGeneratingAiReply ? 'Synthesizing Rebuttal...' : 'AI Auto-Draft Evidence Reply'}</span>
                </button>

                <button
                  type="button"
                  onClick={() => onSimulateBuyerReply(activeChatDisputeId)}
                  className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium flex items-center gap-1.5 transition-all"
                >
                  <Bot className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Simulate Buyer Reply</span>
                </button>
              </div>

              {/* Input Form */}
              <form onSubmit={handleSendChatMessage} className="flex items-center gap-2">
                <input
                  type="text"
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  placeholder="Type an autonomous dispute message or rebuttal offer..."
                  className="flex-1 px-4 py-2.5 rounded-xl bg-slate-950/80 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-sky-500"
                />
                <button
                  type="submit"
                  disabled={!chatInput.trim()}
                  className="px-4 py-2.5 rounded-xl bg-sky-400 hover:bg-sky-300 disabled:opacity-50 text-slate-950 font-semibold text-xs flex items-center gap-1.5 transition-all active:scale-95"
                >
                  <Send className="w-3.5 h-3.5" />
                  <span>Send</span>
                </button>
              </form>

            </div>

          </div>

        </div>
      )}

      {/* Dossier Modal */}
      {selectedDisputeForDossier && (
        <DossierModal
          dispute={selectedDisputeForDossier}
          onClose={() => setSelectedDisputeForDossier(null)}
        />
      )}

      {/* Simulate Inbound Dispute Webhook Modal */}
      {isSimulateModalOpen && (
        <SimulateDisputeModal
          onClose={() => setIsSimulateModalOpen(false)}
          onSimulate={onAddDispute}
        />
      )}

    </div>
  );
}
