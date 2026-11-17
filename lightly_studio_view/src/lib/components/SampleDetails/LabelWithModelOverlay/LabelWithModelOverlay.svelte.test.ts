import { fireEvent, render, screen } from '@testing-library/svelte';
import { tick } from 'svelte';
import { describe, expect, it } from 'vitest';
import LabelWithModelOverlay from './LabelWithModelOverlay.svelte';
import { useModelSuggestionReview } from './useModelSuggestionReview.svelte';

const preview = {
    class_name: 'cat',
    score: 0.9,
    bbox: { x: 10, y: 10, width: 100, height: 100 },
    segmentation_mask: null
};

describe('model suggestion visibility', () => {
    it('renders accepted boxes in blue and removes hidden boxes, tags, and resize controls', async () => {
        const review = useModelSuggestionReview();
        review.replace([preview, { ...preview, class_name: 'dog' }]);
        const { container } = render(LabelWithModelOverlay, {
            sample: { width: 500, height: 500 },
            scale: 1,
            saveAs: 'box',
            labelWithModel: { review, isSaving: false, isGenerating: false }
        });
        const pendingBox = container.querySelector('[data-testid="annotation-preview"] rect');
        expect(pendingBox).toHaveAttribute('stroke-dasharray', '6 5');
        review.accept(review.suggestions[0].id);
        await tick();
        expect(pendingBox).toHaveAttribute('stroke', '#60a5fa');
        expect(pendingBox).toHaveAttribute('stroke-dasharray', '');
        await fireEvent.click(screen.getByRole('button', { name: 'Review suggestion 1: cat' }));
        expect(
            await screen.findByRole('button', { name: 'Resize northwest corner' })
        ).toBeInTheDocument();
        review.setHideAccepted(true);
        review.reject(review.suggestions[1].id);
        await tick();
        expect(screen.queryByRole('button')).not.toBeInTheDocument();
        expect(container.querySelector('[data-testid="annotation-preview"]')).toBeNull();
        expect(container.querySelector('[data-testid="preview-class-tag"]')).toBeNull();
        review.setHideAccepted(false);
        await tick();
        expect(
            screen.getByRole('button', { name: 'Review suggestion 1: cat' })
        ).toBeInTheDocument();
        expect(
            screen.queryByRole('button', { name: 'Review suggestion 2: dog' })
        ).not.toBeInTheDocument();
    });
});
