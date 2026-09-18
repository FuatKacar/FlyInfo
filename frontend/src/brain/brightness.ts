import type { BrainActivity } from "../api/client";

type Scale = BrainActivity["scale"];

/**
 * Parlaklık (0–1), tüm senaryolarda sabit logaritmik ölçek (arka uç BrainScale ile aynı tanım):
 *   log10(1 + hız / referans) / log10(1 + en_yüksek / referans)
 */
export function brightness(rateHz: number, scale: Scale): number {
  if (!(rateHz > 0)) return 0;
  const value =
    Math.log10(1 + rateHz / scale.reference_hz) / Math.log10(1 + scale.max_hz / scale.reference_hz);
  return Math.min(1, Math.max(0, value));
}

/** Ölçek üzerindeki bir hızın konumu (lejant işaretleri için). */
export const scaleTicksHz = [1, 10, 100] as const;
