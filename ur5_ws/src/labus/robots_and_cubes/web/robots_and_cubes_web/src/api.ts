import type { ChildText, Snapshot } from './types';

export const requestId = () => crypto.randomUUID();
let operatorToken = '';

export function setOperatorToken(token: string) { operatorToken = token; }

export async function api<T>(path: string, body?: unknown, operator = false): Promise<T> {
  const headers: Record<string, string> = body === undefined ? {} : { 'Content-Type': 'application/json' };
  if (operator && operatorToken) headers.Authorization = `Bearer ${operatorToken}`;
  const response = await fetch(path, body === undefined ? { headers } : { method: 'POST', headers, body: JSON.stringify(body) });
  if (!response.ok) throw new Error(await response.text());
  return response.json() as Promise<T>;
}

export const getState = () => api<Snapshot>('/api/state');
export const getChildText = () => api<ChildText>('/api/kid/text');
export const verifyOperatorSession = () => api<{ authorized: boolean }>('/api/operator/session', undefined, true);
export const getOperatorCalibration = () => api('/api/calibration', undefined, true);
export const getOperatorTeaching = () => api('/api/teaching', undefined, true);

export function stateSocket(onSnapshot: (snapshot: Snapshot) => void): () => void {
  const socket = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/api/ws`);
  socket.onmessage = (event) => { const payload = JSON.parse(event.data) as { type: string; snapshot: Snapshot }; if (payload.type === 'snapshot') onSnapshot(payload.snapshot); };
  return () => socket.close();
}
