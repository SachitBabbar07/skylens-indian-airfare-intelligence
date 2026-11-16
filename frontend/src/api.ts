export async function api<T>(path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
  const unavailable = 'The SkyLens server is unavailable. Start the local backend and retry.';
  let response: Response;
  try {
    response = await fetch(path, {signal: signal ?? AbortSignal.timeout(15_000),
      ...(body === undefined ? {} : {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)})});
  } catch {
    throw new Error(unavailable);
  }
  const data = await response.json().catch(() => null);
  if (!response.ok || data === null) {
    const detail = data?.detail;
    throw new Error(typeof detail === 'string' ? detail : typeof detail?.message === 'string' ? detail.message :
      Array.isArray(detail) ? detail.map((v: {msg: string}) => v.msg).join(' ') : unavailable);
  }
  return data;
}
