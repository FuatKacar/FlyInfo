import type { ChatResponse, Schemas } from "../api/client";

const behaviors: ChatResponse["output"]["behaviors"] = [
  {
    behavior: "feeding",
    readout_group: "mn9",
    rate_hz: 38.24,
    rate_std_hz: 4.1,
    score: 0.41,
    active: true,
  },
  {
    behavior: "escape",
    readout_group: "giant_fiber",
    rate_hz: 0,
    rate_std_hz: 0,
    score: 0,
    active: false,
  },
  {
    behavior: "antennal_grooming",
    readout_group: "adn1",
    rate_hz: 0,
    rate_std_hz: 0,
    score: 0,
    active: false,
  },
  {
    behavior: "backward_walking",
    readout_group: "mdn",
    rate_hz: 0,
    rate_std_hz: 0,
    score: 0,
    active: false,
  },
  {
    behavior: "forward_walking",
    readout_group: "p9",
    rate_hz: 0,
    rate_std_hz: 0,
    score: null,
    active: false,
  },
];

export function sugarResponse(): ChatResponse {
  return {
    classification: {
      in_scope: true,
      levels: { sugar: 2 },
      evidence: [{ category: "sugar", term: "bal", clause: "Sana bal getirdim", rule: "isim" }],
      out_of_scope_reason: null,
    },
    output: {
      stimulus: {
        components: [
          {
            group: "sugar",
            name_tr: "Şekere duyarlı tat nöronları",
            intensity: 0.6,
            rate_hz: 120,
            neuron_count: 21,
          },
        ],
        match_score: null,
        scenario_key: "sugar@0.6",
      },
      behaviors,
      circuit_only: false,
      top_neuropils: [{ neuropil: "GNG", events_hz: 1000, share: 0.94 }],
      active_neuron_count: 1234,
      model: {
        type: "LIF",
        dataset: "FlyWire v783",
        sign_source: "reference",
        mode: "precomputed",
        n_trials: 30,
        t_run_ms: 1000,
        seed: 42,
        package_version: "1",
      },
    },
    brain: {
      neuropil_rates_hz: { GNG: 5.8, PRW: 4.4, AL_R: 0 },
      scale: { reference_hz: 0.5, max_hz: 200 },
    },
    presentation: {
      text: "Şekere duyarlı tat nöronları (120 Hz, 21 nöron) uyarıldı.",
      source: "template",
      provider: null,
      model: null,
      fallback_reason: "LLM kapalı",
    },
    hint: null,
  };
}

export function outOfScopeResponse(): ChatResponse {
  const base = sugarResponse();
  return {
    ...base,
    classification: {
      in_scope: false,
      levels: {},
      evidence: [],
      out_of_scope_reason: "tanınan uyarıcı yok",
    },
    output: {
      ...base.output,
      stimulus: { components: [], match_score: null, scenario_key: "kontrol" },
      behaviors: base.output.behaviors.map((b) => ({
        ...b,
        rate_hz: 0,
        score: b.score === null ? null : 0,
        active: false,
      })),
      top_neuropils: [],
      active_neuron_count: 0,
    },
    brain: { ...base.brain, neuropil_rates_hz: { GNG: 0, PRW: 0 } },
    presentation: { ...base.presentation, text: "Mesaj hiçbir duyusal kategoriyle eşleşmedi." },
    hint: {
      title: "Sinek dil anlamaz; ona bir şey sunmayı deneyin:",
      examples: ["Sana biraz bal getirdim"],
    },
  };
}

// --- Laboratuvar ------------------------------------------------------------------------------

export function labOptions(): Schemas["LabOptions"] {
  return {
    groups: [
      {
        key: "sugar",
        name_tr: "Şekere duyarlı tat nöronları",
        role: "stimulus",
        neuron_count: 21,
        behavior: null,
      },
      {
        key: "mn9",
        name_tr: "MN9 motor nöronu",
        role: "readout",
        neuron_count: 2,
        behavior: "feeding",
      },
    ],
    neuropils: ["GNG", "PRW"],
    neurotransmitters: ["acetylcholine", "gaba"],
    limits: { max_rate_hz: 400, max_stimuli: 6, max_silenced: 6, max_trials: 50, max_run_ms: 2000 },
    busy: false,
  };
}

function condition(label: string, feedingRate: number): Schemas["ConditionResult"] {
  const base = sugarResponse().output;
  return {
    label_tr: label,
    output: {
      ...base,
      behaviors: base.behaviors.map((b) =>
        b.behavior === "feeding" ? { ...b, rate_hz: feedingRate } : b,
      ),
    },
    neuropil_rates_hz: { GNG: 5.8, PRW: 4.4 },
  };
}

export function experimentResult(): Schemas["ExperimentResult"] {
  return {
    stimuli: [
      {
        selector: { kind: "group", group: "sugar" },
        label_tr: "Şekere duyarlı tat nöronları",
        flywire_ids: ["1000", "1001"],
        missing_ids: [],
      },
    ],
    stimulus_rates_hz: [200],
    silenced: [
      {
        selector: { kind: "cell_type", cell_type: "CB0701" },
        label_tr: "CB0701 hücre tipi",
        flywire_ids: ["2000"],
        missing_ids: [],
      },
    ],
    silenced_neuron_count: 1,
    params: { n_trials: 30, t_run_ms: 1000, seed: 0 },
    control: condition("kontrol", 88.3),
    silenced_condition: condition("susturma", 12.1),
    comparisons: [
      {
        behavior: "feeding",
        control_rate_hz: 88.3,
        silenced_rate_hz: 12.1,
        difference_hz: -76.2,
        percent_change: -86.3,
        p_value: 0.0001,
        significant: true,
      },
    ],
    warnings_tr: [],
    duration_seconds: 84.2,
  };
}

export function pathwayResponse(): Schemas["PathwayResponse"] {
  return {
    target_id: "2000",
    pathways: [
      {
        edges: [
          {
            pre_id: "1000",
            post_id: "2000",
            pre_cell_type: "LB3",
            post_cell_type: "CB0701",
            synapses: 42,
            excitatory: true,
            pre_rate_hz: 120,
            share: 0.62,
          },
        ],
        strength: 0.62,
        excitatory: true,
        hops: 1,
      },
    ],
    note_tr: "Yollar yapısal ve korelasyonel bir özettir, nedensellik kanıtı değildir.",
  };
}

export function experimentReport(): Schemas["ExperimentReport"] {
  return {
    report_version: 1,
    created_utc: "2026-09-17T21:00:00+00:00",
    title_tr: "Deney",
    request: {
      stimuli: [{ selector: { kind: "group", group: "sugar" }, rate_hz: 200 }],
      silenced: [],
      params: { n_trials: 30, t_run_ms: 1000, seed: 0 },
    },
    result: experimentResult(),
    provenance: {
      sinek_version: "0.1.0",
      dataset: "FlyWire v783",
      sign_source: "reference",
      sources_sha256: {},
      neuron_groups_definitions_sha256: "a".repeat(64),
      calibration_sha256: "b".repeat(64),
      environment: { sinek: "0.1.0" },
    },
  };
}

export function job(overrides: Partial<Schemas["JobStatus"]> = {}): Schemas["JobStatus"] {
  return {
    id: "is1",
    kind: "run",
    state: "done",
    progress: 1,
    step_tr: "tamamlandı",
    error_tr: null,
    experiment: null,
    pathways: null,
    report: null,
    replay: null,
    ...overrides,
  };
}
