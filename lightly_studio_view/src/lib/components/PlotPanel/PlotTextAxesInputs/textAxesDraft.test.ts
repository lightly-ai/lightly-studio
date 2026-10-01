import { describe, expect, it } from 'vitest';
import { createEmptyTextAxesDraft, toTextAxes } from './textAxesDraft';

describe('toTextAxes', () => {
    it('returns trimmed text axes when all four texts are filled', () => {
        const draft = {
            xNegative: ' young ',
            xPositive: 'old',
            yNegative: 'sad',
            yPositive: 'happy '
        };

        expect(toTextAxes(draft)).toEqual({
            x: { negative: 'young', positive: 'old' },
            y: { negative: 'sad', positive: 'happy' }
        });
    });

    it('returns null when a text is empty or only whitespace', () => {
        expect(toTextAxes(createEmptyTextAxesDraft())).toBeNull();
        expect(
            toTextAxes({
                xNegative: 'young',
                xPositive: 'old',
                yNegative: '  ',
                yPositive: 'happy'
            })
        ).toBeNull();
    });
});
