import type { BehaviorReadout } from "../api/client";
import { formatNumber, formatPercent, texts, ui } from "../i18n/text";

const behaviorNames = texts.behaviors as Record<string, string>;
const readoutNames = texts.readout_neurons as Record<string, string>;

/** Davranış başına kalibre skor çubuğu; ham hız her zaman metin olarak yazılır. */
export function BehaviorChart({ behaviors }: { behaviors: readonly BehaviorReadout[] }) {
  return (
    <div className="behaviors">
      <ul className="behaviors__list">
        {behaviors.map((b) => {
          const name = behaviorNames[b.behavior] ?? b.behavior;
          const neuron = readoutNames[b.readout_group] ?? b.readout_group;
          const score = b.score ?? null;
          return (
            <li
              key={b.behavior}
              className={b.active ? "behavior behavior--active" : "behavior"}
              title={`${neuron}: ${formatNumber(b.rate_hz)} ± ${formatNumber(b.rate_std_hz)} Hz`}
            >
              <div className="behavior__head">
                <span className="behavior__name">{name}</span>
                <span className="behavior__state">
                  <span aria-hidden="true">{b.active ? "●" : "○"}</span>{" "}
                  {b.active ? ui.how.behavior_active : ui.how.behavior_inactive}
                </span>
              </div>
              <div className="behavior__track" aria-hidden="true">
                {score !== null && (
                  <div
                    className="behavior__bar"
                    style={{ width: `${Math.max(score * 100, 0)}%` }}
                  />
                )}
              </div>
              <div className="behavior__meta">
                <span>
                  {neuron} {formatNumber(b.rate_hz)} Hz
                </span>
                <span>{score === null ? ui.how.unscored : formatPercent(score)}</span>
              </div>
            </li>
          );
        })}
      </ul>
      <p className="hint">{ui.how.score_help}</p>
    </div>
  );
}
