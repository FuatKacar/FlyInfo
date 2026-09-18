import { describe, expect, it } from "vitest";
import schematic from "../assets/beyin-semasi.json";
import { format, formatNumber, formatPercent, texts } from "./text";

describe("metin yardımcıları", () => {
  it("Türkçe ondalık ve binlik ayırıcı kullanır", () => {
    expect(formatNumber(38.25)).toBe("38,3");
    expect(formatNumber(1234.5, 0)).toBe("1.235");
    expect(formatPercent(0.824)).toBe("%82");
  });

  it("yer tutucuları doldurur, bilinmeyenleri korur", () => {
    expect(format("{a} ve {b}", { a: 1 })).toBe("1 ve {b}");
  });

  it("şemadaki her nöropilin Türkçe adı vardır", () => {
    const names = texts.neuropils.names as Record<string, unknown>;
    for (const n of schematic.neuropils) {
      expect(names[n.name.replace(/_[LR]$/, "")], n.name).toBeDefined();
    }
  });
});
