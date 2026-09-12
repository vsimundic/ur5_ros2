import { describe, expect, it } from 'vitest';
import { axisDirections } from './Board';
import { childText } from './childText';
import { answerCubes, displayCoordinate, heartCount, inputLocked, relativeLocation, usesCellSelection } from './gameView';
import { newerSnapshot, selectionIntent } from './intent';
import type { ChildText, Snapshot } from './types';

const text: ChildText = {
  common: { and: 'i', from_origin: 'od ishodišta', loading: 'Učitavanje' },
  directions: { up: 'gore', down: 'dolje', left: 'lijevo', right: 'desno' },
};
const state: Snapshot = {
  version: 2, round_id: 'round', mode: 'standard', game_state: 'WAITING_FOR_CHILD',
  board: { rows: 6, columns: 6 },
  origin: { column: 2, row: 2, rotation_deg: 0, handedness: 'right' },
  target_visual_kind: null, target_coordinate: { x: -1, y: 3 },
  cubes: [
    { id: 'red', visual_kind: 'red', symbol: '♥', column: 1, row: 1, game_coordinate: { x: -1, y: 1 }, removed: false },
    { id: 'green', visual_kind: 'green', symbol: '★', column: 2, row: 2, game_coordinate: { x: 0, y: 1 }, removed: false },
  ],
  answer_order: ['green', 'red'], selected_answer_ids: [], disabled_answer_ids: [], attempts_remaining: 3,
  readiness: { game_flow_ready: true }, motion_stage: null,
  operation: { state: 'idle', request_id: null, id: null }, recoverable_error: null,
};

describe('Kid UI state projection', () => {
  it('uses backend answer order and dynamically configured attempt count', () => {
    expect(answerCubes(state).map((cube) => cube.id)).toEqual(['green', 'red']);
    expect(heartCount(state)).toBe(3);
  });

  it('uses board cells only for Easy/Beginner and shows only negative signs', () => {
    expect(usesCellSelection('easy')).toBe(true);
    expect(usesCellSelection('beginner')).toBe(true);
    expect(usesCellSelection('spatial')).toBe(false);
    expect(usesCellSelection('standard')).toBe(false);
    expect(usesCellSelection('challenge')).toBe(false);
    expect(displayCoordinate({ x: 0, y: -0 })).toBe('(0, 0)');
    expect(displayCoordinate({ x: 2, y: -3 })).toBe('(2, -3)');
  });

  it('locks input immediately and until backend readiness returns', () => {
    expect(inputLocked(state, true)).toBe(true);
    expect(inputLocked({ ...state, readiness: { game_flow_ready: false } }, false)).toBe(true);
    expect(inputLocked(state, false)).toBe(false);
  });

  it('rejects a missing Croatian key rather than silently falling back to English', () => {
    expect(() => childText({ common: {} }, 'common', 'loading')).toThrow('Nedostaje prijevod');
  });

  it('uses backend targets and reuses an uncertain selection request id', () => {
    const createId = () => 'selection-1';
    const red = selectionIntent(null, 'red', createId);
    expect(selectionIntent(red, 'red', () => 'selection-2')).toEqual(red);
    expect(relativeLocation({ x: -1, y: 3 }, text)).toBe('3 gore i 1 lijevo od ishodišta');
  });

  it('does not show an origin in Easy/Beginner snapshots and rejects stale snapshots', () => {
    const easy = { ...state, mode: 'easy', origin: null, target_visual_kind: 'blue' as const, target_coordinate: null };
    expect(easy.origin).toBeNull();
    expect(easy.target_visual_kind).toBe('blue');
    expect(newerSnapshot(easy, { ...easy, version: 1 })).toBe(easy);
  });

  it('draws the educational origin axes with exact rotation and handedness', () => {
    expect(axisDirections(0, 'right')).toEqual({ x: { column: 1, row: 0 }, y: { column: 0, row: 1 } });
    expect(axisDirections(90, 'right')).toEqual({ x: { column: 0, row: 1 }, y: { column: -1, row: 0 } });
    expect(axisDirections(180, 'left')).toEqual({ x: { column: -1, row: 0 }, y: { column: 0, row: 1 } });
    expect(axisDirections(270, 'left')).toEqual({ x: { column: 0, row: -1 }, y: { column: -1, row: 0 } });
  });
});
