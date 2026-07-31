export function paramsEqual(a: Record<string, unknown> | null, b: Record<string, unknown> | null): boolean {
  if (a === b) return true;
  if (!a || !b) return false;
  const keysA = Object.keys(a).filter(k => k !== '_cached_at');
  const keysB = Object.keys(b).filter(k => k !== '_cached_at');
  if (keysA.length !== keysB.length) return false;
  for (const key of keysA) {
    const va = a[key];
    const vb = b[key];
    if (Array.isArray(va) && Array.isArray(vb)) {
      if (va.length !== vb.length || va.some((v, i) => Number(v).toFixed(4) !== Number(vb[i]).toFixed(4))) return false;
    } else if (typeof va === 'number' && typeof vb === 'number') {
      if (Number(va).toFixed(4) !== Number(vb).toFixed(4)) return false;
    } else if (va !== vb) {
      return false;
    }
  }
  return true;
}

export function preloadImage(url: string): Promise<boolean> {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => resolve(true);
    img.onerror = () => resolve(false);
    img.src = url;
  });
}

export async function tryRecoverBgUrl(userId: string): Promise<string | null> {
  const fallbackUrl = `/api/backgrounds/ai/${userId}.png`;
  const ok = await preloadImage(fallbackUrl);
  return ok ? fallbackUrl : null;
}
