import type { Step, StepKind } from "./api";
import { formatTime } from "./format";

const KIND_LABELS: Record<StepKind, string> = {
  tool_call: "Tool call",
  tool_result: "Result",
  reply: "Reply",
};

export function Steps({ steps }: Readonly<{ steps: Step[] }>) {
  return (
    <section className="panel" aria-labelledby="steps">
      <h2 id="steps">Agent&apos;s steps</h2>
      {steps.length === 0 ? (
        <p className="note">No steps yet</p>
      ) : (
        <ol className="steps">
          {steps.map((step) => (
            <li
              key={`${step.recorded_at} ${step.text}`}
              className={`step step-${step.kind}`}
            >
              <p className="step-heading">
                <span className="eyebrow">{KIND_LABELS[step.kind]}</span>{" "}
                <time className="meta" dateTime={step.recorded_at}>
                  {formatTime(step.recorded_at)}
                </time>
              </p>
              <p className={step.kind === "reply" ? "prose" : "step-text mono"}>
                {step.text}
              </p>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
