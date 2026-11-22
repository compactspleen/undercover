/** The backend's API, as the dashboard reads it. Amounts are US dollars. */

export type ClaimStatus =
  "waiting" | "in_progress" | "waiting_for_sign_off" | "decided";

export interface ClaimSummary {
  claim_id: string;
  claim_type: string;
  summary: string;
  amount_claimed: number;
  status: ClaimStatus;
  decision: Decision | null;
}

export interface QueuedClaim extends ClaimSummary {
  customer_name: string;
}

export interface Item {
  description: string;
  category: string;
  amount: number;
}

export interface ClaimDocument {
  name: string;
  type: string;
  content: string;
}

export interface Approval {
  decision: "approve";
  payout: number;
  explanation: string;
  policy_section: string;
}

export interface Rejection {
  decision: "decline" | "refer";
  explanation: string;
  policy_section: string;
}

export type Decision = Approval | Rejection;

export interface Payment {
  amount: number;
  paid_at: string;
}

export interface SignOff {
  handler_id: string;
  handler_name: string;
  signed_off_at: string;
}

export type StepKind = "tool_call" | "tool_result" | "reply";

export interface Step {
  kind: StepKind;
  text: string;
  recorded_at: string;
}

export interface Claim extends ClaimSummary {
  policy_id: string;
  customer_id: string;
  submitted_on: string;
  incident_date: string;
  incident_location: string;
  story: string;
  items: Item[];
  documents: ClaimDocument[];
  payment: Payment | null;
  sign_off: SignOff | null;
  steps: Step[];
}

export interface Plan {
  plan: string;
  name: string;
  trip_cancellation_max: number;
  trip_delay_waiting_hours: number;
  trip_delay_max: number;
  baggage_delay_waiting_hours: number;
  baggage_delay_max: number;
  baggage_max: number;
  per_item_limit: number;
  passport_max: number;
  emergency_medical_max: number;
  deductible: number;
}

export interface AddOn {
  add_on: string;
  name: string;
  effect: string;
  electronics_per_item_limit: number | null;
}

export interface Trip {
  destination: string;
  departs_on: string;
  returns_on: string;
  trip_cost: number;
}

export interface Policy {
  policy_id: string;
  customer_id: string;
  plan: Plan;
  add_ons: AddOn[];
  deductible_applies_to: string[];
  purchased_on: string;
  sold_through: string;
  trip: Trip;
  travelers: string[];
  status: string;
}

export interface Handler {
  handler_id: string;
  name: string;
  role: string;
}

/** Read JSON from the backend. Its shape is the backend's, typed above. */
export async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(path);
  if (!response.ok) throw new Error(await reasonFor(response));
  return (await response.json()) as T;
}

export async function getText(path: string): Promise<string> {
  const response = await fetch(path);
  if (!response.ok) throw new Error(await reasonFor(response));
  return response.text();
}

export async function post(path: string, body: object): Promise<void> {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(await reasonFor(response));
}

/** The message of an error, such as the backend's reason for refusing. */
export function reasonOf(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

/** The backend's reason for refusing, or its status if it gave none. */
async function reasonFor(response: Response): Promise<string> {
  const body: unknown = await response.json().catch(() => null);
  if (
    typeof body === "object" &&
    body !== null &&
    "detail" in body &&
    typeof body.detail === "string"
  ) {
    return body.detail;
  }
  return `The backend answered ${String(response.status)}`;
}
