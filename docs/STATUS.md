# Status

The pilot is being built from `docs/PLAN.md`.

## Built so far

- `backend/`: a SQLite database created from `data/` on first start, and every operation in `docs/PLAN.md`:
  - reads: the queue, a claim, its policy, the customer's claim history, the policy wording, the agent's instructions and the handlers
  - writes: starting a claim, recording a step, recording a decision, paying a claim and a handler's sign-off
  - the rules: a decision only on a claim in progress and only once, and no payment over $1,000 until a handler signs off, which releases it
- `backend/instructions.md`: the agent's instructions
- `agent/`: the UnderCover Agent. `run(claim_id, thread_id)` fetches its instructions, starts the claim and works it with six tools that call the backend: `get_claim`, `get_policy`, `get_claim_history`, `get_policy_wording`, `record_decision` and `pay_claim`. It posts each step to the backend as it goes, and fails if the run ends without a decision or approves a claim within the limit without paying it
- `dashboard/`: the skeleton's page that shows whether the backend is up
- `e2e/`: one test of that page

## Running it

- `npm run dev` starts the backend on port 8000 and the dashboard on port 5173
- `uv run -m agent` works every waiting claim in queue order, and `uv run -m agent CLM-1001` works one claim. Both need `npm run dev` running first. They print only each claim's id and outcome, such as `CLM-1001 approve $420.00`, and stop at the first claim that fails. The model is `openai/gpt-6-luna` on OpenRouter, or the one in `MODEL_NAME`, such as `openrouter/free`
- `npm run check` runs every check

The backend keeps its data in `undercover.db` at the repo root, which git ignores. It's created from `data/` the first time the backend starts. To start again from the seed data, stop the backend and delete `undercover.db`. The environment variable `UNDERCOVER_DB` points the backend at another file.
