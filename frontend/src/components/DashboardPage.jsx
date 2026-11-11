import React, { useState, useMemo, useEffect, useRef } from 'react';
import {
  Search,
  X,
  FileText,
  MessageSquare,
  Send,
  Sparkles,
  ArrowUp,
  ArrowDown,
  ArrowUpDown,
  FlaskConical,
  ChevronDown,
  Plus,
  Bot,
  AlertTriangle,
  CheckCircle2,
  Loader2,
  Inbox,
} from 'lucide-react';
import DossierModal from './DossierModal';
import SimulateDisputeModal from './SimulateDisputeModal';
import {
  statusInfo,
  reasonLabel,
  stageLabel,
  isOpen,
  needsReview,
  isWon,
  formatMoney,
  formatDate,
  REVIEW_ACTIONS,
  submitReviewDecision,
  reviewReasonLabel,
} from '../utils/disputes';

const FILTERS = [
  { id: 'ALL', label: 'All', test: () => true },
  { id: 'REVIEW', label: 'Needs review', test: needsReview },
  { id: 'OPEN', label: 'Open', test: isOpen },
  { id: 'CLOSED', label: 'Closed', test: (d) => !isOpen(d) },
];

const COLUMNS = [
  { id: 'buyer_name', label: 'Buyer', sortable: true },
  { id: 'amount', label: 'Amount', sortable: true },
  { id: 'reason', label: 'Reason', sortable: false },
  { id: 'created_at', label: 'Opened', sortable: true },
  { id: 'pipeline_status', label: 'Status', sortable: false },
  { id: 'win_probability', label: 'Win chance', sortable: true },
];

const winTone = (p) => (p >= 0.85 ? 'success' : p >= 0.5 ? 'warning' : 'danger');

function StatusBadge({ code }) {
  const { label, tone } = statusInfo(code);
  return <span className={`status-badge status-${tone}`}>{label}</span>;
}

function WinChance({ value }) {
  const pct = Math.round(value * 100);
  return (
    <div className="flex items-center gap-2">
      <span className={`win-value win-${winTone(value)}`}>{pct}%</span>
      <span className="win-track" aria-hidden="true">
        <span className={`win-fill win-fill-${winTone(value)}`} style={{ width: `${pct}%` }} />
      </span>
    </div>
  );
}

function MetricCard({ label, value, detail }) {
  return (
    <div className="dash-card dash-metric">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="dash-metric-value font-display">{value}</p>
      <p className="text-xs text-slate-500 mt-1">{detail}</p>
    </div>
  );
}

// One flagged dispute in the "Needs your attention" panel, with a confirm step before acting.
function ReviewItem({ dispute, reviewerId, onDecided }) {
  const [pendingAction, setPendingAction] = useState(null); // action awaiting confirmation
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const why = dispute.hitl_reasons?.length
    ? dispute.hitl_reasons.map(reviewReasonLabel).join(' · ')
    : dispute.ai_summary;

  const confirm = async () => {
    setIsSubmitting(true);
    setError(null);
    try {
      const changes = await submitReviewDecision(dispute, pendingAction, reviewerId);
      onDecided(dispute, pendingAction, changes);
    } catch (err) {
      setError(err.message);
      setIsSubmitting(false);
    }
  };

  return (
    <li className="review-item">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <span className="font-semibold text-slate-900">{dispute.buyer_name}</span>
          <span className="text-sm text-slate-600">{formatMoney(dispute.amount, dispute.currency)}</span>
          <span className="text-sm text-slate-500">{reasonLabel(dispute.reason)}</span>
          <WinChance value={dispute.win_probability} />
        </div>
        {why && <p className="text-sm text-slate-600 mt-1.5 review-why">{why}</p>}
        {error && <p className="text-sm text-rose-600 mt-1.5">Couldn’t apply that decision: {error}</p>}
      </div>

      <div className="review-actions">
        {pendingAction ? (
          <>
            <span className="text-sm text-slate-700">{REVIEW_ACTIONS[pendingAction].label}?</span>
            <button type="button" className="dash-btn dash-btn-primary" onClick={confirm} disabled={isSubmitting}>
              {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Confirm'}
            </button>
            <button type="button" className="dash-btn" onClick={() => setPendingAction(null)} disabled={isSubmitting}>
              Cancel
            </button>
          </>
        ) : (
          <>
            <button type="button" className="dash-btn dash-btn-primary" onClick={() => setPendingAction('DEFEND')}>
              {REVIEW_ACTIONS.DEFEND.label}
            </button>
            <button type="button" className="dash-btn" onClick={() => setPendingAction('MAKE_OFFER')}>
              {REVIEW_ACTIONS.MAKE_OFFER.label}
            </button>
            <button type="button" className="dash-btn dash-btn-quiet" onClick={() => setPendingAction('CONCEDE')}>
              {REVIEW_ACTIONS.CONCEDE.label}
            </button>
          </>
        )}
      </div>
    </li>
  );
}

function DemoToolsMenu({ onSimulateDispute, onSimulateReply, canSimulateReply }) {
  const [isOpenMenu, setIsOpenMenu] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    if (!isOpenMenu) return undefined;
    const close = (e) => {
      if (e.type === 'keydown' ? e.key === 'Escape' : !ref.current?.contains(e.target)) setIsOpenMenu(false);
    };
    document.addEventListener('pointerdown', close);
    document.addEventListener('keydown', close);
    return () => {
      document.removeEventListener('pointerdown', close);
      document.removeEventListener('keydown', close);
    };
  }, [isOpenMenu]);

  const run = (fn) => () => {
    setIsOpenMenu(false);
    fn();
  };

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        className="dash-btn"
        onClick={() => setIsOpenMenu((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={isOpenMenu}
      >
        <FlaskConical className="w-4 h-4 text-violet-600" />
        <span>Demo tools</span>
        <ChevronDown className="w-4 h-4 text-slate-400" />
      </button>
      {isOpenMenu && (
        <div className="app-menu app-menu-wide" role="menu">
          <p className="px-3 pt-2 pb-1 text-xs text-slate-500">For demos and testing</p>
          <button type="button" role="menuitem" className="app-menu-item" onClick={run(onSimulateDispute)}>
            <Plus className="w-4 h-4" />
            <span>Simulate a new dispute</span>
          </button>
          <button
            type="button"
            role="menuitem"
            className="app-menu-item"
            onClick={run(onSimulateReply)}
            disabled={!canSimulateReply}
            title={canSimulateReply ? undefined : 'Open a conversation first'}
          >
            <Bot className="w-4 h-4" />
            <span>Simulate a buyer reply</span>
          </button>
        </div>
      )}
    </div>
  );
}

export default function DashboardPage({
  disputes,
  onAddDispute,
  onUpdateDispute,
  merchantProfile,
  chatConversations,
  onSendMessage,
  onSimulateBuyerReply,
}) {
  const [activeTab, setActiveTab] = useState('disputes'); // 'disputes' | 'chat'
  const [searchQuery, setSearchQuery] = useState('');
  const [filterId, setFilterId] = useState('ALL');
  const [sortField, setSortField] = useState('created_at');
  const [sortOrder, setSortOrder] = useState('desc');

  const [selectedDisputeForDossier, setSelectedDisputeForDossier] = useState(null);
  const [activeChatDisputeId, setActiveChatDisputeId] = useState(disputes[0]?.dispute_id);
  const [chatInput, setChatInput] = useState('');
  const [isSimulateModalOpen, setIsSimulateModalOpen] = useState(false);
  const [isGeneratingAiReply, setIsGeneratingAiReply] = useState(false);
  const [toast, setToast] = useState(null);

  useEffect(() => {
    if (!toast) return undefined;
    const id = setTimeout(() => setToast(null), 4000);
    return () => clearTimeout(id);
  }, [toast]);

  // Headline numbers, worked out from the disputes on screen so they always match the table.
  const metrics = useMemo(() => {
    const open = disputes.filter(isOpen);
    const closed = disputes.filter((d) => !isOpen(d));
    const won = closed.filter(isWon).length;
    const avgWin = open.length ? open.reduce((sum, d) => sum + d.win_probability, 0) / open.length : 0;
    return {
      openCount: open.length,
      atStake: open.reduce((sum, d) => sum + d.amount, 0),
      reviewCount: disputes.filter(needsReview).length,
      closedCount: closed.length,
      won,
      refunded: closed.filter((d) => d.pipeline_status === 'CONCEDED').length,
      avgWin,
    };
  }, [disputes]);

  const reviewQueue = useMemo(() => disputes.filter(needsReview), [disputes]);

  const filteredDisputes = useMemo(() => {
    const filter = FILTERS.find((f) => f.id === filterId) || FILTERS[0];
    const q = searchQuery.trim().toLowerCase();
    return disputes
      .filter(filter.test)
      .filter((d) => {
        if (!q) return true;
        return [d.dispute_id, d.buyer_name, d.buyer_email, d.item_title, reasonLabel(d.reason)]
          .some((field) => field?.toLowerCase().includes(q));
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
  }, [disputes, searchQuery, filterId, sortField, sortOrder]);

  const handleSort = (field) => {
    if (sortField === field) {
      setSortOrder((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortOrder('desc');
    }
  };

  const handleReviewDecided = (dispute, action, changes) => {
    onUpdateDispute(dispute.dispute_id, changes);
    setToast(`${REVIEW_ACTIONS[action].label}: ${dispute.buyer_name}`);
  };

  const openChat = (disputeId) => {
    setActiveChatDisputeId(disputeId);
    setActiveTab('chat');
  };

  const activeChatDispute = disputes.find((d) => d.dispute_id === activeChatDisputeId) || disputes[0];
  const currentChatMessages = (activeChatDispute && chatConversations[activeChatDispute.dispute_id]) || [];

  const handleSendChatMessage = (e) => {
    e?.preventDefault();
    if (!chatInput.trim() || !activeChatDispute) return;
    onSendMessage(activeChatDispute.dispute_id, {
      sender: 'bot',
      name: merchantProfile.business_name,
      time: 'Just now',
      text: chatInput.trim(),
    });
    setChatInput('');
  };

  const handleAiAutoReply = () => {
    if (!activeChatDispute) return;
    setIsGeneratingAiReply(true);
    setTimeout(() => {
      const firstName = activeChatDispute.buyer_name.split(' ')[0];
      let suggestedText;
      if (activeChatDispute.reason.includes('UNAUTHORI')) {
        suggestedText = `Hello ${firstName}, our records show this order was placed from a device you’ve used before (${activeChatDispute.device_hash.substring(0, 8)}) and tracking ${activeChatDispute.tracking_number} shows delivery to your address. Could a family member have placed this order?`;
      } else if (activeChatDispute.reason.includes('NOT_RECEIVED')) {
        suggestedText = `Hi ${firstName}, the carrier scan for ${activeChatDispute.tracking_number} shows the parcel was delivered. Could you check with neighbours or any parcel lockers? We’ve also asked the carrier for a delivery report.`;
      } else {
        suggestedText = `Hello ${firstName}, we’d like to sort out your concern about "${activeChatDispute.item_title}". We can send a free return label, or offer a partial refund if you’d prefer to keep it. Which would you like?`;
      }
      setChatInput(suggestedText);
      setIsGeneratingAiReply(false);
    }, 600);
  };

  const ariaSort = (id) => (sortField === id ? (sortOrder === 'asc' ? 'ascending' : 'descending') : undefined);

  return (
    <div className="dash container mx-auto px-4 sm:px-6 py-8">

      {/* Title row */}
      <div className="flex flex-wrap items-end justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight font-display">Disputes</h1>
          <p className="text-slate-600 mt-1">Everything LexiShield is handling for {merchantProfile.business_name}.</p>
        </div>
        <DemoToolsMenu
          onSimulateDispute={() => setIsSimulateModalOpen(true)}
          onSimulateReply={() => activeChatDispute && onSimulateBuyerReply(activeChatDispute.dispute_id)}
          canSimulateReply={activeTab === 'chat' && Boolean(activeChatDispute)}
        />
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <MetricCard
          label="Open disputes"
          value={metrics.openCount}
          detail={`${formatMoney(metrics.atStake)} at stake`}
        />
        <MetricCard
          label="Needs your review"
          value={metrics.reviewCount}
          detail={metrics.reviewCount ? 'Waiting for your decision' : 'Nothing waiting on you'}
        />
        <MetricCard
          label="Closed"
          value={metrics.closedCount}
          detail={`${metrics.won} resolved in your favour · ${metrics.refunded} refunded`}
        />
        <MetricCard
          label="Average win chance"
          value={metrics.openCount ? `${Math.round(metrics.avgWin * 100)}%` : '—'}
          detail="Across open disputes"
        />
      </div>

      {/* Needs your attention */}
      {reviewQueue.length > 0 ? (
        <section className="dash-card review-panel mb-8" aria-labelledby="review-title">
          <div className="flex items-center gap-2 mb-1">
            <AlertTriangle className="w-5 h-5 text-amber-600" />
            <h2 id="review-title" className="text-lg font-bold text-slate-900 font-display">Needs your attention</h2>
            <span className="review-count">{reviewQueue.length}</span>
          </div>
          <p className="text-sm text-slate-600 mb-4">
            These disputes are high-value or borderline, so LexiShield is waiting for your decision before acting.
          </p>
          <ul className="review-list">
            {reviewQueue.map((d) => (
              <ReviewItem
                key={d.dispute_id}
                dispute={d}
                reviewerId={merchantProfile.merchant_id || 'dashboard-user'}
                onDecided={handleReviewDecided}
              />
            ))}
          </ul>
        </section>
      ) : (
        <div className="dash-card caught-up mb-8">
          <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
          <p className="text-sm text-slate-700">You’re all caught up. Nothing needs your review right now.</p>
        </div>
      )}

      {/* Tabs */}
      <div className="dash-tabs mb-4" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'disputes'}
          className={`dash-tab ${activeTab === 'disputes' ? 'dash-tab-active' : ''}`}
          onClick={() => setActiveTab('disputes')}
        >
          <FileText className="w-4 h-4" />
          <span>All disputes</span>
          <span className="dash-tab-count">{disputes.length}</span>
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'chat'}
          className={`dash-tab ${activeTab === 'chat' ? 'dash-tab-active' : ''}`}
          onClick={() => setActiveTab('chat')}
        >
          <MessageSquare className="w-4 h-4" />
          <span>Conversations</span>
        </button>
      </div>

      {activeTab === 'disputes' && (
        <div className="dash-card dash-table-card">

          {/* Toolbar */}
          <div className="dash-toolbar">
            <div className="dash-search">
              <Search className="w-4 h-4 text-slate-400" aria-hidden="true" />
              <input
                type="search"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search buyer, item, reason or dispute ID"
                aria-label="Search disputes"
              />
              {searchQuery && (
                <button type="button" onClick={() => setSearchQuery('')} aria-label="Clear search" className="dash-icon-btn">
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>
            <div className="dash-filters" role="group" aria-label="Filter disputes">
              {FILTERS.map((f) => (
                <button
                  key={f.id}
                  type="button"
                  aria-pressed={filterId === f.id}
                  className={`dash-filter ${filterId === f.id ? 'dash-filter-active' : ''}`}
                  onClick={() => setFilterId(f.id)}
                >
                  {f.label}
                  <span className="dash-filter-count">{disputes.filter(f.test).length}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="dash-table">
              <thead>
                <tr>
                  {COLUMNS.map((col) => (
                    <th key={col.id} scope="col" aria-sort={col.sortable ? ariaSort(col.id) : undefined}>
                      {col.sortable ? (
                        <button type="button" className="dash-sort" onClick={() => handleSort(col.id)}>
                          <span>{col.label}</span>
                          {sortField === col.id ? (
                            sortOrder === 'asc' ? <ArrowUp className="w-3.5 h-3.5" /> : <ArrowDown className="w-3.5 h-3.5" />
                          ) : (
                            <ArrowUpDown className="w-3.5 h-3.5 dash-sort-idle" />
                          )}
                        </button>
                      ) : (
                        col.label
                      )}
                    </th>
                  ))}
                  <th scope="col" className="text-right"><span className="sr-only">Actions</span></th>
                </tr>
              </thead>
              <tbody>
                {filteredDisputes.length === 0 ? (
                  <tr>
                    <td colSpan={COLUMNS.length + 1}>
                      <div className="dash-empty">
                        <Inbox className="w-6 h-6 text-slate-400" />
                        <p className="font-medium text-slate-700">No disputes match</p>
                        <p className="text-sm text-slate-500">Try a different search or filter.</p>
                      </div>
                    </td>
                  </tr>
                ) : (
                  filteredDisputes.map((d) => (
                    <tr key={d.dispute_id}>
                      <td>
                        <div className="font-medium text-slate-900">{d.buyer_name}</div>
                        <div className="text-xs text-slate-500 font-mono">{d.dispute_id} · {stageLabel(d.stage)}</div>
                      </td>
                      <td>
                        <div className="font-semibold text-slate-900">{formatMoney(d.amount, d.currency)}</div>
                        <div className="text-xs text-slate-500 truncate dash-cell-item">{d.item_title}</div>
                      </td>
                      <td className="text-slate-700">{reasonLabel(d.reason)}</td>
                      <td className="text-slate-600 whitespace-nowrap">{formatDate(d.created_at)}</td>
                      <td><StatusBadge code={d.pipeline_status} /></td>
                      <td><WinChance value={d.win_probability} /></td>
                      <td>
                        <div className="flex items-center justify-end gap-1.5">
                          <button type="button" className="dash-btn dash-btn-sm" onClick={() => setSelectedDisputeForDossier(d)}>
                            <FileText className="w-3.5 h-3.5" />
                            <span>Details</span>
                          </button>
                          <button type="button" className="dash-btn dash-btn-sm" onClick={() => openChat(d.dispute_id)}>
                            <MessageSquare className="w-3.5 h-3.5" />
                            <span>Message</span>
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          <div className="dash-table-footer">
            Showing {filteredDisputes.length} of {disputes.length} disputes
          </div>
        </div>
      )}

      {activeTab === 'chat' && (
        <div className="dash-card dash-chat">

          {/* Conversation list */}
          <div className="dash-chat-list">
            <p className="px-2 pb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">Buyers</p>
            <div className="space-y-1.5">
              {disputes.map((d) => {
                const isSelected = d.dispute_id === activeChatDispute?.dispute_id;
                return (
                  <button
                    key={d.dispute_id}
                    type="button"
                    onClick={() => setActiveChatDisputeId(d.dispute_id)}
                    aria-current={isSelected ? 'true' : undefined}
                    className={`dash-chat-item ${isSelected ? 'dash-chat-item-active' : ''}`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-semibold text-sm text-slate-900 truncate">{d.buyer_name}</span>
                      <span className="text-xs font-semibold text-slate-700">{formatMoney(d.amount, d.currency)}</span>
                    </div>
                    <div className="text-xs text-slate-500 truncate mt-0.5">{d.item_title}</div>
                    <div className="mt-1.5"><StatusBadge code={d.pipeline_status} /></div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Thread */}
          <div className="dash-chat-thread">
            {activeChatDispute && (
              <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 pb-4 mb-4">
                <div className="min-w-0">
                  <h3 className="text-base font-bold text-slate-900">{activeChatDispute.buyer_name}</h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    {activeChatDispute.buyer_email} · Order {activeChatDispute.order_id} · {activeChatDispute.carrier} {activeChatDispute.tracking_number}
                  </p>
                </div>
                <button type="button" className="dash-btn dash-btn-sm" onClick={() => setSelectedDisputeForDossier(activeChatDispute)}>
                  <FileText className="w-3.5 h-3.5" />
                  <span>Details</span>
                </button>
              </div>
            )}

            <div className="dash-messages">
              {currentChatMessages.length === 0 ? (
                <div className="dash-empty">
                  <MessageSquare className="w-6 h-6 text-slate-400" />
                  <p className="font-medium text-slate-700">No messages yet</p>
                  <p className="text-sm text-slate-500">Start the conversation below, or let the AI draft a reply.</p>
                </div>
              ) : (
                currentChatMessages.map((msg, idx) => {
                  const isOurs = msg.sender === 'bot';
                  return (
                    <div key={idx} className={`flex flex-col ${isOurs ? 'items-end' : 'items-start'}`}>
                      <div className="text-xs text-slate-500 mb-1">
                        <span className="font-semibold text-slate-700">{msg.name}</span> · {msg.time}
                      </div>
                      <div className={`dash-msg ${isOurs ? 'dash-msg-ours' : 'dash-msg-theirs'}`}>{msg.text}</div>
                    </div>
                  );
                })
              )}
            </div>

            <div className="border-t border-slate-100 pt-4 space-y-3">
              <button type="button" className="dash-btn dash-btn-sm" onClick={handleAiAutoReply} disabled={isGeneratingAiReply || !activeChatDispute}>
                {isGeneratingAiReply ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5 text-sky-600" />}
                <span>{isGeneratingAiReply ? 'Drafting…' : 'Draft a reply with AI'}</span>
              </button>
              <form onSubmit={handleSendChatMessage} className="flex items-center gap-2">
                <input
                  type="text"
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  placeholder="Write a message to the buyer…"
                  aria-label="Message to buyer"
                  className="dash-input flex-1"
                />
                <button type="submit" disabled={!chatInput.trim()} className="dash-btn dash-btn-primary">
                  <Send className="w-4 h-4" />
                  <span>Send</span>
                </button>
              </form>
            </div>
          </div>

        </div>
      )}

      {toast && (
        <div className="dash-toast" role="status">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          <span>{toast}</span>
        </div>
      )}

      {selectedDisputeForDossier && (
        <DossierModal dispute={selectedDisputeForDossier} onClose={() => setSelectedDisputeForDossier(null)} />
      )}

      {isSimulateModalOpen && (
        <SimulateDisputeModal onClose={() => setIsSimulateModalOpen(false)} onSimulate={onAddDispute} />
      )}

    </div>
  );
}
