import { act, cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { App } from "./App";
import { fakeBackend, json } from "./testing/fakeBackend";
import { CLAIM, POLICY, QUEUE } from "./testing/fixtures";

beforeEach(() => {
  fakeBackend({
    "GET /api/claims": json(QUEUE),
    "GET /api/claims/CLM-1001": json(CLAIM),
    "GET /api/claims/CLM-1001/policy": json(POLICY),
  });
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  window.location.hash = "";
});

function goTo(hash: string) {
  act(() => {
    window.location.hash = hash;
    window.dispatchEvent(new HashChangeEvent("hashchange"));
  });
}

it("shows the header band with links to the queue and the instructions", () => {
  render(<App />);
  const header = within(screen.getByRole("banner"));
  expect(header.getByText("UnderCover")).toBeDefined();
  expect(header.getByRole("link", { name: "Queue" }).getAttribute("href")).toBe(
    "#queue",
  );
  expect(
    header.getByRole("link", { name: "Instructions" }).getAttribute("href"),
  ).toBe("#instructions");
});

it("shows the queue when there's no hash", async () => {
  render(<App />);
  expect(
    await screen.findByRole("heading", { name: "Claims queue" }),
  ).toBeDefined();
});

it("opens the claim named in the hash", async () => {
  window.location.hash = "#CLM-1001";
  render(<App />);
  expect(
    await screen.findByRole("heading", { name: /CLM-1001/ }),
  ).toBeDefined();
});

it("follows the hash from a claim back to the queue", async () => {
  window.location.hash = "#CLM-1001";
  render(<App />);
  await screen.findByRole("heading", { name: /CLM-1001/ });
  goTo("#queue");
  expect(
    await screen.findByRole("heading", { name: "Claims queue" }),
  ).toBeDefined();
});
