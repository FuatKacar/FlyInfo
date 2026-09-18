import { type PointerEvent, useId, useState } from "react";
import type { BrainActivity } from "../api/client";
import schematic from "../assets/beyin-semasi.json";
import { formatNumber, texts, ui } from "../i18n/text";
import { brightness } from "./brightness";
import { neuropilLabel } from "./neuropils";

const readoutNames = texts.readout_neurons as Record<string, string>;

/** Sönük dolgudan ışıma rengine doğrusal karışım (tek ton sıralı rampa). */
function regionFill(level: number): string {
  return `color-mix(in oklab, var(--glow) ${(level * 100).toFixed(1)}%, var(--region-fill))`;
}

interface Props {
  activity: BrainActivity | null;
  activeReadouts: ReadonlySet<string>;
  top: [string, number][];
}

interface Hover {
  code: string;
  x: number;
  y: number;
}

/** Önden görünüm: 78 nöropilin FlyWire ağlarından üretilmiş izdüşümü. */
export function BrainSvg({ activity, activeReadouts, top }: Props) {
  const id = useId();
  const [hover, setHover] = useState<Hover | null>(null);
  const rates = activity?.neuropil_rates_hz ?? {};
  const level = (code: string) => (activity ? brightness(rates[code] ?? 0, activity.scale) : 0);

  function onPointerMove(event: PointerEvent<SVGGElement>) {
    const target = event.target as SVGElement;
    const code = target.dataset.neuropil;
    if (!code) {
      setHover(null);
      return;
    }
    const box = event.currentTarget.ownerSVGElement?.getBoundingClientRect();
    if (!box) return;
    setHover({ code, x: event.clientX - box.left, y: event.clientY - box.top });
  }

  const hovered = hover ? neuropilLabel(hover.code) : null;

  return (
    <>
      <svg
        viewBox={`0 0 ${schematic.width} ${schematic.height}`}
        role="img"
        aria-labelledby={`${id}-baslik`}
        className={activity ? "brain__svg" : "brain__svg brain__svg--idle"}
      >
        <title id={`${id}-baslik`}>
          {top.length
            ? `${ui.brain.top}: ${top
                .map(([code, rate]) => `${neuropilLabel(code).name} ${formatNumber(rate)} Hz`)
                .join(", ")}`
            : ui.brain.idle}
        </title>

        <path className="brain__outline" d={schematic.outline} fillRule="evenodd" />

        {/*
            Dolgular arkadan öne, OPAK renklerle çizilir: üst üste binen bölgelerin yarı saydam
            renkleri toplanmaz. Görünen renk, o noktadaki en öndeki bölgenin değeridir.
          */}
        <g
          className="brain__regions"
          onPointerMove={onPointerMove}
          onPointerLeave={() => setHover(null)}
        >
          {schematic.neuropils.map((n) => (
            <path
              key={n.name}
              d={n.d}
              fillRule="evenodd"
              data-neuropil={n.name}
              data-brightness={level(n.name).toFixed(3)}
              style={{ fill: regionFill(level(n.name)) }}
            />
          ))}
        </g>

        <g className="brain__edges">
          {schematic.neuropils.map((n) => (
            <path key={n.name} d={n.d} fillRule="evenodd" />
          ))}
        </g>

        <g className="brain__readouts">
          {schematic.readouts.map((r) =>
            r.neurons.map((neuron) => {
              const active = activeReadouts.has(r.group);
              const [x = 0, y = 0] = neuron.point;
              return (
                <g
                  key={neuron.root_id}
                  className={active ? "readout readout--active" : "readout"}
                  transform={`translate(${x} ${y})`}
                >
                  <title>{readoutNames[r.group] ?? r.group}</title>
                  {active && <circle className="readout__pulse" r="5" />}
                  <circle className="readout__dot" r="3.2" />
                </g>
              );
            }),
          )}
        </g>

        <text className="brain__side" x="12" y={schematic.height - 12}>
          {ui.brain.right_of_fly}
        </text>
        <text
          className="brain__side"
          x={schematic.width - 12}
          y={schematic.height - 12}
          textAnchor="end"
        >
          {ui.brain.left_of_fly}
        </text>
      </svg>

      {hover && hovered && (
        <div className="tooltip" style={{ left: hover.x, top: hover.y }} role="presentation">
          <strong>{hovered.name}</strong>
          <span className="tooltip__sub">
            {hovered.code} · {hovered.english}
          </span>
          {activity && (
            <span className="tooltip__value">{formatNumber(rates[hover.code] ?? 0, 2)} Hz</span>
          )}
        </div>
      )}

      {hover && hovered && (
        <div className="tooltip" style={{ left: hover.x, top: hover.y }} role="presentation">
          <strong>{hovered.name}</strong>
          <span className="tooltip__sub">
            {hovered.code} · {hovered.english}
          </span>
          {activity && (
            <span className="tooltip__value">{formatNumber(rates[hover.code] ?? 0, 2)} Hz</span>
          )}
        </div>
      )}
    </>
  );
}
