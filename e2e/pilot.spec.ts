import { expect, test, type APIRequestContext } from "@playwright/test";

// The tests share one backend and its database, so they run in order.
test.describe.configure({ mode: "serial" });

async function post(request: APIRequestContext, path: string, data?: object) {
  const response = await request.post(`/api/claims/${path}`, { data });
  expect(response.ok()).toBe(true);
}

test("the queue shows 25 waiting claims", async ({ page }) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Claims queue" }),
  ).toBeVisible();
  await expect(page.getByRole("table").getByRole("row")).toHaveCount(26);
  await expect(page.getByRole("row", { name: /^CLM-1001/ })).toContainText(
    "Maya Patel",
  );
  await expect(
    page.getByRole("list", { name: "Counts" }).getByRole("listitem"),
  ).toHaveText([
    /Waiting\s*25/,
    /In progress\s*0/,
    /sign-off\s*0/,
    /Decided\s*0/,
  ]);
});

test("a claim shows its decision and steps", async ({ page, request }) => {
  await post(request, "CLM-1001/start");
  await post(request, "CLM-1001/steps", {
    kind: "tool_call",
    text: 'get_claim {"claim_id": "CLM-1001"}',
  });
  await post(request, "CLM-1001/decision", {
    decision: "approve",
    payout: 420,
    explanation:
      "Your flight was canceled by the airline, so we cover your costs.",
    policy_section: "3. Trip Delay",
  });
  await post(request, "CLM-1001/payment", { amount: 420 });
  await post(request, "CLM-1001/steps", {
    kind: "reply",
    text: "Approved and paid $420.00.",
  });

  await page.goto("/#CLM-1001");
  const decision = page.getByRole("region", { name: "Decision" });
  await expect(decision.getByText("Approved", { exact: true })).toBeVisible();
  await expect(decision.getByText("3. Trip Delay")).toBeVisible();
  await expect(decision.getByText(/Paid \$420\.00/)).toBeVisible();
  const steps = page.getByRole("region", { name: "Agent's steps" });
  await expect(steps.getByRole("listitem")).toHaveCount(2);
  await expect(steps.getByText("Approved and paid $420.00.")).toBeVisible();
});

test("a claim's page names its customer", async ({ page }) => {
  await page.goto("/#CLM-1002");
  await expect(page.getByText("Customer Tom Becker")).toBeVisible();
});

test("the queue shows each claim's decision and payout", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("row", { name: /^CLM-1001/ })).toHaveText(
    /Decided\s*Approved\s*\$420\.00\s*\$420\.00$/,
  );
  await expect(page.getByRole("row", { name: /^CLM-1002/ })).toHaveText(
    /Waiting\s*\$[\d,.]+$/,
  );
});

test("the instructions page shows the instructions", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Instructions" }).click();
  await expect(
    page.getByRole("heading", { name: "Agent instructions" }),
  ).toBeVisible();
  await expect(page.getByTestId("instructions")).toContainText(
    "You are the UnderCover Agent.",
  );
});

test("an over-limit claim is signed off and then paid", async ({
  page,
  request,
}) => {
  await post(request, "CLM-1003/start");
  await post(request, "CLM-1003/decision", {
    decision: "approve",
    payout: 1250,
    explanation: "Your treatment abroad is covered under Emergency Medical.",
    policy_section: "7. Emergency Medical",
  });

  await page.goto("/#CLM-1003");
  const decision = page.getByRole("region", { name: "Decision" });
  await expect(
    decision.getByText("The payment waits for a handler's sign-off"),
  ).toBeVisible();
  await decision
    .getByLabel("Handler")
    .selectOption({ label: "Dana Whitfield" });
  await decision.getByRole("button", { name: "Sign off" }).click();
  await expect(
    decision.getByText(/Signed off by Dana Whitfield/),
  ).toBeVisible();
  await expect(decision.getByText(/Paid \$1,250\.00/)).toBeVisible();
});
