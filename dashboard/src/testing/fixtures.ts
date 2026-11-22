import type {
  Approval,
  Claim,
  ClaimStatus,
  Handler,
  Policy,
  QueuedClaim,
} from "../api";

const STATUSES: ClaimStatus[] = [
  "waiting",
  "waiting",
  "in_progress",
  "waiting_for_sign_off",
  "decided",
];

export const QUEUE: QueuedClaim[] = Array.from({ length: 25 }, (_, index) => ({
  claim_id: `CLM-${String(1001 + index)}`,
  customer_name: index === 0 ? "Maya Patel" : `Customer ${String(index)}`,
  claim_type: index === 0 ? "trip_delay" : "baggage",
  summary:
    index === 0 ? "Flight home canceled" : `Claim number ${String(index)}`,
  amount_claimed: index === 0 ? 420 : 1250,
  status: STATUSES[index % STATUSES.length] ?? "waiting",
  decision: null,
}));

export const CLAIM: Claim = {
  claim_id: "CLM-1001",
  policy_id: "POL-2001",
  customer_id: "CUS-3001",
  claim_type: "trip_delay",
  submitted_on: "2026-06-24",
  incident_date: "2026-06-18",
  incident_location: "Rome, Italy",
  summary: "Flight home canceled by the airline, rebooked the next morning",
  story: "My flight home from Rome on June 18 was canceled by Meridian Air.",
  items: [
    {
      description: "Airport hotel, one night",
      category: "accommodation",
      amount: 245,
    },
    { description: "Dinner and breakfast", category: "meals", amount: 95 },
  ],
  amount_claimed: 420,
  documents: [
    {
      name: "Hotel receipt",
      type: "receipt",
      content: "Hotel Aurelia Fiumicino. Total paid: $245.00.",
    },
  ],
  status: "waiting",
  decision: null,
  payment: null,
  sign_off: null,
  steps: [],
};

export const APPROVAL: Approval = {
  decision: "approve",
  payout: 420,
  explanation: "Your flight was canceled, so we cover your costs.",
  policy_section: "3. Trip Delay",
};

export const POLICY: Policy = {
  policy_id: "POL-2001",
  customer_id: "CUS-3001",
  plan: {
    plan: "premium",
    name: "UnderCover Premium",
    trip_cancellation_max: 5000,
    trip_delay_waiting_hours: 6,
    trip_delay_max: 800,
    baggage_delay_waiting_hours: 12,
    baggage_delay_max: 300,
    baggage_max: 1500,
    per_item_limit: 300,
    passport_max: 250,
    emergency_medical_max: 100000,
    deductible: 50,
  },
  add_ons: [
    {
      add_on: "electronics_plus",
      name: "Electronics Plus",
      effect: "Raises the per-item limit for electronics.",
      electronics_per_item_limit: 1200,
    },
  ],
  deductible_applies_to: ["baggage", "emergency_medical"],
  purchased_on: "2026-04-22",
  sold_through: "Meridian Air checkout",
  trip: {
    destination: "Rome, Italy",
    departs_on: "2026-06-10",
    returns_on: "2026-06-18",
    trip_cost: 3100,
  },
  travelers: ["Maya Patel"],
  status: "active",
};

export const HANDLERS: Handler[] = [
  {
    handler_id: "HND-01",
    name: "Dana Whitfield",
    role: "Senior Claims Handler",
  },
  { handler_id: "HND-02", name: "Marcus Oyelaran", role: "Claims Handler" },
];
