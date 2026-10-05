import { useRef, type ButtonHTMLAttributes, type PointerEvent, type TouchEvent } from 'react';

type TouchButtonProps = Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'onClick'> & {
  onActivate: () => void;
};

const SYNTHETIC_CLICK_SUPPRESSION_MS = 750;

export function suppressesSyntheticClick(clickAt: number, suppressClickUntil: number) {
  return clickAt < suppressClickUntil;
}

export function TouchButton({ onActivate, ...props }: TouchButtonProps) {
  const suppressClickUntil = useRef(0);
  const activateTouch = () => {
    suppressClickUntil.current = performance.now() + SYNTHETIC_CLICK_SUPPRESSION_MS;
    onActivate();
  };
  const activatePointerTouch = (event: PointerEvent<HTMLButtonElement>) => {
    if (event.pointerType !== 'touch') return;
    event.preventDefault();
    if (suppressesSyntheticClick(performance.now(), suppressClickUntil.current)) return;
    activateTouch();
  };
  const activateTouchEnd = (event: TouchEvent<HTMLButtonElement>) => {
    event.preventDefault();
    if (suppressesSyntheticClick(performance.now(), suppressClickUntil.current)) return;
    activateTouch();
  };
  const activateClick = () => {
    if (suppressesSyntheticClick(performance.now(), suppressClickUntil.current)) return;
    onActivate();
  };
  return <button {...props} onPointerUp={activatePointerTouch} onTouchEnd={activateTouchEnd} onClick={activateClick}/>;
}
