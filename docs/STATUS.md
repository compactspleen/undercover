# Status

The pilot in `docs/PLAN.md` is built: the backend, the UnderCover Agent and the dashboard.

## What's built

- `backend/`: FastAPI and SQLite. It creates `undercover.db` from `data/` on first start and serves every operation in `docs/PLAN.md`:
  - reads: the queue, a claim, its policy, the customer's claim history (without contact details or date of birth), the policy wording, the agent's instructions and the handlers
  - writes: starting a claim, recording a step, recording a decision, paying a claim and a handler's sign-off
  - the rules: a decision only on a claim in progress and only once, and no payment over $1,000 until a handler signs off, which releases it
  - `GET /api/health`: checks that the backend can read its database, the policy wording and the agent's instructions. It answers 200 when all three pass, or 503 naming the check that failed
- `backend/instructions.md`: the agent's instructions, which the agent fetches at the start of each run and the dashboard shows read only
- `agent/`: the UnderCover Agent. `run(claim_id, thread_id)` starts the claim and works it with six tools that call the backend: `get_claim`, `get_policy`, `get_claim_history`, `get_policy_wording`, `record_decision` and `pay_claim`. It posts each step to the backend as it goes: each tool call, each tool's result in full and its final reply. A run fails if it ends without a decision, or approves a claim within the limit without paying it
- `dashboard/`: the handlers' screens in the brand in `docs/BRAND.md`, in light and dark mode:
  - the queue, with each claim's customer, its status, its decision and the payout an approval set beside the amount claimed, and a count of each status
  - a claim's page, at an address such as `#CLM-1001`: the customer's name; the story, items, documents, policy and plan down the left; and the decision, the payment and the agent's steps down the right, refreshed every two seconds. It flags "Approved, not paid" for an approval within the limit that wasn't paid, and has a sign-off control for a payout waiting for sign-off
  - the agent's instructions, read only, at `#instructions`
- `e2e/`: Playwright tests of the queue, a claim's decision and steps, the instructions and a sign-off in the browser

## Running it

1. `npm run dev` starts the backend on port 8000 and the dashboard on http://localhost:5173. The backend's log starts each line with the time in UTC, such as `2026-11-22T21:10:47.184Z`, set by `backend/log_config.json`. Each open claim page fetches its claim every two seconds, so two pages open on the same claim log a fetch about once a second
2. In another terminal, `uv run -m agent` works every waiting claim in queue order, and `uv run -m agent CLM-1001` works one claim

The agent prints only each claim's id and outcome, such as `CLM-1001 approve $420.00`, and stops at the first claim that fails. It uses `openai/gpt-6-luna` on OpenRouter with the key in `.env`, or the model in `MODEL_NAME`, such as `openrouter/free`. It calls the model at most 20 times a minute, evenly spaced, which is our OpenRouter account's limit for now; `MODEL_REQUESTS_PER_MINUTE` in `.env` changes the rate, and must be a whole number above 0. If OpenRouter's rate limit stops it anyway, it names the claim it was working, which stays in progress, so run that claim again by name, such as `uv run -m agent CLM-1004`. It checks the backend's health first. If the backend isn't running, it says "Start the backend with npm run dev", and if the backend can't read its database or documents, it says which, such as "The backend is running but can't read its database".

`npm run check` runs every check: ruff, pyright and pytest; Prettier, ESLint, tsc and vitest; and the Playwright tests. The Playwright tests start their own backend on port 8100, with a fresh database in `e2e/test-results/`, and their own dashboard on port 5174, so they can run while `npm run dev` is running.

## The database

The backend keeps its data in `undercover.db` at the repo root, which git ignores. It's created from `data/` the first time the backend starts. The environment variable `UNDERCOVER_DB` points the backend at another file.

`uv run -m backend.seed` rebuilds the database from `data/`, putting every claim back in the queue as waiting. It shows where the claims stand and asks you to type `yes` first, because every decision, payment, sign-off and step is lost. It keeps the old database in `undercover.backup.db`, replacing any earlier backup. A running backend picks up the rebuilt database straight away. Nothing reads `data/evals/`, `data/security/` or the claims manual.
