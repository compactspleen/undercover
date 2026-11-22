import { getText } from "./api";
import { Show } from "./Show";
import { useLoaded } from "./useLoaded";

export function Instructions() {
  const [instructions] = useLoaded("/api/instructions", getText);
  return (
    <section className="stack">
      <h1>Agent instructions</h1>
      <p className="meta">
        What the UnderCover Agent is told at the start of every claim. Read
        only.
      </p>
      <Show loaded={instructions}>
        {(markdown) => (
          <pre className="panel instructions" data-testid="instructions">
            {markdown}
          </pre>
        )}
      </Show>
    </section>
  );
}
