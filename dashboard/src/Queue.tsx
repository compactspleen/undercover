import type { ClaimStatus, ClaimSummary } from "./api";
import { getJson } from "./api";
import { formatClaimType, formatMoney } from "./format";
import { Show, StatusLabel } from "./Show";
import { useLoaded } from "./useLoaded";

const STATUSES: ClaimStatus[] = [
  "waiting",
  "in_progress",
  "waiting_for_sign_off",
  "decided",
];

export function Queue() {
  const [claims] = useLoaded("/api/claims", getJson<ClaimSummary[]>);
  return (
    <section className="stack">
      <h1>Claims queue</h1>
      <Show loaded={claims}>{(queue) => <QueueTable claims={queue} />}</Show>
    </section>
  );
}

function QueueTable({ claims }: Readonly<{ claims: ClaimSummary[] }>) {
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
              <th scope="col">Type</th>
              <th scope="col">Summary</th>
              <th scope="col" className="number">
                Claimed
              </th>
              <th scope="col">Status</th>
            </tr>
          </thead>
          <tbody>
            {claims.map((claim) => (
              <tr key={claim.claim_id}>
                <td>
                  <a className="mono" href={`#${claim.claim_id}`}>
                    {claim.claim_id}
                  </a>
                </td>
                <td>{formatClaimType(claim.claim_type)}</td>
                <td>{claim.summary}</td>
                <td className="number mono">
                  {formatMoney(claim.amount_claimed)}
                </td>
                <td>
                  <StatusLabel status={claim.status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
