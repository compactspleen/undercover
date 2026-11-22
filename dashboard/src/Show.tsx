import type { ReactNode } from "react";
import type { ClaimStatus, Decision } from "./api";
import { DECISION_LABELS, STATUS_LABELS } from "./format";
import type { Loaded } from "./useLoaded";

/** Show what was loaded, or that it's loading, or why it failed. */
export function Show<T>({
  loaded,
  children,
}: Readonly<{
  loaded: Loaded<T>;
  children: (value: T) => ReactNode;
}>) {
  if (loaded.state === "loading") return <p className="note">Loading…</p>;
  if (loaded.state === "failed") {
    return (
      <p className="note note-alert" role="alert">
        {loaded.reason}
      </p>
    );
  }
  return <>{children(loaded.value)}</>;
}

export function StatusLabel({ status }: Readonly<{ status: ClaimStatus }>) {
  return (
    <span className={`label label-${status}`}>{STATUS_LABELS[status]}</span>
  );
}

export function DecisionLabel({
  decision,
}: Readonly<{
  decision: Decision["decision"];
}>) {
  return (
    <span className={`label label-${decision}`}>
      {DECISION_LABELS[decision]}
    </span>
  );
}

export function AlertLabel({ children }: Readonly<{ children: string }>) {
  return <span className="label label-alert">{children}</span>;
}
