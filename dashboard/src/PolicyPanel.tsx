import type { Plan, Policy } from "./api";
import { formatClaimType, formatDate, formatMoney } from "./format";

const PLAN_LIMITS: [string, (plan: Plan) => string][] = [
  [
    "Trip cancellation and interruption",
    (plan) => formatMoney(plan.trip_cancellation_max),
  ],
  [
    "Trip delay",
    (plan) =>
      `${formatMoney(plan.trip_delay_max)} after ${String(plan.trip_delay_waiting_hours)} hours`,
  ],
  [
    "Baggage delay",
    (plan) =>
      `${formatMoney(plan.baggage_delay_max)} after ${String(plan.baggage_delay_waiting_hours)} hours`,
  ],
  ["Baggage and personal effects", (plan) => formatMoney(plan.baggage_max)],
  ["Per-item limit", (plan) => formatMoney(plan.per_item_limit)],
  ["Passport and travel documents", (plan) => formatMoney(plan.passport_max)],
  ["Emergency medical", (plan) => formatMoney(plan.emergency_medical_max)],
  ["Deductible", (plan) => formatMoney(plan.deductible)],
];

export function PolicyPanel({ policy }: Readonly<{ policy: Policy }>) {
  return (
    <section className="panel" aria-labelledby="policy">
      <h2 id="policy">Policy</h2>
      <dl className="facts">
        <dt>Policy</dt>
        <dd className="mono">{policy.policy_id}</dd>
        <dt>Plan</dt>
        <dd>{policy.plan.name}</dd>
        <dt>Trip</dt>
        <dd>
          {policy.trip.destination}, {formatDate(policy.trip.departs_on)} to{" "}
          {formatDate(policy.trip.returns_on)}
        </dd>
        <dt>Trip cost</dt>
        <dd className="mono">{formatMoney(policy.trip.trip_cost)}</dd>
        <dt>Travelers</dt>
        {policy.travelers.map((traveler) => (
          <dd key={traveler}>{traveler}</dd>
        ))}
        <dt>Add-ons</dt>
        {policy.add_ons.length === 0 && <dd>None</dd>}
        {policy.add_ons.map((addOn) => (
          <dd key={addOn.add_on}>
            <span className="add-on-name">{addOn.name}</span>
            <span className="meta"> {addOn.effect}</span>
          </dd>
        ))}
      </dl>
      <h3>Plan limits</h3>
      <dl className="facts">
        {PLAN_LIMITS.map(([name, limit]) => (
          <div key={name} className="fact">
            <dt>{name}</dt>
            <dd className="mono">{limit(policy.plan)}</dd>
          </div>
        ))}
      </dl>
      <p className="meta">
        The deductible applies to{" "}
        {policy.deductible_applies_to
          .map(formatClaimType)
          .join(" and ")
          .toLowerCase()}
        .
      </p>
    </section>
  );
}
