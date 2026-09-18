import index from "../assets/beyin-3b.json";

export const BRAIN_SHELL = "__beyin__";
export const geometryIndex = index;

export interface Part {
  name: string;
  vertex_offset: number;
  vertex_count: number;
  index_offset: number;
  index_count: number;
  depth_um: number;
}

export interface BrainGeometry {
  /** int16 köşeler; µm'ye çevirmek için `scale` ile çarpılır. */
  positions: Int16Array;
  indices: Uint32Array;
  parts: Part[];
  scale: number;
  radiusUm: number;
  /** Modelin x, y, z boyutları (µm); kamera bu kutuya göre ayarlanır. */
  sizeUm: [number, number, number];
}

export class GeometryError extends Error {}

/** WebGL desteği: tarayıcı sınıfı tanımlı değilse (ör. test ortamı) 3B kullanılamaz. */
export function supportsWebgl(): boolean {
  return typeof WebGL2RenderingContext !== "undefined";
}

export function parseGeometry(buffer: ArrayBuffer): BrainGeometry {
  const { vertex_bytes, index_byte_offset, parts, scale, radius_um, size_um } = index;
  if (buffer.byteLength < index_byte_offset) {
    throw new GeometryError("Beyin geometrisi dosyası eksik");
  }
  const positions = new Int16Array(buffer, 0, vertex_bytes / 2);
  const indices = new Uint32Array(buffer, index_byte_offset);
  const [width = 1, height = 1, depth = 1] = size_um;
  return { positions, indices, parts, scale, radiusUm: radius_um, sizeUm: [width, height, depth] };
}

let pending: Promise<BrainGeometry> | null = null;

/** Geometriyi bir kez indirir; sonraki çağrılar aynı sonucu paylaşır. */
export function loadGeometry(url = `/${index.binary}`): Promise<BrainGeometry> {
  if (!pending) {
    pending = fetch(url)
      .then((response) => {
        if (!response.ok)
          throw new GeometryError(`Beyin geometrisi okunamadı (${response.status})`);
        return response.arrayBuffer();
      })
      .then(parseGeometry)
      .catch((error) => {
        pending = null;
        throw error;
      });
  }
  return pending;
}
