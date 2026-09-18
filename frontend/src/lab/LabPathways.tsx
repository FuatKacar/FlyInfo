import { useState } from "react";
import type { ExperimentRequest, PathwayResponse } from "../api/client";
import { startPathways } from "../api/client";
import { format, formatNumber, texts, ui } from "../i18n/text";
import { useJob } from "./useJob";

const behaviorNames = texts.behaviors as Record<string, string>;
const labels = ui.lab.pathways;
const BEHAVIORS = Object.keys(behaviorNames);

export function LabPathways({ request }: { request: ExperimentRequest }) {
  const [behavior, setBehavior] = useState(BEHAVIORS[0] ?? "feeding");
  const [response, setResponse] = useState<PathwayResponse | null>(null);
  const job = useJob();

  async function find() {
    setResponse(null);
    const status = await job.start(() =>
      startPathways({ experiment: request, behavior: behavior as never, top_k: 5, max_hops: 4 }),
    );
    if (status?.state === "done" && status.pathways) setResponse(status.pathways);
  }

  return (
    <section className="lab-pathways" aria-labelledby="lab-yollar">
      <h3 id="lab-yollar">{labels.title}</h3>

      <div className="row">
        <label className="field">
          <span className="field__label">{labels.behavior}</span>
          <select
            aria-label={labels.behavior}
            value={behavior}
            onChange={(event) => setBehavior(event.target.value)}
          >
            {BEHAVIORS.map((key) => (
              <option key={key} value={key}>
                {behaviorNames[key]}
              </option>
            ))}
          </select>
        </label>
        <button type="button" className="button" disabled={job.running} onClick={() => void find()}>
          {job.running ? ui.lab.running : labels.run}
        </button>
      </div>

      {job.error && <p className="notice">{job.error}</p>}

      {response && (
        <>
          <p className="hint">{format(labels.target, { id: response.target_id })}</p>
          {response.pathways.length === 0 ? (
            <p className="hint">{labels.empty}</p>
          ) : (
            <ol className="pathways">
              {response.pathways.map((path) => (
                <li key={path.edges.map((e) => `${e.pre_id}-${e.post_id}`).join("|")}>
                  <div className="pathway__head">
                    <span>
                      {labels.strength}: {formatNumber(100 * path.strength, 1)}%
                    </span>
                    <span className="hint">
                      {format(labels.hops, { hops: path.hops })} ·{" "}
                      {path.excitatory ? labels.excitatory : labels.inhibitory}
                    </span>
                  </div>
                  <div className="pathway__chain">
                    {path.edges[0] && (
                      <Node id={path.edges[0].pre_id} cellType={path.edges[0].pre_cell_type} />
                    )}
                    {path.edges.map((edge) => (
                      <span key={`${edge.pre_id}-${edge.post_id}`} className="pathway__step">
                        <span
                          className={edge.excitatory ? "arrow arrow--exc" : "arrow arrow--inh"}
                          title={`${edge.synapses} sinaps, ${formatNumber(edge.pre_rate_hz)} Hz`}
                        >
                          {edge.excitatory ? "→" : "⊣"}
                          <small>
                            {format(labels.share, { share: formatNumber(100 * edge.share, 0) })}
                          </small>
                        </span>
                        <Node id={edge.post_id} cellType={edge.post_cell_type} />
                      </span>
                    ))}
                  </div>
                </li>
              ))}
            </ol>
          )}
          <p className="notice">{response.note_tr}</p>
        </>
      )}
    </section>
  );
}

/** Yol düğümü: okunabilir hücre tipi; tam FlyWire kimliği ipucunda. */
function Node({ id, cellType }: { id: string; cellType?: string | null | undefined }) {
  return (
    <span className="node" title={`FlyWire ${id}`}>
      {cellType ?? `…${id.slice(-6)}`}
    </span>
  );
}
