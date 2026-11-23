import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { Claim } from "./api";
import { ClaimPage } from "./ClaimPage";
import { fakeBackend, json, type Answer } from "./testing/fakeBackend";
import { APPROVAL, CLAIM, HANDLERS, HISTORY, POLICY } from "./testing/fixtures";

const OVER_LIMIT: Claim = {
  ...CLAIM,
  status: "waiting_for_sign_off",
  decision: { ...APPROVAL, payout: 1250 },
};

const SIGNED_OFF: Claim = {
  ...OVER_LIMIT,
  status: "decided",
  sign_off: {
    handler_id: "HND-01",
    handler_name: "Dana Whitfield",
    signed_off_at: "2026-11-22T10:20:00+00:00",
  },
  payment: { amount: 1250, paid_at: "2026-11-22T10:20:00+00:00" },
};

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function showClaim(claim: Claim, signOff: Answer = json(SIGNED_OFF)) {
  const answers: Record<string, Answer> = {
    "GET /api/claims/CLM-1001": json(claim),
    "GET /api/claims/CLM-1001/policy": json(POLICY),
    "GET /api/claims/CLM-1001/history": json(HISTORY),
    "GET /api/handlers": json(HANDLERS),
  };
  answers["POST /api/claims/CLM-1001/sign-off"] = () => {
    answers["GET /api/claims/CLM-1001"] = json(SIGNED_OFF);
    return signOff();
  };
  const fetch = fakeBackend(answers);
  render(<ClaimPage claimId="CLM-1001" />);
  return fetch;
}

async function decision() {
  return within(await screen.findByRole("region", { name: "Decision" }));
}

async function signOffAs(handlerId: string) {
  const panel = await decision();
  fireEvent.change(await panel.findByLabelText("Handler"), {
    target: { value: handlerId },
  });
  await act(async () => {
    fireEvent.click(panel.getByRole("button", { name: "Sign off" }));
    await Promise.resolve();
  });
}

it("shows the payout waiting for sign-off, with a sign-off control", async () => {
  showClaim(OVER_LIMIT);
  const panel = await decision();
  expect(panel.getByText("$1,250.00")).toBeDefined();
  expect(
    panel.getByText("The payment waits for a handler's sign-off"),
  ).toBeDefined();
  expect(
    await panel.findByRole("option", { name: "Dana Whitfield" }),
  ).toBeDefined();
});

it("signs off and then shows who signed off, when, and the payment", async () => {
  const fetch = showClaim(OVER_LIMIT);
  await signOffAs("HND-01");
  const panel = await decision();
  expect(await panel.findByText(/Signed off by Dana Whitfield/)).toBeDefined();
  expect(panel.getByText(/Paid \$1,250.00/)).toBeDefined();
  expect(fetch).toHaveBeenCalledWith("/api/claims/CLM-1001/sign-off", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ handler_id: "HND-01" }),
  });
});

it("shows the backend's reason when it refuses a sign-off", async () => {
  showClaim(
    OVER_LIMIT,
    json({ detail: "This claim isn't waiting for sign-off" }, 409),
  );
  await signOffAs("HND-02");
  expect((await screen.findByRole("alert")).textContent).toBe(
    "This claim isn't waiting for sign-off",
  );
});

it("can't sign off until a handler is chosen", async () => {
  showClaim(OVER_LIMIT);
  const panel = await decision();
  await panel.findByRole("option", { name: "Dana Whitfield" });
  expect(
    panel.getByRole("button", { name: "Sign off" }).hasAttribute("disabled"),
  ).toBe(true);
});

it("shows a payment", async () => {
  showClaim({
    ...CLAIM,
    status: "decided",
    decision: APPROVAL,
    payment: { amount: 420, paid_at: "2026-11-22T10:15:00+00:00" },
  });
  expect((await decision()).getByText(/Paid \$420.00/)).toBeDefined();
});
