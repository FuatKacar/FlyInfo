import tr from "@yerel";

export const texts = tr;
export const ui = tr.ui;

/** "{ad} x" kalıbındaki yer tutucuları doldurur. */
export function format(template: string, values: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (match, key: string) =>
    key in values ? String(values[key]) : match,
  );
}

const numberFormats = new Map<number, Intl.NumberFormat>();

/** Türkçe sayı biçimi: 38.25 → "38,3" (ondalık = 1). Binlik ayırıcı nokta. */
export function formatNumber(value: number, decimals = 1): string {
  let formatter = numberFormats.get(decimals);
  if (!formatter) {
    formatter = new Intl.NumberFormat("tr-TR", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    });
    numberFormats.set(decimals, formatter);
  }
  return formatter.format(value);
}

export function formatPercent(share: number): string {
  return `%${formatNumber(share * 100, 0)}`;
}
