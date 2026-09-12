import { childText } from './childText';
import type { ChildText, Cube, Snapshot } from './types';

export function answerCubes(snapshot: Snapshot): Cube[] {
  return snapshot.answer_order.map((id) => snapshot.cubes.find((cube) => cube.id === id)).filter((cube): cube is Cube => cube !== undefined);
}

export function inputLocked(snapshot: Snapshot, submitting: boolean): boolean {
  return submitting || !snapshot.readiness.game_flow_ready;
}

export function heartCount(snapshot: Snapshot): number {
  return Math.max(snapshot.attempts_remaining, 0);
}

export function displayCoordinate(point: { x: number; y: number }): string {
  return `(${signedCoordinate(point.x)}, ${signedCoordinate(point.y)})`;
}

function signedCoordinate(value: number): string {
  if (value === 0) return '0';
  return String(value);
}

export function usesCellSelection(mode: string | null): boolean {
  return mode === 'easy' || mode === 'beginner';
}

export function relativeLocation(point: { x: number; y: number }, text: ChildText): string {
  const parts: string[] = [];
  if (point.y) parts.push(`${Math.abs(point.y)} ${childText(text, 'directions', point.y > 0 ? 'up' : 'down')}`);
  if (point.x) parts.push(`${Math.abs(point.x)} ${childText(text, 'directions', point.x > 0 ? 'right' : 'left')}`);
  return `${parts.join(` ${childText(text, 'common', 'and')} `)} ${childText(text, 'common', 'from_origin')}`;
}
