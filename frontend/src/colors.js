// Impact score (0-100) -> RGB on a green -> amber -> red ramp.
export function scoreColor(score) {
  const t = Math.max(0, Math.min(100, score)) / 100;
  if (t < 0.5) {
    const u = t / 0.5; // green -> amber
    return [Math.round(46 + u * 199), Math.round(204 - u * 12), Math.round(113 - u * 105)];
  }
  const u = (t - 0.5) / 0.5; // amber -> red
  return [Math.round(245 + u * 10), Math.round(192 - u * 116), Math.round(8 + u * 30)];
}

export function scoreCss(score) {
  const [r, g, b] = scoreColor(score);
  return `rgb(${r}, ${g}, ${b})`;
}
