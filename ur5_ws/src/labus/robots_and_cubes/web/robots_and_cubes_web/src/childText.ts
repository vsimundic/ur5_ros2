import type { ChildText } from './types';

export function childText(text: ChildText, section: string, key: string): string {
  const value = text[section];
  if (typeof value !== 'object' || typeof value[key] !== 'string') {
    throw new Error(`Nedostaje prijevod ${section}.${key}`);
  }
  return value[key];
}
