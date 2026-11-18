import { describe, expect, it } from 'vitest';
import { trackGridReload } from './trackGridReload';

describe('trackGridReload', () => {
    it('returns the start time when a reload finishes', () => {
        const track = trackGridReload();

        expect(track(true, 100)).toBeNull();
        expect(track(true, 150)).toBeNull();
        expect(track(false, 200)).toBe(100);
    });

    it('returns null while idle', () => {
        const track = trackGridReload();

        expect(track(false, 100)).toBeNull();
        expect(track(false, 200)).toBeNull();
    });

    it('tracks each reload on its own', () => {
        const track = trackGridReload();
        track(true, 100);
        track(false, 200);

        expect(track(true, 300)).toBeNull();
        expect(track(false, 400)).toBe(300);
    });
});
