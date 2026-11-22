# Status

The pilot is being built from `docs/PLAN.md`.

## Built so far

- `backend/`: a SQLite database created from `data/` on first start, and every operation in `docs/PLAN.md`:
  - reads: the queue, a claim, its policy, the customer's claim history, the policy wording, the agent's instructions and the handlers
  - writes: starting a claim, recording a step, recording a decision, paying a claim and a handler's sign-off
  - the rules: a decision only on a claim in progress and only once, and no payment over $1,000 until a handler signs off, which releases it
- `backend/instructions.md`: the agent's instructions
- `agent/`: the skeleton's entry point `run(claim_id, thread_id)`, with one tool that calls the health route
- `dashboard/`: the skeleton's page that shows whether the backend is up
- `e2e/`: one test of that page

## Running it

- `npm run dev` starts the backend on port 8000 and the dashboard on port 5173
- `npm run check` runs every check

The backend keeps its data in `undercover.db` at the repo root, which git ignores. It's created from `data/` the first time the backend starts. To start again from the seed data, stop the backend and delete `undercover.db`. The environment variable `UNDERCOVER_DB` points the backend at another file.
