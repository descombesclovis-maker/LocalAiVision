// LocalAiWeb 3D quality policy — pure helpers, independent from Three.js and user data.
export const MODES = Object.freeze(['auto', 'quality', 'balanced', 'performance']);
export const clamp = (value, low, high) => Math.min(high, Math.max(low, value));

export function normalizeMode(value) {
  return MODES.includes(value) ? value : 'auto';
}

export function qualityProfile(mode, device = {}) {
  const mobile = Boolean(device.mobile);
  const saveData = Boolean(device.saveData);
  const memory = Number(device.deviceMemory) || 0;
  const hardware = Number(device.hardwareConcurrency) || 0;
  let selected = normalizeMode(mode);
  if (selected === 'auto') {
    selected = mobile || saveData || (memory && memory <= 4) || (hardware && hardware <= 4)
      ? 'balanced' : 'quality';
  }
  const settings = {
    quality:     {pixelRatio: 1.85, shadowSize: 2048, envSize: 192, minScale: .62, frameBudget: 21.5, realtimeShadows: true},
    balanced:    {pixelRatio: 1.45, shadowSize: 1024, envSize: 128, minScale: .65, frameBudget: 27.5, realtimeShadows: true},
    performance: {pixelRatio: 1.0,  shadowSize: 0, envSize: 64, minScale: .72, frameBudget: 39.5, realtimeShadows: false},
  }[selected];
  const ratioLimit = mobile ? (selected === 'quality' ? 1.35 : selected === 'balanced' ? 1.15 : 1) : settings.pixelRatio;
  return {
    ...settings,
    selected,
    ratioLimit,
    targetFPS: mobile ? 30 : selected === 'performance' ? 30 : 60,
  };
}

export function renderPixelRatio(profile, devicePixelRatio = 1, adaptiveScale = 1) {
  return clamp(Math.min(Number(devicePixelRatio) || 1, profile.ratioLimit) * adaptiveScale, .5, 2);
}

// Hysteresis: drop resolution sooner than restoring it, and only after sustained pressure.
export function adaptResolution(scale, averageFrameMs, frameBudgetMs, profile) {
  if (!Number.isFinite(averageFrameMs) || averageFrameMs <= 0) return scale;
  if (averageFrameMs > frameBudgetMs * 1.25) {
    return clamp(Number((scale * .86).toFixed(3)), profile.minScale, 1);
  }
  if (averageFrameMs < frameBudgetMs * .73) {
    return clamp(Number((scale + .045).toFixed(3)), profile.minScale, 1);
  }
  return scale;
}

export function lerpDamp(current, target, dt, speed = 6) {
  return current + (target - current) * (1 - Math.exp(-speed * clamp(dt, 0, .1)));
}

export function smoothstep(a, b, value) {
  const t = clamp((value - a) / Math.max(.00001, b - a), 0, 1);
  return t * t * (3 - 2 * t);
}
