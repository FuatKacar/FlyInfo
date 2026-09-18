import { lazy, Suspense, useEffect, useMemo, useState } from "react";
import type { BrainActivity } from "../api/client";
import { format, formatNumber, texts, ui } from "../i18n/text";
import { BrainSvg } from "./BrainSvg";
import { brightness, scaleTicksHz } from "./brightness";
import { supportsWebgl } from "./geometry3d";
import { neuropilLabel } from "./neuropils";

const TOP_REGIONS = 5;
const MIN_LISTED_RATE_HZ = 0.05;
const STORAGE_KEY = "sinek-beyin-gorunum";
const DEFAULT_SCALE = { reference_hz: 0.5, max_hz: 200 };

// three.js yalnızca 3B görünüm açıldığında indirilir (ilk yükleme hafif kalır).
const Brain3D = lazy(() => import("./Brain3D").then((m) => ({ default: m.Brain3D })));

type View = "2d" | "3d";

interface Props {
  activity: BrainActivity | null;
  /** Etkin davranışların okuma grubu anahtarları (ör. "mn9"). */
  activeReadouts: ReadonlySet<string>;
  pending?: boolean;
  /** Uyarım yalnızca devre aktivitesi gösteren gruplardansa (kötü koku, CO₂) sınırlılık notu. */
  circuitOnly?: boolean;
}

function storedView(): View | null {
  try {
    const value = localStorage.getItem(STORAGE_KEY);
    return value === "2d" || value === "3d" ? value : null;
  } catch {
    return null;
  }
}

export function BrainSchematic({
  activity,
  activeReadouts,
  pending = false,
  circuitOnly = false,
}: Props) {
  const webgl = supportsWebgl();
  const [view, setView] = useState<View>(() => (webgl ? (storedView() ?? "3d") : "2d"));
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, view);
    } catch {
      // depolama kapalıysa seçim yalnızca bu oturumda geçerli
    }
  }, [view]);

  const top = useMemo(
    () =>
      Object.entries(activity?.neuropil_rates_hz ?? {})
        .filter(([, rate]) => rate >= MIN_LISTED_RATE_HZ)
        .sort((a, b) => b[1] - a[1])
        .slice(0, TOP_REGIONS),
    [activity],
  );

  const show3d = view === "3d" && webgl && !error;

  return (
    <figure className="brain" aria-busy={pending}>
      <header className="brain__header">
        <h2 className="brain__title">{ui.brain.title}</h2>
        <div className="brain__tools">
          <span className="brain__view">{ui.brain.view}</span>
          {webgl && (
            <div className="segmented">
              {(["3d", "2d"] as const).map((value) => (
                <button
                  key={value}
                  type="button"
                  className="segmented__option"
                  aria-pressed={view === value}
                  aria-label={`${ui.brain.view_label}: ${value === "3d" ? ui.brain.view_3d : ui.brain.view_2d}`}
                  onClick={() => {
                    setError(null);
                    setView(value);
                  }}
                >
                  {value === "3d" ? ui.brain.view_3d : ui.brain.view_2d}
                </button>
              ))}
            </div>
          )}
        </div>
      </header>

      <div className="brain__canvas">
        {show3d ? (
          <Suspense fallback={<p className="brain3d__loading">{ui.brain.loading_3d}</p>}>
            <Brain3D activity={activity} activeReadouts={activeReadouts} onError={setError} />
          </Suspense>
        ) : (
          <BrainSvg activity={activity} activeReadouts={activeReadouts} top={top} />
        )}
      </div>

      {show3d && <p className="hint">{ui.brain.rotate_hint}</p>}
      {error && <p className="notice">{format(ui.brain.error_3d, { detail: error })}</p>}
      {!webgl && view === "2d" && <p className="hint">{ui.brain.webgl_missing}</p>}

      <div className="legend">
        <svg
          className="legend__bar"
          viewBox="0 0 200 10"
          preserveAspectRatio="none"
          aria-hidden="true"
        >
          <defs>
            <linearGradient id="beyin-olcek">
              <stop offset="0" stopColor="var(--glow)" stopOpacity="0" />
              <stop offset="1" stopColor="var(--glow)" stopOpacity="0.9" />
            </linearGradient>
          </defs>
          <rect width="200" height="10" rx="3" fill="url(#beyin-olcek)" />
        </svg>
        <div className="legend__ticks">
          {scaleTicksHz.map((hz) => (
            <span
              key={hz}
              style={{ left: `${100 * brightness(hz, activity?.scale ?? DEFAULT_SCALE)}%` }}
            >
              {hz}
            </span>
          ))}
        </div>
        <p className="legend__label">{ui.brain.scale}</p>
      </div>

      <figcaption className="brain__caption">
        {activity ? (
          <>
            <p>{texts.chat.brain_caption}</p>
            {circuitOnly && <p className="notice">{ui.brain.circuit_only_note}</p>}
            {top.length ? (
              <ol className="top-regions" aria-label={ui.brain.top}>
                {top.map(([code, rate]) => (
                  <li key={code}>
                    <span>{neuropilLabel(code).name}</span>
                    <span className="top-regions__value">{formatNumber(rate)} Hz</span>
                  </li>
                ))}
              </ol>
            ) : (
              <p>{ui.brain.none_active}</p>
            )}
            <p className="brain__readout-note">
              <span className="readout-swatch" aria-hidden="true" /> {ui.brain.readouts}
            </p>
          </>
        ) : (
          <p>{ui.brain.idle}</p>
        )}
      </figcaption>
    </figure>
  );
}
