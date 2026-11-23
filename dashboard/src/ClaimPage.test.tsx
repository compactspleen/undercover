import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { Claim } from "./api";
import { ClaimPage } from "./ClaimPage";
import { fakeBackend, json } from "./testing/fakeBackend";
import { APPROVAL, CLAIM, HISTORY, POLICY } from "./testing/fixtures";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function showClaim(claim: Claim) {
  fakeBackend({
    "GET /api/claims/CLM-1001": json(claim),
    "GET /api/claims/CLM-1001/policy": json(POLICY),
    "GET /api/claims/CLM-1001/history": json(HISTORY),
  });
  render(<ClaimPage claimId="CLM-1001" />);
}

async function section(name: string) {
  return within(await screen.findByRole("region", { name }));
}

it("shows the claim in full", async () => {
  showClaim(CLAIM);
  expect(
    (await screen.findByRole("heading", { level: 1 })).textContent,
  ).toContain("CLM-1001");
  const story = await section("Story");
  expect(story.getByText(CLAIM.story)).toBeDefined();
  const items = await section("Items");
  expect(items.getByText("Airport hotel, one night")).toBeDefined();
  expect(items.getByText("$245.00")).toBeDefined();
  expect(items.getByText("$420.00")).toBeDefined();
  const documents = await section("Documents");
  expect(documents.getByText("Hotel receipt")).toBeDefined();
  expect(
    documents.getByText("Hotel Aurelia Fiumicino. Total paid: $245.00."),
  ).toBeDefined();
});

it("names the claim's customer", async () => {
  showClaim(CLAIM);
  const label = await screen.findByText("Customer");
  expect(label.parentElement?.textContent).toBe("Customer Maya Patel");
});

it("shows the policy and its plan", async () => {
  showClaim(CLAIM);
  const policy = await section("Policy");
  expect(await policy.findByText("UnderCover Premium")).toBeDefined();
  expect(policy.getByText("POL-2001")).toBeDefined();
  expect(policy.getByText("Maya Patel")).toBeDefined();
  expect(policy.getByText("Electronics Plus")).toBeDefined();
  expect(policy.getByText("$1,500.00")).toBeDefined();
});

it("says when there's no decision yet", async () => {
  showClaim(CLAIM);
  expect(
    (await section("Decision")).getByText("No decision yet"),
  ).toBeDefined();
});

it("shows an approval with its payout and payment", async () => {
  showClaim({
    ...CLAIM,
    status: "decided",
    decision: APPROVAL,
    payment: { amount: 420, paid_at: "2026-11-22T10:15:00+00:00" },
  });
  const decision = await section("Decision");
  expect(decision.getByText("Approved")).toBeDefined();
  expect(decision.getByText("$420.00")).toBeDefined();
  expect(decision.getByText(APPROVAL.explanation)).toBeDefined();
  expect(decision.getByText("3. Trip Delay")).toBeDefined();
  expect(decision.queryByText("Approved, not paid")).toBeNull();
});

it.each([
  ["decline", "Declined"],
  ["refer", "Referred"],
] as const)(
  "shows a %s with its explanation and section",
  async (type, label) => {
    showClaim({
      ...CLAIM,
      status: "decided",
      decision: {
        decision: type,
        explanation: "The wording doesn't cover this.",
        policy_section: "9. General exclusions",
      },
    });
    const decision = await section("Decision");
    expect(decision.getByText(label)).toBeDefined();
    expect(decision.getByText("The wording doesn't cover this.")).toBeDefined();
    expect(decision.getByText("9. General exclusions")).toBeDefined();
  },
);

it("flags an approval within the limit that wasn't paid", async () => {
  showClaim({ ...CLAIM, status: "decided", decision: APPROVAL });
  expect(
    (await section("Decision")).getByText("Approved, not paid"),
  ).toBeDefined();
});

it("says when the claim doesn't exist", async () => {
  fakeBackend({});
  render(<ClaimPage claimId="CLM-9999" />);
  expect((await screen.findAllByRole("alert"))[0]?.textContent).toBe(
    "Not found",
  );
});
