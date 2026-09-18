import { useState } from "react";
import type { ExperimentResult } from "../api/client";
import { BrainSchematic } from "../brain/BrainSchematic";
import { BehaviorChart } from "../chat/BehaviorChart";
import { format, formatNumber, texts, ui } from "../i18n/text";

const behaviorNames = texts.behaviors as Record<string, string>;
const labels = ui.lab.results;

function activeReadouts(result: ExperimentResult, silenced: boolean): Set<string> {
  const condition = silenced ? result.silenced_condition : result.control;
  return new Set(
    condition?.output.behaviors.filter((b) => b.active).map((b) => b.readout_group) ?? [],
  );
}

export function LabResults({ result }: { result: ExperimentResult }) {
  const hasSilencing = result.silenced_condition !== null;
  const [showSilenced, setShowSilenced] = useState(hasSilencing);
  const condition =
    showSilenced && result.silenced_condition ? result.silenced_condition : result.control;

  return (
    <section className="lab-results" aria-labelledby="lab-sonuclar">
      <h3 id="lab-sonuclar">{labels.title}</h3>

      <ul className="facts facts--muted">
        <li>
          {format(labels.stimulated, {
            items: result.stimuli
              .map(
                (s, index) =>
                  `${s.label_tr} (${formatNumber(result.stimulus_rates_hz[index] ?? 0, 0)} Hz, ${s.flywire_ids.length} nöron)`,
              )
              .join(", "),
          })}
        </li>
        {hasSilencing && (
          <li>{format(labels.silenced_count, { count: result.silenced_neuron_count })}</li>
        )}
        <li>{format(labels.duration, { seconds: formatNumber(result.duration_seconds, 1) })}</li>
      </ul>

      {result.warnings_tr.map((warning) => (
        <p key={warning} className="notice">
          {warning}
        </p>
      ))}

      {hasSilencing ? (
        <table className="comparison">
          <caption className="visually-hidden">{labels.title}</caption>
          <thead>
            <tr>
              <th scope="col">{labels.behavior}</th>
              <th scope="col">{labels.control}</th>
              <th scope="col">{labels.silenced}</th>
              <th scope="col">{labels.difference}</th>
              <th scope="col">{labels.significance}</th>
            </tr>
          </thead>
          <tbody>
            {result.comparisons.map((row) => (
              <tr key={row.behavior} className={row.significant ? "comparison--significant" : ""}>
                <th scope="row">{behaviorNames[row.behavior] ?? row.behavior}</th>
                <td>{formatNumber(row.control_rate_hz)} Hz</td>
                <td>{formatNumber(row.silenced_rate_hz)} Hz</td>
                <td>
                  {row.difference_hz > 0 ? "+" : ""}
                  {formatNumber(row.difference_hz)} Hz
                  {row.percent_change !== null && ` (${formatNumber(row.percent_change, 0)}%)`}
                </td>
                <td>
                  {row.p_value < 0.001 ? "< 0,001" : formatNumber(row.p_value, 3)}{" "}
                  <span className="hint">
                    {row.significant ? labels.significant : labels.not_significant}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="hint">{labels.no_silencing}</p>
      )}

      {hasSilencing && (
        <div className="segmented">
          {[false, true].map((silenced) => (
            <button
              key={String(silenced)}
              type="button"
              className="segmented__option"
              aria-pressed={showSilenced === silenced}
              aria-label={`${labels.condition}: ${silenced ? labels.silenced : labels.control}`}
              onClick={() => setShowSilenced(silenced)}
            >
              {silenced ? labels.silenced : labels.control}
            </button>
          ))}
        </div>
      )}

      <BehaviorChart behaviors={condition.output.behaviors} />

      <BrainSchematic
        activity={{
          neuropil_rates_hz: condition.neuropil_rates_hz,
          scale: { reference_hz: 0.5, max_hz: 200 },
        }}
        activeReadouts={activeReadouts(result, showSilenced)}
        circuitOnly={condition.output.circuit_only}
      />
    </section>
  );
}
