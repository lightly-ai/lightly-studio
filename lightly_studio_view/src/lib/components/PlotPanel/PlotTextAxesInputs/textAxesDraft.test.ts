import { describe, expect, it } from 'vitest';
import { toCornerMarkers } from './textAxesDraft';

describe('toCornerMarkers', () => {
    it('combines each x text with each y text, bottom row first', () => {
        const markers = toCornerMarkers({
            x: { negative: 'young', positive: 'old' },
            y: { negative: 'sad', positive: 'happy' }
        });

        expect(markers).toEqual([
            { label: 'young + sad', text: 'young sad' },
            { label: 'old + sad', text: 'old sad' },
            { label: 'young + happy', text: 'young happy' },
            { label: 'old + happy', text: 'old happy' }
        ]);
    });

    it('returns each marker once when an axis has the same text twice', () => {
        const markers = toCornerMarkers({
            x: { negative: 'dog', positive: 'dog' },
            y: { negative: 'sad', positive: 'happy' }
        });

        expect(markers).toEqual([
            { label: 'dog + sad', text: 'dog sad' },
            { label: 'dog + happy', text: 'dog happy' }
        ]);
    });
});
