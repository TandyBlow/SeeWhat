import { ensureContrastAgainstWhite, ensureContrastAgainstDark, isSkyDark, colorTupleToCSS } from './styleColor';

export function resetParamsToDOM() {
  const el = document.documentElement;
  el.style.removeProperty('--color-primary');
  el.style.removeProperty('--color-hint');
  el.style.removeProperty('--color-primary-on-light');
  el.style.removeProperty('--color-hint-on-light');
  el.style.removeProperty('--color-primary-on-dark');
  el.style.removeProperty('--color-hint-on-dark');
  el.style.removeProperty('--color-glass-border');
  el.style.removeProperty('--color-glass-bg');
  el.style.removeProperty('--shadow-inset-a');
  el.style.removeProperty('--shadow-inset-b');
  el.style.removeProperty('--shadow-raised-a');
  el.style.removeProperty('--shadow-raised-b');
  el.style.removeProperty('--bg-gradient');
  document.body.style.background = 'linear-gradient(180deg, #ffffff 0%, #eefaff 20%, #bfefff 55%, #66ccff 100%)';
  el.setAttribute('data-theme-brightness', 'light');
}

export function applyParamsToDOM(params: Record<string, unknown>) {
  const el = document.documentElement;
  const leafMid = Array.isArray(params.leafMidColor) ? params.leafMidColor as number[] : [0.4, 0.5, 0.4];
  const leafLight = Array.isArray(params.leafLightColor) ? params.leafLightColor as number[] : [0.6, 0.7, 0.5];
  const textPrimary = Array.isArray(params.textPrimaryColor) ? params.textPrimaryColor as number[] : leafMid;
  const textHint = Array.isArray(params.textHintColor) ? params.textHintColor as number[] : leafLight;
  const skyBottom = Array.isArray(params.skyBottomColor) ? params.skyBottomColor as number[] : [0.9, 0.9, 0.9];

  const primary = colorTupleToCSS(textPrimary);
  const hint = colorTupleToCSS(textHint);
  const glassBorderRgb = textPrimary.map((v) => Math.round(v * 255));
  const skyBottomRgb = skyBottom.map((v) => Math.round(v * 255));

  el.style.setProperty('--color-primary', primary);
  el.style.setProperty('--color-hint', hint);
  el.style.setProperty('--color-glass-border', `rgba(${glassBorderRgb.join(',')},0.28)`);
  el.style.setProperty('--color-glass-bg', `rgba(${glassBorderRgb.join(',')},0.12)`);
  el.style.setProperty('--shadow-inset-a', `rgba(${glassBorderRgb.map((v) => Math.round(v * 0.4)).join(',')},0.56)`);
  el.style.setProperty('--shadow-inset-b', `rgba(${glassBorderRgb.map((v) => Math.round(v * 0.8 + 60)).join(',')},0.52)`);
  el.style.setProperty('--shadow-raised-a', `rgba(${glassBorderRgb.join(',')},0.14)`);
  el.style.setProperty('--shadow-raised-b', 'rgba(255,255,255,0.28)');
  el.style.setProperty(
    '--bg-gradient',
    `linear-gradient(180deg, #ffffff 0%, rgb(${skyBottom.map((v) => Math.round(255 - (255 - v * 255) * 0.36)).join(',')}) 20%, rgb(${skyBottomRgb.join(',')}) 55%, rgb(${skyBottomRgb.join(',')}) 100%)`,
  );
  document.body.style.background = `linear-gradient(180deg, #ffffff 0%, rgb(${skyBottom.map((v) => Math.round(255 - (255 - v * 255) * 0.36)).join(',')}) 20%, rgb(${skyBottomRgb.join(',')}) 55%, rgb(${skyBottomRgb.join(',')}) 100%)`;

  // WCAG contrast correction
  const primaryOnLight = ensureContrastAgainstWhite(textPrimary);
  const hintOnLight = ensureContrastAgainstWhite(textHint);
  el.style.setProperty('--color-primary-on-light', colorTupleToCSS(primaryOnLight));
  el.style.setProperty('--color-hint-on-light', colorTupleToCSS(hintOnLight));
  const primaryOnDark = ensureContrastAgainstDark(textPrimary);
  const hintOnDark = ensureContrastAgainstDark(textHint);
  el.style.setProperty('--color-primary-on-dark', colorTupleToCSS(primaryOnDark));
  el.style.setProperty('--color-hint-on-dark', colorTupleToCSS(hintOnDark));
  el.setAttribute('data-theme-brightness', isSkyDark(skyBottom) ? 'dark' : 'light');
}

export function applyThemeToDOM(styleValue: string, params: Record<string, unknown> | null): void {
  if (params && styleValue !== 'default') {
    applyParamsToDOM(params);
  } else {
    resetParamsToDOM();
  }
}
