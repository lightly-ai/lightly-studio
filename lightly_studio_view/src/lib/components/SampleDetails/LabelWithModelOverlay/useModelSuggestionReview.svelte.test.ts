import { describe, expect, it } from 'vitest';
import { getSuggestionPreview, useModelSuggestionReview } from './useModelSuggestionReview.svelte';

const preview = {
    class_name: 'cat',
    score: 0.9,
    bbox: { x: 10, y: 10, width: 20, height: 20 },
    segmentation_mask: null
};

describe('model suggestion review', () => {
    it('starts pending, records reversible decisions, and does not warn for rejected results', () => {
        const review = useModelSuggestionReview();
        review.replace([preview]);
        const id = review.suggestions[0].id;
        expect(review.pendingCount).toBe(1);
        expect(review.acceptedSuggestions).toHaveLength(0);
        review.accept(id);
        expect(review.acceptedSuggestions).toHaveLength(1);
        review.reject(id);
        expect(review.hasUnsavedSuggestions).toBe(false);
        review.accept(id);
        expect(review.hasUnsavedSuggestions).toBe(true);
    });

    it('hides reviewed boxes without changing decisions and resets visibility for new results', () => {
        const review = useModelSuggestionReview();
        review.replace([preview, { ...preview, class_name: 'dog' }]);
        const [accepted, rejected] = review.suggestions;
        review.accept(accepted.id);
        review.reject(rejected.id);
        expect(review.isVisible(rejected)).toBe(false);
        review.setHideAccepted(true);
        expect(review.isVisible(accepted)).toBe(false);
        expect(review.acceptedSuggestions).toHaveLength(1);
        review.undo(rejected.id);
        expect(review.isVisible(rejected)).toBe(true);
        review.replace([preview]);
        expect(review.hideAccepted).toBe(false);
    });

    it('changes the requested class independently of focus and preserves review state and geometry', () => {
        const review = useModelSuggestionReview();
        review.replace([{ ...preview }, { ...preview }]);
        const [first, second] = review.suggestions;
        review.accept(first.id);
        review.focus(second.id);
        review.changeClass(first.id, 'fox');
        expect(first.preview.class_name).toBe('fox');
        expect(second.preview.class_name).toBe('cat');
        expect(first.status).toBe('accepted');
        expect(first.box).toEqual(preview.bbox);
    });

    it('clamps edited boxes to image bounds and keeps segmentation geometry unchanged', () => {
        const review = useModelSuggestionReview();
        review.replace([{ ...preview, segmentation_mask: [0, 1] }]);
        const suggestion = review.suggestions[0];
        review.updateBox(
            suggestion.id,
            { x: -10, y: 90, width: 200, height: 30 },
            { width: 100, height: 100 }
        );
        expect(getSuggestionPreview(suggestion, 'box').bbox).toEqual({
            x: 0,
            y: 90,
            width: 100,
            height: 10
        });
        expect(getSuggestionPreview(suggestion, 'mask').bbox).toEqual(preview.bbox);
        review.updateBox(
            suggestion.id,
            { x: 120, y: 130, width: -10, height: 0 },
            { width: 100, height: 100 }
        );
        expect(suggestion.box).toEqual({ x: 99, y: 99, width: 1, height: 1 });
    });
});
