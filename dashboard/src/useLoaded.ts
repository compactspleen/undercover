import { useCallback, useEffect, useState, useSyncExternalStore } from "react";
import { reasonOf } from "./api";

const POLL_INTERVAL_MS = 2000;

export type Loaded<T> =
  | { state: "loading" }
  | { state: "ready"; value: T }
  | { state: "failed"; reason: string };

/** Load from the backend on mount, and again whenever `reload` is called. */
export function useLoaded<T>(
  path: string,
  read: (path: string) => Promise<T>,
): [Loaded<T>, () => void] {
  const [loaded, setLoaded] = useState<Loaded<T>>({ state: "loading" });
  const reload = useCallback(() => {
    read(path).then(
      (value) => {
        setLoaded({ state: "ready", value });
      },
      (error: unknown) => {
        setLoaded({ state: "failed", reason: reasonOf(error) });
      },
    );
  }, [path, read]);
  useEffect(reload, [reload]);
  return [loaded, reload];
}

/** Call `reload` every two seconds while the page is open, to show the agent's changes. */
export function usePolling(reload: () => void) {
  useEffect(() => {
    const timer = setInterval(reload, POLL_INTERVAL_MS);
    return () => {
      clearInterval(timer);
    };
  }, [reload]);
}

function subscribeToHash(onChange: () => void): () => void {
  window.addEventListener("hashchange", onChange);
  return () => {
    window.removeEventListener("hashchange", onChange);
  };
}

/** The page's address, such as "#CLM-1001", kept up to date as it changes. */
export function useHash(): string {
  return useSyncExternalStore(subscribeToHash, () => window.location.hash);
}
