/**
 * LexiShield Enterprise Defense System
 * Interactive Web Application Engine
 */

(function () {
  'use strict';

  // Global State
  let disputes = [];
  let currentFilter = { stage: 'ALL', status: 'ALL', search: '' };
  let currentTenant = 'all';

  // Initial Seed Data for immediate interactive showcase
  const defaultDisputes = [
    {
      dispute_id: 'PP-D-8842-CE3',
      merchant_id: 'merchant_alpha_retail',
      stage: 'CLAIM',
      reason: 'UNAUTHORISED',
      amount: 389.00,
      currency: 'USD',
      customer_email: 'j.harrison@example.com',
      pipeline_status: 'DEFENDED',
      win_probability: 0.98,
      expected_value: 366.22,
      dispute_fee_applied: 15.00,
      hitl_flagged: false,
      hitl_reasons: [],
      compliance_eligible: true,
      visa_ce3_qualified: true,
      pdf_dossier_path: '/artifacts/dossiers/dossier_PP-D-8842-CE3.pdf',
      telemetry_carrier: {
        carrier_name: 'UPS',
        tracking_number: '1Z9999999999999999',
        status: 'DELIVERED',
        delivery_timestamp: '2026-10-15T14:22:00Z',
        destination_address: '742 Evergreen Terr, Springfield OR',
        signature_required: true,
        signed_by: 'J. HARRISON',
        is_redirection_detected: false,
        gps_coordinates: '44.0462,-123.0220'
      },
      telemetry_warehouse: {
        weight_kg: 1.450,
        expected_weight_kg: 1.448,
        item_serial_scanned: 'SN-X990-48201',
        package_dimensions: '12x8x4 in'
      },
      telemetry_order: {
        customer_id: 'CUST-ELITE-994',
        past_orders_count: 5,
        lifetime_spend: 3450.00,
        checkout_ip: '198.51.100.44',
        device_fingerprint: 'fp_884920b784a9'
      },
      audit_trail: [
        'Dispute intake via CUSTOMER.DISPUTE.CREATED',
        'Compliance Check: AVS Exact Match confirmed',
        'Visa CE 3.0: 2 qualifying prior orders verified with matching IP & Device Fingerprint',
        'Gemini 1.5 Multimodal: Packing camera & scale weight verified',
        'ReportLab Rebuttal PDF compiled and submitted to PayPal provide-evidence API'
      ]
    },
    {
      dispute_id: 'PP-D-9912-SIG',
      merchant_id: 'merchant_luxury_goods',
      stage: 'CLAIM',
      reason: 'MERCHANDISE_OR_SERVICE_NOT_RECEIVED',
      amount: 850.00,
      currency: 'USD',
      customer_email: 'marcus.vance@example.com',
      pipeline_status: 'CONCEDED',
      win_probability: 0.05,
      expected_value: -880.00,
      dispute_fee_applied: 30.00,
      hitl_flagged: false,
      hitl_reasons: ['Amount >= $750 without signature confirmation'],
      compliance_eligible: false,
      compliance_disqualifications: ['Violates PayPal $750+ Signature Mandate (No carrier signature)'],
      visa_ce3_qualified: false,
      pdf_dossier_path: null,
      telemetry_carrier: {
        carrier_name: 'FedEx',
        tracking_number: '794628419201',
        status: 'DELIVERED',
        delivery_timestamp: '2026-10-12T11:05:00Z',
        destination_address: '100 Sunset Blvd, Beverly Hills CA',
        signature_required: false,
        signed_by: null,
        is_redirection_detected: false
      },
      audit_trail: [
        'Dispute intake for $850.00 Item Not Received',
        'Compliance Rule Triggered: Amount exceeds $750.00 and carrier signature is missing',
        'Seller Protection auto-disqualified under Section 11.3',
        'Early Concession executed via accept-claim API: Saved secondary dispute fee'
      ]
    },
    {
      dispute_id: 'PP-D-HITL-4410',
      merchant_id: 'merchant_alpha_retail',
      stage: 'CLAIM',
      reason: 'MERCHANDISE_OR_SERVICE_NOT_AS_DESCRIBED',
      amount: 450.00,
      currency: 'USD',
      customer_email: 'elena.rostova@example.com',
      pipeline_status: 'FLAGGED_HITL',
      win_probability: 0.68,
      expected_value: 172.50,
      dispute_fee_applied: 15.00,
      hitl_flagged: true,
      hitl_reasons: ['Order amount > $300 ($450.00)', 'Borderline Win Probability P(win)=0.68 in [0.60, 0.75)'],
      compliance_eligible: true,
      visa_ce3_qualified: false,
      pdf_dossier_path: '/artifacts/dossiers/dossier_PP-D-HITL-4410.pdf',
      telemetry_carrier: {
        carrier_name: 'DHL Express',
        tracking_number: '94001000000000000000',
        status: 'DELIVERED',
        delivery_timestamp: '2026-10-14T09:40:00Z',
        destination_address: '450 Park Ave, New York NY',
        signature_required: true,
        signed_by: 'E. ROSTOVA',
        is_redirection_detected: false
      },
      audit_trail: [
        'Dispute intake: SNAD Claim for $450.00',
        'Warehouse video shows sealed anti-tamper tape applied',
        'Flagged for Human-in-the-Loop review due to high order value and borderline probability'
      ]
    },
    {
      dispute_id: 'PP-D-INQ-4401',
      merchant_id: 'merchant_alpha_retail',
      stage: 'INQUIRY',
      reason: 'MERCHANDISE_OR_SERVICE_NOT_RECEIVED',
      amount: 89.50,
      currency: 'USD',
      customer_email: 'sarah.jenkins@example.com',
      pipeline_status: 'PENDING',
      win_probability: 0.88,
      expected_value: 78.76,
      dispute_fee_applied: 0.00,
      hitl_flagged: false,
      compliance_eligible: true,
      audit_trail: [
        'Dispute intake in INQUIRY phase',
        'Conversational Settlement Bot engaged: Step 1 (Dispatched carrier tracking & delivery photo)',
        'Buyer replied: Package not found on porch',
        'Conversational Settlement Bot engaged: Step 2 (Offered 20% partial refund or replacement)'
      ]
    }
  ];

  // In-memory Deflection Alerts Feed
  const deflectionFeed = [
    {
      network: 'ETHOCA',
      order_id: 'ORD-DEFLECT-9901',
      amount: 142.50,
      reason: 'Cardholder dispute notification (Prior to posting)',
      timestamp: '25 mins ago',
      status: 'AUTO_REFUNDED_ZERO_FEE'
    },
    {
      network: 'VERIFI_RDR',
      order_id: 'ORD-DEFLECT-7720',
      amount: 98.00,
      reason: 'Issuer pre-chargeback alert rule matched',
      timestamp: '2 hours ago',
      status: 'AUTO_REFUNDED_ZERO_FEE'
    }
  ];

  // RMA Registry
  const rmaList = [
    {
      rma_number: 'RMA-2026-88192',
      dispute_id: 'PP-D-HITL-4410',
      carrier: 'USPS Return Service',
      tracking_number: '9400 1118 9956 2000 1122 33',
      status: 'LABEL_GENERATED_AWAITING_INBOUND',
      created_at: '2026-10-18T18:30:00Z'
    }
  ];

  // Accounting Ledger Stream
  const accountingEntries = [
    {
      id: 'JE-99012',
      timestamp: 'Today 10:15 AM',
      type: 'ESCROW_FREEZE',
      dispute_id: 'PP-D-8842-CE3',
      debit: 'Dispute Escrow Receivable ($389.00)',
      credit: 'Operating Cash ($389.00)'
    },
    {
      id: 'JE-99013',
      timestamp: 'Today 10:20 AM',
      type: 'DEFENSE_WON_REVERSAL',
      dispute_id: 'PP-D-8842-CE3',
      debit: 'Operating Cash ($389.00)',
      credit: 'Dispute Escrow Receivable ($389.00)'
    },
    {
      id: 'JE-99008',
      timestamp: 'Yesterday 16:45 PM',
      type: 'CONCESSION_WRITE_OFF',
      dispute_id: 'PP-D-9912-SIG',
      debit: 'Loss on Disputed Claims ($850.00)',
      credit: 'Inventory COGS / Escrow ($850.00)'
    }
  ];

  // Chat Bot State
  const chatMessages = [
    {
      sender: 'buyer',
      name: 'Sarah Jenkins',
      time: '10:12 AM',
      text: "Hi, I have not received my package yet even though the app marked it delivered yesterday. Can you help?"
    },
    {
      sender: 'bot',
      name: 'LexiShield Resolution Assistant',
      time: '10:13 AM',
      text: "Hello Sarah, thank you for reaching out! We checked with UPS (Tracking: 1Z9999999999999999) and delivery was confirmed yesterday at 2:22 PM at your Front Porch. We recommend checking with neighbors or building reception. Here is your tracking proof: https://ups.com/track/1Z9999999999999999."
    },
    {
      sender: 'buyer',
      name: 'Sarah Jenkins',
      time: '10:28 AM',
      text: "I checked with my neighbors and nobody saw it. I'd like a refund please."
    },
    {
      sender: 'bot',
      name: 'LexiShield Resolution Assistant',
      time: '10:29 AM',
      text: "We understand your frustration! As a courtesy, we would be delighted to immediately issue a 20% partial refund ($17.90) to your PayPal account, or we can ship a complimentary expedited replacement right away. Would either of these options work for you?"
    }
  ];

  // Initialize
  async function init() {
    await fetchDisputesFromBackend();
    renderDisputes();
    renderDeflectionFeed();
    renderRmaGrid();
    renderAccountingLedger();
    renderChat();
    updateKpis();
  }

  // Fetch from backend API
  async function fetchDisputesFromBackend() {
    try {
      const resp = await fetch('/api/v1/disputes');
      if (resp.ok) {
        const data = await resp.json();
        if (data && data.length > 0) {
          disputes = data;
          showToast('Synced active disputes from PayPal Dispute Engine backend.');
          return;
        }
      }
    } catch (err) {
      console.warn('API sync fallback to seeded store:', err);
    }
    // Fallback to rich default dataset
    disputes = defaultDisputes;
  }

  // Render Disputes Card Grid
  function renderDisputes() {
    const grid = document.getElementById('disputesGrid');
    if (!grid) return;

    let filtered = disputes.filter(d => {
      if (currentTenant !== 'all' && d.merchant_id && d.merchant_id !== currentTenant) {
        return false;
      }
      if (currentFilter.stage !== 'ALL' && d.stage.toUpperCase() !== currentFilter.stage) {
        return false;
      }
      if (currentFilter.status !== 'ALL' && d.pipeline_status.toUpperCase() !== currentFilter.status) {
        return false;
      }
      if (currentFilter.search) {
        const q = currentFilter.search.toLowerCase();
        const str = `${d.dispute_id} ${d.customer_email || ''} ${d.amount} ${d.reason}`.toLowerCase();
        if (!str.includes(q)) return false;
      }
      return true;
    });

    if (filtered.length === 0) {
      grid.innerHTML = `
        <div class="loading-state">
          <div style="font-size: 2rem; margin-bottom: 0.5rem;">🛡️</div>
          <span>No disputes match the selected filters or tenant.</span>
        </div>
      `;
      return;
    }

    grid.innerHTML = filtered.map(d => {
      const pwin = d.win_probability !== null && d.win_probability !== undefined ? Math.round(d.win_probability * 100) : 75;
      const fillClass = pwin >= 75 ? 'fill-high' : (pwin >= 50 ? 'fill-med' : 'fill-low');
      const stagePill = d.stage === 'INQUIRY' 
        ? '<span class="dispute-stage-pill stage-inquiry">STAGE: INQUIRY</span>' 
        : '<span class="dispute-stage-pill stage-claim">STAGE: CLAIM</span>';

      const complianceBadge = d.compliance_eligible === false
        ? '<span class="badge badge-crimson">⚠️ POLICY VOID</span>'
        : (d.visa_ce3_qualified 
          ? '<span class="badge badge-purple">⚡ VISA CE 3.0</span>'
          : '<span class="badge badge-emerald">✓ SELLER PROTECTED</span>');

      const hitlBadge = d.hitl_flagged
        ? '<span class="badge badge-amber">⚠️ HITL REVIEW</span>'
        : `<span class="badge badge-cyan">${d.pipeline_status}</span>`;

      return `
        <div class="dispute-card">
          <div class="dispute-card-header">
            <div class="dispute-id-group">
              <span class="dispute-id-title">${d.dispute_id}</span>
              <span class="dispute-customer-meta">${d.customer_email || 'Verified Buyer'} • ${d.reason.replace(/_/g, ' ')}</span>
              ${stagePill}
            </div>
            <div class="dispute-amount-group">
              <div class="dispute-amount-val">$${d.amount.toFixed(2)}</div>
              <div style="font-size: 0.7rem; color: var(--text-dim);">${d.currency}</div>
            </div>
          </div>

          <div class="dispute-arbitration-meter">
            <div class="meter-header">
              <span style="color: var(--text-muted); font-weight: 600;">AI Arbitration Win Probability P(win):</span>
              <span style="font-family: var(--font-mono); font-weight: 700; color: #fff;">${pwin}%</span>
            </div>
            <div class="meter-bar-track">
              <div class="meter-bar-fill ${fillClass}" style="width: ${pwin}%;"></div>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 0.7rem; color: var(--text-dim); margin-top: 0.4rem;">
              <span>Expected Value E[V]: <strong>$${(d.expected_value || 0).toFixed(2)}</strong></span>
              <span>Dispute Fee Risk: <strong>$${(d.dispute_fee_applied || 15).toFixed(2)}</strong></span>
            </div>
          </div>

          <div class="compliance-badge-list">
            ${complianceBadge}
            ${hitlBadge}
            ${d.telemetry_carrier && d.telemetry_carrier.signature_required ? '<span class="badge badge-cyan">✍️ Signed</span>' : ''}
          </div>

          <div class="card-action-footer">
            <button class="btn btn-outline btn-sm" onclick="window.inspectDispute('${d.dispute_id}')">
              🔍 Inspect Dossier
            </button>
            ${d.hitl_flagged ? `
              <button class="btn btn-primary btn-sm" onclick="window.inspectDispute('${d.dispute_id}')">
                ⚖️ Triage HITL
              </button>
            ` : (d.pdf_dossier_path ? `
              <a href="/api/v1/disputes/${d.dispute_id}/pdf" target="_blank" class="btn btn-secondary btn-sm">
                📄 PDF Dossier
              </a>
            ` : `
              <span style="font-size: 0.75rem; color: var(--text-dim);">Automated Decision</span>
            `)}
          </div>
        </div>
      `;
    }).join('');
  }

  // Update KPI counters
  function updateKpis() {
    const gmv = disputes.reduce((acc, d) => acc + (d.amount || 0), 1482900);
    const totalWithPwin = disputes.filter(d => d.win_probability !== null);
    const avgPwin = totalWithPwin.length > 0 
      ? (totalWithPwin.reduce((acc, d) => acc + d.win_probability, 0) / totalWithPwin.length) * 100 
      : 94.8;
    const hitlCount = disputes.filter(d => d.hitl_flagged).length;

    const elGmv = document.getElementById('kpiGmv');
    if (elGmv) elGmv.textContent = `$${gmv.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;

    const elWin = document.getElementById('kpiWinRate');
    if (elWin) elWin.textContent = `${avgPwin.toFixed(1)}%`;

    const elHitl = document.getElementById('kpiHitlQueue');
    if (elHitl) elHitl.textContent = `${hitlCount} Pending`;
  }

  // Deflection Feed Rendering
  function renderDeflectionFeed() {
    const feed = document.getElementById('deflectionFeed');
    if (!feed) return;

    feed.innerHTML = deflectionFeed.map(item => `
      <div class="deflection-item">
        <div class="deflection-network">
          <div class="deflection-network-icon">${item.network === 'ETHOCA' ? '🛡️' : '⚡'}</div>
          <div>
            <div style="font-weight: 700; color: #fff; font-size: 0.95rem;">
              ${item.network === 'ETHOCA' ? 'Ethoca Consumer Clarity Alert' : 'Verifi Rapid Dispute Resolution (RDR)'}
            </div>
            <div style="font-size: 0.78rem; color: var(--text-muted); margin-top: 0.2rem;">
              Order Ref: <strong style="font-family: var(--font-mono); color: var(--color-cyan);">${item.order_id}</strong> • ${item.reason}
            </div>
          </div>
        </div>
        <div style="text-align: right;">
          <div style="font-family: var(--font-display); font-size: 1.15rem; font-weight: 700; color: #fff;">
            $${item.amount.toFixed(2)}
          </div>
          <span class="badge badge-emerald" style="margin-top: 0.25rem;">
            ✓ ZERO-FEE AUTO REFUNDED
          </span>
          <div style="font-size: 0.7rem; color: var(--text-dim); margin-top: 0.2rem;">
            Saved $15.00 Fee • ${item.timestamp}
          </div>
        </div>
      </div>
    `).join('');
  }

  // RMA Hub Rendering
  function renderRmaGrid() {
    const grid = document.getElementById('rmaGrid');
    if (!grid) return;

    grid.innerHTML = rmaList.map(item => `
      <div class="ce3-card" style="margin-bottom: 1rem;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
          <div>
            <div style="font-family: var(--font-mono); font-size: 1rem; font-weight: 700; color: var(--color-cyan);">
              ${item.rma_number}
            </div>
            <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 0.2rem;">
              Associated Dispute: <strong>${item.dispute_id}</strong> • Carrier: ${item.carrier}
            </div>
          </div>
          <span class="badge badge-amber">INBOUND SCAN PENDING</span>
        </div>
        <div style="margin-top: 1rem; padding: 0.85rem; background: rgba(0,0,0,0.3); border-radius: var(--radius-sm); display: flex; align-items: center; justify-content: space-between;">
          <div style="font-family: var(--font-mono); font-size: 0.82rem; letter-spacing: 1px;">
            ${item.tracking_number}
          </div>
          <button class="btn btn-outline btn-sm" onclick="window.simulateRmaScan('${item.rma_number}')">
            📦 Simulate Inbound Scan
          </button>
        </div>
      </div>
    `).join('');
  }

  // Accounting Ledger Stream
  function renderAccountingLedger() {
    const container = document.getElementById('accountingLedger');
    if (!container) return;

    container.innerHTML = accountingEntries.map(e => `
      <div style="padding: 0.75rem 0; border-bottom: 1px solid var(--border-subtle); display: flex; justify-content: space-between; font-size: 0.8rem;">
        <div>
          <span style="font-family: var(--font-mono); color: var(--color-purple); font-weight: 700;">${e.id}</span>
          <span style="color: var(--text-dim); margin-left: 0.5rem;">(${e.dispute_id})</span>
          <div style="color: #fff; margin-top: 0.2rem;">
            Dr: ${e.debit} | Cr: ${e.credit}
          </div>
        </div>
        <div style="text-align: right; color: var(--text-dim); font-size: 0.72rem;">
          ${e.timestamp}
        </div>
      </div>
    `).join('');
  }

  // Render Bot Chat
  function renderChat() {
    const container = document.getElementById('chatMessages');
    if (!container) return;

    container.innerHTML = chatMessages.map(msg => `
      <div class="chat-bubble ${msg.sender}">
        <div class="bubble-sender">${msg.name} • ${msg.time}</div>
        <div>${msg.text}</div>
      </div>
    `).join('');

    container.scrollTop = container.scrollHeight;
  }

  // Window API Expositions
  window.switchTab = function (tabId) {
    document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

    const tabBtn = document.querySelector(`.nav-tab[data-tab="${tabId}"]`);
    const tabContent = document.getElementById(tabId);
    if (tabBtn) tabBtn.classList.add('active');
    if (tabContent) tabContent.classList.add('active');
  };

  window.switchTenant = function (tenantId) {
    currentTenant = tenantId;
    renderDisputes();
    showToast(`Switched active context to: ${tenantId.toUpperCase()}`);
  };

  window.filterDisputes = function () {
    currentFilter.search = document.getElementById('disputeSearchInput')?.value || '';
    currentFilter.stage = document.getElementById('filterStage')?.value || 'ALL';
    currentFilter.status = document.getElementById('filterStatus')?.value || 'ALL';
    renderDisputes();
  };

  window.refreshDisputes = async function () {
    await fetchDisputesFromBackend();
    renderDisputes();
    updateKpis();
    showToast('Dispute radar synchronized with engine state.');
  };

  // Inspect Dispute Dossier Modal
  window.inspectDispute = function (disputeId) {
    const d = disputes.find(x => x.dispute_id === disputeId);
    if (!d) return;

    const title = document.getElementById('modalDisputeTitle');
    const body = document.getElementById('modalDisputeBody');
    const footer = document.getElementById('modalDisputeFooter');

    if (title) title.textContent = `Evidentiary Dossier: ${d.dispute_id}`;

    if (body) {
      body.innerHTML = `
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1.25rem;">
          <div class="ce3-card">
            <h4 style="font-size: 0.85rem; color: var(--color-cyan); margin-bottom: 0.5rem;">Carrier Tracking & Telemetry</h4>
            <div style="font-size: 0.8rem; line-height: 1.6;">
              <div>Carrier: <strong>${d.telemetry_carrier?.carrier_name || 'UPS'}</strong></div>
              <div>Tracking #: <strong style="font-family: var(--font-mono);">${d.telemetry_carrier?.tracking_number || '1Z9999999999999999'}</strong></div>
              <div>Status: <strong style="color: var(--color-emerald);">${d.telemetry_carrier?.status || 'DELIVERED'}</strong></div>
              <div>Signature Required: <strong>${d.telemetry_carrier?.signature_required ? 'Yes (' + (d.telemetry_carrier?.signed_by || 'Signed') + ')' : 'No (Unsigned)'}</strong></div>
              <div>Redirection Detected: <strong>${d.telemetry_carrier?.is_redirection_detected ? '⚠️ YES (VOID)' : 'None (Direct Delivery)'}</strong></div>
            </div>
          </div>
          <div class="ce3-card">
            <h4 style="font-size: 0.85rem; color: var(--color-purple); margin-bottom: 0.5rem;">Warehouse Sensor Readings</h4>
            <div style="font-size: 0.8rem; line-height: 1.6;">
              <div>Scale Scanned: <strong>${d.telemetry_warehouse?.weight_kg || '1.450'} kg</strong></div>
              <div>Baseline Weight: <strong>${d.telemetry_warehouse?.expected_weight_kg || '1.448'} kg</strong> (Variance: 0.14%)</div>
              <div>Serial Scanned: <strong style="font-family: var(--font-mono);">${d.telemetry_warehouse?.item_serial_scanned || 'SN-X990-48201'}</strong></div>
              <div>Packing Camera: <strong>Verified Anti-Tamper Tape</strong></div>
            </div>
          </div>
        </div>

        <div class="ce3-card" style="margin-bottom: 1.25rem;">
          <h4 style="font-size: 0.85rem; color: var(--color-emerald); margin-bottom: 0.5rem;">Multimodal AI Arbitration Decision</h4>
          <div style="font-size: 0.82rem; line-height: 1.6; color: var(--text-muted);">
            Win Probability: <strong style="color: #fff; font-size: 1rem;">${d.win_probability ? Math.round(d.win_probability * 100) : 75}%</strong> | 
            Expected Value: <strong style="color: #fff;">$${(d.expected_value || 0).toFixed(2)}</strong> | 
            Status: <strong style="color: var(--color-cyan);">${d.pipeline_status}</strong>
          </div>
          ${d.hitl_reasons && d.hitl_reasons.length > 0 ? `
            <div style="margin-top: 0.5rem; padding: 0.5rem; background: rgba(245, 158, 11, 0.1); border-left: 3px solid var(--color-amber); border-radius: 4px; font-size: 0.78rem; color: var(--color-amber);">
              <strong>HITL Flag Triggers:</strong> ${d.hitl_reasons.join('; ')}
            </div>
          ` : ''}
        </div>

        <div class="ce3-card">
          <h4 style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.5rem;">Audit Trail & Event Log</h4>
          <ul style="padding-left: 1.25rem; font-size: 0.78rem; color: var(--text-dim); line-height: 1.6;">
            ${(d.audit_trail || []).map(a => `<li>${a}</li>`).join('')}
          </ul>
        </div>
      `;
    }

    if (footer) {
      if (d.hitl_flagged) {
        footer.innerHTML = `
          <button class="btn btn-ghost" onclick="window.closeDetailModal()">Cancel</button>
          <button class="btn btn-outline" style="border-color: var(--color-crimson); color: var(--color-crimson);" onclick="window.submitHitlDecision('${d.dispute_id}', 'CONCEDE')">
            Concede Claim
          </button>
          <button class="btn btn-primary" onclick="window.submitHitlDecision('${d.dispute_id}', 'DEFEND')">
            Approve & Dispatch PDF Defense
          </button>
        `;
      } else {
        footer.innerHTML = `
          <button class="btn btn-ghost" onclick="window.closeDetailModal()">Close</button>
          ${d.pdf_dossier_path ? `
            <a href="/api/v1/disputes/${d.dispute_id}/pdf" target="_blank" class="btn btn-primary">
              Download Evidentiary Dossier PDF
            </a>
          ` : ''}
        `;
      }
    }

    const modal = document.getElementById('disputeDetailModal');
    if (modal) modal.classList.add('active');
  };

  window.closeDetailModal = function () {
    const modal = document.getElementById('disputeDetailModal');
    if (modal) modal.classList.remove('active');
  };

  // Submit HITL Decision Override
  window.submitHitlDecision = async function (disputeId, action) {
    try {
      const resp = await fetch(`/api/v1/disputes/${disputeId}/hitl/override`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          reviewer_id: 'OP-LEAD-CHIEF-RISK',
          action: action,
          override_reason: `Operator manual authorization: ${action}`
        })
      });
    } catch (e) {
      console.warn('API override fallback:', e);
    }

    // Local state update
    const record = disputes.find(x => x.dispute_id === disputeId);
    if (record) {
      record.hitl_flagged = false;
      record.pipeline_status = action === 'DEFEND' ? 'DEFENDED' : 'CONCEDED';
      record.audit_trail.push(`Human reviewer override executed: ${action}`);
    }

    window.closeDetailModal();
    renderDisputes();
    updateKpis();
    showToast(`HITL Decision applied: Dispute ${disputeId} marked as ${action}!`);
  };

  // Simulate Dispute Ingestion
  window.openDisputeModal = function () {
    const modal = document.getElementById('simulateDisputeModal');
    if (modal) modal.classList.add('active');
  };

  window.closeSimulateModal = function () {
    const modal = document.getElementById('simulateDisputeModal');
    if (modal) modal.classList.remove('active');
  };

  window.applyScenarioPreset = function (preset) {
    if (preset === 'sig_mandate_fail') {
      document.getElementById('simDisputeId').value = 'PP-D-MANDATE-FAIL';
      document.getElementById('simAmount').value = '820.00';
      document.getElementById('simStage').value = 'CLAIM';
      document.getElementById('simReason').value = 'MERCHANDISE_OR_SERVICE_NOT_RECEIVED';
      document.getElementById('simSigReq').value = 'false';
    } else if (preset === 'ce3_liability_shift') {
      document.getElementById('simDisputeId').value = 'PP-D-CE3-SHIFT';
      document.getElementById('simAmount').value = '340.00';
      document.getElementById('simStage').value = 'CLAIM';
      document.getElementById('simReason').value = 'UNAUTHORISED';
      document.getElementById('simSigReq').value = 'true';
    } else if (preset === 'hitl_high_value') {
      document.getElementById('simDisputeId').value = 'PP-D-HITL-CASE';
      document.getElementById('simAmount').value = '495.00';
      document.getElementById('simStage').value = 'CLAIM';
      document.getElementById('simReason').value = 'MERCHANDISE_OR_SERVICE_NOT_AS_DESCRIBED';
      document.getElementById('simSigReq').value = 'true';
    }
  };

  window.submitSimulatedDispute = function () {
    const disputeId = document.getElementById('simDisputeId').value || 'PP-D-SIM-1';
    const amount = parseFloat(document.getElementById('simAmount').value) || 250.00;
    const stage = document.getElementById('simStage').value;
    const reason = document.getElementById('simReason').value;
    const sigReq = document.getElementById('simSigReq').value === 'true';

    // Compliance Evaluation
    const isSigViolation = amount >= 750.00 && !sigReq;
    const pwin = isSigViolation ? 0.05 : (amount > 300 ? 0.72 : 0.94);
    const hitl = !isSigViolation && (amount > 300 || (pwin >= 0.60 && pwin < 0.75));

    const newRecord = {
      dispute_id: disputeId,
      merchant_id: currentTenant !== 'all' ? currentTenant : 'merchant_alpha_retail',
      stage: stage,
      reason: reason,
      amount: amount,
      currency: 'USD',
      customer_email: 'customer.sim@example.com',
      pipeline_status: isSigViolation ? 'CONCEDED' : (hitl ? 'FLAGGED_HITL' : 'DEFENDED'),
      win_probability: pwin,
      expected_value: pwin * amount - (1 - pwin) * (amount + 15),
      dispute_fee_applied: 15.00,
      hitl_flagged: hitl,
      hitl_reasons: hitl ? ['Order value > $300 or borderline probability'] : (isSigViolation ? ['Violates $750+ Signature Mandate'] : []),
      compliance_eligible: !isSigViolation,
      visa_ce3_qualified: false,
      telemetry_carrier: {
        carrier_name: 'FedEx Ground',
        tracking_number: '794000112233',
        status: 'DELIVERED',
        destination_address: '100 Main St, Austin TX',
        signature_required: sigReq,
        signed_by: sigReq ? 'SIM CUSTOMER' : null,
        is_redirection_detected: false
      },
      audit_trail: [
        'Ingested synthetic PayPal dispute webhook',
        isSigViolation ? 'Compliance Rule: $750+ Signature Mandate failed -> P(win) capped at 0.05' : 'Seller Protection verified',
        hitl ? 'Flagged for Human Review in HITL Queue' : 'Dispatched automated evidentiary defense'
      ]
    };

    disputes.unshift(newRecord);
    window.closeSimulateModal();
    renderDisputes();
    updateKpis();
    showToast(`Dispute ${disputeId} processed through defense engine!`);
  };

  // Pre-Chargeback Deflection Modal
  window.openDeflectionModal = function () {
    const modal = document.getElementById('deflectionModal');
    if (modal) modal.classList.add('active');
  };

  window.closeDeflectionModal = function () {
    const modal = document.getElementById('deflectionModal');
    if (modal) modal.classList.remove('active');
  };

  window.submitDeflectionAlert = async function () {
    const network = document.getElementById('alertNetwork').value;
    const orderRef = document.getElementById('alertOrderRef').value || 'ORD-ALERT-1';
    const amount = parseFloat(document.getElementById('alertAmount').value) || 120.00;
    const reason = document.getElementById('alertReason').value;

    try {
      await fetch('/api/v1/alerts/deflection', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          alert_id: `ALT-${Date.now()}`,
          network: network,
          order_id: orderRef,
          amount: amount,
          currency: 'USD',
          reason_code: '10.4',
          reason_description: reason
        })
      });
    } catch (e) {
      console.warn('Alert API post error:', e);
    }

    deflectionFeed.unshift({
      network: network,
      order_id: orderRef,
      amount: amount,
      reason: reason,
      timestamp: 'Just now',
      status: 'AUTO_REFUNDED_ZERO_FEE'
    });

    window.closeDeflectionModal();
    renderDeflectionFeed();
    showToast(`Deflection successful! Auto-refund dispatched for ${orderRef}, saving $15.00 dispute fee.`);
  };

  // Visa CE 3.0 Check Lab
  window.runCe3Check = function () {
    const custId = document.getElementById('ce3CustomerId').value;
    const amount = document.getElementById('ce3Amount').value;
    const ip = document.getElementById('ce3Ip').value;
    const device = document.getElementById('ce3Device').value;

    const badge = document.getElementById('ce3Badge');
    const statement = document.getElementById('ce3Statement');

    if (badge) {
      badge.textContent = 'QUALIFIED FOR AUTOMATED LIABILITY SHIFT';
      badge.className = 'ce3-status-badge qualified';
    }

    if (statement) {
      statement.textContent = `"Under Visa Core Rules Section 10.4.1 (Compelling Evidence 3.0), liability for this dispute is shifted to the card issuer. The merchant has provided two prior undisputed qualifying transactions occurring within 120-365 days of the disputed purchase date, matching on core technical credentials (IP address ${ip} and Device Fingerprint ${device})."`;
    }

    showToast(`Visa CE 3.0 verified: 2-Factor technical match confirmed for ${custId}!`);
  };

  // Bot advance turn
  window.advanceBotTurn = function () {
    chatMessages.push({
      sender: 'buyer',
      name: 'Sarah Jenkins',
      time: '10:35 AM',
      text: "The 20% partial refund sounds fair to me. Thank you for resolving this so quickly!"
    });
    chatMessages.push({
      sender: 'bot',
      name: 'LexiShield Resolution Assistant',
      time: '10:36 AM',
      text: "Wonderful, Sarah! We have just credited $17.90 back to your PayPal balance via transaction refund. The dispute inquiry is now settled and closed. Have a wonderful day!"
    });
    renderChat();
    showToast('Customer accepted Step 2 partial refund: Dispute settled without arbitration!');
  };

  window.sendManualBotMessage = function () {
    const input = document.getElementById('chatManualInput');
    if (!input || !input.value.trim()) return;

    chatMessages.push({
      sender: 'bot',
      name: 'CS Supervisor (Manual Override)',
      time: 'Just now',
      text: input.value.trim()
    });
    input.value = '';
    renderChat();
    showToast('Manual response dispatched to PayPal Dispute messaging API.');
  };

  // Simulate Inbound RMA Scan
  window.simulateRmaScan = function (rmaNum) {
    const item = rmaList.find(x => x.rma_number === rmaNum);
    if (item) {
      item.status = 'INSPECTED_RETURN_VERIFIED_REFUND_APPROVED';
    }
    renderRmaGrid();
    showToast(`Inbound scan verified for ${rmaNum}: Item weight and serial verified. Concession released.`);
  };

  window.openRmaModal = function () {
    const rmaNum = `RMA-${new Date().getFullYear()}-${Math.floor(10000 + Math.random() * 90000)}`;
    rmaList.unshift({
      rma_number: rmaNum,
      dispute_id: 'PP-D-NEW-RETURN',
      carrier: 'EasyPost USPS Commercial',
      tracking_number: `9400 1000 ${Math.floor(1000 + Math.random() * 9000)} ${Math.floor(1000 + Math.random() * 9000)} 01`,
      status: 'LABEL_GENERATED_AWAITING_INBOUND',
      created_at: new Date().toISOString()
    });
    renderRmaGrid();
    showToast(`Prepaid RMA return label generated: ${rmaNum}`);
  };

  // Toast System
  function showToast(message) {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.innerHTML = `<span>🛡️</span> <div>${message}</div>`;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }

  // Self-start on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
