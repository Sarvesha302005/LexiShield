/**
 * Shared dispute helpers: maps backend DisputeRecords into the shape the UI uses,
 * turns status/reason codes into plain-English labels, and applies review decisions.
 */

// "jordan.lee@techcorp.io" -> "Jordan Lee", for records that carry an email but no customer name.
const nameFromEmail = (email) =>
  email
    ?.split('@')[0]
    .split(/[._-]+/)
    .filter((part) => /^[a-z]+$/i.test(part))
    .map((part) => part[0].toUpperCase() + part.slice(1).toLowerCase())
    .join(' ') || null;

// Maps a backend DisputeRecord into the UI's dispute shape.
// `fallbacks` fills fields the backend may not know (e.g. what the user typed in the simulate form).
export function mapApiDispute(item, fallbacks = {}) {
  const order = item.telemetry_order || {};
  const carrier = item.telemetry_carrier || {};
  const firstLineItem = Array.isArray(order.line_items) && order.line_items[0];
  return {
    dispute_id: item.dispute_id,
    is_live: true, // exists in the backend, so review decisions go through the API
    buyer_email: item.customer_email || order.customer_email || fallbacks.buyer_email || 'customer@lexishield.io',
    buyer_name:
      order.customer_name || fallbacks.buyer_name || nameFromEmail(item.customer_email || order.customer_email) || 'Verified Buyer',
    amount: item.amount ?? 199.99,
    currency: item.currency || 'USD',
    reason: item.reason || item.dispute_reason || 'UNAUTHORISED',
    stage: item.stage || item.dispute_stage || 'CLAIM',
    pipeline_status: item.pipeline_status || 'DEFENDED',
    win_probability: item.win_probability ?? 0.92,
    created_at: item.created_at || new Date().toISOString(),
    evidence_score: Math.round((item.win_probability ?? 0.92) * 100),
    fee_saved: item.dispute_fee_applied || 15.0,
    tracking_number: carrier.tracking_number || '1Z9999999999999999',
    carrier: carrier.carrier_name || 'UPS',
    device_ip: order.checkout_ip || '198.51.100.42',
    device_hash: order.device_fingerprint || 'DEV-FINGERPRINT-LEXI',
    buyer_sentiment: item.hitl_flagged ? 'HITL Review' : 'Active Case',
    order_id: item.order_id || order.order_id || 'SHP-LIVE',
    item_title: firstLineItem?.name || fallbacks.item_title || 'Commercial Electronics',
    ai_summary: item.rebuttal_statement || 'Synthesized evidence rebuttal.',
    action_taken: item.action_taken || 'DEFEND',
    hitl_reasons: item.hitl_reasons || [],
    pdf_dossier_sha256: item.pdf_dossier_sha256 || null,
    specialist_agent: item.specialist_agent || null,
    persona_mode: item.persona_mode || null,
    llm_tier_used: item.llm_tier_used || null,
    reasoning_steps: item.reasoning_steps || [],
    rma_number: item.rma_number || null,
  };
}

// tone: which badge colour to use (see .status-* in index.css)
const STATUS = {
  PENDING: { label: 'Pending', tone: 'neutral' },
  ANALYZING: { label: 'Analyzing', tone: 'info' },
  AUTO_NEGOTIATING: { label: 'Talking to buyer', tone: 'info' },
  FLAGGED_HITL: { label: 'Needs review', tone: 'warning' },
  DEFENDED: { label: 'Evidence submitted', tone: 'info' },
  OVERRIDDEN: { label: 'Reviewed', tone: 'neutral' },
  DE_ESCALATED: { label: 'Resolved with buyer', tone: 'success' },
  RESOLVED_WON: { label: 'Won', tone: 'success' },
  RESOLVED: { label: 'Closed', tone: 'neutral' },
  CONCEDED: { label: 'Refunded', tone: 'neutral' },
  FAILED: { label: 'Failed', tone: 'danger' },
};

const REASONS = {
  UNAUTHORISED: 'Unauthorized purchase',
  UNAUTHORIZED_TRANSACTION: 'Unauthorized purchase',
  MERCHANDISE_OR_SERVICE_NOT_RECEIVED: 'Item not received',
  MERCHANDISE_OR_SERVICE_NOT_AS_DESCRIBED: 'Not as described',
  INCORRECT_AMOUNT: 'Incorrect amount',
  DUPLICATE_TRANSACTION: 'Duplicate charge',
  CANCELED_RECURRING_BILLING: 'Canceled subscription',
  OTHER: 'Other',
};

const STAGES = { INQUIRY: 'Inquiry', CLAIM: 'Claim', CHARGEBACK: 'Chargeback', RESOLVED: 'Resolved' };

const toTitle = (code = '') =>
  code.toLowerCase().replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase());

export const statusInfo = (code) => STATUS[code] || { label: toTitle(code), tone: 'neutral' };
export const reasonLabel = (code) => REASONS[code] || toTitle(code);
export const stageLabel = (code) => STAGES[code] || toTitle(code);

// Why a dispute was held for review. Backend reasons look like "ORDER_VALUE_EXCEEDS_THRESHOLD ($849.00 > $300.00)".
const REVIEW_REASONS = {
  ORDER_VALUE_EXCEEDS_THRESHOLD: (detail) => {
    const limit = detail?.match(/>\s*(\$[\d,.]+)/)?.[1];
    return limit ? `Order is above your ${limit} review limit` : 'Order is above your review limit';
  },
  MANDATORY_SIGNATURE_VERIFICATION: () => 'Signature confirmation required',
};

export const reviewReasonLabel = (raw) => {
  const [, code, detail] = raw.match(/^([A-Z0-9_]+)\s*(.*)$/) || [];
  if (code && REVIEW_REASONS[code]) return REVIEW_REASONS[code](detail);
  return code ? toTitle(code) + (detail ? ` ${detail}` : '') : raw;
};

const CLOSED_STATUSES =new Set(['RESOLVED_WON', 'RESOLVED', 'CONCEDED', 'DE_ESCALATED']);
export const isOpen = (dispute) => !CLOSED_STATUSES.has(dispute.pipeline_status);
export const needsReview = (dispute) => dispute.pipeline_status === 'FLAGGED_HITL';
export const isWon = (dispute) => ['RESOLVED_WON', 'DE_ESCALATED'].includes(dispute.pipeline_status);

export const formatMoney = (amount, currency = 'USD') =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency }).format(amount);

export const formatDate = (iso) =>
  new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

// Review decisions offered in the "Needs your attention" panel, mapped to the backend's override actions.
export const REVIEW_ACTIONS = {
  DEFEND: { label: 'Approve evidence', status: 'DEFENDED' },
  MAKE_OFFER: { label: 'Offer 50% refund', status: 'DE_ESCALATED' },
  CONCEDE: { label: 'Accept claim', status: 'CONCEDED' },
};

/**
 * Applies a review decision. Live disputes go through POST /disputes/{id}/hitl/override and
 * return the updated record; demo disputes only exist in the browser, so they're updated locally.
 * Returns the fields to merge into the dispute.
 */
export async function submitReviewDecision(dispute, action, reviewerId) {
  if (!dispute.is_live) {
    return { pipeline_status: REVIEW_ACTIONS[action].status, action_taken: `HUMAN_OVERRIDE_${action}` };
  }
  const res = await fetch(`/api/v1/disputes/${encodeURIComponent(dispute.dispute_id)}/hitl/override`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      reviewer_id: reviewerId,
      action,
      override_reason: `${REVIEW_ACTIONS[action].label} from the LexiShield dashboard review queue.`,
    }),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail || `Request failed (${res.status})`);
  }
  const record = await res.json();
  const updated = mapApiDispute(record, dispute);
  // Keep what the backend doesn't return (buyer name, item) from the existing row.
  return {
    pipeline_status: updated.pipeline_status,
    action_taken: updated.action_taken,
    pdf_dossier_sha256: updated.pdf_dossier_sha256 || dispute.pdf_dossier_sha256,
  };
}
