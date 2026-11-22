import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { Queue } from "./Queue";
import { fakeBackend, json } from "./testing/fakeBackend";
import { QUEUE } from "./testing/fixtures";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

async function rows() {
  const table = await screen.findByRole("table");
  return within(table).getAllByRole("row").slice(1);
}

it("lists every claim in order with its details and status", async () => {
  fakeBackend({ "GET /api/claims": json(QUEUE) });
  render(<Queue />);
  const claims = await rows();
  expect(claims).toHaveLength(25);
  expect(claims[0]?.textContent).toBe(
    "CLM-1001Trip delayFlight home canceled$420.00Waiting",
  );
  expect(claims.map((row) => row.querySelector("a")?.textContent)).toEqual(
    QUEUE.map((claim) => claim.claim_id),
  );
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
