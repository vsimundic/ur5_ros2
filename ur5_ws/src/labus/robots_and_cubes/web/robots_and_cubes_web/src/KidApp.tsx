import { useEffect, useMemo, useRef, useState } from 'react';

import { api, getChildText, getState, requestId, stateSocket } from './api';
import { Board } from './Board';
import { childText } from './childText';
import { answerCubes, displayCoordinate, heartCount, inputLocked, relativeLocation, usesCellSelection } from './gameView';
import { newerSnapshot, selectionIntent, type PendingSelection } from './intent';
import type { ChildText, Cube, Snapshot } from './types';

const shapeSymbols: Record<string, string> = {
  green: '★', blue: '●', red: '♥', black: '▲', white: '☾',
};

export function KidApp() {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [text, setText] = useState<ChildText | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const pendingSelection = useRef<PendingSelection | null>(null);

  useEffect(() => {
    void Promise.all([getState(), getChildText()]).then(([state, copy]) => {
      setSnapshot((current) => newerSnapshot(current, state));
      setText(copy);
    });
    return stateSocket((incoming) => setSnapshot((current) => newerSnapshot(current, incoming)));
  }, []);

  const answers = useMemo(() => snapshot ? answerCubes(snapshot) : [], [snapshot]);
  if (!snapshot || !text) return <main className="kid"><p aria-busy="true">…</p></main>;

  const locked = inputLocked(snapshot, submitting);
  const cellSelection = usesCellSelection(snapshot.mode);
  const targetKind = snapshot.target_visual_kind;
  const targetPiece = targetKind ? { visual_kind: targetKind, symbol: shapeSymbols[targetKind] } : null;
  const showWrongHint = snapshot.game_state === 'WAITING_FOR_CHILD'
    && snapshot.disabled_answer_ids.length > 0 && snapshot.attempts_remaining > 0;

  const submit = async (cubeId: string) => {
    if (locked || !snapshot.round_id) return;
    const intent = selectionIntent(pendingSelection.current, cubeId, requestId);
    pendingSelection.current = intent;
    setSubmitting(true);
    try {
      await api('/api/rounds/selections', {
        request_id: intent.requestId, round_id: snapshot.round_id, cube_id: cubeId,
      });
      pendingSelection.current = null;
    } finally {
      setSubmitting(false);
    }
  };

  return <main className="kid">
    <header className="kid-header">
      <h1>{text.title as string}</h1>
      <div className="lives" aria-label={`${childText(text, 'common', 'attempts')}: ${heartCount(snapshot)}`}>
        <span>{childText(text, 'common', 'attempts')}</span>
        <span className="hearts">{Array.from({ length: heartCount(snapshot) }, () => '♥').join(' ')}</span>
      </div>
    </header>
    <Board
      snapshot={snapshot}
      interactive={cellSelection}
      disabled={locked}
      onCubeSelect={(cubeId) => void submit(cubeId)}
    />
    {snapshot.game_state === 'SUCCESS' ? <Result text={text} success />
      : snapshot.game_state === 'FAILED' ? <Result text={text} snapshot={snapshot} target={targetPiece} />
        : snapshot.recoverable_error ? <section className="result"><p>{childText(text, 'error', 'placeholder')}</p></section>
          : <section className="question">
            <h2>{locked ? childText(text, 'motion', 'waiting') : childText(text, snapshot.mode ?? 'standard', 'instruction')}</h2>
            {!locked && <Task text={text} snapshot={snapshot} target={targetPiece}/>} 
            {!locked && <p className="action-prompt">{childText(text, 'common', cellSelection ? 'choose_cell' : 'choose_piece')}</p>}
            {showWrongHint && <p className="wrong-hint">{childText(text, 'wrong', 'one_left')}</p>}
            {!cellSelection && <div className="answers">
              {answers.map((cube) => <Answer
                key={cube.id} cube={cube} mode={snapshot.mode}
                disabled={locked || snapshot.disabled_answer_ids.includes(cube.id)}
                text={text} onClick={() => void submit(cube.id)}
              />)}
            </div>}
          </section>}
  </main>;
}

function Task({ text, snapshot, target }: { text: ChildText; snapshot: Snapshot; target: { visual_kind: string; symbol: string } | null }) {
  if ((snapshot.mode === 'easy' || snapshot.mode === 'beginner' || snapshot.mode === 'challenge') && target) {
    return <p className="target-piece">
      {childText(text, snapshot.mode, 'target_prefix')}: {' '}
      {snapshot.mode === 'easy'
        ? <strong>{childText(text, 'colours', target.visual_kind)}</strong>
        : snapshot.mode === 'beginner'
          ? <strong>{childText(text, 'shapes', target.visual_kind)}</strong>
        : <strong className={snapshot.mode === 'challenge' ? `shape-target ${target.visual_kind}` : 'shape-target'}>{target.symbol}</strong>}
    </p>;
  }
  if (snapshot.mode === 'spatial' && snapshot.target_coordinate) {
    return <p className="target-location">
      {childText(text, 'spatial', 'target_prefix')}: <strong>{relativeLocation(snapshot.target_coordinate, text)}</strong>
    </p>;
  }
  return null;
}

function Answer({ cube, mode, disabled, text, onClick }: { cube: Cube; mode: string | null; disabled: boolean; text: ChildText; onClick: () => void }) {
  if (mode === 'standard' || mode === 'challenge') {
    return <button disabled={disabled} onClick={onClick}>
      <span className="answer-label">{childText(text, 'common', 'coordinate')}</span>
      <strong>{displayCoordinate(cube.game_coordinate)}</strong>
    </button>;
  }
  const label = mode === 'easy' ? childText(text, 'colours', cube.visual_kind) : cube.symbol;
  return <button disabled={disabled} onClick={onClick} className={mode === 'easy' ? `answer-colour ${cube.visual_kind}` : ''}>
    <strong>{label}</strong>
  </button>;
}

function Result({ text, snapshot, target, success = false }: { text: ChildText; snapshot?: Snapshot; target?: { visual_kind: string; symbol: string } | null; success?: boolean }) {
  if (success) return <section className="result success"><div className="result-icon" aria-hidden="true">★</div><h2>{childText(text, 'success', 'title')}</h2><p>{childText(text, 'success', 'text')}</p></section>;
  const isEasy = snapshot?.mode === 'easy';
  const coordinateAnswer = snapshot?.mode === 'standard' || snapshot?.mode === 'challenge';
  return <section className="result failure"><div className="result-icon loss-icon" aria-hidden="true">☹</div><h2>{childText(text, 'failure', 'title')}</h2><p className="loss-message">{childText(text, 'failure', 'lost')}</p>{coordinateAnswer && snapshot?.target_coordinate ? <p>{childText(text, 'failure', 'answer_prefix')}: {displayCoordinate(snapshot.target_coordinate)}</p> : target && <p>{childText(text, 'failure', 'answer_prefix')}: {' '}{isEasy ? childText(text, 'colours', target.visual_kind) : snapshot?.mode === 'beginner' ? childText(text, 'shapes', target.visual_kind) : target.symbol}</p>}</section>;
}
