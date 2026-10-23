export async function request<T>(path: string, body?: unknown, method?: string): Promise<T> {
  if (!path.startsWith('/api/')) throw new Error('Destinazione API locale non autorizzata.');
  const form = body instanceof FormData;
  const response = await fetch(path, {
    method: method ?? (body === undefined ? 'GET' : 'POST'),
    headers: body !== undefined && !form ? { 'Content-Type': 'application/json' } : undefined,
    body: body === undefined ? undefined : form ? body : JSON.stringify(body),
  });
  if (!response.ok) {
    let reason = `${response.status} — ${response.statusText}`;
    try {
      const error = await response.json() as { detail?: unknown };
      if (typeof error.detail === 'string') reason = error.detail;
      else if (Array.isArray(error.detail)) reason = error.detail.map((item: { loc?: (string | number)[]; msg?: string }) => `${(item.loc ?? []).filter(part => part !== 'body').join(' → ')}: ${item.msg ?? 'Valore non valido'}`).join(' · ');
      else if (error.detail) reason = JSON.stringify(error.detail);
    } catch { /* An HTTP error can have a non-JSON body. */ }
    throw new Error(reason);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
