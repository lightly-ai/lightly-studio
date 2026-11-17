import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import { useModelSuggestionReview } from '../useModelSuggestionReview.svelte';
import ModelSuggestionBox from './ModelSuggestionBox.svelte';

const preview = {
    class_name: 'cat',
    score: 0.9,
    bbox: { x: 10, y: 10, width: 20, height: 20 },
    segmentation_mask: null
};

describe('ModelSuggestionBox', () => {
    it('resizes the review box by dragging a corner', async () => {
        const review = useModelSuggestionReview();
        review.replace([preview]);
        const suggestion = review.suggestions[0];
        render(ModelSuggestionBox, {
            suggestion,
            review,
            sample: { width: 100, height: 100 },
            scale: 1
        });
        const handle = await screen.findByRole('button', { name: 'Resize southeast corner' });
        const dragEvent = (type: string, clientX: number, clientY: number) => {
            const event = new MouseEvent(type, { bubbles: true, clientX, clientY, buttons: 1 });
            // jsdom rejects its Window proxy as a MouseEvent constructor option.
            Object.defineProperty(event, 'view', { value: window });
            return event;
        };
        await fireEvent(handle, dragEvent('mousedown', 30, 30));
        await fireEvent(window, dragEvent('mousemove', 40, 45));
        await fireEvent(window, dragEvent('mouseup', 40, 45));
        expect(suggestion.box).toEqual({ x: 10, y: 10, width: 30, height: 35 });
        expect(suggestion.preview.bbox).toEqual(preview.bbox);
    });
});
