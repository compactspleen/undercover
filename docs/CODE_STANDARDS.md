# Code standards

Where a rule here and the existing code disagree, follow the rule in new code and don't rewrite old code just to conform. Never loosen a rule yourself: if one can't be followed, stop and ask. When rules pull against each other: tests pass, then intent is clear, then no duplication, then fewest parts.

## General

1. Keep it simple, do not overcomplicate. Build only what the docs ask for now: no speculative features, options or extension points.
2. Comments only when necessary: they give reasons, constraints or warnings, never what the code does. If a name needs a comment, rename it. Delete commented-out code.
3. Be concise: a short README and no emojis.
4. IMPORTANT: avoid overly defensive code. Handle exceptions only when necessary.
5. Use uv: ALWAYS `uv run`, NEVER `python3`.
6. TypeScript: strict mode, never `any`.

## Code

7. Short functions, about 7 lines of code. Track about 4 things at once (inputs, named values, branches): return early, and group related values into one type. Don't cram lines to fit, and don't split a function into pieces that only make sense together.
8. Prefer duplication over the wrong abstraction: merge only copies that would always change together. If a shared helper needs a new flag or branch for one caller, inline it back. Input-to-output mappings are lookup tables, not if/else chains.
9. A string or number used more than once becomes a named constant at the top of the module, and a fixed set of values becomes an enum. One-off literals are fine, as are `""`, 0 and 1 in their ordinary meaning.
10. No flag arguments: two named functions, not a boolean that switches behavior.
11. Type every parameter and return value. No `# type: ignore`, `Any` or casts to silence the checker.
12. Make illegal states unrepresentable: one type per case, not optional fields plus flags.
13. Prefer pure functions and immutable data. Keep side effects (I/O, the clock, randomness, the environment, model calls) at the edges.
14. Full-word names; abbreviate only loop counters and common terms (id, url). Functions are verbs, values are nouns, booleans are yes/no questions (`is_`, `has_`).
15. Format with Ruff and Prettier; never hand-format or reformat untouched code. One statement per line, no nested ternaries.

## Tests

16. Every behavior change has a test that fails without it.
17. Test through public interfaces: never import private names (`_x`) in tests, and don't make code public just to test it. Assert visible results, not internal state or call order.
18. Prefer fakes to mocks; pure code needs neither.
19. Never write tests just to raise coverage.

## Errors and security

20. Fail fast: catch only what you can handle, and otherwise let the error propagate. No empty catches, and no `None`, -1 or `""` to hide a failure.
21. Parse untrusted input (requests, files, model output, the environment) once at the boundary into precise types, such as Pydantic models, and don't re-check it inside.
22. No secrets in code, config, logs or git; load them from `.env` at runtime. If a secret is ever committed, rotate it.
23. Never log keys, tokens or claimants' personal or health data.
24. Use established libraries for auth, crypto and parsing.
25. Destructive operations: dry-run first, back up, write atomically, confirm. Never run them on real data while testing.

## Version control and dependencies

26. One logical change per commit; refactors go in their own commit.
27. Commit messages follow Conventional Commits (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`).
28. Commit `uv.lock` and `package-lock.json`, and change dependencies only through `uv add` / `uv remove` and `npm install`. Never edit a lockfile by hand.
29. Add only the dependencies the docs or the approved plan name; ask before adding any other, and prefer the standard library.
30. Never commit generated output, `.env` or personal data; gitignore them.
