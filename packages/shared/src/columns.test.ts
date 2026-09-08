import { describe, expect, it } from 'vitest';
import { DEFAULT_COLUMNS, toggleColumn } from './columns';

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
});
