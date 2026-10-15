import { describe, expect, it } from 'vitest';
import { getDefaultViewport } from './textAxesViewport';

describe('getDefaultViewport', () => {
    it('fits PaCMAP to the data and fixes text axes around the origin', () => {
        expect(getDefaultViewport(null)).toBeNull();
        expect(getDefaultViewport({ x: [1, 0], y: [0, 1] })).toEqual({ x: 0, y: 0, scale: 5 });
    });
});
