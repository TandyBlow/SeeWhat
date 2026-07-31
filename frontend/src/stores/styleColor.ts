function _linearize(c: number): number {
  if (c <= 0.04045) return c / 12.92;
  return Math.pow((c + 0.055) / 1.055, 2.4);
}

function _relativeLuminance(rgb: number[]): number {
  return 0.2126 * _linearize(rgb[0]!)
       + 0.7152 * _linearize(rgb[1]!)
       + 0.0722 * _linearize(rgb[2]!);
}

function _contrastRatio(lum1: number, lum2: number): number {
  const lighter = Math.max(lum1, lum2);
  const darker = Math.min(lum1, lum2);
  return (lighter + 0.05) / (darker + 0.05);
}

const MIN_CONTRAST_AGAINST_WHITE = 4.5;
const WHITE_LUMINANCE = 1.0;
const MIN_CONTRAST_AGAINST_BLACK = 4.5;
const BLACK_LUMINANCE = 0.0;

export function ensureContrastAgainstWhite(rgb: number[]): number[] {
  const textLum = _relativeLuminance(rgb);
  if (_contrastRatio(textLum, WHITE_LUMINANCE) >= MIN_CONTRAST_AGAINST_WHITE) {
    return rgb;
  }
  let lo = 0.0, hi = 1.0;
  let best = [...rgb];
  for (let i = 0; i < 12; i++) {
    const mid = (lo + hi) / 2;
    const blended = [rgb[0]! * (1 - mid), rgb[1]! * (1 - mid), rgb[2]! * (1 - mid)];
    if (_contrastRatio(_relativeLuminance(blended), WHITE_LUMINANCE) >= MIN_CONTRAST_AGAINST_WHITE) {
      best = blended;
      hi = mid;
    } else {
      lo = mid;
    }
  }
  return best.map(v => Math.round(v * 10000) / 10000);
}

export function ensureContrastAgainstDark(rgb: number[]): number[] {
  const textLum = _relativeLuminance(rgb);
  if (_contrastRatio(textLum, BLACK_LUMINANCE) >= MIN_CONTRAST_AGAINST_BLACK) {
    return rgb;
  }
  let lo = 0.0, hi = 1.0;
  let best = [...rgb];
  for (let i = 0; i < 12; i++) {
    const mid = (lo + hi) / 2;
    const blended = [rgb[0]! + (1 - rgb[0]!) * mid, rgb[1]! + (1 - rgb[1]!) * mid, rgb[2]! + (1 - rgb[2]!) * mid];
    if (_contrastRatio(_relativeLuminance(blended), BLACK_LUMINANCE) >= MIN_CONTRAST_AGAINST_BLACK) {
      best = blended;
      hi = mid;
    } else {
      lo = mid;
    }
  }
  return best.map(v => Math.round(v * 10000) / 10000);
}

export function isSkyDark(skyBottomColor: number[]): boolean {
  return _relativeLuminance(skyBottomColor) < 0.5;
}

export function colorTupleToCSS(rgb: unknown): string {
  if (Array.isArray(rgb) && rgb.length >= 3) {
    const [r, g, b] = rgb.map((v) => Math.round(Number(v) * 255));
    return `rgb(${r},${g},${b})`;
  }
  return 'rgb(102,128,255)';
}
