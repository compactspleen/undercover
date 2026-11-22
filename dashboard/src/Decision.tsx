import type { Claim } from "./api";
import { formatMoney } from "./format";
import { AlertLabel, DecisionLabel } from "./Show";

export function Decision({ claim }: Readonly<{ claim: Claim }>) {
  return (
    <section className="panel" aria-labelledby="decision">
      <h2 id="decision">Decision</h2>
      <DecisionDetail claim={claim} />
    </section>
  );
}

function DecisionDetail({ claim }: Readonly<{ claim: Claim }>) {
  const { decision } = claim;
  if (!decision) return <p className="note">No decision yet</p>;
  return (
    <div className="stack-tight">
      <p className="decision-line">
        <DecisionLabel decision={decision.decision} />
        {decision.decision === "approve" && (
          <span className="payout mono">{formatMoney(decision.payout)}</span>
        )}
      </p>
      <p className="prose">{decision.explanation}</p>
      <p className="meta">
        Policy section{" "}
        <span className="section-name">{decision.policy_section}</span>
      </p>
      {isApprovedButNotPaid(claim) && (
        <AlertLabel>Approved, not paid</AlertLabel>
      )}
    </div>
  );
}

/** An approval within the limit is decided at once, so it should be paid. */
function isApprovedButNotPaid(claim: Claim): boolean {
  return (
    claim.decision?.decision === "approve" &&
    claim.status === "decided" &&
    claim.payment === null
  );
}
