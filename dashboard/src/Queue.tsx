import type { ClaimStatus, QueuedClaim } from "./api";
import { getJson } from "./api";
import { formatClaimType, formatMoney } from "./format";
import { DecisionLabel, Show, StatusLabel } from "./Show";
import { useLoaded, usePolling } from "./useLoaded";

const STATUSES: ClaimStatus[] = [
  "waiting",
  "in_progress",
  "waiting_for_sign_off",
  "decided",
];

export function Queue() {
  const [claims, reload] = useLoaded("/api/claims", getJson<QueuedClaim[]>);
  // The agent starts and decides claims while the queue is open.
  usePolling(reload);
  return (
    <section className="stack">
      <h1>Claims queue</h1>
      <Show loaded={claims}>{(queue) => <QueueTable claims={queue} />}</Show>
    </section>
  );
}

function QueueTable({ claims }: Readonly<{ claims: QueuedClaim[] }>) {
  return (
    <>
      <ul className="counts" aria-label="Counts">
        {STATUSES.map((status) => (
          <li key={status} className="panel count">
            <StatusLabel status={status} />
            <span className="count-number">
              {claims.filter((claim) => claim.status === status).length}
            </span>
          </li>
        ))}
      </ul>
      <div className="panel table-scroll">
        <table>
          <thead>
            <tr>
              <th scope="col">Claim</th>
              <th scope="col">Customer</th>
              <th scope="col">Type</th>
              <th scope="col">Summary</th>
              <th scope="col">Status</th>
              <th scope="col">Decision</th>
              <th scope="col" className="number">
                Claimed
              </th>
              <th scope="col" className="number">
                Payout
              </th>
            </tr>
          </thead>
          <tbody>
            {claims.map((claim) => (
              <tr key={claim.claim_id}>
                <td>
                  <a className="mono identifier" href={`#${claim.claim_id}`}>
                    {claim.claim_id}
                  </a>
                </td>
                <td>{claim.customer_name}</td>
                <td>{formatClaimType(claim.claim_type)}</td>
                <td>{claim.summary}</td>
                <td>
                  <StatusLabel status={claim.status} />
                </td>
                <td>
                  {claim.decision && (
                    <DecisionLabel decision={claim.decision.decision} />
                  )}
                </td>
                <td className="number mono">
                  {formatMoney(claim.amount_claimed)}
                </td>
                <td className="number mono">
                  {claim.decision?.decision === "approve" &&
                    formatMoney(claim.decision.payout)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
