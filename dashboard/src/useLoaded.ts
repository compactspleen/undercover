import { useCallback, useEffect, useState, useSyncExternalStore } from "react";

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
        setLoaded({
          state: "failed",
          reason: String(error).replace(/^Error: /, ""),
        });
      },
    );
  }, [path, read]);
  useEffect(reload, [reload]);
  return [loaded, reload];
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
