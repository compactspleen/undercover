# Plan: the claims pilot

This plan builds the pilot in `docs/SPEC.md`: a backend that holds UnderCover's records and enforces the payment rule, the UnderCover Agent that works the queue, and a dashboard where the handlers watch it and sign off large payouts. It follows `docs/TECH_STACK.md`, `docs/CODE_STANDARDS.md`, `docs/PROCESS.md` and `docs/BRAND.md`.

## The approach

**The backend is the source of truth and the enforcer.** The agent can decide, but it can only act through the backend's API, and the backend checks every rule. The $1,000 sign-off rule lives in the payment operation itself: if the agent tries to pay an over-limit claim before a handler signs off, the backend refuses. No prompt can talk its way past that.

**Records.** On first start, the backend creates a SQLite database (`undercover.db` at the repo root, ignored by git) and loads it from `data/`: claims, policies, customers, plans, handlers and company settings. The policy wording is read from `data/policy_wording.md`. Nothing reads `data/evals/`, `data/security/` or the claims manual. The environment variable `UNDERCOVER_DB` points the backend at another file, which the tests and the end-to-end run use so they never touch your working database. To start again from the seed data, delete `undercover.db`.

**A claim's status** is one of four values, an enum: `waiting`, `in_progress`, `waiting_for_sign_off` and `decided`. Every claim in `data/claims.json` starts as `waiting`.

**A decision** is one of three types, so an illegal state such as a declined claim with a payout can't be represented:

- `approve`: payout, explanation and policy section
- `decline`: explanation and policy section
- `refer`: explanation and policy section

A decision can only be recorded on a claim that's in progress, and only once. Recording an `approve` with a payout over the company's limit (from `data/company.json`) moves the claim to `waiting_for_sign_off`; every other decision moves it to `decided`.

**Amounts** are US dollars with two decimal places, kept as `Decimal` in the code and as whole cents in the database. They cross the API as JSON numbers, such as `1250.0`, in both directions, because Pydantic would otherwise send a `Decimal` as a string and break the dashboard's sums and the agent's reading of them.

**The payment rule.** `pay_claim` takes the amount and pays only when the claim is approved, the amount equals the approved payout, it hasn't been paid already, and either the payout is within the limit or a handler has signed off. Otherwise it answers 409 with the reason. A handler's sign-off releases the payment, so an over-limit claim is paid once, by the handler's action.

**An approval that isn't paid.** Paying is a separate operation from deciding, so the agent could approve a claim within the limit and never pay it. The run checks for this when the agent finishes and fails with "approved but not paid", and the claim's page shows "Approved, not paid", so it can't pass unnoticed.

**What the agent sees.** Tools for the claim, the policy with its plan and add-ons, the customer's claim history and the policy wording. The claim tool returns the claim itself, without its decision, payment or steps, to keep the model's context to what it needs. The claim history leaves out contact details, address and date of birth, because the agent doesn't need them to decide (CODE_STANDARDS 23). The agent's instructions are a Markdown file in the backend, `backend/instructions.md`, served by the API: the agent fetches them at the start of each run, and the dashboard shows the same text read only.

**When the backend refuses.** A 409 or 422 from the backend is an answer the agent can act on, such as a payment waiting for sign-off or a decision missing its policy section, so the tool returns the backend's reason to the model as the tool's result. Any other error, such as the backend being down or a 500, propagates and stops the run.

**When to refer.** The spec says the claims manual explains referrals, and the manual is out of scope for the pilot. So the instructions say when to refer using the wording alone: when a document the wording asks for is missing, when the documents contradict the story or each other, or when the wording doesn't settle the claim.

**What the agent is doing.** `run(claim_id, thread_id)` streams the agent's progress and posts each step to the backend as it happens: each tool it calls, a short summary of each result and its final reply. The dashboard polls the claim while it's in progress, so the handlers watch the steps appear.

The steps hold tool results, which can include a claimant's medical details. They are product data for the handlers, who see the full claim anyway, and they never go to the console or a log.

**The command line.** `uv run -m agent` works every waiting claim in queue order; `uv run -m agent CLM-1001` works one claim. It needs the backend running (`npm run dev`); if the backend isn't up, it says "Start the backend with npm run dev" rather than showing a connection error. Each run gets a fresh thread id. It prints only each claim's id and its outcome, such as `CLM-1001 approve $420.00`. If a run ends without a decision, or approves within the limit without paying, the command fails with that message and the claim stays as it is; starting an in-progress claim again is allowed. Working the whole queue stops at the first failure and names the claim, following the fail-fast rule.

**The dashboard's addresses.** There's no router, so each page has an address in the URL's hash, such as `#CLM-1001` for a claim and `#instructions` for the instructions. A refresh, the back button and a shared link all land on the same page.

**No new dependencies.** SQLite is in Python's standard library, FastAPI brings Pydantic, and the dashboard uses React alone, without a router. Coverage thresholds rise from 80% to the 95% that `docs/PROCESS.md` asks for.

**Not in this build.** The handlers' decisions in `data/evals/` aren't used to score the agent here. The spec keeps them for checking the agent's work later, and evaluations come in a later build, so nothing in the pilot opens them.

## The API

Every operation has an `operation_id`, a one-line docstring and no optional inputs.

| Operation | Route | What it does |
|---|---|---|
| `health` | `GET /api/health` | Already built |
| `list_claims` | `GET /api/claims` | The queue in order, with each claim's status |
| `get_claim` | `GET /api/claims/{claim_id}` | The claim in full, with its decision, payment, sign-off and steps |
| `get_policy` | `GET /api/claims/{claim_id}/policy` | The claim's policy, with its plan's limits and add-ons |
| `get_claim_history` | `GET /api/claims/{claim_id}/history` | The customer's name, customer-since date and previous claims |
| `get_policy_wording` | `GET /api/policy-wording` | The policy wording as Markdown |
| `get_instructions` | `GET /api/instructions` | The agent's instructions as Markdown |
| `list_handlers` | `GET /api/handlers` | The claims handlers |
| `start_claim` | `POST /api/claims/{claim_id}/start` | Moves a waiting or in-progress claim to in progress |
| `record_step` | `POST /api/claims/{claim_id}/steps` | Adds one step to the claim's activity |
| `record_decision` | `POST /api/claims/{claim_id}/decision` | Records the decision on an in-progress claim and sets the status |
| `pay_claim` | `POST /api/claims/{claim_id}/payment` | Pays the amount, if the rules allow it |
| `sign_off` | `POST /api/claims/{claim_id}/sign-off` | A handler signs off an over-limit payout, which releases the payment |

An unknown claim or handler answers 404. A request in the wrong state answers 409 with the reason, such as "This claim is not in progress".

## The phases

Each phase says what it builds, then lists the tests and checks that show it works. The tests are written first, as `docs/PROCESS.md` asks, and they're the boxes that get ticked.

## Phase 1: the records in the backend

The database, the seed loading and the read operations. Everything later reads these records, so they come first.

### Implementation

- `backend/` gets modules for the database and seeding, the Pydantic models and the routes, with `ClaimStatus` as an enum
- On start, the backend creates the database if the file doesn't exist and loads it from `data/`, with every claim `waiting`. An existing database is kept as it is
- `UNDERCOVER_DB` sets the database file, defaulting to `undercover.db` at the repo root. A pytest fixture gives each test its own temporary file
- Amounts are `Decimal` in the code, whole cents in the database and JSON numbers in the API
- The read operations: `list_claims`, `get_claim`, `get_policy`, `get_claim_history`, `get_policy_wording` and `list_handlers`. `get_claim_history` returns the customer's name, customer-since date and previous claims, and leaves out the email, phone, address and date of birth, which are never loaded into the database
- An unknown claim id answers 404
- The coverage threshold in `pyproject.toml` rises from 80% to 95%

### Tests and checks

With pytest:

- [x] With no database file, starting the backend creates one and loads 25 claims, all `waiting`
- [x] Starting it again on the same file keeps the existing data and doesn't load the seed a second time
- [x] With `UNDERCOVER_DB` set to a temporary path, the database is created there, and no `undercover.db` appears at the repo root after the tests run
- [x] `GET /api/claims` returns 25 claims in the order of `data/claims.json`, starting with CLM-1001, each with its id, type, summary, amount claimed and status
- [x] In that response, CLM-1001 has `"amount_claimed": 420.0`, a JSON number, not a string
- [x] `GET /api/claims/CLM-1001` returns the story, items and documents, with no decision, payment or steps yet
- [x] `GET /api/claims/CLM-1001/policy` returns POL-2001 on the Premium plan with its limits (such as `baggage_max` 1500.00) and its add-ons
- [x] `GET /api/claims/CLM-1001/history` returns customer CUS-3001, Maya Patel, with her previous claim CLM-0412, and the response has no `email`, `phone`, `address` or `date_of_birth`
- [x] `GET /api/policy-wording` returns the wording, starting "# UnderCover Travel Insurance: Policy Wording"
- [x] `GET /api/handlers` returns the three handlers
- [x] `GET /api/claims/CLM-9999` answers 404

Commands:

- [x] A search of `backend/` finds no reference to `data/evals/`, `data/security/` or `data/claims_manual.md`
- [x] `npm run check:python` passes at the 95% coverage threshold

## Phase 2: decisions, payments and sign-off

The write operations and the rules they enforce. The payment rule is the heart of the pilot, so it's built and tested in the backend before any agent can call it.

### Implementation

- `backend/instructions.md` holds the agent's instructions: work one claim, read the claim, policy, history and wording, decide by the wording alone, work out the payout using the plan's limits and deductible, explain in two or three polite, professional sentences, cite the section, record the decision, then pay an approval
- The instructions say when to refer: a document the wording asks for is missing, the documents contradict the story or each other, or the wording doesn't settle the claim
- `get_instructions` serves that file's text
- `start_claim` moves a waiting or in-progress claim to `in_progress`, and answers 409 for any other status
- `record_step` adds one step to the activity of a claim that has been started, and `get_claim` returns the steps in order. Steps keep arriving after the decision, from the payment and the agent's final reply, so only a waiting claim refuses them
- `record_decision` takes the three decision types as separate models, so a payout on a `decline` or `refer` is rejected. It works only on an in-progress claim, and only once. An `approve` over the limit in `data/company.json` sets `waiting_for_sign_off`; every other decision sets `decided`
- `pay_claim` takes the amount and pays only when the claim is approved, the amount equals the payout, it isn't paid already, and the payout is within the limit or signed off. Otherwise it answers 409 with the reason
- `sign_off` takes a handler id. On a claim waiting for sign-off, it sets `decided`, records who signed off and when, and records the payment

### Tests and checks

With pytest:

- [x] `GET /api/instructions` returns the text of `backend/instructions.md`
- [x] `start_claim` moves CLM-1001 from `waiting` to `in_progress`
- [x] `start_claim` answers 409 for a decided claim
- [x] Two `record_step` calls on an in-progress claim come back from `get_claim` in order
- [x] `record_step` answers 409 for a claim that hasn't been started
- [x] `record_decision` answers 409 for a claim that's waiting, waiting for sign-off or decided
- [x] Recording `approve` with a payout of 420.00 sets the status to `decided`
- [x] Recording `approve` with a payout of 1,250.00 sets the status to `waiting_for_sign_off`
- [x] Recording `decline` or `refer` sets the status to `decided`
- [x] A `decline` with a payout is rejected with 422
- [x] A second decision on the same claim answers 409
- [x] `pay_claim` pays an approved claim within the limit, and `get_claim` then shows the payment
- [x] `pay_claim` answers 409 for each of: an over-limit claim not yet signed off, an amount that differs from the payout, a claim already paid, and a declined or referred claim
- [x] `sign_off` by HND-01 on a `waiting_for_sign_off` claim sets it to `decided`, with who signed off and when, and the payment recorded
- [x] After that sign-off, `pay_claim` answers 409 as already paid
- [x] `sign_off` answers 409 for a claim that isn't waiting for sign-off
- [x] `sign_off` answers 404 for an unknown handler

Reviews and commands:

- [x] `backend/instructions.md` covers each point above, including the three reasons to refer
- [x] `npm run check:python` passes

## Phase 3: the UnderCover Agent

The agent's tools, its run and the command line. The backend already enforces the rules, so the agent only has to call the API, and tests with a stub model can drive it down every path without calling a real one.

### Implementation

- `agent/` gets tools for `get_claim`, `get_policy`, `get_claim_history`, `get_policy_wording`, `record_decision` and `pay_claim`. Each calls the backend's API and nothing else, so the agent never reads `data/`
- The `get_claim` tool leaves out the claim's decision, payment, sign-off and steps
- A 409 or 422 from the backend becomes the tool's result, with the backend's reason. Any other error propagates and stops the run
- `run(claim_id, thread_id)` fetches the instructions from `GET /api/instructions`, starts the claim, streams the agent and posts each tool call, a summary of each tool result and the final reply as steps
- When the agent finishes, `run` raises an error if there's no decision, or "approved but not paid" if it approved within the limit and didn't pay
- The command line: `uv run -m agent CLM-1001` works one claim, and `uv run -m agent` works every waiting claim in queue order, stopping at the first failure and naming the claim. Each run gets a fresh thread id. It prints only each claim's id and outcome, and says "Start the backend with npm run dev" when it can't reach the backend
- The model stays `openai/gpt-6-luna` with low reasoning effort, or `MODEL_NAME` when it's set

### Tests and checks

With pytest, a stub model and the backend in-process:

- [x] The stub model gets the text of `backend/instructions.md` as its instructions
- [x] Working CLM-1001 through to an approval and payment leaves the claim `decided` and paid, with steps for each tool call, each result's summary and the final reply
- [x] Approving an over-limit claim and then trying to pay leaves it `waiting_for_sign_off` and unpaid, with the refusal recorded as a step
- [x] The `get_claim` tool returns CLM-1001 with no decision, payment, sign-off or steps
- [x] Recording a decision on a claim that isn't in progress gives the model the 409 reason as the tool's result
- [x] A 500 from the backend (a fake one, since the real backend has no way to fail on request) propagates and stops the run
- [x] A run that ends without a decision raises an error saying so, and the claim stays `in_progress`
- [x] A run that approves within the limit and never pays raises "approved but not paid"

With pytest, a stub model and the backend in-process, for the command line:

- [x] `uv run -m agent CLM-1001` works only that claim
- [x] `uv run -m agent` works every waiting claim in queue order
- [x] When a claim fails partway through the queue, the command stops there and names the claim that failed
- [x] The output is only claim ids and outcomes, such as `CLM-1001 approve $420.00`, and never a claim's story, documents or tool results
- [x] With no backend running, the command says "Start the backend with npm run dev"
- [x] The model is `openai/gpt-6-luna` with low reasoning effort, or `MODEL_NAME` when set (the existing test, kept)

Commands:

- [x] A search of `agent/` finds no reads of `data/`
- [x] `npm run check:python` passes

## Phase 4: the queue and the claim in the dashboard

The handlers' main screens, in the brand in `docs/BRAND.md`. Everything else in the dashboard sits on these two pages, so they come first.

### Implementation

- The brand: Libre Franklin and JetBrains Mono, a Sky Blue header band, small corners and hairline outlines, in light and dark modes
- The header band shows UnderCover and links to the queue and the instructions
- The queue page lists every claim in order, with its id, type, summary, amount claimed and a status label for waiting, in progress, waiting for sign-off or decided, and a count of each status above the list
- The claim page shows the story, the items with amounts, the documents, the policy and plan, and the decision with its explanation, policy section and payout, or "No decision yet". An approved claim within the limit with no payment shows "Approved, not paid"
- Each page has its address in the hash: no hash is the queue (as is `#queue`, which the header links to) and `#CLM-1001` is that claim. The page follows the hash, so a refresh, the back button and a shared link land on the same page
- Amounts are formatted as US dollars, such as $1,250.00
- The coverage threshold in `dashboard/vite.config.ts` rises from 80% to 95%

### Tests and checks

With vitest, with `fetch` stubbed:

- [x] The queue shows all 25 claims in order, each with its id, type, summary, amount claimed and status label
- [x] The counts above the queue match the claims' statuses
- [x] Choosing a claim opens it in full: the story, the items with amounts, the documents, and the policy and plan
- [x] An `approve`, a `decline` and a `refer` each show their explanation and policy section, an approval shows its payout, and a claim with no decision shows "No decision yet"
- [x] An approved claim within the limit with no payment shows "Approved, not paid"
- [x] The hash `#CLM-1001` opens that claim, and no hash shows the queue
- [x] Amounts show as US dollars, such as $1,250.00

In the browser, with the Playwright MCP server:

- [x] The header band shows UnderCover and links to the queue and the instructions
- [x] The queue and CLM-1001 render in the brand in light and dark mode, with no console errors
- [x] Opening `#CLM-1001` directly, refreshing it, and pressing back to the queue each land on the right page

Commands:

- [x] `npm run check:ts` passes at the 95% coverage threshold

## Phase 5: the agent's steps, its instructions and sign-off

The parts of the dashboard that follow the agent as it works and let a handler release a large payout. They build on the backend's steps and sign-off from Phase 2 and the pages from Phase 4.

### Implementation

- A claim's page shows the agent's steps in order, and polls every two seconds while it's open, so new steps appear without a reload. It keeps polling after the decision, because the payment and the agent's final reply come after it
- The instructions page, at `#instructions`, shows the agent's instructions read only, from `GET /api/instructions`
- A claim waiting for sign-off shows the payout and a sign-off control: choose a handler, then sign off. A refused sign-off shows the backend's reason
- A claim's page shows its payment, or that the payment waits for sign-off. After sign-off, it shows who signed off and when

### Tests and checks

With vitest, with `fetch` stubbed:

- [x] A claim's steps show in order
- [x] While a claim is in progress, a new step appears within two seconds without a reload
- [x] `#instructions` shows the instructions read only
- [x] Signing off a claim that's waiting for sign-off shows it as decided, with who signed off, when, and the payment
- [x] A refused sign-off shows the backend's reason
- [x] A paid claim shows its payment, and an over-limit approval shows that the payment waits for sign-off

In the browser, with the Playwright MCP server:

- [x] After recording an over-limit approval with the API, the claim shows the sign-off control, and signing off as Dana Whitfield (HND-01) shows the payment

Commands:

- [x] `npm run check:ts` passes

## Phase 6: end to end, and a real run

Playwright runs the whole product together, and one real run shows the agent working with a real model. This comes last because it needs every earlier phase.

### Implementation

- `playwright.config.ts` starts its own backend on port 8100, with a fresh database in `e2e/test-results/` through `UNDERCOVER_DB`, and its own dashboard on port 5174 that proxies to it, so it never touches `undercover.db` or a running `npm run dev`
- End-to-end tests in `e2e/` set up decisions through the API rather than a model
- `docs/STATUS.md` says what's built and how to run it: `npm run dev` first, then `uv run -m agent` or `uv run -m agent CLM-1001`, `npm run check`, and deleting `undercover.db` to start again

### Tests and checks

With Playwright end-to-end tests:

- [x] The queue shows 25 waiting claims
- [x] A claim shows its decision and steps
- [x] The instructions page shows the instructions
- [x] An over-limit claim is signed off in the browser and then shows the payment

Commands:

- [x] The end-to-end tests pass while `npm run dev` is running, and leave `undercover.db` unchanged
- [x] A real run of `uv run -m agent CLM-1001` with the model from `.env` decides the claim, and the dashboard shows its steps and decision. This calls the model once, for a few cents, or for free with `MODEL_NAME=openrouter/free`
- [x] Following `docs/STATUS.md` from a fresh database works as written
- [x] `npm run check` passes
