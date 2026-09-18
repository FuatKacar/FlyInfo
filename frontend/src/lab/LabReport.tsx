import { type ChangeEvent, useState } from "react";
import type { ExperimentRequest, ReplayResult } from "../api/client";
import { startReplay, startReport } from "../api/client";
import { format, formatNumber, ui } from "../i18n/text";
import { useJob } from "./useJob";

const labels = ui.lab.report;

function download(name: string, data: unknown): void {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  URL.revokeObjectURL(url);
}

export function LabReport({ request }: { request: ExperimentRequest }) {
  const [title, setTitle] = useState("");
  const [replay, setReplay] = useState<ReplayResult | null>(null);
  const reportJob = useJob();
  const replayJob = useJob();

  async function exportReport() {
    const status = await reportJob.start(() => startReport(request, title.trim() || null));
    if (status?.state === "done" && status.report) {
      const stamp = new Date().toISOString().slice(0, 19).replaceAll(":", "-");
      download(`flyinfo-deney-${stamp}.json`, status.report);
    }
  }

  async function loadReport(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setReplay(null);
    let parsed: unknown;
    try {
      parsed = JSON.parse(await file.text());
    } catch {
      replayJob.reset();
      return;
    }
    const status = await replayJob.start(() => startReplay(parsed));
    if (status?.state === "done" && status.replay) setReplay(status.replay);
  }

  return (
    <section className="lab-report" aria-labelledby="lab-rapor">
      <h3 id="lab-rapor">{labels.title}</h3>
      <p className="hint">{labels.help}</p>

      <div className="row">
        <label className="field">
          <span className="field__label">{labels.title_placeholder}</span>
          <input
            type="text"
            value={title}
            maxLength={200}
            placeholder={labels.title_placeholder}
            onChange={(event) => setTitle(event.target.value)}
          />
        </label>
        <button
          type="button"
          className="button"
          disabled={reportJob.running}
          onClick={() => void exportReport()}
        >
          {reportJob.running ? ui.lab.running : labels.download}
        </button>
        <label className="button file-button">
          {replayJob.running ? ui.lab.running : labels.load}
          <input
            type="file"
            accept="application/json,.json"
            className="visually-hidden"
            onChange={(event) => void loadReport(event)}
          />
        </label>
      </div>

      {reportJob.error && <p className="notice">{reportJob.error}</p>}
      {replayJob.error && <p className="notice">{replayJob.error}</p>}

      {replay && (
        <div className="replay">
          <p className={replay.identical ? "replay__ok" : "notice"}>
            {replay.identical
              ? labels.identical
              : format(labels.different, {
                  difference: formatNumber(replay.max_difference_hz, 3),
                })}
          </p>
          <p className="hint">
            {replay.provenance_matches
              ? labels.provenance_ok
              : format(labels.provenance_warning, { notes: replay.provenance_notes.join("; ") })}
          </p>
        </div>
      )}
    </section>
  );
}
