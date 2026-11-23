import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import type { Claim, Step, StepKind } from "./api";
import { ClaimPage } from "./ClaimPage";
import { fakeBackend, json, type Answer } from "./testing/fakeBackend";
import { CLAIM, HISTORY, POLICY } from "./testing/fixtures";

function step(kind: StepKind, text: string, second: number): Step {
  const recordedAt = `2026-11-22T10:15:${String(second).padStart(2, "0")}Z`;
  return { kind, text, recorded_at: recordedAt };
}

const CLAIM_RESULT_TEXT = '{"claim_id":"CLM-1001"}';
const CLAIM_CALL = step("tool_call", 'get_claim {"claim_id": "CLM-1001"}', 0);
const POLICY_CALL = step("tool_call", 'get_policy {"claim_id": "CLM-1001"}', 1);
const POLICY_RESULT = step(
  "tool_result",
  'get_policy: {"policy_id":"POL-2001","plan":"premium"}',
  2,
);
const CLAIM_RESULT = step("tool_result", `get_claim: ${CLAIM_RESULT_TEXT}`, 3);
const REPLY = step("reply", "Approved and paid.", 9);
const WORDING = `# Policy wording ${"Cover starts when you buy the policy. ".repeat(6)}The end.`;
const WORDING_CALL = step("tool_call", "get_policy_wording {}", 4);
const WORDING_RESULT = step("tool_result", `get_policy_wording: ${WORDING}`, 5);

let answers: Record<string, Answer>;

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

function worked(...steps: Step[]): Claim {
  return { ...CLAIM, status: "in_progress", steps };
}

function serve(claim: Claim) {
  answers["GET /api/claims/CLM-1001"] = json(claim);
}

function showClaim(claim: Claim) {
  answers = {
    "GET /api/claims/CLM-1001/policy": json(POLICY),
    "GET /api/claims/CLM-1001/history": json(HISTORY),
  };
  serve(claim);
  fakeBackend(answers);
  render(<ClaimPage claimId="CLM-1001" />);
}

async function stepTexts() {
  const steps = within(
    await screen.findByRole("region", { name: "Agent's steps" }),
  );
  return steps.getAllByRole("listitem").map((item) => item.textContent);
}

async function openResult() {
  const result = await screen.findByRole("button", { name: /^Result/ });
  fireEvent.click(result);
  return result;
}

it("pairs each tool call with its result, in the order of the calls", async () => {
  showClaim(
    worked(CLAIM_CALL, POLICY_CALL, POLICY_RESULT, CLAIM_RESULT, REPLY),
  );
  const texts = await stepTexts();
  expect(texts).toHaveLength(3);
  expect(texts[0]).toContain("Tool call");
  expect(texts[0]).toContain(CLAIM_CALL.text);
  expect(texts[0]).toContain(`Result ${CLAIM_RESULT_TEXT}`);
  expect(texts[0]).not.toContain("POL-2001");
  expect(texts[1]).toContain(POLICY_CALL.text);
  expect(texts[1]).toContain('"policy_id":"POL-2001"');
  expect(texts[2]).toContain(REPLY.text);
});

it("gives a rerun's result to the rerun's call", async () => {
  const rerunCall = step("tool_call", CLAIM_CALL.text, 30);
  const rerunResult = step("tool_result", CLAIM_RESULT.text, 31);
  showClaim(worked(CLAIM_CALL, rerunCall, rerunResult));
  const texts = await stepTexts();
  expect(texts).toHaveLength(2);
  expect(texts[0]).toContain("No result");
  expect(texts[1]).toContain(CLAIM_RESULT_TEXT);
});

it("shows a result in full when its disclosure is opened", async () => {
  showClaim(worked(WORDING_CALL, WORDING_RESULT));
  expect(
    (await screen.findByRole("button", { name: /^Result/ })).getAttribute(
      "aria-expanded",
    ),
  ).toBe("false");
  expect(screen.queryByText(WORDING)).toBeNull();
  const result = await openResult();
  expect(result.getAttribute("aria-expanded")).toBe("true");
  expect(screen.getByText(WORDING)).toBeDefined();
});

it("lays a JSON result out over several lines", async () => {
  showClaim(worked(POLICY_CALL, POLICY_RESULT));
  await openResult();
  expect((await stepTexts())[0]).toContain(
    '{\n  "policy_id": "POL-2001",\n  "plan": "premium"\n}',
  );
});

it("keeps a result open as new steps arrive", async () => {
  showClaim(worked(POLICY_CALL, POLICY_RESULT));
  const result = await openResult();
  serve(worked(POLICY_CALL, POLICY_RESULT, REPLY));
  await act(() => vi.advanceTimersByTimeAsync(2000));
  await screen.findByText(REPLY.text);
  expect(result.getAttribute("aria-expanded")).toBe("true");
});

it("says when the agent hasn't started", async () => {
  showClaim(CLAIM);
  const steps = within(
    await screen.findByRole("region", { name: "Agent's steps" }),
  );
  expect(steps.getByText("No steps yet")).toBeDefined();
});

it("shows new steps within two seconds, without a reload", async () => {
  showClaim(worked(CLAIM_CALL));
  await screen.findByText(CLAIM_CALL.text);
  serve(worked(CLAIM_CALL, CLAIM_RESULT));
  await act(() => vi.advanceTimersByTimeAsync(2000));
  expect(await screen.findByText(CLAIM_RESULT_TEXT)).toBeDefined();
});
