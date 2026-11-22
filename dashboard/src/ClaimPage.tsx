import type { Claim, Policy } from "./api";
import { getJson } from "./api";
import { formatClaimType, formatDate, formatMoney } from "./format";
import { Decision } from "./Decision";
import { PolicyPanel } from "./PolicyPanel";
import { Show, StatusLabel } from "./Show";
import { useLoaded } from "./useLoaded";

export function ClaimPage({ claimId }: Readonly<{ claimId: string }>) {
  const [claim] = useLoaded(`/api/claims/${claimId}`, getJson<Claim>);
  const [policy] = useLoaded(`/api/claims/${claimId}/policy`, getJson<Policy>);
  return (
    <Show loaded={claim}>
      {(value) => (
        <article className="stack">
          <ClaimHeading claim={value} />
          <div className="columns">
            <div className="stack">
              <Story claim={value} />
              <Items claim={value} />
              <Documents claim={value} />
            </div>
            <div className="stack">
              <Decision claim={value} />
              <Show loaded={policy}>
                {(found) => <PolicyPanel policy={found} />}
              </Show>
            </div>
          </div>
        </article>
      )}
    </Show>
  );
}

function ClaimHeading({ claim }: Readonly<{ claim: Claim }>) {
  return (
    <header className="claim-heading">
      <p className="eyebrow">{formatClaimType(claim.claim_type)}</p>
      <h1>
        <span className="mono">{claim.claim_id}</span>{" "}
        <StatusLabel status={claim.status} />
      </h1>
      <p className="lead">{claim.summary}</p>
      <p className="meta">
        {claim.incident_location}, {formatDate(claim.incident_date)}. Submitted{" "}
        {formatDate(claim.submitted_on)}.
      </p>
    </header>
  );
}

function Story({ claim }: Readonly<{ claim: Claim }>) {
  return (
    <section className="panel" aria-labelledby="story">
      <h2 id="story">Story</h2>
      <p className="prose">{claim.story}</p>
    </section>
  );
}

function Items({ claim }: Readonly<{ claim: Claim }>) {
  return (
    <section className="panel" aria-labelledby="items">
      <h2 id="items">Items</h2>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th scope="col">Item</th>
              <th scope="col">Category</th>
              <th scope="col" className="number">
                Amount
              </th>
            </tr>
          </thead>
          <tbody>
            {claim.items.map((item) => (
              <tr key={item.description}>
                <td>{item.description}</td>
                <td>{formatClaimType(item.category)}</td>
                <td className="number mono">{formatMoney(item.amount)}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <th scope="row" colSpan={2}>
                Total claimed
              </th>
              <td className="number mono">
                {formatMoney(claim.amount_claimed)}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
    </section>
  );
}

function Documents({ claim }: Readonly<{ claim: Claim }>) {
  return (
    <section className="panel" aria-labelledby="documents">
      <h2 id="documents">Documents</h2>
      <ul className="documents">
        {claim.documents.map((document) => (
          <li key={document.name}>
            <p className="document-name">
              {document.name}{" "}
              <span className="eyebrow">{formatClaimType(document.type)}</span>
            </p>
            <p className="prose">{document.content}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
