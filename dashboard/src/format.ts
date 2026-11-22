import type { ClaimStatus, Decision } from "./api";

const DOLLARS = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
});

export const STATUS_LABELS: Record<ClaimStatus, string> = {
  waiting: "Waiting",
  in_progress: "In progress",
  waiting_for_sign_off: "Waiting for sign-off",
  decided: "Decided",
};

export const DECISION_LABELS: Record<Decision["decision"], string> = {
  approve: "Approved",
  decline: "Declined",
  refer: "Referred",
};

export function formatMoney(amount: number): string {
  return DOLLARS.format(amount);
}

/** Turn a name such as `emergency_medical` into words: "Emergency medical". */
export function formatClaimType(name: string): string {
  const words = name.replaceAll("_", " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

/** Show a date such as `2026-06-18` as "Jun 18, 2026", the same in every time zone. */
export function formatDate(isoDate: string): string {
  return new Date(isoDate).toLocaleDateString("en-US", {
    dateStyle: "medium",
    timeZone: "UTC",
  });
}

export function formatTime(isoTime: string): string {
  return new Date(isoTime).toLocaleString("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}
