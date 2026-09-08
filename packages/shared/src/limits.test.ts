import { describe, expect, it } from 'vitest';
import { MAX_UPLOAD_BYTES, splitBySize } from './limits';

describe('splitBySize', () => {
  it('separates files above the upload limit from the rest', () => {
    const small = { name: 'a.cpp', size: 10 };
    const edge = { name: 'b.png', size: MAX_UPLOAD_BYTES };
    const big = { name: 'c.zip', size: MAX_UPLOAD_BYTES + 1 };
    expect(splitBySize([small, edge, big])).toEqual({ accepted: [small, edge], rejected: [big] });
  });
});
