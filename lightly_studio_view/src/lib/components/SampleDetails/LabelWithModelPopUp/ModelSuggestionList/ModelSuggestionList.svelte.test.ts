import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import { useModelSuggestionReview } from '$lib/components/SampleDetails/LabelWithModelOverlay/useModelSuggestionReview.svelte';
import ModelSuggestionList from './ModelSuggestionList.svelte';

vi.mock('$lib/hooks/useAnnotationLabels/useAnnotationLabels', () => ({
    useAnnotationLabels: () => ({ data: [], isLoading: false })
}));

const preview = {
    class_name: 'cat',
    score: 0.9,
    bbox: { x: 0, y: 0, width: 10, height: 10 },
    segmentation_mask: null
};

describe('ModelSuggestionList', () => {
    it('supports reversible accept and reject actions and focuses the annotation class editor', async () => {
        const review = useModelSuggestionReview();
        review.replace([preview, { ...preview, class_name: 'dog', score: 0.7 }]);
        render(ModelSuggestionList, { collectionId: 'collection-1', review, disabled: false });
        await fireEvent.click(screen.getByRole('button', { name: 'Accept suggestion 1' }));
        expect(screen.getByText('1 accepted · 1 pending · 0 rejected')).toBeInTheDocument();
        await fireEvent.click(screen.getByRole('button', { name: 'Reject all' }));
        expect(screen.getByText('0 accepted · 0 pending · 2 rejected')).toBeInTheDocument();
        await fireEvent.click(screen.getByRole('button', { name: 'Accept all' }));
        expect(screen.getByText('2 accepted · 0 pending · 0 rejected')).toBeInTheDocument();
        await fireEvent.click(screen.getByRole('button', { name: '1. cat 90%' }));
        expect(review.focusedSuggestion?.preview.class_name).toBe('cat');
        expect(screen.getByText('Annotation class')).toBeInTheDocument();
        review.changeClass('fox');
        expect(await screen.findByRole('button', { name: '1. fox 90%' })).toBeInTheDocument();
    });
});
