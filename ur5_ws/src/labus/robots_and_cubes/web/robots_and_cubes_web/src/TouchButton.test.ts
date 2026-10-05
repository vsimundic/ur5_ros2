import { describe, expect, it } from 'vitest';

import { suppressesSyntheticClick } from './TouchButton';

describe('tablet activation timing', () => {
  it('suppresses the click synthesized immediately after a touch activation', () => {
    expect(suppressesSyntheticClick(1001, 1750)).toBe(true);
  });

  it('does not suppress a later independent click', () => {
    expect(suppressesSyntheticClick(1750, 1750)).toBe(false);
  });
});
