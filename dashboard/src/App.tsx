import type { ReactNode } from "react";
import { ClaimPage } from "./ClaimPage";
import { Instructions } from "./Instructions";
import { Queue } from "./Queue";
import { useHash } from "./useLoaded";

const CLAIM_ADDRESS = /^#CLM-\d+$/;

function pageFor(hash: string): ReactNode {
  if (hash === "#instructions") return <Instructions />;
  if (CLAIM_ADDRESS.test(hash)) {
    return <ClaimPage key={hash} claimId={hash.slice(1)} />;
  }
  return <Queue />;
}

export function App() {
  const hash = useHash();
  return (
    <>
      <header className="band">
        <div className="band-inner">
          <a className="wordmark" href="#queue">
            UnderCover
          </a>
          <span className="tagline">Claims desk</span>
          <nav className="nav" aria-label="Pages">
            <a href="#queue">Queue</a>
            <a href="#instructions">Instructions</a>
          </nav>
        </div>
      </header>
      <main className="page">{pageFor(hash)}</main>
    </>
  );
}
