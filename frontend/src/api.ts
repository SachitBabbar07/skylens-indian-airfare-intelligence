export class ApiError extends Error {
  constructor(message: string, public readonly status: number, public readonly code?: string,
    public readonly retryable?: boolean) {
    super(message);
  }
}

export async function api<T>(path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
  const unavailable = 'The SkyLens server is unavailable. Start the local backend and retry.';
  let response: Response;
  try {
    response = await fetch(path, {signal: signal ?? AbortSignal.timeout(15_000),
      ...(body === undefined ? {} : {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)})});
  } catch {
    throw new ApiError(unavailable, 0);
  }
  const data = await response.json().catch(() => null);
  if (!response.ok || data === null) {
    const detail = data?.detail;
    const validation = Array.isArray(detail)
      ? detail.flatMap(issue => typeof issue?.msg === 'string' ? [issue.msg.replace(/^Value error, /, '')] : []).join(' ')
      : '';
    const message = typeof detail === 'string' ? detail : typeof detail?.message === 'string' ? detail.message :
      validation || unavailable;
    throw new ApiError(message, response.status, typeof detail?.code === 'string' ? detail.code : undefined,
      typeof detail?.retryable === 'boolean' ? detail.retryable : undefined);
  }
  return data;
}
