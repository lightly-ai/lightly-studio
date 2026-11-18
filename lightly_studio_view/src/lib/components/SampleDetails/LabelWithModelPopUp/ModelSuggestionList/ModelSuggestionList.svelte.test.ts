import { fireEvent, render, screen, within } from '@testing-library/svelte';
import { tick } from 'svelte';
import { describe, expect, it, vi } from 'vitest';
import { useModelSuggestionReview } from '$lib/components/SampleDetails/LabelWithModelOverlay/useModelSuggestionReview.svelte';
import ModelSuggestionList from './ModelSuggestionList.svelte';

vi.mock('$lib/hooks/useAnnotationLabels/useAnnotationLabels', () => ({
    useAnnotationLabels: () => ({
        data: [{ annotation_label_name: 'fox', annotation_label_id: 'fox-id' }],
        isLoading: false
    })
}));

const preview = {
    class_name: 'cat',
    score: 0.9,
    bbox: { x: 0, y: 0, width: 10, height: 10 },
    segmentation_mask: null
};
const setup = () => {
    const review = useModelSuggestionReview();
    review.replace([{ ...preview }, { ...preview, class_name: 'dog', score: 0.7 }]);
    const view = render(ModelSuggestionList, {
        collectionId: 'collection-1',
        review,
        disabled: false
    });
    return { review, ...view };
};

describe('ModelSuggestionList', () => {
    it('supports icon decisions, undo and hiding accepted suggestions without a reject-all action', async () => {
        const { review } = setup();
        const accept = screen.getByRole('button', { name: 'Accept suggestion: cat' });
        expect(accept).toHaveTextContent('');
        expect(screen.queryByRole('button', { name: 'Reject all' })).not.toBeInTheDocument();
        await fireEvent.click(accept);
        expect(screen.getByText('1 accepted · 1 pending · 0 rejected')).toBeInTheDocument();
        await fireEvent.click(screen.getByRole('button', { name: 'Undo decision: cat' }));
        await fireEvent.click(screen.getByRole('button', { name: 'Reject suggestion: cat' }));
        expect(screen.getByText('Rejected')).toBeInTheDocument();
        await fireEvent.click(screen.getByRole('button', { name: 'Accept all' }));
        expect(screen.getByText('Review complete · 2 accepted')).toBeInTheDocument();
        await fireEvent.click(screen.getByRole('checkbox', { name: 'Hide accepted on image' }));
        const picker = screen.getByRole('combobox', { name: 'Annotation class cat' });
        await fireEvent.focusIn(picker);
        expect(review.focusedId).toBe(review.suggestions[0].id);
        expect(review.isVisible(review.suggestions[0])).toBe(false);
        await fireEvent.click(screen.getByRole('button', { name: 'Show on image' }));
        expect(review.hideAccepted).toBe(false);
        expect(review.acceptedSuggestions).toHaveLength(2);
        expect(screen.queryByText(/^1\./)).not.toBeInTheDocument();
    });

    it('disables class edits and decisions while the tool is busy', async () => {
        const { review, rerender } = setup();
        await rerender({ collectionId: 'collection-1', review, disabled: true });
        expect(screen.getByRole('combobox', { name: 'Annotation class cat' })).toBeDisabled();
        expect(screen.getByRole('button', { name: 'Accept suggestion: cat' })).toBeDisabled();
        expect(screen.getByRole('button', { name: 'Reject suggestion: cat' })).toBeDisabled();
    });

    it('uses the class name as the dropdown and highlights the selected row', async () => {
        const { review } = setup();
        const picker = screen.getByRole('combobox', { name: 'Annotation class cat' });
        await fireEvent.focusIn(picker);
        await fireEvent.click(picker);
        await fireEvent.click(await screen.findByText('fox'));
        expect(
            await screen.findByRole('combobox', { name: 'Annotation class fox' })
        ).toBeInTheDocument();
        expect(review.suggestions[0].preview.class_name).toBe('fox');
        expect(review.suggestions[1].preview.class_name).toBe('dog');
        review.focus(review.suggestions[1].id);
        await tick();
        const selected = screen
            .getAllByRole('listitem')
            .find((row) => row.getAttribute('aria-current') === 'true');
        expect(
            within(selected!).getByRole('combobox', { name: 'Annotation class dog' })
        ).toBeInTheDocument();
    });
});
