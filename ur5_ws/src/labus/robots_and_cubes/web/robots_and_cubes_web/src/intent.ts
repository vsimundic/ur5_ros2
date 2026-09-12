export type PendingSelection = { cubeId: string; requestId: string };

export function selectionIntent(
  pending: PendingSelection | null,
  cubeId: string,
  createId: () => string,
): PendingSelection {
  return pending?.cubeId === cubeId ? pending : { cubeId, requestId: createId() };
}

export function newerSnapshot<T extends { version: number }>(
  current: T | null,
  incoming: T,
): T {
  return current === null || incoming.version >= current.version ? incoming : current;
}
