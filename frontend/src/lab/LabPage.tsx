import { useEffect, useRef, useState } from "react";
import {
  ApiError,
  type ExampleInfo,
  type ExperimentRequest,
  type ExperimentResult,
  getExample,
  getLabOptions,
  type LabOptions,
  listExamples,
  type NeuronSelector,
  startExperiment,
} from "../api/client";
import { format, formatNumber, ui } from "../i18n/text";
import { LabPathways } from "./LabPathways";
import { LabReport } from "./LabReport";
import { LabResults } from "./LabResults";
import { defaultSelector, SelectorPicker } from "./SelectorPicker";
import { useJob } from "./useJob";

const labels = ui.lab;
const DEFAULT_RATE_HZ = 200;

interface StimulusRow {
  id: number; // yalnızca liste anahtarı; isteğe gönderilmez
  selector: NeuronSelector;
  rate_hz: number;
}

interface SilencedRow {
  id: number;
  selector: NeuronSelector;
}

export function LabPage() {
  const [options, setOptions] = useState<LabOptions | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [stimuli, setStimuli] = useState<StimulusRow[]>([]);
  const [silenced, setSilenced] = useState<SilencedRow[]>([]);
  const nextId = useRef(1);
  const newId = () => nextId.current++;
  const [params, setParams] = useState({ n_trials: 30, t_run_ms: 1000, seed: 0 });
  const [result, setResult] = useState<ExperimentResult | null>(null);
  const [ranRequest, setRanRequest] = useState<ExperimentRequest | null>(null);
  const [examples, setExamples] = useState<ExampleInfo[]>([]);
  const [exampleTitle, setExampleTitle] = useState<string | null>(null);
  const job = useJob();

  useEffect(() => {
    const controller = new AbortController();
    getLabOptions(controller.signal)
      .then((data) => {
        setOptions(data);
        setStimuli([
          {
            id: nextId.current++,
            selector: defaultSelector("group", data, ["stimulus"]),
            rate_hz: DEFAULT_RATE_HZ,
          },
        ]);
      })
      .catch((error) => {
        if (error instanceof ApiError) setLoadError(error.detail);
      });
    listExamples(controller.signal)
      .then(setExamples)
      .catch(() => setExamples([]));
    return () => controller.abort();
  }, []);

  if (loadError) return <p className="placeholder">{loadError}</p>;
  if (!options) return <p className="placeholder">{ui.pending}</p>;

  const request: ExperimentRequest = {
    stimuli: stimuli.map(({ selector, rate_hz }) => ({ selector, rate_hz })),
    silenced: silenced.map((row) => row.selector),
    params,
  };
  const limit = (key: string, fallback: number) => options.limits[key] ?? fallback;

  async function openExample(name: string) {
    const report = await getExample(name);
    const { request: saved } = report;
    setStimuli(
      saved.stimuli.map((s) => ({ id: newId(), selector: s.selector, rate_hz: s.rate_hz })),
    );
    setSilenced((saved.silenced ?? []).map((selector) => ({ id: newId(), selector })));
    if (saved.params) setParams(saved.params);
    setResult(report.result);
    setRanRequest(saved);
    setExampleTitle(report.title_tr);
  }

  async function run() {
    setResult(null);
    setExampleTitle(null);
    const status = await job.start(() => startExperiment(request));
    if (status?.state === "done" && status.experiment) {
      setResult(status.experiment);
      setRanRequest(request);
    }
  }

  return (
    <div className="lab">
      <section className="lab-setup" aria-labelledby="lab-kurulum">
        <h2 id="lab-kurulum">{labels.title}</h2>
        <p className="hint">{labels.intro}</p>

        {examples.length > 0 && (
          <>
            <h3>{labels.examples.title}</h3>
            <p className="hint">{labels.examples.help}</p>
            <ul className="chips">
              {examples.map((example) => (
                <li key={example.name}>
                  <button
                    type="button"
                    className="chip chip--button"
                    disabled={job.running}
                    onClick={() => void openExample(example.name)}
                  >
                    {example.title_tr}
                  </button>
                </li>
              ))}
            </ul>
          </>
        )}

        <h3>{labels.stimuli}</h3>
        {stimuli.map((row, index) => (
          <fieldset key={row.id} className="lab-row">
            <SelectorPicker
              value={row.selector}
              options={options}
              roles={["stimulus", "readout"]}
              onChange={(selector) =>
                setStimuli(stimuli.map((r, i) => (i === index ? { ...r, selector } : r)))
              }
            />
            <label className="field field--narrow">
              <span className="field__label">{labels.rate}</span>
              <input
                type="number"
                min={1}
                max={limit("max_rate_hz", 400)}
                value={row.rate_hz}
                onChange={(event) =>
                  setStimuli(
                    stimuli.map((r, i) =>
                      i === index ? { ...r, rate_hz: Number(event.target.value) } : r,
                    ),
                  )
                }
              />
            </label>
            {stimuli.length > 1 && (
              <button
                type="button"
                className="link-button"
                onClick={() => setStimuli(stimuli.filter((_, i) => i !== index))}
              >
                {labels.remove}
              </button>
            )}
          </fieldset>
        ))}
        {stimuli.length < limit("max_stimuli", 6) && (
          <button
            type="button"
            className="button"
            onClick={() =>
              setStimuli([
                ...stimuli,
                {
                  id: newId(),
                  selector: defaultSelector("group", options, ["stimulus"]),
                  rate_hz: DEFAULT_RATE_HZ,
                },
              ])
            }
          >
            {labels.add}
          </button>
        )}

        <h3>{labels.silencing}</h3>
        {silenced.map((row) => (
          <fieldset key={row.id} className="lab-row">
            <SelectorPicker
              value={row.selector}
              options={options}
              onChange={(next) =>
                setSilenced(silenced.map((s) => (s.id === row.id ? { ...s, selector: next } : s)))
              }
            />
            <button
              type="button"
              className="link-button"
              onClick={() => setSilenced(silenced.filter((s) => s.id !== row.id))}
            >
              {labels.remove}
            </button>
          </fieldset>
        ))}
        {silenced.length < limit("max_silenced", 6) && (
          <button
            type="button"
            className="button"
            onClick={() =>
              setSilenced([
                ...silenced,
                { id: newId(), selector: defaultSelector("cell_type", options) },
              ])
            }
          >
            {labels.add}
          </button>
        )}

        <h3>{labels.params.title}</h3>
        <div className="row">
          {(
            [
              ["n_trials", labels.params.n_trials, 1, limit("max_trials", 50)],
              ["t_run_ms", labels.params.t_run_ms, 100, limit("max_run_ms", 2000)],
              ["seed", labels.params.seed, 0, 2 ** 31 - 1],
            ] as const
          ).map(([key, label, min, max]) => (
            <label key={key} className="field field--narrow">
              <span className="field__label">{label}</span>
              <input
                type="number"
                min={min}
                max={max}
                value={params[key]}
                onChange={(event) => setParams({ ...params, [key]: Number(event.target.value) })}
              />
            </label>
          ))}
        </div>
        <p className="hint">{labels.params.help}</p>

        <div className="row">
          <button
            type="button"
            className="button button--primary"
            disabled={job.running || stimuli.length === 0}
            onClick={() => void run()}
          >
            {job.running ? labels.running : labels.run}
          </button>
          {job.running && job.status && (
            <span className="lab-progress">
              <progress value={job.status.progress} max={1} />
              <span className="hint">
                {job.status.step_tr} · %{formatNumber(100 * job.status.progress, 0)}
              </span>
            </span>
          )}
        </div>
        <p className="hint">{labels.cancel_note}</p>
        {job.error && (
          <p className="notice" role="alert">
            {format(labels.error, { detail: job.error })}
          </p>
        )}
      </section>

      <div className="lab-output">
        {result && exampleTitle && (
          <p className="notice">{format(labels.examples.loaded, { title: exampleTitle })}</p>
        )}
        {result && <LabResults result={result} />}
        {result && ranRequest && <LabPathways request={ranRequest} />}
        {result && ranRequest && <LabReport request={ranRequest} />}
      </div>
    </div>
  );
}
