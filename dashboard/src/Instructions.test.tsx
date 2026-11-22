import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { App } from "./App";
import { fakeBackend, text } from "./testing/fakeBackend";

const INSTRUCTIONS =
  "# UnderCover Agent\n\nYou decide travel insurance claims.";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  window.location.hash = "";
});

it("shows the agent's instructions at #instructions, read only", async () => {
  fakeBackend({ "GET /api/instructions": text(INSTRUCTIONS) });
  window.location.hash = "#instructions";
  render(<App />);
  expect(
    await screen.findByRole("heading", { name: "Agent instructions" }),
  ).toBeDefined();
  expect((await screen.findByTestId("instructions")).textContent).toBe(
    INSTRUCTIONS,
  );
  expect(screen.queryByRole("textbox")).toBeNull();
});
