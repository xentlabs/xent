export function parseModelSpec(spec: string): { model: string; params: Record<string, any> } {
  if (!spec) return { model: '', params: {} };

  const qIndex = spec.indexOf('?');
  if (qIndex === -1) return { model: spec, params: {} };

  const base = spec.slice(0, qIndex);
  const query = spec.slice(qIndex + 1);

  const params: Record<string, any> = {};
  const usp = new URLSearchParams(query);
  for (const [key, value] of usp.entries()) {
    if (!(key in params)) {
      // Only take first value per key to match CLI behavior
      let parsed: any = value;
      try {
        parsed = JSON.parse(value);
      } catch (_) {
        // keep as string if not JSON
      }
      params[key] = parsed;
    }
  }

  return { model: base, params };
}

