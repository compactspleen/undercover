import { vi } from "vitest";

export type Answer = () => Response;

export function json(body: unknown, status = 200): Answer {
  return () => Response.json(body, { status });
}

/** Stub `fetch` with answers keyed by method and path, such as "GET /api/claims". */
export function fakeBackend(answers: Partial<Record<string, Answer>>) {
  const fetch = vi.fn((path: string, init?: RequestInit) => {
    const answer = answers[`${init?.method ?? "GET"} ${path}`];
    return Promise.resolve(
      answer ? answer() : json({ detail: "Not found" }, 404)(),
    );
  });
  vi.stubGlobal("fetch", fetch);
  return fetch;
}
