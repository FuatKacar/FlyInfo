import { useEffect, useId, useState } from "react";
import {
  type CellTypeMatch,
  type LabOptions,
  type NeuronSelector,
  searchCellTypes,
} from "../api/client";
import { format, ui } from "../i18n/text";

const SEARCH_DEBOUNCE_MS = 250;
const labels = ui.lab.selector;

type Kind = NeuronSelector["kind"];

const KINDS: Kind[] = ["group", "cell_type", "neurotransmitter", "neuropil", "ids"];

export function defaultSelector(kind: Kind, options: LabOptions, roles?: string[]): NeuronSelector {
  const groups = options.groups.filter((g) => !roles || roles.includes(g.role));
  switch (kind) {
    case "group":
      return { kind, group: groups[0]?.key ?? "" };
    case "cell_type":
      return { kind, cell_type: "" };
    case "neurotransmitter":
      return { kind, neurotransmitter: options.neurotransmitters[0] ?? "acetylcholine" };
    case "neuropil":
      return { kind, neuropil: options.neuropils[0] ?? "GNG" };
    case "ids":
      return { kind, ids: [] };
  }
}

interface Props {
  value: NeuronSelector;
  onChange: (value: NeuronSelector) => void;
  options: LabOptions;
  /** Hazır gruplarda yalnızca bu roller listelenir (ör. yalnızca uyarım grupları). */
  roles?: string[];
}

export function SelectorPicker({ value, onChange, options, roles }: Props) {
  const id = useId();
  const groups = options.groups.filter((g) => !roles || roles.includes(g.role));

  return (
    <div className="selector">
      <label className="field">
        <span className="field__label">{labels.kind}</span>
        <select
          aria-label={labels.kind}
          value={value.kind}
          onChange={(event) =>
            onChange(defaultSelector(event.target.value as Kind, options, roles))
          }
        >
          {KINDS.map((kind) => (
            <option key={kind} value={kind}>
              {labels[kind]}
            </option>
          ))}
        </select>
      </label>

      {value.kind === "group" && (
        <label className="field">
          <span className="field__label">{labels.group}</span>
          <select
            aria-label={labels.group}
            value={value.group}
            onChange={(event) => onChange({ kind: "group", group: event.target.value })}
          >
            {groups.map((group) => (
              <option key={group.key} value={group.key}>
                {group.name_tr} ({format(labels.neuron_count, { count: group.neuron_count })})
              </option>
            ))}
          </select>
        </label>
      )}

      {value.kind === "cell_type" && (
        <CellTypeField
          value={value.cell_type}
          onChange={(cell_type) => onChange({ kind: "cell_type", cell_type })}
          listId={`${id}-tipler`}
        />
      )}

      {value.kind === "neurotransmitter" && (
        <label className="field">
          <span className="field__label">{labels.neurotransmitter}</span>
          <select
            aria-label={labels.neurotransmitter}
            value={value.neurotransmitter}
            onChange={(event) =>
              onChange({ kind: "neurotransmitter", neurotransmitter: event.target.value })
            }
          >
            {options.neurotransmitters.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </label>
      )}

      {value.kind === "neuropil" && (
        <label className="field">
          <span className="field__label">{labels.neuropil}</span>
          <select
            aria-label={labels.neuropil}
            value={value.neuropil}
            onChange={(event) => onChange({ kind: "neuropil", neuropil: event.target.value })}
          >
            {options.neuropils.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </label>
      )}

      {value.kind === "ids" && (
        <label className="field">
          <span className="field__label">{labels.ids}</span>
          <textarea
            rows={3}
            placeholder={labels.ids_placeholder}
            value={value.ids.join("\n")}
            onChange={(event) =>
              onChange({
                kind: "ids",
                // Kimlikler metin olarak taşınır: JavaScript 2^53'ten büyük tam sayıları bozar.
                ids: event.target.value.split(/[\s,;]+/).filter((part) => /^[0-9]+$/.test(part)),
              })
            }
          />
        </label>
      )}
    </div>
  );
}

function CellTypeField({
  value,
  onChange,
  listId,
}: {
  value: string;
  onChange: (value: string) => void;
  listId: string;
}) {
  const [matches, setMatches] = useState<CellTypeMatch[]>([]);

  useEffect(() => {
    const text = value.trim();
    if (!text) {
      setMatches([]);
      return;
    }
    const controller = new AbortController();
    const timer = setTimeout(() => {
      searchCellTypes(text, controller.signal)
        .then(setMatches)
        .catch(() => setMatches([]));
    }, SEARCH_DEBOUNCE_MS);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [value]);

  return (
    <label className="field">
      <span className="field__label">{ui.lab.selector.cell_type}</span>
      <input
        type="text"
        list={listId}
        value={value}
        placeholder={ui.lab.selector.search_placeholder}
        onChange={(event) => onChange(event.target.value)}
      />
      <datalist id={listId}>
        {matches.map((match) => (
          <option key={match.cell_type} value={match.cell_type}>
            {format(ui.lab.selector.neuron_count, { count: match.neuron_count })}
          </option>
        ))}
      </datalist>
    </label>
  );
}
