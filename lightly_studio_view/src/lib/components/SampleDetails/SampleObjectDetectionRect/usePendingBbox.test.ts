import { get } from 'svelte/store';
import { describe, expect, it } from 'vitest';
import { usePendingBbox } from './usePendingBbox';

const BOX_A = { x: 10, y: 20, width: 30, height: 40 };
const BOX_B = { x: 50, y: 20, width: 30, height: 40 };

const shownBoxes = (pending: ReturnType<typeof usePendingBbox>) =>
    get(pending.boxes).map((box) => box.bbox);

describe('usePendingBbox', () => {
    it('keeps the drawn box until the created annotation is in the sample data', () => {
        const pending = usePendingBbox();

        const token = pending.start(BOX_A);
        // Sample data without the new annotation must not hide the box.
        pending.sync(['other']);
        expect(shownBoxes(pending)).toEqual([BOX_A]);

        pending.created(token, 'new-annotation');
        pending.sync(['other']);
        expect(shownBoxes(pending)).toEqual([BOX_A]);

        pending.sync(['other', 'new-annotation']);
        expect(shownBoxes(pending)).toEqual([]);
    });

    it('keeps two overlapping creations apart', () => {
        const pending = usePendingBbox();
        const tokenA = pending.start(BOX_A);
        const tokenB = pending.start(BOX_B);

        pending.created(tokenA, 'a');
        expect(shownBoxes(pending)).toEqual([BOX_A, BOX_B]);
        pending.created(tokenB, 'b');

        pending.sync(['a']);
        expect(shownBoxes(pending)).toEqual([BOX_B]);
        pending.sync(['a', 'b']);
        expect(shownBoxes(pending)).toEqual([]);
    });

    it('hides only the failed box when a creation fails while another is pending', () => {
        const pending = usePendingBbox();
        const tokenA = pending.start(BOX_A);
        const tokenB = pending.start(BOX_B);

        pending.clear(tokenA);

        expect(shownBoxes(pending)).toEqual([BOX_B]);
        pending.created(tokenB, 'b');
        pending.sync(['b']);
        expect(shownBoxes(pending)).toEqual([]);
    });

    it('tells whether a newer box was started', () => {
        const pending = usePendingBbox();
        const tokenA = pending.start(BOX_A);
        expect(pending.isNewest(tokenA)).toBe(true);

        const tokenB = pending.start(BOX_B);

        expect(pending.isNewest(tokenA)).toBe(false);
        expect(pending.isNewest(tokenB)).toBe(true);
    });

    it('hides every box on clearAll, and none of them is the newest', () => {
        const pending = usePendingBbox();
        pending.start(BOX_A);
        const tokenB = pending.start(BOX_B);

        pending.clearAll();

        expect(shownBoxes(pending)).toEqual([]);
        expect(pending.isNewest(tokenB)).toBe(false);
    });
});
