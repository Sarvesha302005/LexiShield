/**
 * Rich seed disputes, telemetry, and buyer conversation mock data
 * used for instant interactive demonstrations, sandbox simulations, and fallback.
 * Strictly mirrors the 6 canonical persistent demo disputes in lexishield.db.
 */

export const INITIAL_DISPUTES = [
  {
    dispute_id: "PP-D-99412",
    buyer_email: "elena.rostova@example.com",
    buyer_name: "Elena Rostova",
    amount: 349.00,
    currency: "USD",
    reason: "MERCHANDISE_OR_SERVICE_NOT_AS_DESCRIBED",
    stage: "CLAIM",
    pipeline_status: "DEFENDED",
    win_probability: 0.92,
    created_at: "2026-10-15T14:30:00Z",
    evidence_score: 92,
    fee_saved: 15.0,
    tracking_number: "UPS-1Z99999903",
    carrier: "UPS Ground",
    device_ip: "198.51.100.82",
    device_hash: "a9f84bc910e3d",
    buyer_sentiment: "Defect Alleged / Under Review",
    order_id: "ORD-ZAP-99412",
    item_title: "Shure SM7B Vocal Dynamic Studio Microphone",
    ai_summary: "Outbound calibrated scale weight matched catalog tare weight (0.0% variance). Hardware serial SN-SHURE-SM7B-4412 logged and verified. Pre-paid RMA label required before refund.",
    specialist_agent: "SNADAgent",
    action_taken: "PROVIDE_EVIDENCE"
  },
  {
    dispute_id: "PP-D-77194",
    buyer_email: "samantha.cole@outlook.com",
    buyer_name: "Samantha Cole",
    amount: 299.99,
    currency: "USD",
    reason: "UNAUTHORISED",
    stage: "CLAIM",
    pipeline_status: "DEFENDED",
    win_probability: 0.98,
    created_at: "2026-10-10T16:00:00Z",
    evidence_score: 98,
    fee_saved: 15.0,
    tracking_number: "FDX-771940022",
    carrier: "FedEx Home Delivery",
    device_ip: "198.51.100.42",
    device_hash: "c318fe009941a",
    buyer_sentiment: "First-Party Misuse / Friendly Fraud",
    order_id: "ORD-ZAP-77194",
    item_title: "Sony WH-1000XM5 Wireless Headphones",
    ai_summary: "Visa Compelling Evidence 3.0 (CE 3.0) liability shift qualified: 2 prior undisputed orders (>120d old) matching IP, device fingerprint, and confirmed shipping address.",
    specialist_agent: "FraudAgent",
    action_taken: "PROVIDE_EVIDENCE"
  },
  {
    dispute_id: "PP-D-55210",
    buyer_email: "sophia.chen@enterprise.io",
    buyer_name: "Sophia Chen",
    amount: 79.00,
    currency: "USD",
    reason: "CANCELED_RECURRING_BILLING",
    stage: "INQUIRY",
    pipeline_status: "DE_ESCALATED",
    win_probability: 0.95,
    created_at: "2026-10-01T09:00:00Z",
    evidence_score: 95,
    fee_saved: 15.0,
    tracking_number: "DIGITAL-LIC-55210",
    carrier: "Digital Fulfillment",
    device_ip: "24.130.88.12",
    device_hash: "e441bcda81021",
    buyer_sentiment: "De-escalated / Subscription Active",
    order_id: "ORD-ZAP-55210",
    item_title: "LexiShield Security Suite (1-Seat Pro Annual)",
    ai_summary: "Customer assented to recurring Terms of Service at checkout. Active server sessions and telemetry recorded post-renewal. Concierge offered billing pause or tier adjustments.",
    specialist_agent: "BillingAgent",
    action_taken: "SEND_MESSAGE"
  },
  {
    dispute_id: "PP-D-44102",
    buyer_email: "liam.smith@example.com",
    buyer_name: "Liam Smith",
    amount: 35.00,
    currency: "USD",
    reason: "CREDIT_NOT_PROCESSED",
    stage: "CLAIM",
    pipeline_status: "CONCEDED",
    win_probability: 0.15,
    created_at: "2026-10-12T11:20:00Z",
    evidence_score: 15,
    fee_saved: 0.0,
    tracking_number: "USPS-9400100044102",
    carrier: "USPS Ground Advantage",
    device_ip: "108.162.245.8",
    device_hash: "b7721a6011a78",
    buyer_sentiment: "Billing Adjustment Accepted",
    order_id: "ORD-ZAP-44102",
    item_title: "High-Speed USB-C to Lightning Braided Cable",
    ai_summary: "Billing credit discrepancy verified from customer support ticket logs. Autonomous concession executed early to avoid non-refundable dispute penalty fee.",
    specialist_agent: "BillingAgent",
    action_taken: "ACCEPT_CLAIM"
  },
  {
    dispute_id: "PP-D-66305",
    buyer_email: "jordan.lee@techcorp.io",
    buyer_name: "Jordan Lee",
    amount: 849.00,
    currency: "USD",
    reason: "MERCHANDISE_OR_SERVICE_NOT_RECEIVED",
    stage: "CLAIM",
    pipeline_status: "FLAGGED_HITL",
    win_probability: 0.88,
    created_at: "2026-10-18T09:45:00Z",
    evidence_score: 88,
    fee_saved: 0.0,
    tracking_number: "FDX-998822011",
    carrier: "FedEx Priority",
    device_ip: "66.249.79.1",
    device_hash: "f1092a830112c",
    buyer_sentiment: "Awaiting Human Sign-off",
    order_id: "ORD-ZAP-66305",
    item_title: "ASUS ROG Swift 34\" Ultrawide Gaming Monitor",
    ai_summary: "High order value ($849.00 > $300.00 threshold). Delivery confirmed with recipient signature 'J. LEE' under PayPal §11. Held for Human-in-the-Loop review before dispatch.",
    specialist_agent: "INRAgent",
    hitl_reasons: ["High order value ($849.00 > $300.00).", "Mandatory signature verification met."],
    action_taken: "FLAG_FOR_HITL"
  },
  {
    dispute_id: "PP-D-88201",
    buyer_email: "marcus.vance@gmail.com",
    buyer_name: "Marcus Vance",
    amount: 249.99,
    currency: "USD",
    reason: "MERCHANDISE_OR_SERVICE_NOT_RECEIVED",
    stage: "INQUIRY",
    pipeline_status: "DE_ESCALATED",
    win_probability: 0.94,
    created_at: "2026-10-20T11:20:00Z",
    evidence_score: 94,
    fee_saved: 15.0,
    tracking_number: "1Z9999999999999999",
    carrier: "UPS Next Day Air",
    device_ip: "74.125.21.18",
    device_hash: "d8819ab0012e8",
    buyer_sentiment: "Delivery Verified / Informational",
    order_id: "ORD-ZAP-10294",
    item_title: "Bose QuietComfort 45 Noise Cancelling Headphones",
    ai_summary: "Carrier verified delivery at confirmed address with courier drop-off GPS (34.0983, -118.3267) and signed recipient proof 'M. VANCE'. Concierge provided delivery assistance.",
    specialist_agent: "INRAgent",
    action_taken: "SEND_MESSAGE"
  }
];

export const INITIAL_CHAT_CONVERSATIONS = {
  "PP-D-88201": [
    {
      sender: "buyer",
      name: "Marcus Vance",
      time: "Yesterday, 11:20 AM",
      text: "Tracking shows delivered yesterday, but I looked on my porch and there was no package anywhere. Please reship or refund!"
    },
    {
      sender: "bot",
      name: "LexiShield AI Assistant",
      time: "Yesterday, 11:21 AM",
      text: "Hi Marcus! We reviewed the UPS Next Day Air tracking 1Z9999999999999999. The package was delivered with signature 'M. VANCE' and GPS coordinates confirmed at your address. Could you check around your side porch or with neighbors?"
    },
    {
      sender: "buyer",
      name: "Marcus Vance",
      time: "Yesterday, 11:45 AM",
      text: "Oh! My neighbor picked it up to keep it out of the rain. I have the box now. Thank you for the quick verification!"
    }
  ],
  "PP-D-99412": [
    {
      sender: "buyer",
      name: "Elena Rostova",
      time: "Oct 15, 2:30 PM",
      text: "The microphone arrived but I think an accessory is missing or it's defective."
    },
    {
      sender: "bot",
      name: "LexiShield AI Assistant",
      time: "Oct 15, 2:32 PM",
      text: "Hello Elena, our automated packing station recorded an exact catalog tare weight match (0.0% delta) with unbroken tamper seal SEAL-ZAP-8821. If you would like to return it for a replacement, we have issued a pre-paid RMA return shipping label."
    }
  ],
  "PP-D-77194": [
    {
      sender: "buyer",
      name: "Samantha Cole",
      time: "Oct 10, 4:00 PM",
      text: "I do not recognize this charge of $299.99 on my card!"
    },
    {
      sender: "bot",
      name: "LexiShield AI Assistant",
      time: "Oct 10, 4:02 PM",
      text: "Hello Samantha, this order was placed from your verified home IP address and delivered to your confirmed billing address where 2 previous undisputed orders were shipped. Could a household member have made the purchase?"
    }
  ],
  "PP-D-55210": [
    {
      sender: "buyer",
      name: "Sophia Chen",
      time: "Oct 01, 9:00 AM",
      text: "I was charged $79.00 for annual renewal but I wanted to review my plan first."
    },
    {
      sender: "bot",
      name: "LexiShield AI Assistant",
      time: "Oct 01, 9:02 AM",
      text: "Hello Sophia! We can certainly help you review your subscription tier or apply a credit toward your renewal."
    }
  ]
};

export const INITIAL_MERCHANT_PROFILE = {
  merchant_id: "merch_apex_us_01",
  business_name: "Apex Electronics Store (US)",
  paypal_account: "payments@apex-electronics.com",
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
