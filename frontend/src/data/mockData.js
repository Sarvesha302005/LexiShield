/**
 * Rich seed disputes, telemetry, and buyer conversation mock data
 * used for instant interactive demonstrations, sandbox simulations, and fallback.
 */

export const INITIAL_DISPUTES = [
  {
    dispute_id: "PP-D-849201",
    buyer_email: "michael.b92@gmail.com",
    buyer_name: "Michael Barnes",
    amount: 349.99,
    currency: "USD",
    reason: "UNAUTHORIZED_TRANSACTION",
    stage: "CLAIM",
    pipeline_status: "DEFENDED",
    win_probability: 0.94,
    created_at: "2026-10-18T14:22:00Z",
    evidence_score: 96,
    fee_saved: 15.0,
    tracking_number: "1Z9999999999999999",
    carrier: "UPS Express",
    device_ip: "74.125.21.18",
    device_hash: "a9f84bc910e3d",
    buyer_sentiment: "Frustrated / Evasive",
    order_id: "SHP-99214",
    item_title: "Sony WH-1000XM5 Wireless Headphones",
    ai_summary: "Confirmed delivery to buyer billing address with GPS match (0.002 mi delta) and photo signature. Device fingerprint matched past 4 legitimate logins.",
    action_taken: "DEFEND_AUTONOMOUS"
  },
  {
    dispute_id: "PP-D-849202",
    buyer_email: "sarah.t_sf@yahoo.com",
    buyer_name: "Sarah Jenkins",
    amount: 189.50,
    currency: "USD",
    reason: "MERCHANDISE_OR_SERVICE_NOT_RECEIVED",
    stage: "INQUIRY",
    pipeline_status: "AUTO_NEGOTIATING",
    win_probability: 0.88,
    created_at: "2026-10-19T09:15:00Z",
    evidence_score: 89,
    fee_saved: 0.0,
    tracking_number: "940011189956291039",
    carrier: "USPS Priority",
    device_ip: "198.51.100.42",
    device_hash: "c318fe009941a",
    buyer_sentiment: "Confused",
    order_id: "SHP-99219",
    item_title: "Ergonomic Mechanical Keyboard (Pro RGB)",
    ai_summary: "Package scanned as 'Delivered to Front Porch' 12 hours ago. AI settlement bot offered parcel locker re-check and $20 goodwill store coupon.",
    action_taken: "BOT_CONVERSATION"
  },
  {
    dispute_id: "PP-D-849203",
    buyer_email: "alex.chen.dev@gmail.com",
    buyer_name: "Alex Chen",
    amount: 620.00,
    currency: "USD",
    reason: "MERCHANDISE_OR_SERVICE_NOT_AS_DESCRIBED",
    stage: "CLAIM",
    pipeline_status: "FLAGGED_HITL",
    win_probability: 0.65,
    created_at: "2026-10-17T18:40:00Z",
    evidence_score: 72,
    fee_saved: 0.0,
    tracking_number: "782991048192",
    carrier: "FedEx Standard",
    device_ip: "172.56.42.109",
    device_hash: "e441bcda81021",
    buyer_sentiment: "High Risk / Dispute Escalated",
    order_id: "SHP-99180",
    item_title: "Ultra-wide 4K Gaming Monitor (34-inch)",
    ai_summary: "High value order ($620). Buyer claims screen flicker; merchant policy specifies 30-day RMA return. Flagged for operational Human sign-off.",
    action_taken: "FLAG_HITL_OPERATIONS"
  },
  {
    dispute_id: "PP-D-849204",
    buyer_email: "elena.rodriguez@outlook.com",
    buyer_name: "Elena Rodriguez",
    amount: 79.99,
    currency: "USD",
    reason: "UNAUTHORIZED_TRANSACTION",
    stage: "RESOLVED",
    pipeline_status: "RESOLVED_WON",
    win_probability: 0.98,
    created_at: "2026-10-16T11:05:00Z",
    evidence_score: 99,
    fee_saved: 15.0,
    tracking_number: "1Z8888888888888888",
    carrier: "UPS Ground",
    device_ip: "66.249.79.1",
    device_hash: "f1092a830112c",
    buyer_sentiment: "Resolved",
    order_id: "SHP-99122",
    item_title: "USB-C Dual 4K Laptop Docking Station",
    ai_summary: "Dispute closed in merchant favor by PayPal. 100% evidence acceptance on IP geolocation, session cookie history, and signed delivery manifest.",
    action_taken: "WON_AUTOMATICALLY"
  },
  {
    dispute_id: "PP-D-849205",
    buyer_email: "david.miller@gmail.com",
    buyer_name: "David Miller",
    amount: 45.00,
    currency: "USD",
    reason: "DUPLICATE_TRANSACTION",
    stage: "CLAIM",
    pipeline_status: "CONCEDED",
    win_probability: 0.12,
    created_at: "2026-10-15T16:50:00Z",
    evidence_score: 25,
    fee_saved: 0.0,
    tracking_number: "9400100000000000",
    carrier: "USPS First Class",
    device_ip: "108.162.245.8",
    device_hash: "b7721a6011a78",
    buyer_sentiment: "Justified Claim",
    order_id: "SHP-99094",
    item_title: "Braided Nylon Cable Pack (5-Pack)",
    ai_summary: "Accidental double-click during checkout resulted in duplicate charge. Engine autonomously conceded and refunded to preserve merchant dispute ratio.",
    action_taken: "AUTO_CONCEDED_REFUNDED"
  }
];

export const INITIAL_CHAT_CONVERSATIONS = {
  "PP-D-849201": [
    {
      sender: "buyer",
      name: "Michael Barnes",
      time: "Yesterday, 2:22 PM",
      text: "I did not make this purchase of $349.99 on my PayPal account! Someone must have hacked into my account. I want an immediate full refund."
    },
    {
      sender: "bot",
      name: "LexiShield AI Assistant",
      time: "Yesterday, 2:23 PM",
      text: "Hello Michael, thank you for reaching out. We take security very seriously. We verified that this order was placed using your primary residential IP (74.125.21.18) and delivered to your verified PayPal address on file with signed UPS confirmation. Could another member of your household have ordered this?"
    },
    {
      sender: "buyer",
      name: "Michael Barnes",
      time: "Yesterday, 3:10 PM",
      text: "Wait... let me check with my son. He mentioned needing new headphones for college."
    },
    {
      sender: "bot",
      name: "LexiShield AI Assistant",
      time: "Yesterday, 3:11 PM",
      text: "Thank you for checking! If the order was made by someone in your household, please consider closing the PayPal dispute to avoid unnecessary account holds. If you still need to return the unopened package, our 30-day pre-paid return label is ready for you."
    }
  ],
  "PP-D-849202": [
    {
      sender: "buyer",
      name: "Sarah Jenkins",
      time: "Today, 9:15 AM",
      text: "Tracking shows delivered yesterday, but I looked on my porch and there was no package anywhere. Please reship or refund!"
    },
    {
      sender: "bot",
      name: "LexiShield AI Assistant",
      time: "Today, 9:16 AM",
      text: "Hi Sarah! We reviewed the USPS carrier telemetry for tracking 940011189956291039. The scan timestamp was at 4:32 PM yesterday at mailbox/parcel locker #14. Have you had a chance to check the secure apartment parcel locker?"
    },
    {
      sender: "buyer",
      name: "Sarah Jenkins",
      time: "Today, 9:45 AM",
      text: "Oh! I didn't see the USPS parcel locker notification slip in my mailbox. I'll go check downstairs right now."
    }
  ],
  "PP-D-849203": [
    {
      sender: "buyer",
      name: "Alex Chen",
      time: "Oct 17, 6:40 PM",
      text: "The 34-inch monitor has slight flickering when using HDMI at 144Hz. This is not what I expected for a $620 screen."
    },
    {
      sender: "bot",
      name: "LexiShield AI Assistant",
      time: "Oct 17, 6:42 PM",
      text: "Hello Alex, we apologize for the display experience. High refresh 4K rates often require DisplayPort 1.4 or certified HDMI 2.1 cables. We can dispatch a complimentary certified braided DisplayPort cable immediately, or provide an RMA return label for a brand-new replacement."
    }
  ]
};

export const INITIAL_MERCHANT_PROFILE = {
  merchant_id: "merch_apex_us_01",
  business_name: "Apex Electronics Store (US)",
  paypal_account: "merchant-sandbox-apex@lexishield.io",
  shopify_domain: "apex-electronics.myshopify.com",
  paypal_mode: "SANDBOX_REST_V2",
  auto_defense_enabled: true,
  risk_threshold: 0.75,
  chargeback_ratio: 0.42,
  chargeback_ratio_target: 1.00,
  dispute_fees_saved: 2840.00,
  total_defended_count: 142,
  win_rate: 92.4,
  protected_volume: 48250.00
};
