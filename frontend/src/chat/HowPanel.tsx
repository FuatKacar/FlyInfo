import type { ChatResponse } from "../api/client";
import { neuropilLabel } from "../brain/neuropils";
import { format, formatNumber, formatPercent, texts, ui } from "../i18n/text";
import { BehaviorChart } from "./BehaviorChart";

const reasons = texts.chat.out_of_scope_reasons as Record<string, string>;
const levelNames = ui.how.levels as Record<string, string>;

interface Props {
  response: ChatResponse;
  groupNames: Record<string, string>;
}

/** Dört katmanın ara çıktıları: girdi eşleme → simülasyon → çözümleyici → sunum. */
export function HowPanel({ response, groupNames }: Props) {
  const { classification: c, output, presentation: p } = response;
  const model = output.model;

  return (
    <details className="how">
      <summary>{ui.how.toggle}</summary>
      <ol className="how__steps">
        <li className="how__step">
          <h3>{ui.how.step1}</h3>
          {c.in_scope ? (
            <ul className="chips">
              {Object.entries(c.levels).map(([group, level]) => (
                <li key={group} className="chip">
                  {groupNames[group] ?? group} · {levelNames[String(level)] ?? level}
                </li>
              ))}
            </ul>
          ) : (
            <p>
              <strong>{ui.how.out_of_scope}:</strong>{" "}
              {(c.out_of_scope_reason && reasons[c.out_of_scope_reason]) ?? c.out_of_scope_reason}
            </p>
          )}
          {c.evidence.length > 0 && (
            <ul className="evidence">
              {c.evidence.map((e) => (
                <li key={`${e.category}-${e.term}-${e.clause}`}>
                  {format(ui.how.evidence, { term: e.term, rule: e.rule })}
                </li>
              ))}
            </ul>
          )}
        </li>

        <li className="how__step">
          <h3>{ui.how.step2}</h3>
          {output.stimulus.components.length ? (
            <ul className="facts">
              {output.stimulus.components.map((s) => (
                <li key={s.group}>
                  {s.name_tr}: {formatNumber(s.rate_hz, 0)} Hz Poisson, {s.neuron_count} nöron
                </li>
              ))}
            </ul>
          ) : (
            <p>{ui.how.no_stimulus}</p>
          )}
          <ul className="facts facts--muted">
            <li>
              {model.mode === "live"
                ? ui.how.mode.live
                : format(ui.how.mode.precomputed, { version: model.package_version ?? "?" })}
              {" · "}
              {model.type}, {model.dataset}
            </li>
            <li>
              {format(ui.how.trials, {
                trials: model.n_trials,
                seconds: formatNumber(model.t_run_ms / 1000, 0),
                seed: model.seed,
              })}
            </li>
            <li>
              {format(ui.how.active_neurons, {
                count: output.active_neuron_count.toLocaleString("tr-TR"),
              })}
            </li>
          </ul>
        </li>

        <li className="how__step">
          <h3>{ui.how.step3}</h3>
          {output.circuit_only && <p className="notice">{ui.how.circuit_only}</p>}
          <BehaviorChart behaviors={output.behaviors} />
          {output.top_neuropils.length > 0 && (
            <>
              <h4>{ui.how.top_neuropils}</h4>
              <ul className="facts">
                {output.top_neuropils.map((n) => (
                  <li key={n.neuropil}>
                    {neuropilLabel(n.neuropil).name} ({n.neuropil}): {formatPercent(n.share)}
                  </li>
                ))}
              </ul>
            </>
          )}
        </li>

        <li className="how__step">
          <h3>{ui.how.step4}</h3>
          <p>
            {p.source === "llm"
              ? format(ui.how.presentation_llm, {
                  provider: p.provider ?? "?",
                  model: p.model ?? "?",
                })
              : ui.how.presentation_template}
          </p>
          {p.fallback_reason && (
            <p className="hint">{format(ui.how.fallback, { reason: p.fallback_reason })}</p>
          )}
          <p className="hint">{ui.source.note}</p>
        </li>
      </ol>
      <details className="raw">
        <summary>{ui.how.raw}</summary>
        <pre>{JSON.stringify(response, null, 2)}</pre>
      </details>
    </details>
  );
}
