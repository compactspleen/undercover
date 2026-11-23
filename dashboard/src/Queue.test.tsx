import { act, cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { ClaimStatus, Decision, QueuedClaim } from "./api";
import { Queue } from "./Queue";
import { fakeBackend, json, type Answer } from "./testing/fakeBackend";
import { APPROVAL, QUEUE } from "./testing/fixtures";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

async function rows() {
  const table = await screen.findByRole("table");
  return within(table).getAllByRole("row").slice(1);
}

async function column(name: string) {
  const headers = within(await screen.findByRole("table")).getAllByRole(
    "columnheader",
  );
  const index = headers.findIndex((header) => header.textContent === name);
  return (await rows()).map(
    (row) => within(row).getAllByRole("cell")[index]?.textContent,
  );
}

function claim(
  claimId: string,
  status: ClaimStatus,
  decision: Decision | null,
): QueuedClaim {
  return {
    claim_id: claimId,
    customer_name: "Maya Patel",
    claim_type: "baggage",
    summary: "Bag lost on the flight out",
    amount_claimed: 1250,
    status,
    decision,
  };
}

it("lists every claim in order with its details and status", async () => {
  fakeBackend({ "GET /api/claims": json(QUEUE) });
  render(<Queue />);
  const claims = await rows();
  expect(claims).toHaveLength(25);
  expect(claims[0]?.textContent).toBe(
    "CLM-1001Maya PatelTrip delayFlight home canceledWaiting$420.00",
  );
  expect(claims.map((row) => row.querySelector("a")?.textContent)).toEqual(
    QUEUE.map((claim) => claim.claim_id),
  );
});

it("names each claim's customer right after the claim", async () => {
  fakeBackend({ "GET /api/claims": json(QUEUE) });
  render(<Queue />);
  await rows();
  expect(
    screen.getAllByRole("columnheader").map((header) => header.textContent),
  ).toEqual([
    "Claim",
    "Customer",
    "Type",
    "Summary",
    "Status",
    "Decision",
    "Claimed",
    "Payout",
  ]);
  expect(await column("Customer")).toEqual(
    QUEUE.map((claim) => claim.customer_name),
  );
});

it("shows each claim's decision and the payout it approved", async () => {
  fakeBackend({
    "GET /api/claims": json([
      claim("CLM-1001", "decided", { ...APPROVAL, payout: 400 }),
      claim("CLM-1002", "decided", {
        decision: "decline",
        explanation: "The wording doesn't cover this.",
        policy_section: "9. General exclusions",
      }),
      claim("CLM-1003", "decided", {
        decision: "refer",
        explanation: "A handler will look at your claim.",
        policy_section: "11. How to claim",
      }),
      claim("CLM-1004", "waiting_for_sign_off", { ...APPROVAL, payout: 1250 }),
      claim("CLM-1005", "waiting", null),
    ]),
  });
  render(<Queue />);
  expect(await column("Decision")).toEqual([
    "Approved",
    "Declined",
    "Referred",
    "Approved",
    "",
  ]);
  expect(await column("Payout")).toEqual(["$400.00", "", "", "$1,250.00", ""]);
  expect(await column("Claimed")).toEqual(Array(5).fill("$1,250.00"));
});

it("links each claim to its page", async () => {
  fakeBackend({ "GET /api/claims": json(QUEUE) });
  render(<Queue />);
  await rows();
  expect(
    screen.getByRole("link", { name: "CLM-1001" }).getAttribute("href"),
  ).toBe("#CLM-1001");
});

it("counts the claims in each status", async () => {
  fakeBackend({ "GET /api/claims": json(QUEUE) });
  render(<Queue />);
  const counts = within(await screen.findByRole("list", { name: "Counts" }));
  expect(
    counts.getAllByRole("listitem").map((item) => item.textContent),
  ).toEqual(["Waiting10", "In progress5", "Waiting for sign-off5", "Decided5"]);
});

it("shows the agent's changes within two seconds, without a reload", async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  const waiting = claim("CLM-1001", "waiting", null);
  const answers: Record<string, Answer> = {
    "GET /api/claims": json([waiting]),
  };
  fakeBackend(answers);
  render(<Queue />);
  expect(await column("Status")).toEqual(["Waiting"]);
  answers["GET /api/claims"] = json([{ ...waiting, status: "in_progress" }]);
  await act(() => vi.advanceTimersByTimeAsync(2000));
  expect(await column("Status")).toEqual(["In progress"]);
  const counts = within(screen.getByRole("list", { name: "Counts" }));
  expect(
    counts.getAllByRole("listitem").map((item) => item.textContent),
  ).toEqual(["Waiting0", "In progress1", "Waiting for sign-off0", "Decided0"]);
});

it("shows why the queue couldn't load", async () => {
  fakeBackend({});
  render(<Queue />);
  expect((await screen.findByRole("alert")).textContent).toBe("Not found");
});

it("gives the status when the backend can't be reached", async () => {
  fakeBackend({
    "GET /api/claims": () => new Response("Proxy error", { status: 502 }),
  });
  render(<Queue />);
  expect((await screen.findByRole("alert")).textContent).toBe(
    "The backend answered 502",
  );
});
