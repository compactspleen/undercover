import { useState } from "react";
import type { Step, StepKind } from "./api";
import { formatTime } from "./format";

const KIND_LABELS: Record<StepKind, string> = {
  tool_call: "Tool call",
  tool_result: "Result",
  reply: "Reply",
};
// The agent writes a call as `name {arguments}` and a result as `name: result`.
const NAME_END = /[ :]/;
const RESULT_SEPARATOR = ": ";
const PREVIEW_LENGTH = 120;

/** A tool call and, once the tool answers, its result. */
interface ToolUse {
  call: Step;
  result: Step | null;
}

type Entry = ToolUse | Step;

export function Steps({ steps }: Readonly<{ steps: Step[] }>) {
  return (
    <section className="panel" aria-labelledby="steps">
      <h2 id="steps">Agent&apos;s steps</h2>
      {steps.length === 0 ? (
        <p className="note">No steps yet</p>
      ) : (
        <ol className="steps">
          {paired(steps).map((entry) => (
            <EntryItem key={keyOf(entry)} entry={entry} />
          ))}
        </ol>
      )}
    </section>
  );
}

/** Pair each tool call with its result, and leave every other step on its own. */
function paired(steps: Step[]): Entry[] {
  const entries: Entry[] = [];
  for (const step of steps) {
    if (step.kind === "tool_call") entries.push({ call: step, result: null });
    else if (!isAnswer(entries, step)) entries.push(step);
  }
  return entries;
}

/**
 * Give a result to the latest call to its tool that has none yet, and say if
 * there was one. Results arrive as the tools finish, not in the order of the
 * calls, and a run that stopped can leave a call with no result before a
 * rerun calls the same tool.
 */
function isAnswer(entries: Entry[], step: Step): boolean {
  if (step.kind !== "tool_result") return false;
  const use = entries.findLast(
    (entry): entry is ToolUse =>
      "call" in entry &&
      entry.result === null &&
      toolName(entry.call) === toolName(step),
  );
  if (!use) return false;
  use.result = step;
  return true;
}

function toolName(step: Step): string {
  return step.text.split(NAME_END, 1)[0] ?? step.text;
}

/** The tool's answer, without the tool's name in front. */
function resultText(result: Step): string {
  return result.text.slice(toolName(result).length + RESULT_SEPARATOR.length);
}

/** Lay a JSON result out over several lines, and leave any other as it is. */
function laidOut(text: string): string {
  try {
    return JSON.stringify(JSON.parse(text), null, 2);
  } catch {
    return text;
  }
}

function preview(text: string): string {
  if (text.length <= PREVIEW_LENGTH) return text;
  return `${text.slice(0, PREVIEW_LENGTH)}…`;
}

// The key stays the same as the claim refreshes, so an open result stays open.
function keyOf(entry: Entry): string {
  const first = "call" in entry ? entry.call : entry;
  return `${first.recorded_at} ${first.text}`;
}

function EntryItem({ entry }: Readonly<{ entry: Entry }>) {
  if ("call" in entry) return <ToolUseItem use={entry} />;
  return <StepItem step={entry} />;
}

function ToolUseItem({ use }: Readonly<{ use: ToolUse }>) {
  return (
    <li className="step step-tool_call">
      <StepHeading step={use.call} />
      <p className="step-text mono">{use.call.text}</p>
      {use.result ? (
        <Result result={use.result} />
      ) : (
        <p className="note">No result</p>
      )}
    </li>
  );
}

function Result({ result }: Readonly<{ result: Step }>) {
  const [isOpen, setIsOpen] = useState(false);
  const text = resultText(result);
  return (
    <div className="result">
      <button
        type="button"
        className="disclosure"
        aria-expanded={isOpen}
        onClick={() => {
          setIsOpen(!isOpen);
        }}
      >
        <span className="eyebrow">Result</span>{" "}
        <span className="result-preview mono">{preview(text)}</span>
      </button>
      {isOpen && <pre className="result-text">{laidOut(text)}</pre>}
    </div>
  );
}

function StepItem({ step }: Readonly<{ step: Step }>) {
  return (
    <li className={`step step-${step.kind}`}>
      <StepHeading step={step} />
      <p className={step.kind === "reply" ? "prose" : "step-text mono"}>
        {step.text}
      </p>
    </li>
  );
}

function StepHeading({ step }: Readonly<{ step: Step }>) {
  return (
    <p className="step-heading">
      <span className="eyebrow">{KIND_LABELS[step.kind]}</span>{" "}
      <time className="meta" dateTime={step.recorded_at}>
        {formatTime(step.recorded_at)}
      </time>
    </p>
  );
}
