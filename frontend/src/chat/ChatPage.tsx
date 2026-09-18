import { useEffect, useMemo, useRef, useState } from "react";
import { ApiError, type ChatResponse, sendChat } from "../api/client";
import { BrainSchematic } from "../brain/BrainSchematic";
import { format, texts, ui } from "../i18n/text";
import { Composer } from "./Composer";
import { HowPanel } from "./HowPanel";
import { ExampleChips, OutOfScopeHint } from "./OutOfScopeHint";
import { useScenarioInfo } from "./useScenarioInfo";

const LIVE_HINT_AFTER_MS = 4000;
const ELAPSED_TICK_MS = 1000;

type Turn =
  | { id: number; message: string; state: "pending" }
  | { id: number; message: string; state: "done"; response: ChatResponse }
  | { id: number; message: string; state: "error"; error: string };

export function ChatPage() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [draft, setDraft] = useState("");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [slow, setSlow] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const nextId = useRef(1);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const { names: groupNames, packageProblem } = useScenarioInfo();

  const pending = turns.some((t) => t.state === "pending");
  const lastTurnId = turns.at(-1)?.id;

  useEffect(() => {
    if (!pending) {
      setSlow(false);
      setElapsed(0);
      return;
    }
    const started = Date.now();
    const hint = setTimeout(() => setSlow(true), LIVE_HINT_AFTER_MS);
    // Uzun süren canlı simülasyonlarda arayüz donmuş görünmesin: geçen süre sayılır.
    const ticker = setInterval(
      () => setElapsed(Math.round((Date.now() - started) / 1000)),
      ELAPSED_TICK_MS,
    );
    return () => {
      clearTimeout(hint);
      clearInterval(ticker);
    };
  }, [pending]);

  useEffect(() => {
    if (lastTurnId !== undefined) endRef.current?.scrollIntoView?.({ block: "end" });
  }, [lastTurnId]);

  const shown = useMemo(() => {
    const done = turns.filter((t): t is Extract<Turn, { state: "done" }> => t.state === "done");
    return done.find((t) => t.id === selectedId) ?? done.at(-1) ?? null;
  }, [turns, selectedId]);

  const activeReadouts = useMemo(
    () =>
      new Set(
        shown?.response.output.behaviors.filter((b) => b.active).map((b) => b.readout_group) ?? [],
      ),
    [shown],
  );

  async function send(text: string) {
    const message = text.trim();
    if (!message || pending) return;
    const id = nextId.current++;
    setTurns((all) => [...all, { id, message, state: "pending" }]);
    setDraft("");
    try {
      const response = await sendChat(message);
      setTurns((all) =>
        all.map((t) => (t.id === id ? { id, message, state: "done", response } : t)),
      );
      setSelectedId(id);
    } catch (error) {
      const detail = error instanceof ApiError ? error.detail : String(error);
      setTurns((all) =>
        all.map((t) => (t.id === id ? { id, message, state: "error", error: detail } : t)),
      );
    }
  }

  function pick(example: string) {
    setDraft(example);
    inputRef.current?.focus();
  }

  return (
    <div className="chat-layout">
      <section className="chat" aria-label={ui.tabs.chat}>
        {packageProblem && (
          <p className="banner" role="status">
            {format(ui.package_warning, { detail: packageProblem })}
          </p>
        )}
        <div className="chat__log" role="log" aria-live="polite" aria-relevant="additions">
          {turns.length === 0 && (
            <div className="welcome">
              <h2>{ui.welcome.title}</h2>
              <p>{ui.welcome.body}</p>
              <p className="welcome__try">{ui.welcome.try}</p>
              <ExampleChips examples={texts.chat.out_of_scope_examples} onPick={pick} />
            </div>
          )}

          {turns.map((turn) => (
            <div key={turn.id} className="turn">
              <div className="bubble bubble--user">
                <span className="visually-hidden">{ui.you}: </span>
                {turn.message}
              </div>

              {turn.state === "pending" && (
                <div className="bubble bubble--fly bubble--pending">
                  <span className="spinner" aria-hidden="true" />
                  <span>{slow ? ui.pending_live : ui.pending}</span>
                  {elapsed > 0 && (
                    <span className="pending-elapsed">
                      {format(ui.pending_elapsed, { seconds: elapsed })}
                    </span>
                  )}
                </div>
              )}

              {turn.state === "error" && (
                <div className="bubble bubble--fly bubble--error" role="alert">
                  <p>{format(ui.error, { detail: turn.error })}</p>
                  <button
                    type="button"
                    className="button"
                    disabled={pending}
                    onClick={() => {
                      setTurns((all) => all.filter((t) => t.id !== turn.id));
                      void send(turn.message);
                    }}
                  >
                    {ui.retry}
                  </button>
                </div>
              )}

              {turn.state === "done" && (
                <article
                  className={
                    shown?.id === turn.id
                      ? "bubble bubble--fly bubble--selected"
                      : "bubble bubble--fly"
                  }
                >
                  <header className="bubble__header">
                    <span className="bubble__who">
                      <span aria-hidden="true">🪰</span> {ui.fly}
                    </span>
                    <span className="source-chip">
                      {turn.response.presentation.source === "llm"
                        ? format(ui.source.llm, { model: turn.response.presentation.model ?? "" })
                        : ui.source.template}
                    </span>
                  </header>
                  <p className="bubble__text">{turn.response.presentation.text}</p>
                  {turn.response.hint && <OutOfScopeHint hint={turn.response.hint} onPick={pick} />}
                  <div className="bubble__actions">
                    {shown?.id !== turn.id && (
                      <button
                        type="button"
                        className="link-button"
                        onClick={() => setSelectedId(turn.id)}
                      >
                        {ui.show_in_brain}
                      </button>
                    )}
                  </div>
                  <HowPanel response={turn.response} groupNames={groupNames} />
                </article>
              )}
            </div>
          ))}
          <div ref={endRef} />
        </div>

        <Composer
          value={draft}
          onChange={setDraft}
          onSend={() => void send(draft)}
          disabled={pending}
          inputRef={inputRef}
        />
      </section>

      <aside className="brain-panel">
        <BrainSchematic
          activity={shown?.response.brain ?? null}
          activeReadouts={activeReadouts}
          pending={pending}
          circuitOnly={shown?.response.output.circuit_only ?? false}
        />
      </aside>
    </div>
  );
}
