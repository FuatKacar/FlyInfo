import { texts } from "../i18n/text";

const names: Record<string, readonly string[]> = texts.neuropils.names;
const sides = texts.neuropils.sides as Record<string, string>;

export interface NeuropilLabel {
  code: string;
  name: string; // Türkçe ad, taraf dahil
  english: string;
}

/** "AL_R" → { name: "Anten lobu (sağ)", english: "antennal lobe" } */
export function neuropilLabel(code: string): NeuropilLabel {
  const match = /^(.*)_([LR])$/.exec(code);
  const base = match?.[1] ?? code;
  const side = match?.[2];
  const entry = names[base];
  const name = entry?.[0] ?? base;
  return {
    code,
    name: side ? `${name} (${sides[side]})` : name,
    english: entry?.[1] ?? base,
  };
}
