import { describe, expect, it } from 'vitest';
import { COLUMN_KEYS, DEFAULT_COLUMNS, hideAllButName, toggleColumn } from './columns';

describe('toggleColumn', () => {
  it('flips a column and returns a new object', () => {
    const next = toggleColumn(DEFAULT_COLUMNS, 'createdAt');
    expect(next.createdAt).toBe(false);
    expect(DEFAULT_COLUMNS.createdAt).toBe(true);
    expect(toggleColumn(next, 'createdAt').createdAt).toBe(true);
  });

  it('never hides the name column', () => {
    expect(toggleColumn(DEFAULT_COLUMNS, 'name').name).toBe(true);
  });

  it('hideAllButName keeps only the name', () => {
    const v = hideAllButName();
    expect(v.name).toBe(true);
    expect(COLUMN_KEYS.filter((k) => k !== 'name').every((k) => v[k] === false)).toBe(true);
  });
});
