import { afterEach, describe, expect, it, vi } from "vitest";
import {
  BRAIN_SHELL,
  GeometryError,
  geometryIndex,
  loadGeometry,
  parseGeometry,
  supportsWebgl,
} from "./geometry3d";

function tamBuffer(): ArrayBuffer {
  const { index_byte_offset, parts } = geometryIndex;
  const sonPart = parts[parts.length - 1];
  const uzunluk =
    index_byte_offset + ((sonPart?.index_offset ?? 0) + (sonPart?.index_count ?? 0)) * 4;
  return new ArrayBuffer(uzunluk);
}

describe("3B beyin geometrisi", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("dizin dosyası 78 nöropil ve beyin kabuğu içerir", () => {
    const adlar = geometryIndex.parts.map((p) => p.name);
    expect(adlar).toContain(BRAIN_SHELL);
    expect(adlar.filter((a) => a !== BRAIN_SHELL)).toHaveLength(78);
    expect(geometryIndex.index_byte_offset % 4).toBe(0); // uint32 hizası
    expect(geometryIndex.vertex_bytes % 6).toBe(0); // köşe başına 3 × int16
  });

  it("ikili dosyayı köşe ve dizin dizilerine ayırır", () => {
    const geometri = parseGeometry(tamBuffer());

    expect(geometri.positions).toHaveLength(geometryIndex.vertex_bytes / 2);
    expect(geometri.positions.length % 3).toBe(0);
    expect(geometri.scale).toBeGreaterThan(0);
    expect(geometri.sizeUm).toHaveLength(3);
    const sonPart = geometryIndex.parts[geometryIndex.parts.length - 1];
    expect(geometri.indices.length).toBeGreaterThanOrEqual(
      (sonPart?.index_offset ?? 0) + (sonPart?.index_count ?? 0),
    );
  });

  it("eksik dosyayı reddeder", () => {
    expect(() => parseGeometry(new ArrayBuffer(16))).toThrow(GeometryError);
  });

  it("indirme başarısızsa anlaşılır hata verir", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(null, { status: 404 })),
    );

    await expect(loadGeometry("/yok.bin")).rejects.toThrow(/404/);
  });

  it("test ortamında WebGL yoktur, 2B şemaya düşülür", () => {
    expect(supportsWebgl()).toBe(false);
  });
});
