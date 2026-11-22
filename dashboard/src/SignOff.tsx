import { useState } from "react";
import type { Handler } from "./api";
import { getJson, post, reasonOf } from "./api";
import { Show } from "./Show";
import { useLoaded } from "./useLoaded";

/** Choose a handler and sign off an over-limit payout, which releases the payment. */
export function SignOff({
  claimId,
  onSignedOff,
}: Readonly<{ claimId: string; onSignedOff: () => void }>) {
  const [handlers] = useLoaded("/api/handlers", getJson<Handler[]>);
  const [handlerId, setHandlerId] = useState("");
  const [refusal, setRefusal] = useState("");

  function signOff() {
    setRefusal("");
    post(`/api/claims/${claimId}/sign-off`, { handler_id: handlerId }).then(
      onSignedOff,
      (error: unknown) => {
        setRefusal(reasonOf(error));
      },
    );
  }

  return (
    <Show loaded={handlers}>
      {(list) => (
        <form
          className="sign-off"
          onSubmit={(event) => {
            event.preventDefault();
            signOff();
          }}
        >
          <label className="field">
            <span className="eyebrow">Handler</span>
            <select
              value={handlerId}
              onChange={(event) => {
                setHandlerId(event.target.value);
              }}
            >
              <option value="">Choose a handler</option>
              {list.map((handler) => (
                <option key={handler.handler_id} value={handler.handler_id}>
                  {handler.name}
                </option>
              ))}
            </select>
          </label>
          <button type="submit" disabled={handlerId === ""}>
            Sign off
          </button>
          {refusal && (
            <p className="note note-alert" role="alert">
              {refusal}
            </p>
          )}
        </form>
      )}
    </Show>
  );
}
