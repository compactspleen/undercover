import { act, cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import type { Claim, Step } from "./api";
import { ClaimPage } from "./ClaimPage";
import { fakeBackend, json, type Answer } from "./testing/fakeBackend";
import { CLAIM, POLICY } from "./testing/fixtures";

const CALL: Step = {
  kind: "tool_call",
  text: 'get_claim {"claim_id": "CLM-1001"}',
  recorded_at: "2026-11-22T10:15:00+00:00",
};
const RESULT: Step = {
  kind: "tool_result",
  text: 'get_claim: {"claim_id": "CLM-1001"}',
  recorded_at: "2026-11-22T10:15:01+00:00",
};
const REPLY: Step = {
  kind: "reply",
  text: "Approved and paid.",
  recorded_at: "2026-11-22T10:15:09+00:00",
};

let answers: Record<string, Answer>;

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

function serve(claim: Claim) {
  answers["GET /api/claims/CLM-1001"] = json(claim);
}

function showClaim(claim: Claim) {
  answers = { "GET /api/claims/CLM-1001/policy": json(POLICY) };
  serve(claim);
  fakeBackend(answers);
  render(<ClaimPage claimId="CLM-1001" />);
}

async function stepTexts() {
  const steps = within(
    await screen.findByRole("region", { name: "Agent's steps" }),
  );
  return steps.getAllByRole("listitem").map((step) => step.textContent);
}

it("shows the agent's steps in order", async () => {
  showClaim({ ...CLAIM, status: "in_progress", steps: [CALL, RESULT, REPLY] });
  const texts = await stepTexts();
  expect(texts).toHaveLength(3);
  expect(texts[0]).toContain("Tool call");
  expect(texts[0]).toContain(CALL.text);
  expect(texts[1]).toContain("Result");
  expect(texts[2]).toContain(REPLY.text);
});

it("says when the agent hasn't started", async () => {
  showClaim(CLAIM);
  const steps = within(
    await screen.findByRole("region", { name: "Agent's steps" }),
  );
  expect(steps.getByText("No steps yet")).toBeDefined();
});

it("shows new steps within two seconds, without a reload", async () => {
  showClaim({ ...CLAIM, status: "in_progress", steps: [CALL] });
  await screen.findByText(CALL.text);
  serve({ ...CLAIM, status: "in_progress", steps: [CALL, RESULT] });
  await act(() => vi.advanceTimersByTimeAsync(2000));
  expect(await screen.findByText(RESULT.text)).toBeDefined();
});
