import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import EvaluationScopeField from './EvaluationScopeFieldTestWrapper.svelte';

const tags = [
    { tag_id: 'tag-1', name: 'vehicles' },
    { tag_id: 'tag-2', name: 'night' }
];

describe('EvaluationScopeField', () => {
    it('evaluates all images when no tag is selected', () => {
        render(EvaluationScopeField, { props: { tags } });

        expect(screen.getByText('All images')).toBeInTheDocument();
        expect(screen.getByRole('checkbox', { name: 'vehicles' })).not.toBeChecked();
    });

    it('selects the images of the ticked tags', async () => {
        render(EvaluationScopeField, { props: { tags } });

        await fireEvent.click(screen.getByRole('checkbox', { name: 'night' }));

        expect(screen.getByTestId('selected-tag-ids')).toHaveTextContent('tag-2');
        expect(screen.getByText('Images with any of the selected tags')).toBeInTheDocument();
    });

    it('explains that the collection has no tags', () => {
        render(EvaluationScopeField, { props: { tags: [] } });

        expect(screen.getByText('All images. Add tags to evaluate a subset.')).toBeInTheDocument();
    });
});
