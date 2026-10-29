import { get } from 'svelte/store';
import { describe, expect, it } from 'vitest';
import { usePendingBbox } from './usePendingBbox';

const BOX = { x: 10, y: 20, width: 30, height: 40 };

describe('usePendingBbox', () => {
    it('keeps the drawn box until the created annotation is in the sample data', () => {
        const pending = usePendingBbox();

        pending.start(BOX);
        // Sample data without the new annotation must not hide the box.
        pending.sync(['other']);
        expect(get(pending.bbox)).toEqual(BOX);

        pending.created('new-annotation');
        pending.sync(['other']);
        expect(get(pending.bbox)).toEqual(BOX);

        pending.sync(['other', 'new-annotation']);
        expect(get(pending.bbox)).toBeNull();
    });

    it('hides the box on clear, for example when the creation fails', () => {
        const pending = usePendingBbox();

        pending.start(BOX);
        pending.clear();

        expect(get(pending.bbox)).toBeNull();
    });

    it('waits for the newest annotation when a second box is drawn', () => {
        const pending = usePendingBbox();
        pending.start(BOX);
        pending.created('first');

        const secondBox = { ...BOX, x: 50 };
        pending.start(secondBox);
        pending.sync(['first']);

        expect(get(pending.bbox)).toEqual(secondBox);
    });
});
