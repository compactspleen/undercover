import type { Claim } from "./api";
import { formatMoney, formatTime } from "./format";
import { AlertLabel, DecisionLabel } from "./Show";
import { SignOff } from "./SignOff";

export function Decision({
  claim,
  onSignedOff,
}: Readonly<{ claim: Claim; onSignedOff: () => void }>) {
  return (
    <section className="panel" aria-labelledby="decision">
      <h2 id="decision">Decision</h2>
      <DecisionDetail claim={claim} onSignedOff={onSignedOff} />
    </section>
  );
}

function DecisionDetail({
  claim,
  onSignedOff,
}: Readonly<{ claim: Claim; onSignedOff: () => void }>) {
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
      {decision.decision === "approve" && (
        <Payment claim={claim} onSignedOff={onSignedOff} />
      )}
    </div>
  );
}

function Payment({
  claim,
  onSignedOff,
}: Readonly<{ claim: Claim; onSignedOff: () => void }>) {
  if (claim.status === "waiting_for_sign_off") {
    return (
      <div className="stack-tight">
        <p className="note">The payment waits for a handler&apos;s sign-off</p>
        <SignOff claimId={claim.claim_id} onSignedOff={onSignedOff} />
      </div>
    );
  }
  if (!claim.payment) return <AlertLabel>Approved, not paid</AlertLabel>;
  return (
    <div className="stack-tight">
      {claim.sign_off && (
        <p className="meta">
          Signed off by {claim.sign_off.handler_name} on{" "}
          {formatTime(claim.sign_off.signed_off_at)}
        </p>
      )}
      <p className="paid">
        {`Paid ${formatMoney(claim.payment.amount)} on ${formatTime(claim.payment.paid_at)}`}
      </p>
    </div>
  );
}
