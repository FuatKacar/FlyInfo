import { describe, expect, it } from "vitest";
import { brightness } from "./brightness";
import { neuropilLabel } from "./neuropils";

const scale = { reference_hz: 0.5, max_hz: 200 };

describe("parlaklık ölçeği", () => {
  it("sıfır ve geçersiz hız sönüktür, en yüksek hız tam parlaktır", () => {
    expect(brightness(0, scale)).toBe(0);
    expect(brightness(Number.NaN, scale)).toBe(0);
    expect(brightness(200, scale)).toBeCloseTo(1, 10);
    expect(brightness(5000, scale)).toBe(1);
  });

  it("arka uçtaki logaritmik tanımla birebir aynıdır ve monotondur", () => {
    expect(brightness(5.8, scale)).toBeCloseTo(Math.log10(1 + 5.8 / 0.5) / Math.log10(401), 12);
    const values = [0.1, 1, 10, 24, 150].map((hz) => brightness(hz, scale));
    expect([...values].sort((a, b) => a - b)).toEqual(values);
  });
});

describe("nöropil adları", () => {
  it("taraf ekiyle Türkçe ad üretir", () => {
    expect(neuropilLabel("AL_R")).toEqual({
      code: "AL_R",
      name: "Anten lobu (sağ)",
      english: "antennal lobe",
    });
    expect(neuropilLabel("MB_CA_L").name).toBe("Mantar cisim kaliksi (sol)");
    expect(neuropilLabel("GNG").name).toBe("Gnatal gangliyonlar");
  });

  it("bilinmeyen kodu olduğu gibi gösterir", () => {
    expect(neuropilLabel("XYZ").name).toBe("XYZ");
  });
});
